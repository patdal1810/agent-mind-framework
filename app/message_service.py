from typing import Any

from sqlalchemy.orm import Session

from app.models import AgentMessage


def create_agent_message(
    db: Session,
    sender_agent_id: int,
    receiver_agent_id: int,
    content: str,
    trace_id: str,
    message_type: str = "task",
    task_id: int | None = None,
) -> AgentMessage:
    """
    Save a message between two agents.

    This is separate from task history.
    Task history tracks work.
    Message history tracks communication.
    """

    message = AgentMessage(
        sender_agent_id=sender_agent_id,
        receiver_agent_id=receiver_agent_id,
        task_id=task_id,
        message_type=message_type,
        content=content,
        trace_id=trace_id,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


def serialize_agent_message(message: AgentMessage) -> dict[str, Any]:
    """
    Convert database message object into API-friendly JSON.
    """

    return {
        "id": message.id,
        "sender_agent_id": message.sender_agent_id,
        "receiver_agent_id": message.receiver_agent_id,
        "task_id": message.task_id,
        "message_type": message.message_type,
        "content": message.content,
        "trace_id": message.trace_id,
        "created_at": message.created_at,
    }