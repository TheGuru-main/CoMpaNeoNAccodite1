"""Tree-sitter parser with graceful fallbacks.

Public API:
    parse_file(path, source)   -> ParseResult
    extract_symbols(source, lang) -> list[Symbol]

Tree-sitter optional. Fallback uses ast (python) or regex.
"""
from __future__ import annotations
import ast as _ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from tree_sitter.languages import lang_for

# --- tree-sitter (optional) ---
try:
    from tree_sitter_languages import get_parser as _get_parser
    TS_AVAILABLE = True
except Exception:
    TS_AVAILABLE = False


@dataclass
class Symbol:
    name: str
    kind: str            # function | class | method | var | import | type
    path: str
    start_line: int
    end_line: int
    signature: str = ""
    parent: Optional[str] = None
    lang: str = "text"

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ParseResult:
    path: str
    lang: str
    ok: bool = True
    errors: List[Dict[str, Any]] = field(default_factory=list)
    symbols: List[Symbol] = field(default_factory=list)
    source_hash: str = ""
    backend: str = "none"          # tree-sitter | python-ast | regex

    def as_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "lang": self.lang,
            "ok": self.ok,
            "errors": list(self.errors),
            "symbols": [s.as_dict() for s in self.symbols],
            "source_hash": self.source_hash,
            "backend": self.backend,
        }


# ---------------------------------------------------------------------------

def parse_file(path: str, source: str) -> ParseResult:
    lang = lang_for(path or "")
    res = ParseResult(path=path, lang=lang)

    if TS_AVAILABLE:
        try:
            res = _parse_ts(path, source, lang)
            res.backend = "tree-sitter"
            return res
        except Exception:
            pass

    if lang == "python":
        res = _parse_python_ast(path, source)
        res.backend = "python-ast"
        return res

    res = _parse_regex(path, source, lang)
    res.backend = "regex"
    return res


def extract_symbols(source: str, lang: str = "python", path: str = "<mem>") -> List[Symbol]:
    return parse_file(path, source).symbols


# ---------------------------------------------------------------------------
# tree-sitter
# ---------------------------------------------------------------------------

_TS_KIND_MAP = {
    "function_definition": "function",
    "function_declaration": "function",
    "class_definition": "class",
    "class_declaration": "class",
    "method_definition": "method",
    "import_statement": "import",
    "import_from_statement": "import",
    "variable_declarator": "var",
    "type_alias_declaration": "type",
    "interface_declaration": "type",
}


def _parse_ts(path: str, source: str, lang: str) -> ParseResult:
    parser = _get_parser(lang)
    tree = parser.parse((source or "").encode("utf-8"))
    res = ParseResult(path=path, lang=lang)

    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "ERROR" or node.is_missing:
            res.errors.append({
                "line": node.start_point[0] + 1,
                "col":  node.start_point[1],
                "message": f"unexpected {node.type}",
                "severity": "error",
                "source": "tree-sitter",
            })
        kind = _TS_KIND_MAP.get(node.type)
        if kind:
            name = _node_name(node, source)
            if name:
                res.symbols.append(Symbol(
                    name=name, kind=kind, path=path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    signature=_first_line(source, node.start_byte),
                    lang=lang,
                ))
        for c in node.children:
            stack.append(c)
    return res


def _node_name(node, source: bytes) -> str:
    for child in node.children:
        if child.type in ("identifier", "name", "property_identifier"):
            try:
                return source[child.start_byte:child.end_byte].decode("utf-8", "ignore")
            except Exception:
                return ""
    return ""


def _first_line(source: str, start_byte: int) -> str:
    try:
        b = (source or "").encode("utf-8")
        chunk = b[start_byte:start_byte + 200].decode("utf-8", "ignore")
        return chunk.splitlines()[0] if chunk else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# python ast fallback
# ---------------------------------------------------------------------------

def _parse_python_ast(path: str, source: str) -> ParseResult:
    res = ParseResult(path=path, lang="python")
    try:
        tree = _ast.parse(source or "")
    except SyntaxError as e:
        res.ok = False
        res.errors.append({
            "line": e.lineno or 1,
            "col": e.offset or 0,
            "message": f"SyntaxError: {e.msg}",
            "severity": "error",
            "source": "python-ast",
        })
        return res

    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            res.symbols.append(Symbol(
                name=node.name, kind="function", path=path,
                start_line=node.lineno, end_line=node.end_lineno or node.lineno,
                signature=f"def {node.name}(...)",
                lang="python",
            ))
        elif isinstance(node, _ast.ClassDef):
            res.symbols.append(Symbol(
                name=node.name, kind="class", path=path,
                start_line=node.lineno, end_line=node.end_lineno or node.lineno,
                signature=f"class {node.name}",
                lang="python",
            ))
        elif isinstance(node, (_ast.Import, _ast.ImportFrom)):
            for alias in getattr(node, "names", []):
                res.symbols.append(Symbol(
                    name=alias.name, kind="import", path=path,
                    start_line=node.lineno, end_line=node.lineno,
                    lang="python",
                ))
    return res


# ---------------------------------------------------------------------------
# regex fallback
# ---------------------------------------------------------------------------

_RX_FLAGS = re.MULTILINE

_RX_PY_FUNC = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)", _RX_FLAGS)
_RX_CLASS   = re.compile(r"^\s*class\s+(\w+)", _RX_FLAGS)
_RX_JS_FUNC = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", _RX_FLAGS)
_RX_JS_ARROW= re.compile(r"^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(", _RX_FLAGS)


def _parse_regex(path: str, source: str, lang: str) -> ParseResult:
    res = ParseResult(path=path, lang=lang)
    for i, line in enumerate((source or "").splitlines(), start=1):
        m = _RX_CLASS.match(line)
        if m:
            res.symbols.append(Symbol(m.group(1), "class", path, i, i, lang=lang))
            continue
        m = _RX_PY_FUNC.match(line) or _RX_JS_FUNC.match(line) or _RX_JS_ARROW.match(line)
        if m:
            res.symbols.append(Symbol(m.group(1), "function", path, i, i, lang=lang))
    return res
