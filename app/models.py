from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    purpose = Column(Text, nullable=True)
    capabilities = Column(Text, nullable=True)
    api_key_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)

    permissions = relationship(
        "AgentPermission",
        back_populates="agent",
        cascade="all, delete-orphan",
    )


class AgentPermission(Base):
    __tablename__ = "agent_permissions"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    permission = Column(String(120), nullable=False)

    agent = relationship("Agent", back_populates="permissions")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=False)
    permission_required = Column(String, nullable=False)

    input_schema = Column(JSON, nullable=False)
    validation_rules = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    example_request = Column(JSON, nullable=True)
    example_response = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True)

    is_webhook = Column(Boolean, default=False)
    webhook_url = Column(Text, nullable=True)
    webhook_method = Column(String, default="POST")
    webhook_headers = Column(JSON, nullable=True)
    webhook_timeout_seconds = Column(Integer, default=30)
    

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, nullable=True)
    action = Column(String(120), nullable=False)
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    status = Column(String(40), nullable=False)
    trace_id = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True, index=True)

    task = Column(Text, nullable=False)
    status = Column(String(40), default="created")

    caller_agent_id = Column(Integer, nullable=True)
    assigned_agent_id = Column(Integer, nullable=False)

    response = Column(Text, nullable=True)
    tool_calls = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    trace_id = Column(String(120), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    workflow_id = Column(Integer, ForeignKey("agent_workflows.id"), nullable=True)


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, index=True)

    sender_agent_id = Column(Integer, nullable=False)
    receiver_agent_id = Column(Integer, nullable=False)

    task_id = Column(Integer, nullable=True)

    message_type = Column(String(50), default="task")
    content = Column(Text, nullable=False)

    trace_id = Column(String(120), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class AgentWorkflow(Base):
    __tablename__ = "agent_workflows"

    id = Column(Integer, primary_key=True, index=True)

    objective = Column(Text, nullable=False)

    status = Column(String(40), default="created")

    coordinator_agent_id = Column(Integer, nullable=False)

    shared_context = Column(Text, nullable=True)

    trace_id = Column(String(120), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)