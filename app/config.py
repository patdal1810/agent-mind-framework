from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AgentMind"
    DATABASE_URL: str = "postgresql://postgres:MPiJNQRnSkDRhwYnlwGhnkCDQhFbzxrj@postgres.railway.internal:5432/railway"
    REDIS_URL: str = "redis://default:nKzchSEzjCUAZfVfkiEKmIvBFDsGDGqr@redis.railway.internal:6379"
    CHROMA_PATH: str = "./chroma_db"
    API_KEY_PREFIX: str = "agm"
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    REGISTRATION_INVITE_CODE: str = "AGENTMIND-BETA-001"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-mini"
    
    class Config:
        env_file = ".env"


settings = Settings()
