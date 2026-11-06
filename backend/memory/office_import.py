"""
Import Excel / CSV into Accodite SheetS cell maps.
Bytes from client upload, file:// or B2 payload_ref, or http(s) URL.
"""
from __future__ import annotations
import csv
import io
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen


def _col_letter(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def cells_from_matrix(rows: List[List[Any]], max_rows: int = 64, max_cols: int = 54) -> Dict[str, Any]:
    cells: Dict[str, Any] = {}
    width = 1
    for r, row in enumerate(rows[:max_rows]):
        if not isinstance(row, (list, tuple)):
            continue
        width = max(width, min(len(row), max_cols))
        for c, val in enumerate(list(row)[:max_cols]):
            if val is None or val == "":
                continue
            key = f"{_col_letter(c)}{r + 1}"
            cells[key] = {"v": str(val), "meta": ""}
    return {
        "cells": cells,
        "n_rows": min(max(len(rows), 1), max_rows),
        "n_cols": min(width, max_cols),
    }


def parse_csv_bytes(data: bytes, encoding: str = "utf-8") -> Dict[str, Any]:
    text = data.decode(encoding, errors="replace")
    reader = csv.reader(io.StringIO(text))
    matrix = [list(row) for row in reader]
    out = cells_from_matrix(matrix)
    out["sheet_names"] = ["Sheet1"]
    out["format"] = "csv"
    return out


def parse_xlsx_bytes(data: bytes) -> Dict[str, Any]:
    try:
        import openpyxl
    except ImportError as e:
        raise RuntimeError("openpyxl not installed — pip install openpyxl") from e
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    names = list(wb.sheetnames)
    sheets: Dict[str, Any] = {}
    first = None
    for name in names:
        ws = wb[name]
        matrix = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= 64:
                break
            matrix.append(list(row)[:54])
        parsed = cells_from_matrix(matrix)
        sheets[name] = {"cells": parsed["cells"]}
        if first is None:
            first = dict(parsed)
    wb.close()
    if first is None:
        first = cells_from_matrix([])
    first["sheets"] = sheets
    first["active_sheet"] = names[0] if names else "Sheet1"
    first["sheet_names"] = names
    first["format"] = "xlsx"
    return first


def download_url(url: str, timeout: int = 30) -> Tuple[bytes, str]:
    if not re.match(r"^https?://", url or "", re.I):
        raise ValueError("only http(s) URLs allowed")
    req = Request(url, headers={"User-Agent": "AccoditeOfficeImport/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
    if len(data) > 25 * 1024 * 1024:
        raise ValueError("download exceeds 25MB")
    return data, ctype


def load_ref(payload_ref: str) -> bytes:
    if payload_ref.startswith("file://"):
        from pathlib import Path as P
        return P(payload_ref[7:]).read_bytes()
    from storage.b2 import b2_get_bytes
    return b2_get_bytes(payload_ref)


def import_spreadsheet(
    *,
    data: Optional[bytes] = None,
    filename: str = "",
    url: str = "",
    payload_ref: str = "",
) -> Dict[str, Any]:
    if url:
        data, _ctype = download_url(url)
        if not filename:
            filename = url.rstrip("/").split("/")[-1] or "download.csv"
    elif payload_ref and data is None:
        data = load_ref(payload_ref)
    if not data:
        raise ValueError("no spreadsheet bytes")
    low = (filename or "").lower()
    if low.endswith(".csv") or low.endswith(".txt"):
        return parse_csv_bytes(data)
    if low.endswith(".xlsx") or low.endswith(".xlsm"):
        return parse_xlsx_bytes(data)
    if data[:2] == b"PK":
        return parse_xlsx_bytes(data)
    return parse_csv_bytes(data)
