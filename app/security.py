import hashlib
import secrets

from app.config import settings


def create_api_key() -> str:
    raw_token = secrets.token_urlsafe(32)
    return f"{settings.API_KEY_PREFIX}_{raw_token}"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    incoming_hash = hash_api_key(api_key)
    return secrets.compare_digest(incoming_hash, hashed_key)