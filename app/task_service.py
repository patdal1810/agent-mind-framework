import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AgentTask


def create_task_record(
    db: Session,
    task: str,
    assigned_agent_id: int,
    trace_id: str,
    caller_agent_id: int | None = None,
) -> AgentTask:
    """
    Create a task record before the runtime starts working.

    Status starts as 'created'.
    """

    record = AgentTask(
        task=task,
        status="created",
        caller_agent_id=caller_agent_id,
        assigned_agent_id=assigned_agent_id,
        trace_id=trace_id,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def mark_task_running(
    db: Session,
    task_record: AgentTask,
) -> AgentTask:
    """
    Mark a task as running.

    This tells us the agent runtime has started processing it.
    """

    task_record.status = "running"
    task_record.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task_record)

    return task_record


def mark_task_completed(
    db: Session,
    task_record: AgentTask,
    response: str,
    tool_calls: list[dict[str, Any]],
) -> AgentTask:
    """
    Mark a task as completed and save the final response.
    """

    task_record.status = "completed"
    task_record.response = response
    task_record.tool_calls = json.dumps(tool_calls, default=str)
    task_record.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task_record)

    return task_record


def mark_task_failed(
    db: Session,
    task_record: AgentTask,
    error: str,
    tool_calls: list[dict[str, Any]] | None = None,
) -> AgentTask:
    """
    Mark a task as failed and save the error.
    """

    task_record.status = "failed"
    task_record.error = error
    task_record.tool_calls = json.dumps(tool_calls or [], default=str)
    task_record.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task_record)

    return task_record


def serialize_task(task_record: AgentTask) -> dict[str, Any]:
    """
    Convert database task record into clean JSON for API responses.
    """

    try:
        tool_calls = json.loads(task_record.tool_calls or "[]")
    except Exception:
        tool_calls = []

    return {
        "id": task_record.id,
        "task": task_record.task,
        "status": task_record.status,
        "caller_agent_id": task_record.caller_agent_id,
        "assigned_agent_id": task_record.assigned_agent_id,
        "response": task_record.response,
        "tool_calls": tool_calls,
        "error": task_record.error,
        "trace_id": task_record.trace_id,
        "created_at": task_record.created_at,
        "updated_at": task_record.updated_at,
    }