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

    # ---------------------------------------------------------------
    # PAIR 3: ts.parse / ts.symbols
    # ---------------------------------------------------------------

    @reg.tool(
        name="ts.parse",
        category="ts",
        description="Parse a file with tree-sitter (falls back to ast / regex).",
        mutating=False,
    )
    def ts_parse(path: str) -> Dict[str, Any]:
        from tree_sitter.parser import parse_file
        p = ctx["guard"].resolve(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"no such file: {path}")
        source = p.read_text(encoding="utf-8", errors="replace")
        res = parse_file(str(p.relative_to(ctx["guard"].root)), source)
        return res.as_dict()

    @reg.tool(
        name="ts.symbols",
        category="ts",
        description="Extract symbols from a workspace file.",
        mutating=False,
    )
    def ts_symbols(
        path: str,
        kind: str = "",
        limit: int = 500,
    ) -> Dict[str, Any]:
        from tree_sitter.parser import parse_file
        p = ctx["guard"].resolve(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"no such file: {path}")
        source = p.read_text(encoding="utf-8", errors="replace")
        res = parse_file(str(p.relative_to(ctx["guard"].root)), source)
        syms = [s.as_dict() for s in res.symbols]
        if kind:
            syms = [s for s in syms if s.get("kind") == kind]
        return {
            "path": str(p.relative_to(ctx["guard"].root)),
            "lang": res.lang,
            "backend": res.backend,
            "ok": res.ok,
            "count": len(syms[:limit]),
            "symbols": syms[:limit],
        }

    # ---------------------------------------------------------------
    # PAIR 4: lsp.diagnostics / lsp.symbols
    # ---------------------------------------------------------------

    @reg.tool(
        name="lsp.diagnostics",
        category="lsp",
        description="Run LSP diagnostics on a workspace file (fallback: compiler_gate).",
        mutating=False,
    )
    def lsp_diagnostics(path: str) -> Dict[str, Any]:
        from lsp.manager import LSPManager
        p = ctx["guard"].resolve(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"no such file: {path}")
        source = p.read_text(encoding="utf-8", errors="replace")
        mgr = ctx.get("lsp")
        if mgr is None:
            mgr = LSPManager()
            ctx["lsp"] = mgr
        diags = mgr.diagnose(
            root=str(ctx["guard"].root),
            path=str(p.relative_to(ctx["guard"].root)),
            source=source,
        )
        return {
            "path": str(p.relative_to(ctx["guard"].root)),
            "backend": mgr.last_backend,
            "count": len(diags),
            "errors": [d.as_dict() for d in diags if d.severity == "error"],
            "warnings": [d.as_dict() for d in diags if d.severity == "warning"],
        }

    @reg.tool(
        name="lsp.symbols",
        category="lsp",
        description="Symbol view of a file (currently delegates to tree_sitter).",
        mutating=False,
    )
    def lsp_symbols(
        path: str,
        kind: str = "",
        limit: int = 500,
    ) -> Dict[str, Any]:
        from tree_sitter.parser import parse_file
        p = ctx["guard"].resolve(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"no such file: {path}")
        source = p.read_text(encoding="utf-8", errors="replace")
        res = parse_file(str(p.relative_to(ctx["guard"].root)), source)
        syms = [s.as_dict() for s in res.symbols]
        if kind:
            syms = [s for s in syms if s.get("kind") == kind]
        return {
            "path": str(p.relative_to(ctx["guard"].root)),
            "backend": "tree-sitter",
            "count": len(syms[:limit]),
            "symbols": syms[:limit],
        }

    # ---------------------------------------------------------------
    # PAIR 5: build.compile / build.lint  (SANDBOXPATH FIX applied)
    # ---------------------------------------------------------------

    @reg.tool(
        name="build.compile",
        category="build",
        description="Compile-check a file in the sandbox.",
        mutating=False,
    )
    def build_compile(
        path: str,
        lang: str = "python",
        timeout_s: int = 15,
    ) -> Dict[str, Any]:
        from sandbox.runner import SandboxRunner
        p = ctx["guard"].resolve(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"no such file: {path}")

        rel = str(p.relative_to(ctx["guard"].root))
        source = p.read_text(encoding="utf-8", errors="replace")

        runner = ctx.get("sandbox")
        if runner is None:
            runner = SandboxRunner(prefer="subprocess", timeout_s=timeout_s)
            ctx["sandbox"] = runner

        if lang == "python":
            extra = {rel: source}
            wrapped = (
                "import py_compile\n"
                f"py_compile.compile({rel!r}, doraise=True)\n"
                "print('compile-ok')\n"
            )
            res = runner.run_code(
                source=wrapped, filename="_accd_compile_check.py",
                lang="python", extra_files=extra,
            )
        else:
            res = runner.run_code(source=source, filename=rel, lang=lang)

        return {
            "path": rel,
            "lang": lang,
            "ok": res.ok,
            "exit_code": res.exit_code,
            "stdout": res.stdout[-2000:],
            "stderr": res.stderr[-2000:],
            "duration_s": res.duration_s,
            "timed_out": res.timed_out,
        }

    @reg.tool(
        name="build.lint",
        category="build",
        description="Lint a file (py_compile fallback for python).",
        mutating=False,
    )
    def build_lint(
        path: str,
        lang: str = "python",
        timeout_s: int = 15,
    ) -> Dict[str, Any]:
        from sandbox.runner import SandboxRunner
        p = ctx["guard"].resolve(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"no such file: {path}")

        rel = str(p.relative_to(ctx["guard"].root))
        source = p.read_text(encoding="utf-8", errors="replace")

        runner = ctx.get("sandbox")
        if runner is None:
            runner = SandboxRunner(prefer="subprocess", timeout_s=timeout_s)
            ctx["sandbox"] = runner

        if lang != "python":
            return {
                "path": rel, "lang": lang,
                "ok": True, "skipped": True,
                "reason": f"lint not implemented for {lang}",
                "findings": [],
            }

        extra = {rel: source}
        wrapper = (
            "import py_compile\n"
            f"py_compile.compile({rel!r}, doraise=True)\n"
            "print('lint-fallback-compile-ok')\n"
        )
        res = runner.run_code(
            source=wrapper, filename="_accd_lint_check.py",
            lang="python", extra_files=extra,
        )

        findings = []
        if res.stderr.strip():
            for line in res.stderr.strip().splitlines()[-20:]:
                findings.append({"message": line})

        return {
            "path": rel,
            "lang": lang,
            "ok": res.ok,
            "exit_code": res.exit_code,
            "stdout": res.stdout[-2000:],
            "stderr": res.stderr[-2000:],
            "duration_s": res.duration_s,
            "findings": findings,
        }

    return reg
