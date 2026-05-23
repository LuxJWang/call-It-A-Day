from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://callitaday:callitaday@localhost:5432/callitaday"
    CHROMA_URL: str = "http://localhost:8000"
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "diary_embeddings"
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_DIARY_INDEX: str = "diary_metadata"
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    BEDROCK_URL: str = ""
    BEDROCK_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    LLM_MODEL_ID: str = "mistral.ministral-3-14b-instruct"
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    COLBERT_MODEL: str = "answerdotai/answerai-colbert-small-v1"
    LANGSMITH_TRACING: bool = False
    LANGSMITH_PROJECT: str = "call-it-a-day"
    LANGSMITH_API_KEY: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
