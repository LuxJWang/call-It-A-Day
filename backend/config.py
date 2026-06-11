from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://callitaday:callitaday@localhost:5432/callitaday"
    CHROMA_URL: str = "http://localhost:8000"
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "diary_embeddings"
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_DIARY_INDEX: str = "diary_metadata"
    MODEL_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("MODEL_API_KEY", "OPENAI_API_KEY"),
    )
    MODEL_BASE_URL: str = Field(
        default="",
        validation_alias=AliasChoices("MODEL_BASE_URL", "OPENAI_BASE_URL"),
    )
    DEFAULT_LLM_MODEL: str = Field(
        default="mistral.ministral-3-14b-instruct",
        validation_alias=AliasChoices("DEFAULT_LLM_MODEL", "LLM_MODEL_ID"),
    )
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    COLBERT_MODEL: str = "answerdotai/answerai-colbert-small-v1"
    LANGSMITH_TRACING: bool = False
    LANGSMITH_PROJECT: str = "call-it-a-day"
    LANGSMITH_API_KEY: str = ""
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = Field(
        default="https://api.langfuse.com",
        validation_alias=AliasChoices("LANGFUSE_HOST", "LANGFUSE_BASE_URL"),
    )
    LANGCHAIN_VERBOSE: bool = False
    PROMETHEUS_ENABLED: bool = True
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4317"
    OTEL_INSECURE: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
