from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid

from database import init_db, get_db
from models import DiaryEntry, ChatMessage
from schemas import (
    DiaryEntryCreate, DiaryEntryResponse, ChatMessageCreate, ChatMessageResponse,
    ChatRequest, ChatResponse, PaginatedDiaryEntries, PaginatedChatMessages
)
from embeddings import embedding_store
from agents import ChatWorkflow

app = FastAPI(title="CallItADay", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.post("/api/diaries", response_model=DiaryEntryResponse)
def create_diary(entry: DiaryEntryCreate, db: Session = Depends(get_db)):
    db_entry = DiaryEntry(content=entry.content)
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    embedding_id = embedding_store.add_entry(
        entry_id=str(db_entry.id),
        content=entry.content,
        metadata={
            "created_at": db_entry.created_at.isoformat(),
            "entry_id": db_entry.id
        }
    )

    db_entry.embedding_id = embedding_id
    db.commit()

    return db_entry


@app.get("/api/diaries", response_model=PaginatedDiaryEntries)
def list_diaries(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    total = db.query(DiaryEntry).count()
    entries = db.query(DiaryEntry).order_by(desc(DiaryEntry.created_at)).offset(skip).limit(limit).all()
    has_more = (skip + limit) < total

    return PaginatedDiaryEntries(entries=entries, total=total, has_more=has_more)


@app.get("/api/diaries/search")
def search_diaries(query: str, limit: int = Query(5, ge=1, le=20)):
    results = embedding_store.search_similar(query, n_results=limit)
    return {"results": results}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    user_message = ChatMessage(
        role="user",
        content=request.message,
        session_id=request.session_id
    )
    db.add(user_message)
    db.commit()

    recent_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == request.session_id
    ).order_by(desc(ChatMessage.created_at)).limit(10).all()

    chat_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(recent_messages)
    ]

    workflow = ChatWorkflow(db)
    result = workflow.process_message(
        user_message=request.message,
        chat_history=chat_history[:-1],
        session_id=request.session_id
    )

    assistant_message = ChatMessage(
        role="assistant",
        content=result["response"],
        session_id=request.session_id
    )
    db.add(assistant_message)
    db.commit()

    return ChatResponse(
        response=result["response"],
        tool_calls=result.get("tool_calls")
    )


@app.get("/api/chat", response_model=PaginatedChatMessages)
def list_chat_messages(
    session_id: str = Query("default"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
    total = query.count()
    messages = query.order_by(desc(ChatMessage.created_at)).offset(skip).limit(limit).all()
    has_more = (skip + limit) < total

    return PaginatedChatMessages(messages=list(reversed(messages)), total=total, has_more=has_more)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
