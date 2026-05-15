import chromadb
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Memory


client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
collection = client.get_or_create_collection(name="agent_memories")


def save_memory(db: Session, agent_id: int, content: str):
    memory = Memory(agent_id=agent_id, content=content)

    db.add(memory)
    db.commit()
    db.refresh(memory)

    collection.add(
        ids=[str(memory.id)],
        documents=[content],
        metadatas=[{"agent_id": agent_id}],
    )

    existing = db.query(Memory).filter(
        Memory.agent_id == agent_id,
        Memory.content == content
    ).first()

    if existing:
        return existing
    
    return memory


def search_memory(agent_id: int, query: str, limit: int = 5):
    results = collection.query(
        query_texts=[query],
        n_results=limit,
        where={"agent_id": agent_id},
    )

    return results.get("documents", [[]])[0]