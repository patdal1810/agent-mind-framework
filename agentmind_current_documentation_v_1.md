# AgentMind Documentation

## Overview

AgentMind is an autonomous multi-agent orchestration framework that allows developers to:

- Create AI agents
- Register custom tools
- Connect webhook APIs
- Delegate tasks between agents
- Build workflows
- Persist shared memory
- Track agent communication
- Execute autonomous multi-step reasoning

AgentMind is designed to be developer-first.

Developers can use AgentMind to build:

- Banking systems
- Logistics systems
- Research assistants
- Customer support agents
- AI workflow orchestration systems
- Multi-agent enterprise platforms

---

# Core Architecture

AgentMind is built around 3 major concepts:

## 1. Agents

Agents are autonomous AI workers.

Each agent has:

- Name
- Purpose
- Capabilities
- Permissions
- API Key

Example:

```text
BankGuard Fraud Agent
```

Purpose:

```text
Investigates suspicious banking transactions and uses fraud analysis tools.
```

---

## 2. Capabilities

Capabilities describe what an agent is GOOD AT.

Examples:

```text
fraud_detection
summarization
routing
coordination
credit_risk
web_research
```

Capabilities are used for:

- Agent discovery
- Delegation
- Routing
- LLM reasoning

IMPORTANT:

Capabilities DO NOT automatically grant execution rights.

---

## 3. Permissions

Permissions describe what an agent is ALLOWED TO EXECUTE.

Examples:

```text
memory:read
memory:write
agents:delegate
tools:fraud_checker:run
tools:loan_evaluator:run
```

Permissions are used for:

- Security
- Tool access control
- Enterprise governance
- Agent isolation

IMPORTANT:

An agent may have a capability without permission.

Example:

```text
Capability:
web_research

BUT

No permission:
tools:url_reader:run
```

That agent understands web research conceptually but cannot execute the tool.

---

# Tool System

AgentMind supports:

- Internal tools
- Python tools
- Webhook tools

---

## Internal Tools

Example:

```text
calculator
quadratic_solver
memory_search
```

These are built directly into AgentMind.

---

## Webhook Tools

Webhook tools allow developers to connect external systems.

Examples:

```text
fraud_checker
loan_evaluator
shipment_tracker
inventory_checker
```

Webhook tools are registered dynamically.

Example:

```json
{
  "name": "fraud_checker",
  "permission_required": "tools:fraud_checker:run",
  "is_webhook": true,
  "webhook_url": "http://127.0.0.1:9000/fraud-check",
  "webhook_method": "POST"
}
```

---

# Multi-Agent Delegation

AgentMind supports autonomous agent delegation.

Coordinator agents can:

- Discover specialist agents
- Route tasks
- Delegate subtasks
- Aggregate results
- Produce final outputs

Example flow:

```text
Coordinator Agent
→ Fraud Agent
→ fraud_checker webhook
→ Loan Agent
→ loan_evaluator webhook
→ Summary Agent
→ Final recommendation
```

---

# Workflow System

Workflows provide:

- Shared context
- Multi-step execution
- Long-running coordination
- Agent collaboration
- Workflow history

Workflow states:

```text
created
running
completed
failed
```

Each workflow stores:

- Messages
- Completed steps
- Pending steps
- Delegation history
- Tool calls

---

# Memory System

AgentMind includes shared memory.

Permissions:

```text
memory:read
memory:write
```

Memory allows agents to:

- Recall previous tasks
- Share workflow context
- Persist knowledge
- Store summaries

Example:

```text
User prefers concise reports.
```

---

# Agent Types

## Coordinator Agent

Responsibilities:

- Routing
- Delegation
- Workflow management
- Shared context management

Recommended permissions:

```text
agents:delegate
memory:read
memory:write
```

Coordinator agents should NOT usually have specialist tool permissions.

---

## Specialist Agent

Responsibilities:

- Domain-specific reasoning
- Tool execution
- Specialized analysis

Examples:

```text
Fraud Agent
Loan Agent
Research Agent
Delivery Risk Agent
```

---

## Summary Agent

Responsibilities:

- Executive summaries
- Final recommendations
- Human-readable reporting

Summary agents should ideally:

