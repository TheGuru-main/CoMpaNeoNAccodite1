"""
Accodite Default Tools
======================
Concrete tools registered on ToolRegistry.

Pairs (added incrementally):
    1. fs.read_file            / fs.write_file
    2. fs.list_dir             / fs.glob
    3. ts.parse                / ts.symbols
    4. lsp.diagnostics         / lsp.symbols
    5. build.compile           / build.lint
    6. test.run                / sandbox.verify
    7. doc.pdf.create          / archive.zip.create
    8. web.http.get            / web.http.post

Every tool:
    - role-checked before dispatch
    - sandboxed to workspace root (path traversal refused)
    - traced via ToolRegistry
"""
from __future__ import annotations
import os
import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.tools import ToolRegistry, ToolSpec, ToolCall, ToolResult


# ============================================================================
# PATH GUARD
# ============================================================================

class WorkspaceGuard:
    """Refuses paths that escape the workspace root."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def resolve(self, path: str) -> Path:
        p = (self.root / (path or "")).resolve()
        try:
            p.relative_to(self.root)
        except ValueError:
            raise PermissionError(f"path escapes workspace: {path}")
        return p


# ============================================================================
# FACTORY
# ============================================================================

def build_registry(
    *,
    root: str = ".",
    tracer=None,
    role_lookup=None,
    sandbox=None,
) -> ToolRegistry:
    reg = ToolRegistry(tracer=tracer, role_lookup=role_lookup)
    guard = WorkspaceGuard(root)
    ctx = {"root": root, "guard": guard, "sandbox": sandbox}

    # ---------------------------------------------------------------
    # PAIR 1: fs.read_file / fs.write_file
    # ---------------------------------------------------------------

    @reg.tool(
        name="fs.read_file",
        category="fs",
        description="Read a file inside the workspace.",
        mutating=False,
    )
    def fs_read_file(path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        p = ctx["guard"].resolve(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"no such file: {path}")
        text = p.read_text(encoding=encoding)
        return {
            "path": str(p.relative_to(ctx["guard"].root)),
            "size": len(text),
            "content": text,
        }

    @reg.tool(
        name="fs.write_file",
        category="fs",
        description="Write a file inside the workspace.",
        mutating=True,
    )
    def fs_write_file(path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        p = ctx["guard"].resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content or "", encoding=encoding)
        return {
            "path": str(p.relative_to(ctx["guard"].root)),
            "size": len(content or ""),
        }

    # ---------------------------------------------------------------
    # PAIR 2: fs.list_dir / fs.glob
    # ---------------------------------------------------------------

    @reg.tool(
        name="fs.list_dir",
        category="fs",
        description="List entries in a workspace directory (non-recursive).",
        mutating=False,
    )
    def fs_list_dir(path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
        p = ctx["guard"].resolve(path or ".")
        if not p.exists() or not p.is_dir():
            raise NotADirectoryError(f"no such directory: {path}")
        entries = []
        for child in sorted(p.iterdir()):
            if not show_hidden and child.name.startswith("."):
                continue
            try:
                st = child.stat()
            except OSError:
                continue
            entries.append({
                "name": child.name,
                "kind": "dir" if child.is_dir() else "file",
                "size": st.st_size if child.is_file() else None,
            })
        return {
            "path": str(p.relative_to(ctx["guard"].root)) or ".",
            "count": len(entries),
            "entries": entries,
        }

    @reg.tool(
        name="fs.glob",
        category="fs",
        description="Glob workspace paths (supports ** via recursive=True).",
        mutating=False,
    )
    def fs_glob(
        pattern: str,
        recursive: bool = True,
        limit: int = 500,
    ) -> Dict[str, Any]:
        p = ctx["guard"].resolve(".")
        pattern = (pattern or "").strip() or "*"
        if pattern.startswith("/"):
            raise PermissionError("absolute patterns are not allowed")
        # BADPAT: reject any path traversal in the pattern
        parts = pattern.replace("\\", "/").split("/")
        if any(seg == ".." for seg in parts):
            raise PermissionError("parent-directory patterns are not allowed")
        matches = []
        if recursive:
            for path in p.rglob(pattern):
                try:
                    path.relative_to(ctx["guard"].root)
                except ValueError:
                    continue
                matches.append(path.relative_to(ctx["guard"].root).as_posix())
                if len(matches) >= limit:
                    break
        else:
            for path in p.glob(pattern):
                try:
                    path.relative_to(ctx["guard"].root)
                except ValueError:
                    continue
                matches.append(path.relative_to(ctx["guard"].root).as_posix())
                if len(matches) >= limit:
                    break
        return {
            "pattern": pattern,
            "recursive": bool(recursive),
            "count": len(matches),
            "matches": sorted(matches),
        }

    return reg
