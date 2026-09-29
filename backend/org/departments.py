"""Accodite Department Rooms."""
import uuid
from org.room_types import DEPARTMENT

def create_department_room(*, session, organization_id,
                           department_name, created_by):
    from db_models import AIBrain
    try:
        from db.models_org import Workspace, WorkspaceMember
    except ImportError:
        from models import Workspace
        WorkspaceMember = None

    existing = (
        session.query(Workspace)
        .filter_by(organization_id=organization_id,
                   workspace_type=DEPARTMENT,
                   project_name=department_name)
        .first()
    )
    if existing:
        return existing

    room = Workspace(
        id=uuid.uuid4(), user_id=None, organization_id=organization_id,
        workspace_type=DEPARTMENT, project_name=department_name,
        project_domain="general", ai_invocation="@AI",
    )
    session.add(room); session.flush()

    ws_uid = f"ws-{room.id}-brain"
    session.add(AIBrain(
        id=uuid.uuid4(), ai_uid=ws_uid, scope_type="team_workspace",
        organization_id=organization_id, workspace_id=room.id,
        memorygrid_uid=f"mg-{ws_uid}", is_active=True,
    ))

    if WorkspaceMember is not None:
        session.add(WorkspaceMember(
            workspace_id=room.id, user_id=created_by, added_by=created_by,
        ))

    session.flush()
    return room
