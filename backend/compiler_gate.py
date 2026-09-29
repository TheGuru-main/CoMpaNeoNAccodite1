"""
CoMpaNeoNAccodite — Compiler / Syntax Gate
==========================================
Real syntax validation with graceful fallback:

    tree-sitter   (if installed)   -> parse + collect ERROR nodes
    ast           (Python fallback)-> compile() to catch SyntaxError
    regex         (last resort)    -> colon / bracket heuristics

Diagnostics are written into the brain's own grid at the LSP zone
(rows 24-39) with negative activation, so pattern/relevancy layers
see them as fault signals.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from accodite_brain import AccoditeBrain


# --- tree-sitter (optional) ------------------------------------------------
try:
    from tree_sitter import Language, Parser  # noqa: F401
    try:
        from tree_sitter_languages import get_language, get_parser
        TS_AVAILABLE = True
    except Exception:
        TS_AVAILABLE = False
except Exception:
    TS_AVAILABLE = False


LANG_BY_EXT = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".mjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx",
    ".go": "go", ".rs": "rust", ".rb": "ruby",
    ".java": "java", ".c": "c", ".h": "c",
    ".cpp": "cpp", ".hpp": "cpp",
}


def _lang_for(filename: str) -> str:
    for ext, lang in LANG_BY_EXT.items():
        if filename.endswith(ext):
            return lang
    return "python"


class AccoditeCompilerGate:
    def __init__(self, brain: AccoditeBrain):
        self.brain = brain

    # -----------------------------------------------------------------

    def inject_lsp_diagnostics(
        self, file_name: str, syntax_stream: str
    ) -> List[Dict[str, Any]]:
        faults: List[Dict[str, Any]] = []

        if TS_AVAILABLE:
            faults.extend(self._ts_faults(file_name, syntax_stream))
        if not faults and file_name.endswith(".py"):
            faults.extend(self._py_ast_faults(syntax_stream))
        if not faults:
            faults.extend(self._basic_faults(syntax_stream))

        for f in faults:
            c, r = self.brain.calculate_gsp_slot(f["message"], "lsp")
            try:
                self.brain._own_grid[r][c] = -1.0
            except Exception:
                pass
            f["grid_mapping"] = {"col": c, "row": r}

        return faults

    # -----------------------------------------------------------------

    def _ts_faults(self, file_name: str, src: str) -> List[Dict[str, Any]]:
        try:
            lang = _lang_for(file_name)
            parser = get_parser(lang)
            tree = parser.parse((src or "").encode("utf-8"))
        except Exception:
            return []
        out: List[Dict[str, Any]] = []
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if node.type == "ERROR" or node.is_missing:
                out.append({
                    "line": node.start_point[0] + 1,
                    "col":  node.start_point[1],
                    "message": f"SyntaxError: unexpected {node.type}",
                    "severity": "Error",
                    "source": "tree-sitter",
                })
            for child in node.children:
                stack.append(child)
        return out

    # -----------------------------------------------------------------

    def _py_ast_faults(self, src: str) -> List[Dict[str, Any]]:
        try:
            compile(src or "", "<accodite>", "exec")
            return []
        except SyntaxError as e:
            return [{
                "line": e.lineno or 1,
                "col":  e.offset or 0,
                "message": f"SyntaxError: {e.msg}",
                "severity": "Error",
                "source": "python-ast",
            }]
        except Exception as e:
            return [{
                "line": 1, "col": 0,
                "message": f"ParseError: {e}",
                "severity": "Error", "source": "python-ast",
            }]

    # -----------------------------------------------------------------

    def _basic_faults(self, src: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        lines = (src or "").splitlines()
        for i, ln in enumerate(lines, start=1):
            s = ln.strip()
            if s.startswith(("def ", "class ", "if ", "for ", "while ",
                             "elif ", "else", "try", "except", "finally",
                             "with ")):
                if not s.endswith((":", ",", "\\")):
                    out.append({
                        "line": i,
                        "message": "SyntaxError: expected ':' at end of block",
                        "severity": "Error",
                        "source": "regex",
                    })
        return out
