from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Agent
from app.security import verify_api_key


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_agent(
    x_agent_key: str = Header(...),
    db: Session = Depends(get_db),
):
    agents = db.query(Agent).filter(Agent.is_active == True).all()

    for agent in agents:
        if verify_api_key(x_agent_key, agent.api_key_hash):
            return agent

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid agent API key",
    )


def require_permission(permission: str):
    def checker(agent: Agent = Depends(get_current_agent)):
        permissions = [p.permission for p in agent.permissions]

        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )

        return agent

    return checker