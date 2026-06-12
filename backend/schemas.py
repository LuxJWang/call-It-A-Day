from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DiaryEntryCreate(BaseModel):
    content: str
    occurred_at: Optional[datetime] = None


class DiaryEntryResponse(BaseModel):
    id: int
    title: Optional[str] = None
    content: str
    metadata_json: Optional[Dict[str, Any]] = None
    occurred_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    session_id: str

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: Optional[List[dict]] = None
    run_id: Optional[str] = None
    trace_events: Optional[List[dict]] = None
    session_id: Optional[str] = None


class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str


class AuthResponse(BaseModel):
    username: str
    token: str


class ChatSessionResponse(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    expired: bool

    class Config:
        from_attributes = True


class ModelConfigPayload(BaseModel):
    provider: str = "openai_compatible"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    enabled: bool = True
    extra_json: Optional[Dict[str, Any]] = None


class ModelConfigResponse(ModelConfigPayload):
    purpose: str
    updated_at: datetime

    class Config:
        from_attributes = True


class RuntimeConfigPayload(BaseModel):
    value_json: Dict[str, Any]


class RuntimeConfigResponse(BaseModel):
    key: str
    value_json: Dict[str, Any]
    updated_at: datetime

    class Config:
        from_attributes = True


class TraceEventResponse(BaseModel):
    id: int
    run_id: str
    session_id: str
    layer: Optional[str] = None
    node_name: str
    event_type: str
    tool_name: Optional[str] = None
    input_json: Optional[Dict[str, Any]] = None
    output_json: Optional[Dict[str, Any]] = None
    latency_ms: Optional[int] = None
    langsmith_run_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SoulDocumentResponse(BaseModel):
    name: str
    content: str
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedDiaryEntries(BaseModel):
    entries: List[DiaryEntryResponse]
    total: int
    has_more: bool


class PaginatedChatMessages(BaseModel):
    messages: List[ChatMessageResponse]
    total: int
    has_more: bool
