"""
ScrapingBee Adapter
===================
Replaces YouTube for the media domain.

Simple HTTP proxy that renders pages server-side so we get real
content from JS-heavy sources without a browser on-device.

API:  GET https://app.scrapingbee.com/api/v1/?api_key=...&url=...

Public:
    fetch_page(url, render_js=True) -> {"ok","url","html","bytes"} | {"ok":False,"error"}
    is_configured()                 -> bool
"""
from __future__ import annotations
import os
from typing import Any, Dict, Optional

try:
    import httpx
    _HTTPX = True
except ImportError:
    httpx = None
    _HTTPX = False

SCRAPINGBEE_KEY = os.environ.get("SCRAPINGBEE_API_KEY", "")
BASE_URL = "https://app.scrapingbee.com/api/v1/"
DEFAULT_MAX_BYTES = 512 * 1024


def is_configured() -> bool:
    return bool(SCRAPINGBEE_KEY) and _HTTPX


def fetch_page(
    url: str,
    *,
    render_js: bool = True,
    country_code: str = "ng",
    timeout: int = 30,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Dict[str, Any]:
    """Fetch a URL through ScrapingBee. Returns normalized dict."""
    if not is_configured():
        return {
            "ok": False,
            "error": "scrapingbee not configured (SCRAPINGBEE_API_KEY missing or httpx absent)",
            "url": url,
        }

    params = {
        "api_key": SCRAPINGBEE_KEY,
        "url": url,
        "render_js": "true" if render_js else "false",
        "country_code": country_code,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(BASE_URL, params=params)
            r.raise_for_status()
            text = r.text or ""
            if len(text) > max_bytes:
                text = text[:max_bytes]
            return {
                "ok": True,
                "url": url,
                "html": text,
                "bytes": len(text),
                "content_type": r.headers.get("content-type", ""),
            }
    except Exception as e:
        return {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "url": url,
        }
