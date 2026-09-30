"""
Datamuse client
===============
Keyless public API. https://www.datamuse.com/api/

Supported ops (subset):
    ml      means-like          "words with similar meaning to X"
    rel_syn synonyms
    rel_ant antonyms
    rel_trg triggered-by
    rel_jja adjectives describing X
    rel_jjb adjectives describing X
    sp      spelled-like
    sl      sounds-like
    sug     prefix suggestions
"""
from __future__ import annotations
import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


BASE = "https://api.datamuse.com/words"

OPS = {
    "ml", "rel_syn", "rel_ant", "rel_trg",
    "rel_jja", "rel_jjb", "rel_bga", "rel_bgb",
    "sp", "sl", "sug",
}


def fetch_datamuse(
    query: str,
    *,
    op: str = "ml",
    max_results: int = 10,
    timeout_s: int = 15,
    metadata: bool = True,
) -> Dict[str, Any]:
    """
    Query Datamuse. Returns:
        {"ok": bool, "op": str, "query": str, "results": [...], "error": str|None}
    """
    q = (query or "").strip()
    if not q:
        return {"ok": False, "op": op, "query": q, "results": [],
                "error": "empty query"}
    if op not in OPS:
        return {"ok": False, "op": op, "query": q, "results": [],
                "error": f"unsupported op; use one of {sorted(OPS)}"}

    params = {op: q, "max": str(max(1, min(100, int(max_results or 10))))}
    if metadata:
        params["md"] = "dp"   # definitions + parts of speech
    url = BASE + "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            body = r.read().decode("utf-8", errors="replace")
        data = json.loads(body) if body else []
        if not isinstance(data, list):
            data = []
        return {"ok": True, "op": op, "query": q, "results": data[:max_results],
                "error": None, "url": url}
    except Exception as e:
        return {"ok": False, "op": op, "query": q, "results": [],
                "error": f"{type(e).__name__}: {e}", "url": url}


def word_relations(word: str, *, max_results: int = 10) -> Dict[str, Any]:
    """Convenience: gather syn/ant/ml for a single word."""
    out: Dict[str, Any] = {"word": word, "synonyms": [], "antonyms": [],
                            "similar": [], "errors": []}
    for key, op in (("synonyms", "rel_syn"),
                    ("antonyms", "rel_ant"),
                    ("similar",  "ml")):
        r = fetch_datamuse(word, op=op, max_results=max_results)
        if r["ok"]:
            out[key] = [x.get("word") for x in r["results"] if x.get("word")]
        else:
            out["errors"].append(f"{op}: {r['error']}")
    return out
