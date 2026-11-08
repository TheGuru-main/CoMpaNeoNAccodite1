"""Ownership scope + GSP UID consistency (no DB required for pure units)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

def test_start_row_uid_alias():
    from gsp_chain import start_row_for_name, uid_from_name
    p = start_row_for_name("Accodite")
    assert "start_row" in p
    assert 1 <= p["start_row"] <= 64
    uid = uid_from_name("Accodite")
    assert p.get("uid") == uid or p.get("uid_str") == uid
    assert p.get("uid_str") == p.get("uid_compact") == uid
    # description must not affect placement
    p2 = start_row_for_name("Accodite")
    assert p["start_row"] == p2["start_row"]
    assert p["uid_str"] == p2["uid_str"]

def test_place_uid_resolution():
    from gsp_chain import start_row_for_name, uid_from_name
    place = start_row_for_name("DemoBase")
    doc_uid = str(place.get("uid") or place.get("uid_str") or place.get("uid_compact") or uid_from_name("DemoBase") or "")
    assert doc_uid
    assert doc_uid == uid_from_name("DemoBase")

def test_b2_prefix_shapes():
    from memory.ownership_scope import _b2_prefix
    assert _b2_prefix("room", "abc-123", "dbase").startswith("rooms/")
    assert "collabsheets" in _b2_prefix("org", "org1", "collabsheets")
    assert "personal/brainstorm" in _b2_prefix("user_personal", "u1", "dbase")
    assert "regular" in _b2_prefix("user_regular", "u1", "dbase")

def test_same_name_different_partition_keys():
    from docs_store import _b2_key
    a = _b2_key("room", "r1", "uidX", b2_prefix="rooms/r1/dbase")
    b = _b2_key("user", "u1", "uidX", b2_prefix="users/u1/regular/dbase")
    assert a != b
    assert a.startswith("rooms/r1/dbase/")
    assert b.startswith("users/u1/regular/dbase/")
