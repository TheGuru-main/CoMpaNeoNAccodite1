"""
Train pipeline for ONE owner grid (user or org).

    crawl external  ->  seed into grid  ->  train from grid  ->  save

Every step gets the owner's grid path and nothing else. The platform grid is
never an argument, and OwnerRef cannot represent the platform, so background
training cannot reach it by construction.

Per run, under instances/<kind>/<id>/runs/<run_id>/:
    before.pkl        copy of the grid before the run (local rollback)
    crawled.json      docs fetched from external sources (url, text, meta)
    seeded.json       doc ids written into the grid, plus their source urls
    train.json        training report
    run.json          manifest: status, steps, paths, seeded doc ids

On success the grid snapshot goes to B2 (snapshots/...) and the manifest to
B2 (workflows/train/...). Weights are never uploaded.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from memory.artifact_policy import check_b2_key, sha256_file
from memory.instance_grid import (
    GRID_NAME,
    InstanceGridError,
    OwnerRef,
    grid_path,
    instance_dir,
    snapshot_instance_grid,
)

CrawlFn = Callable[[List[str]], List[dict]]                 # sources -> docs
SeedFn = Callable[[str, List[dict]], List[str]]             # (grid_path, docs) -> seeded doc ids
TrainFn = Callable[[str], dict]                             # grid_path -> report
UploadFn = Callable[[str, str], None]                       # (b2_key, local_path)
PublishAdapterFn = Callable[[OwnerRef, str], dict]          # (owner, adapter_file) -> version record


class PipelineError(RuntimeError):
    pass


def _write_json(path: Path, obj) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _check_owner_path(owner: OwnerRef, path: Path, base: Optional[str]) -> None:
    root = instance_dir(owner, base).resolve()
    if root not in Path(path).resolve().parents:
        raise PipelineError("step tried to touch a file outside the owner's grid")


def run_train_pipeline(
    owner: OwnerRef,
    *,
    sources: List[str],
    crawl: CrawlFn,
    seed: SeedFn,
    train: TrainFn,
    upload: UploadFn,
    publish_adapter: Optional[PublishAdapterFn] = None,
    base: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict:
    if not isinstance(owner, OwnerRef):
        raise PipelineError("pipeline runs on an OwnerRef (user or org) only")
    grid = grid_path(owner, base)
    if not grid.is_file():
        raise PipelineError(f"{owner.key} has no grid; create it at signup first")

    run_id = run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_dir = instance_dir(owner, base) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "owner": owner.key,
        "run_id": run_id,
        "sources": list(sources),
        "status": "running",
        "steps": [],
        "paths": {},
        "seeded_doc_ids": [],
        "snapshot_key": None,
        "workflow_key": None,
    }

    def step(name: str, status: str, detail: str = "") -> None:
        manifest["steps"].append({"name": name, "status": status, "detail": detail, "at": int(time.time())})
        _write_json(run_dir / "run.json", manifest)

    # 0. rollback point, local only
    before = run_dir / "before.pkl"
    shutil.copyfile(grid, before)
    manifest["paths"]["before"] = str(before)
    step("snapshot_before", "ok")

    # 1. crawl external sources (no grid access)
    try:
        docs = crawl(list(sources))
    except Exception as e:
        step("crawl", "failed", f"{type(e).__name__}: {e}")
        manifest["status"] = "failed"
        _write_json(run_dir / "run.json", manifest)
        return manifest
    crawled = run_dir / "crawled.json"
    _write_json(crawled, docs)
    manifest["paths"]["crawled"] = str(crawled)
    step("crawl", "ok", f"{len(docs)} docs")

    # 2. seed into the owner's grid
    try:
        _check_owner_path(owner, grid, base)
        seeded_ids = seed(str(grid), docs)
    except Exception as e:
        shutil.copyfile(before, grid)
        step("seed", "failed", f"{type(e).__name__}: {e}; grid rolled back")
        manifest["status"] = "failed"
        _write_json(run_dir / "run.json", manifest)
        return manifest
    seeded = run_dir / "seeded.json"
    seeded_index = [{"doc_id": did, "url": d.get("url")} for did, d in zip(seeded_ids, docs)]
    _write_json(seeded, seeded_index)
    manifest["seeded_doc_ids"] = list(seeded_ids)
    manifest["paths"]["seeded"] = str(seeded)
    step("seed", "ok", f"{len(seeded_ids)} docs seeded")

    # 3. train from the owner's grid
    try:
        _check_owner_path(owner, grid, base)
        report = train(str(grid))
    except Exception as e:
        # roll the grid back to the pre-run copy so a failed train leaves no partial state
        shutil.copyfile(before, grid)
        step("train", "failed", f"{type(e).__name__}: {e}; grid rolled back")
        manifest["status"] = "failed"
        _write_json(run_dir / "run.json", manifest)
        return manifest
    report_path = run_dir / "train.json"
    _write_json(report_path, report if isinstance(report, dict) else {"report": str(report)})
    manifest["paths"]["train_report"] = str(report_path)
    step("train", "ok")

    # 3b. publish the owner's new LoRA adapter (Hugging Face, not B2)
    adapter_file = report.get("adapter_path") if isinstance(report, dict) else None
    if adapter_file and publish_adapter is not None:
        try:
            rec = publish_adapter(owner, adapter_file)
        except Exception as e:
            shutil.copyfile(before, grid)
            step("publish_adapter", "failed", f"{type(e).__name__}: {e}; grid rolled back")
            manifest["status"] = "failed"
            _write_json(run_dir / "run.json", manifest)
            return manifest
        manifest["adapter"] = {"version": rec.get("sha256_raw"), "hf_path": rec.get("hf_path")}
        step("publish_adapter", "ok", rec.get("hf_path") or "")

    # 4. save: grid snapshot to B2 + manifest to B2 workflows
    key = snapshot_instance_grid(owner, uploader=upload, base=base)
    manifest["snapshot_key"] = key
    wf_key = check_b2_key(f"workflows/train/{owner.kind}/{owner.id}/{run_id}.json")
    manifest["grid_sha256"] = sha256_file(grid)
    manifest["workflow_key"] = wf_key
    manifest["status"] = "ok"
    _write_json(run_dir / "run.json", manifest)
    upload(wf_key, str(run_dir / "run.json"))
    step("save", "ok", key)
    return manifest
