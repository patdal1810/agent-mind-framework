import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AgentWorkflow


def create_workflow(
    db: Session,
    objective: str,
    coordinator_agent_id: int,
    trace_id: str,
) -> AgentWorkflow:
    workflow = AgentWorkflow(
        objective=objective,
        coordinator_agent_id=coordinator_agent_id,
        status="created",
        shared_context=json.dumps(
            {
                "objective": objective,
                "messages": [],
                "completed_steps": [],
                "pending_steps": [],
            }
        ), trace_id=trace_id,
    )

    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    return workflow



def mark_workflow_running(
    db: Session,
    workflow: AgentWorkflow,
):
    workflow.status = "running"
    workflow.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(workflow)

    return workflow

def mark_workflow_completed(
    db: Session,
    workflow: AgentWorkflow,
):
    workflow.status = "completed"
    workflow.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(workflow)

    return workflow



def mark_workflow_failed(
    db: Session,
    workflow: AgentWorkflow,
):
    workflow.status = "failed"
    workflow.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(workflow)

    return workflow


def get_workflow_context(
    workflow: AgentWorkflow,
) -> dict[str, Any]:
    try:
        return json.loads(workflow.shared_context or "{}")
    except Exception:
        return {}



def update_workflow_context(
    db: Session,
    workflow: AgentWorkflow,
    context_data: dict[str, Any],
):
    workflow.shared_context = json.dumps(
        context_data,
        default=str,
    )

    workflow.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(workflow)

    return workflow