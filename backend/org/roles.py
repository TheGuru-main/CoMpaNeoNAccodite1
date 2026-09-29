"""Accodite Role Constants."""
ROLE_OWNER="owner"; ROLE_CEO="ceo"; ROLE_C_SUITE="c_suite"; ROLE_HR="hr"
ROLE_DEPT_HEAD="dept_head"; ROLE_MANAGER="manager"; ROLE_MEMBER="member"
ROLE_REVIEWER="reviewer"; ROLE_VIEWER="viewer"; ROLE_AGENT="agent"
DEFAULT_ORG_ROLE = ROLE_MEMBER
ROLE_RANK = {ROLE_OWNER:0,ROLE_CEO:1,ROLE_C_SUITE:2,ROLE_HR:3,
             ROLE_DEPT_HEAD:4,ROLE_MANAGER:5,ROLE_MEMBER:6,
             ROLE_REVIEWER:7,ROLE_VIEWER:8,ROLE_AGENT:9}
LTM_ACCESS_ROLES = frozenset({ROLE_OWNER,ROLE_CEO,ROLE_C_SUITE,ROLE_HR})
def can_read_ltm(r): return r in LTM_ACCESS_ROLES
def can_write_ltm(r): return r in {ROLE_OWNER,ROLE_CEO,ROLE_C_SUITE}
def can_create_room(r):
    return r in {ROLE_OWNER,ROLE_CEO,ROLE_C_SUITE,ROLE_HR,ROLE_DEPT_HEAD,ROLE_MANAGER}
def outranks(a,b): return ROLE_RANK.get(a,999) < ROLE_RANK.get(b,999)
