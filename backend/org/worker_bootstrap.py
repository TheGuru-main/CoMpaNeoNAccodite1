"""Accodite Org Worker Bootstrap."""
import uuid
from org.room_types import PERSONAL_BRAINSTORM, DEPARTMENT
from org.roles import ROLE_MEMBER

def provision_org_worker(*, session, user_id, organization_id,
                         department, display_name,
                         role=ROLE_MEMBER, added_by=None):
    from db_models import AIBrain
    try:
        from db.models_org import Workspace, WorkspaceMember
    except ImportError:
        from models import Workspace
        WorkspaceMember = None

    brainstorm = Workspace(
        id=uuid.uuid4(), user_id=user_id, organization_id=organization_id,
        workspace_type=PERSONAL_BRAINSTORM,
        project_name=f"{display_name}'s Brainstorm",
        project_domain="general", ai_invocation="@AI",
    )
    session.add(brainstorm); session.flush()

    ws_uid = f"ws-{brainstorm.id}-brain"
    ws_brain = AIBrain(
        id=uuid.uuid4(), ai_uid=ws_uid, scope_type="personal_workspace",
        user_id=user_id, organization_id=organization_id,
        workspace_id=brainstorm.id,
        memorygrid_uid=f"mg-{ws_uid}", is_active=True,
    )
    session.add(ws_brain)

    dept_room = (
        session.query(Workspace)
        .filter_by(organization_id=organization_id,
                   workspace_type=DEPARTMENT,
                   project_name=department)
        .first()
    )
    if dept_room is not None and WorkspaceMember is not None:
        session.add(WorkspaceMember(
            workspace_id=dept_room.id, user_id=user_id, added_by=added_by,
        ))

    session.flush()
    return {
        "brainstorm_workspace_id": brainstorm.id,
        "brainstorm_brain_uid": ws_brain.ai_uid,
        "department_room_id": dept_room.id if dept_room else None,
    }
