from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import ChatMessage


class ChatAgent:
    skill_name = "chat-manager"

    def __init__(self, db: Session):
        self.db = db

    def query_chat_messages(self, session_id: str = "default", limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": row.id,
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.isoformat(),
                "session_id": row.session_id,
            }
            for row in reversed(rows)
        ]

    def count_chat_messages(self, session_id: str = "default") -> Dict[str, int]:
        total = self.db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
        return {"total": total}
