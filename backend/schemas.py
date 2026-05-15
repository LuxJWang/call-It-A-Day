from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class DiaryEntryCreate(BaseModel):
    content: str


class DiaryEntryResponse(BaseModel):
    id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str
    session_id: str = "default"


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
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    tool_calls: Optional[List[dict]] = None


class PaginatedDiaryEntries(BaseModel):
    entries: List[DiaryEntryResponse]
    total: int
    has_more: bool


class PaginatedChatMessages(BaseModel):
    messages: List[ChatMessageResponse]
    total: int
    has_more: bool
