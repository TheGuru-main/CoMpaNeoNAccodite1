"""Accodite Solo-User Bootstrap."""
import uuid
from org.room_types import PERSONAL_BRAINSTORM

def provision_solo_user(*, session, user_id, display_name, language="en"):
    from db_models import AIBrain
    try:
        from db.models_org import Workspace
    except ImportError:
        from models import Workspace

    personal_uid = f"user-{user_id}-brain"
    personal_brain = AIBrain(
        id=uuid.uuid4(), ai_uid=personal_uid, scope_type="user",
        user_id=user_id, memorygrid_uid=f"mg-{personal_uid}", is_active=True,
    )
    session.add(personal_brain)

    workspace = Workspace(
        id=uuid.uuid4(), user_id=user_id, organization_id=None,
        workspace_type=PERSONAL_BRAINSTORM,
        project_name=f"{display_name}'s Brainstorm",
        project_domain="general", ai_invocation="@AI",
    )
    session.add(workspace); session.flush()

    ws_uid = f"ws-{workspace.id}-brain"
    ws_brain = AIBrain(
        id=uuid.uuid4(), ai_uid=ws_uid, scope_type="personal_workspace",
        user_id=user_id, workspace_id=workspace.id,
        memorygrid_uid=f"mg-{ws_uid}", is_active=True,
    )
    session.add(ws_brain); session.flush()

    return {
        "personal_brain_id": personal_brain.id,
        "personal_brain_uid": personal_brain.ai_uid,
        "brainstorm_workspace_id": workspace.id,
        "brainstorm_brain_id": ws_brain.id,
        "brainstorm_brain_uid": ws_brain.ai_uid,
    }