- Have no tool permissions
- Avoid memory access unless required

---

# Streamlit Studio

AgentMind Studio provides a visual interface for:

- Registering agents
- Registering webhook tools
- Viewing workflows
- Running tasks
- Viewing messages
- Viewing tool calls
- Autonomous workflow testing

Current tabs:

```text
Register Agent
Current Agent
Tools
Webhook Tools
Workflows
Run Task
Tasks
Messages
BankGuard Demo
```

---

# BankGuard Autonomous Multi-Agent Demo

The BankGuard demo demonstrates:

- Multi-agent orchestration
- Autonomous delegation
- Webhook execution
- Workflow coordination
- Final recommendation synthesis

Agents:

```text
BankGuard Autonomous Coordinator Agent
BankGuard Fraud Agent
BankGuard Loan Agent
BankGuard Summary Agent
```

Webhook tools:

```text
fraud_checker
loan_evaluator
```

Example execution:

```text
Coordinator Agent
→ delegates fraud task
→ Fraud Agent calls fraud_checker
→ delegates loan task
→ Loan Agent calls loan_evaluator
→ delegates summary task
→ Summary Agent creates final recommendation
```

---

# Current Features Implemented

## Agent Features

- Agent registration
- API key generation
- Capability-based routing
- Permission-based execution
- Autonomous delegation
- Agent-to-agent messaging

---

## Tool Features

- Internal tools
- Dynamic webhook tools
- Tool registry
- Tool permissions
- Tool schemas
- Tool validation

---

## Workflow Features

- Workflow creation
- Shared workflow context
- Workflow state tracking
- Delegation history
- Tool execution history

---

## Memory Features

- Shared memory
- Memory search
- Memory persistence

---

## Runtime Features

- Autonomous multi-step reasoning
- Recursive delegation
- Tool execution loops
- Dynamic routing
- Multi-agent coordination

---

# Recommended Architecture

## Best Practice

```text
Coordinator
→ delegates work
→ Specialist agents execute tools
→ Summary agents create final outputs
```

Avoid:

```text
Coordinator doing all specialist work itself
```

---

# Example Real-World Use Cases

## Banking

Agents:

```text
Fraud Agent
Loan Agent
Compliance Agent
Summary Agent
```

---

## Logistics

Agents:

```text
Shipment Tracking Agent
Delivery Risk Agent
Inventory Agent
Customer Support Agent
```

---

## Healthcare

Agents:

```text
Triage Agent
Medical Research Agent
Appointment Agent
Summary Agent
```

---

## Research Platform

Agents:

```text
Web Research Agent
RSS Monitoring Agent
Report Generator Agent
```

---

# Current Improvements Planned

## Planned Features

- Human approval workflows
- Agent editing UI
- Agent deletion UI
- Tool argument validation
- Workflow graphs
- Realtime workflow streaming
- Agent marketplace
- MCP support improvements
- Multi-tenant architecture
- Async task queues
- Agent scheduling
- Tool retry policies
- Vector memory upgrades
- Role templates
- RBAC
- Docker deployment
- Cloud deployment templates

---

# Key Learning Concepts

## Capabilities vs Permissions

Capabilities:

```text
What the agent is good at.
```

Permissions:

```text
What the agent is allowed to execute.
```

---

## Autonomous Agent Design

Good architecture:

```text
Coordinator
→ delegates
→ specialists execute
→ summaries generated
```

---

## Enterprise Design Principle

Never give all agents all permissions.

Use:

- Principle of least privilege
- Specialized agents
- Permission isolation
- Controlled delegation

---

# Current Tech Stack

Backend:

```text
FastAPI
SQLAlchemy
PostgreSQL
Redis
OpenAI API
```

Frontend:

```text
Streamlit
```

Runtime:

```text
Python
Webhook APIs
OpenAI function calling
```

---

# Conclusion

AgentMind is evolving into a full autonomous multi-agent orchestration platform.

The current implementation already supports:

- Multi-agent coordination
- Autonomous delegation
- Tool execution
- Webhook integration
- Workflow management
- Shared memory
- Agent messaging
- Specialist routing

This provides a strong foundation for building enterprise-grade AI agent systems.

