from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, create_engine
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base, sessionmaker
from config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    password_salt = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    embedding_id = Column(String, nullable=True)

    chunks = relationship("DiaryChunk", back_populates="diary", cascade="all, delete-orphan")


class DiaryChunk(Base):
    __tablename__ = "diary_chunks"

    id = Column(Integer, primary_key=True, index=True)
    diary_id = Column(Integer, ForeignKey("diary_entries.id"), nullable=False, index=True)
    chunk_id = Column(String, nullable=False, unique=True, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    start_offset = Column(Integer, nullable=True)
    end_offset = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    semantic_group_id = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    diary = relationship("DiaryEntry", back_populates="chunks")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String, default="default")


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, index=True)
    purpose = Column(String, nullable=False, unique=True, index=True)
    provider = Column(String, default="openai_compatible")
    base_url = Column(String, nullable=True)
    api_key = Column(Text, nullable=True)
    model = Column(String, nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, nullable=True)
    enabled = Column(Boolean, default=True)
    extra_json = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RuntimeConfig(Base):
    __tablename__ = "runtime_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, nullable=False, unique=True, index=True)
    value_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatRun(Base):
    __tablename__ = "chat_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String, default="default", index=True)
    user_message_id = Column(Integer, nullable=True)
    assistant_message_id = Column(Integer, nullable=True)
    layer1_result_json = Column(JSON, nullable=True)
    response = Column(Text, nullable=True)
    langsmith_run_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatTraceEvent(Base):
    __tablename__ = "chat_trace_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    run_id = Column(String, nullable=False, index=True)
    session_id = Column(String, default="default", index=True)
    layer = Column(String, nullable=True)
    node_name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    tool_name = Column(String, nullable=True)
    input_json = Column(JSON, nullable=True)
    output_json = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    langsmith_run_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SoulDocument(Base):
    __tablename__ = "soul_documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SoulChangeLog(Base):
    __tablename__ = "soul_change_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, nullable=False, index=True)
    previous_content = Column(Text, nullable=True)
    proposed_content = Column(Text, nullable=False)
    applied_content = Column(Text, nullable=True)
    validation_json = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
