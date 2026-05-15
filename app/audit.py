import json
import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


def create_trace_id() -> str:
    return f"trace_{uuid.uuid4().hex}"


def write_audit_log(
    db: Session,
    agent_id: int | None,
    action: str,
    input_data,
    output_data,
    status: str,
    trace_id: str,
):
    log = AuditLog(
        agent_id=agent_id,
        action=action,
        input_data=json.dumps(input_data, default=str),
        output_data=json.dumps(output_data, default=str),
        status=status,
        trace_id=trace_id,
    )

    db.add(log)
    db.commit()