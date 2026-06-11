from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid

from database import SessionLocal, init_db, get_db
from models import (
    ChatMessage, ChatRun, ChatTraceEvent, DiaryEntry, ModelConfig, RuntimeConfig, SoulDocument
)
from schemas import (
    DiaryEntryCreate, DiaryEntryResponse, ChatMessageCreate, ChatMessageResponse,
    ChatRequest, ChatResponse, ModelConfigPayload, ModelConfigResponse,
    PaginatedDiaryEntries, PaginatedChatMessages, RuntimeConfigPayload,
    RuntimeConfigResponse, SoulDocumentResponse, TraceEventResponse
)
from agents import ChatWorkflow
from observability import init_observability, PrometheusMiddleware, metrics_response
from services.config_registry import config_registry
from services.diary_service import DiaryRetrievalService, DiaryStorageService

app = FastAPI(title="CallItADay", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(PrometheusMiddleware)


@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        config_registry.load_from_db(db)
    finally:
        db.close()
    init_observability()


@app.post("/api/diaries", response_model=DiaryEntryResponse)
def create_diary(entry: DiaryEntryCreate, db: Session = Depends(get_db)):
    return DiaryStorageService(db).add_diary(entry.content, occurred_at=entry.occurred_at)


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
def search_diaries(query: str, limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    results = DiaryRetrievalService(db).search(query, limit=limit)
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
        session_id=request.session_id,
        user_message_id=user_message.id,
    )

    assistant_message = ChatMessage(
        role="assistant",
        content=result["response"],
        session_id=request.session_id
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    run = db.query(ChatRun).filter(ChatRun.run_id == result["run_id"]).first()
    if run:
        run.assistant_message_id = assistant_message.id
        run.response = result["response"]
        db.commit()

    trace_events = db.query(ChatTraceEvent).filter(
        ChatTraceEvent.run_id == result["run_id"]
    ).order_by(ChatTraceEvent.created_at.asc()).all()

    return ChatResponse(
        response=result["response"],
        tool_calls=result.get("tool_calls"),
        run_id=result.get("run_id"),
        trace_events=[
            {
                "id": event.id,
                "run_id": event.run_id,
                "session_id": event.session_id,
                "layer": event.layer,
                "node_name": event.node_name,
                "event_type": event.event_type,
                "tool_name": event.tool_name,
                "input_json": event.input_json,
                "output_json": event.output_json,
                "latency_ms": event.latency_ms,
                "created_at": event.created_at.isoformat(),
            }
            for event in trace_events
        ],
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


@app.get("/metrics")
def metrics():
    return metrics_response()


@app.get("/api/model-configs", response_model=List[ModelConfigResponse])
def list_model_configs(db: Session = Depends(get_db)):
    return db.query(ModelConfig).order_by(ModelConfig.purpose.asc()).all()


@app.put("/api/model-configs/{purpose}", response_model=ModelConfigResponse)
def update_model_config(purpose: str, payload: ModelConfigPayload, db: Session = Depends(get_db)):
    row = db.query(ModelConfig).filter(ModelConfig.purpose == purpose).first()
    if not row:
        row = ModelConfig(purpose=purpose)
        db.add(row)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    config_registry.set_model(row)
    return row


@app.get("/api/runtime-configs", response_model=List[RuntimeConfigResponse])
def list_runtime_configs(db: Session = Depends(get_db)):
    return db.query(RuntimeConfig).order_by(RuntimeConfig.key.asc()).all()


@app.put("/api/runtime-configs/{key}", response_model=RuntimeConfigResponse)
def update_runtime_config(key: str, payload: RuntimeConfigPayload, db: Session = Depends(get_db)):
    row = db.query(RuntimeConfig).filter(RuntimeConfig.key == key).first()
    if not row:
        row = RuntimeConfig(key=key, value_json=payload.value_json)
        db.add(row)
    else:
        row.value_json = payload.value_json
    db.commit()
    db.refresh(row)
    config_registry.set_runtime(row)
    return row


@app.get("/api/chat/runs/{run_id}/trace", response_model=List[TraceEventResponse])
def get_chat_trace(run_id: str, db: Session = Depends(get_db)):
    return db.query(ChatTraceEvent).filter(
        ChatTraceEvent.run_id == run_id
    ).order_by(ChatTraceEvent.created_at.asc()).all()


@app.get("/api/soul-docs", response_model=List[SoulDocumentResponse])
def list_soul_docs(db: Session = Depends(get_db)):
    return db.query(SoulDocument).order_by(SoulDocument.name.asc()).all()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
