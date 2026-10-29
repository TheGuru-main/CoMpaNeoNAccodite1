"""
Backblaze B2 via S3-compatible API (boto3).

Env:
  B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET, B2_ENDPOINT
  B2_REGION (optional), ACCD_B2_PREFIX (default accodite)
"""
from __future__ import annotations

import json
import os
from typing import Any

_client = None
_warned = False


def b2_enabled() -> bool:
    return bool(
        os.environ.get("B2_KEY_ID")
        and os.environ.get("B2_APPLICATION_KEY")
        and os.environ.get("B2_BUCKET")
        and os.environ.get("B2_ENDPOINT")
    )


def _prefix() -> str:
    return (os.environ.get("ACCD_B2_PREFIX") or "accodite").strip().strip("/")


def _bucket() -> str:
    return os.environ["B2_BUCKET"]


def _get_client():
    global _client, _warned
    if not b2_enabled():
        if not _warned:
            print("[b2] disabled — set B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET, B2_ENDPOINT")
            _warned = True
        return None
    if _client is not None:
        return _client
    import boto3
    from botocore.config import Config

    region = os.environ.get("B2_REGION") or "us-west-004"
    _client = boto3.client(
        "s3",
        endpoint_url=os.environ["B2_ENDPOINT"].rstrip("/"),
        aws_access_key_id=os.environ["B2_KEY_ID"],
        aws_secret_access_key=os.environ["B2_APPLICATION_KEY"],
        region_name=region,
        config=Config(signature_version="s3v4"),
    )
    return _client


def b2_put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = _get_client()
    if client is None:
        raise RuntimeError("B2 not configured")
    full = f"{_prefix()}/{key.lstrip('/')}"
    client.put_object(Bucket=_bucket(), Key=full, Body=data, ContentType=content_type)
    return full


def b2_get_bytes(key: str) -> bytes:
    client = _get_client()
    if client is None:
        raise RuntimeError("B2 not configured")
    full = key if key.startswith(_prefix()) else f"{_prefix()}/{key.lstrip('/')}"
    return client.get_object(Bucket=_bucket(), Key=full)["Body"].read()


def b2_put_json(key: str, obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
    return b2_put_bytes(key, raw, content_type="application/json; charset=utf-8")


def b2_get_json(key: str) -> Any:
    return json.loads(b2_get_bytes(key).decode("utf-8"))


def b2_delete(key: str) -> None:
    client = _get_client()
    if client is None:
        return
    full = key if key.startswith(_prefix()) else f"{_prefix()}/{key.lstrip('/')}"
    try:
        client.delete_object(Bucket=_bucket(), Key=full)
    except Exception as e:
        print(f"[b2] delete {full}: {e}")
