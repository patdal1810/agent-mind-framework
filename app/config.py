from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AgentMind"
    DATABASE_URL: str
    REDIS_URL: str
    CHROMA_PATH: str = "./chroma_db"
    API_KEY_PREFIX: str = "agm"
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
