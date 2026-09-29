"""Accodite Room (Workspace) Types."""
PERSONAL_BRAINSTORM="personal_brainstorm"; GROUP="group"
DEPARTMENT="department"; TEAM="team"; MEETING="meeting"; ORGANIZATION="organization"
ALL_ROOM_TYPES = frozenset({PERSONAL_BRAINSTORM,GROUP,DEPARTMENT,
                            TEAM,MEETING,ORGANIZATION})
INVITE_ONLY = frozenset({DEPARTMENT,TEAM,MEETING,ORGANIZATION})
FLUSH_TO_LTM = frozenset({MEETING})
SOLO_DEFAULT = frozenset({PERSONAL_BRAINSTORM})
