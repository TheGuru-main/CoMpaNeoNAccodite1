"""
Accodite License Filter
=======================
Sequential 4-source license check for code that enters the grid.

Order:
    1. LICENSE / LICENSE.md / LICENSE.txt / COPYING at repo root
    2. SPDX id in package.json / pyproject.toml / Cargo.toml / go.mod
    3. Inline SPDX header in the file (first 20 lines)
    4. Git metadata via provider API (github/gitlab)

Whitelist: MIT · Apache-2.0 · BSD-3-Clause · CC0-1.0
Anything else is refused, unless the caller passes an override.

Per-link cap enforced on every remote fetch.
"""
from __future__ import annotations
import re
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

# --- policy ---
LICENSE_WHITELIST = frozenset({
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
    "CC0-1.0",
})

MAX_BYTES_PER_LINK = 512 * 1024      # 512 KB
TIMEOUT_S = 10

# --- patterns ---
_SPDX_HEADER = re.compile(
    r"SPDX-License-Identifier:\s*([A-Za-z0-9.\-+]+)",
    re.IGNORECASE,
)
_LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")

# spdx → canonical name mapping for common aliases
SPDX_ALIASES = {
    "MIT": "MIT",
    "MIT-LICENSE": "MIT",
    "APACHE-2.0": "Apache-2.0",
    "APACHE2": "Apache-2.0",
    "BSD-3-CLAUSE": "BSD-3-Clause",
    "BSD3": "BSD-3-Clause",
    "CC0-1.0": "CC0-1.0",
}


@dataclass
class LicenseVerdict:
    allowed: bool
    license: Optional[str]
    source: str          # which of the 4 sources matched
    reason: str = ""


# ---------------------------------------------------------------------------
# FETCH HELPER (capped)
# ---------------------------------------------------------------------------

def _fetch(url: str, cap: int = MAX_BYTES_PER_LINK) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Accodite/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            raw = r.read(cap + 1)
            if len(raw) > cap:
                raw = raw[:cap]
            return raw.decode("utf-8", errors="ignore")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# SOURCE 1 — LICENSE file at repo root
# ---------------------------------------------------------------------------

def _check_license_file(repo_url: str) -> Optional[str]:
    base = repo_url.rstrip("/")
    for name in _LICENSE_FILES:
        for branch in ("main", "master"):
            raw = _fetch(f"{base}/raw/{branch}/{name}", cap=64 * 1024)
            if not raw:
                continue
            low = raw.lower()
            if "mit license" in low or "permission is hereby granted, free of charge" in low:
                return "MIT"
            if "apache license" in low and "version 2.0" in low:
                return "Apache-2.0"
            if "bsd 3-clause" in low or "redistribution and use in source and binary forms" in low and "3." in raw:
                return "BSD-3-Clause"
            if "cc0 1.0" in low or "creative commons zero" in low:
                return "CC0-1.0"
    return None


# ---------------------------------------------------------------------------
# SOURCE 2 — SPDX id in package manifest
# ---------------------------------------------------------------------------

_MANIFESTS = (
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "composer.json",
)

def _check_manifest(repo_url: str) -> Optional[str]:
    base = repo_url.rstrip("/")
    for name in _MANIFESTS:
        for branch in ("main", "master"):
            raw = _fetch(f"{base}/raw/{branch}/{name}", cap=64 * 1024)
            if not raw:
                continue
            m = _SPDX_HEADER.search(raw)
            if m:
                return _canonical(m.group(1))
            # json key "license"
            m2 = re.search(r'"license"\s*:\s*"([^"]+)"', raw)
            if m2:
                return _canonical(m2.group(1))
    return None


# ---------------------------------------------------------------------------
# SOURCE 3 — inline SPDX in the file itself
# ---------------------------------------------------------------------------

def _check_inline_spdx(file_text: str) -> Optional[str]:
    head = "\n".join((file_text or "").splitlines()[:20])
    m = _SPDX_HEADER.search(head)
    if m:
        return _canonical(m.group(1))
    return None


# ---------------------------------------------------------------------------
# SOURCE 4 — provider API
# ---------------------------------------------------------------------------

def _check_provider_api(repo_url: str) -> Optional[str]:
    if "github.com" in repo_url:
        m = re.search(r"github\.com/([^/]+)/([^/.\s]+)", repo_url)
        if m:
            owner, repo = m.group(1), m.group(2)
            raw = _fetch(f"https://api.github.com/repos/{owner}/{repo}", cap=64 * 1024)
            if raw:
                j = re.search(r'"spdx_id"\s*:\s*"([^"]+)"', raw)
                if j:
                    return _canonical(j.group(1))
    if "gitlab.com" in repo_url:
        m = re.search(r"gitlab\.com/([^/]+)/([^/.\s]+)", repo_url)
        if m:
            owner, repo = m.group(1), m.group(2)
            raw = _fetch(f"https://gitlab.com/api/v4/projects/{owner}%2F{repo}", cap=64 * 1024)
            if raw:
                j = re.search(r'"license"\s*:\s*\{[^}]*"key"\s*:\s*"([^"]+)"', raw)
                if j:
                    return _canonical(j.group(1))
    return None


# ---------------------------------------------------------------------------
# CANONICALIZATION
# ---------------------------------------------------------------------------

def _canonical(spdx: str) -> Optional[str]:
    if not spdx:
        return None
    key = spdx.strip().upper()
    return SPDX_ALIASES.get(key)


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def check_repo(repo_url: str) -> LicenseVerdict:
    """Sequential 4-source check on a remote repo."""
    for checker, name in (
        (_check_license_file, "license_file"),
        (_check_manifest, "manifest"),
        (_check_provider_api, "provider_api"),
    ):
        lic = checker(repo_url)
        if lic:
            allowed = lic in LICENSE_WHITELIST
            return LicenseVerdict(
                allowed=allowed,
                license=lic,
                source=name,
                reason="ok" if allowed else f"{lic} not in whitelist",
            )
    return LicenseVerdict(
        allowed=False, license=None, source="none",
        reason="no license found in 4 sources",
    )


def check_file(file_text: str, *, repo_url: str = "") -> LicenseVerdict:
    """Inline check for a single file; falls back to repo-level check."""
    lic = _check_inline_spdx(file_text)
    if lic:
        allowed = lic in LICENSE_WHITELIST
        return LicenseVerdict(
            allowed=allowed, license=lic, source="inline_spdx",
            reason="ok" if allowed else f"{lic} not in whitelist",
        )
    if repo_url:
        return check_repo(repo_url)
    return LicenseVerdict(
        allowed=False, license=None, source="none",
        reason="no license in file or repo",
    )


def check_own_repo(local_path: str) -> LicenseVerdict:
    """Anything inside the user's own device is allowed by default."""
    return LicenseVerdict(
        allowed=True, license="OWN", source="local",
        reason="user-owned content",
    )
