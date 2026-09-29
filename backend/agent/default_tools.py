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

    # ---------------------------------------------------------------
    # PAIR 6: test.run / sandbox.verify
    # ---------------------------------------------------------------

    @reg.tool(
        name="test.run",
        category="test",
        description="Run a workspace file as a test target in the sandbox.",
        mutating=False,
    )
    def test_run(
        path: str,
        lang: str = "python",
        timeout_s: int = 20,
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

        res = runner.run_code(source=source, filename=rel, lang=lang)
        return {
            "path": rel,
            "lang": lang,
            "ok": res.ok,
            "exit_code": res.exit_code,
            "stdout": res.stdout[-4000:],
            "stderr": res.stderr[-4000:],
            "duration_s": res.duration_s,
            "timed_out": res.timed_out,
        }

    @reg.tool(
        name="sandbox.verify",
        category="sandbox",
        description="Run the 6-stage verification pipeline on a file.",
        mutating=False,
    )
    def sandbox_verify(
        path: str,
        lang: str = "python",
        run_tests: bool = True,
        run_security: bool = True,
    ) -> Dict[str, Any]:
        from verification.pipeline import VerificationPipeline
        p = ctx["guard"].resolve(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"no such file: {path}")

        rel = str(p.relative_to(ctx["guard"].root))
        source = p.read_text(encoding="utf-8", errors="replace")

        pipe = ctx.get("pipeline")
        if pipe is None:
            pipe = VerificationPipeline(
                root=str(ctx["guard"].root),
                stop_on_first_failure=True,
            )
            ctx["pipeline"] = pipe

        report = pipe.verify(
            path=rel, source=source, lang=lang,
            run_tests=run_tests, run_security=run_security,
        )
        return {
            "path": rel,
            "lang": lang,
            "ok": report.ok,
            "stopped_at": report.stopped_at,
            "stages": [s.as_dict() for s in report.stages],
        }

    # ---------------------------------------------------------------
    # PAIR 7: doc.pdf.create / archive.zip.create
    # ---------------------------------------------------------------

    @reg.tool(
        name="doc.pdf.create",
        category="doc",
        description="Create a PDF from text (reportlab if available, minimal fallback).",
        mutating=True,
    )
    def doc_pdf_create(
        output: str,
        content: str,
        title: str = "",
    ) -> Dict[str, Any]:
        p = ctx["guard"].resolve(output)
        p.parent.mkdir(parents=True, exist_ok=True)

        text_lines = (content or "").splitlines() or [""]
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(str(p), pagesize=A4)
            w, h = A4
            y = h - 40
            if title:
                c.setFont("Helvetica-Bold", 14)
                c.drawString(40, y, title[:80])
                y -= 24
            c.setFont("Helvetica", 10)
            for line in text_lines:
                if y < 40:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = h - 40
                c.drawString(40, y, line[:110])
                y -= 14
            c.save()
            engine = "reportlab"
        except ImportError:
            # minimal valid PDF (single page, plain text)
            escaped = (content or "").replace("(", "\\(").replace(")", "\\)")
            body = f"BT /F1 12 Tf 40 780 Td ({escaped[:2000]}) Tj ET"
            pdf = (
                b"%PDF-1.4\n"
                b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]"
                b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
                + f"4 0 obj<</Length {len(body)}>>stream\n".encode()
                + body.encode()
                + b"\nendstream endobj\n"
                b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
                b"xref\n0 6\n0000000000 65535 f \n"
                b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
            )
            p.write_bytes(pdf)
            engine = "minimal"

        return {
            "path": str(p.relative_to(ctx["guard"].root)),
            "size": p.stat().st_size,
            "engine": engine,
            "lines": len(text_lines),
        }

    @reg.tool(
        name="archive.zip.create",
        category="archive",
        description="Create a ZIP from workspace files (zip-slip protected).",
        mutating=True,
    )
    def archive_zip_create(
        output: str,
        sources: List[str],
        compression: str = "deflate",
    ) -> Dict[str, Any]:
        import zipfile
        p = ctx["guard"].resolve(output)
        p.parent.mkdir(parents=True, exist_ok=True)

        compression_map = {
            "store":   zipfile.ZIP_STORED,
            "deflate": zipfile.ZIP_DEFLATED,
            "bzip2":   zipfile.ZIP_BZIP2,
            "lzma":    zipfile.ZIP_LZMA,
        }
        cmode = compression_map.get(compression, zipfile.ZIP_DEFLATED)

        added = []
        skipped = []
        with zipfile.ZipFile(str(p), "w", compression=cmode) as zf:
            for src in sources or []:
                try:
                    sp = ctx["guard"].resolve(src)
                except PermissionError:
                    skipped.append({"src": src, "reason": "escapes workspace"})
                    continue
                if not sp.exists():
                    skipped.append({"src": src, "reason": "not found"})
                    continue
                if sp.is_file():
                    arc = sp.relative_to(ctx["guard"].root).as_posix()
                    zf.write(str(sp), arcname=arc)
                    added.append(arc)
                elif sp.is_dir():
                    for child in sp.rglob("*"):
                        if child.is_file():
                            arc = child.relative_to(ctx["guard"].root).as_posix()
                            zf.write(str(child), arcname=arc)
                            added.append(arc)

        return {
            "path": str(p.relative_to(ctx["guard"].root)),
            "size": p.stat().st_size,
            "compression": compression,
            "added_count": len(added),
            "added": added[:200],
            "skipped": skipped,
        }

    # ---------------------------------------------------------------
    # PAIR 8: web.http.get / web.http.post
    # ---------------------------------------------------------------

    _web_allow = {"allow_hosts": None}  # None = all HTTPS hosts

    @reg.tool(
        name="web.http.get",
        category="web",
        description="HTTPS GET. HTTP refused unless insecure=True.",
        mutating=False,
    )
    def web_http_get(
        url: str,
        timeout_s: int = 20,
        max_bytes: int = 2_000_000,
        insecure: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        import urllib.request
        import urllib.error

        if not url.startswith("https://"):
            if not insecure:
                raise PermissionError("only HTTPS is allowed (pass insecure=True to override)")
        try:
            req = urllib.request.Request(
                url, headers=headers or {}, method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                raw = r.read(max_bytes + 1)
                truncated = len(raw) > max_bytes
                raw = raw[:max_bytes]
                text = raw.decode("utf-8", errors="replace")
                return {
                    "url": url,
                    "status": getattr(r, "status", None),
                    "content_type": r.headers.get("Content-Type", ""),
                    "bytes": len(raw),
                    "truncated": truncated,
                    "text": text,
                }
        except urllib.error.HTTPError as e:
            return {
                "url": url, "status": e.code, "bytes": 0,
                "truncated": False, "text": "",
                "error": f"HTTP {e.code} {e.reason}",
            }
        except Exception as e:
            raise RuntimeError(f"{type(e).__name__}: {e}")

    @reg.tool(
        name="web.http.post",
        category="web",
        description="HTTPS POST with JSON or raw data.",
        mutating=False,
    )
    def web_http_post(
        url: str,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[str] = None,
        timeout_s: int = 20,
        max_bytes: int = 2_000_000,
        insecure: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        import urllib.request
        import urllib.error

        if not url.startswith("https://"):
            if not insecure:
                raise PermissionError("only HTTPS is allowed (pass insecure=True to override)")

        body_bytes = b""
        hdrs = dict(headers or {})
        if json_body is not None:
            import json as _json
            body_bytes = _json.dumps(json_body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        elif data is not None:
            body_bytes = str(data).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=body_bytes, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                raw = r.read(max_bytes + 1)
                truncated = len(raw) > max_bytes
                raw = raw[:max_bytes]
                text = raw.decode("utf-8", errors="replace")
                return {
                    "url": url,
                    "status": getattr(r, "status", None),
                    "content_type": r.headers.get("Content-Type", ""),
                    "bytes": len(raw),
                    "truncated": truncated,
                    "text": text,
                }
        except urllib.error.HTTPError as e:
            return {
                "url": url, "status": e.code, "bytes": 0,
                "truncated": False, "text": "",
                "error": f"HTTP {e.code} {e.reason}",
            }
        except Exception as e:
            raise RuntimeError(f"{type(e).__name__}: {e}")

    return reg
