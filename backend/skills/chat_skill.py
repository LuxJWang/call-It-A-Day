from __future__ import annotations

from typing import Any, Dict, List
from sqlalchemy.orm import Session

from tools.chat_tools import ChatTools


class ChatSkill:
    skill_name = "chat-manager"

    def __init__(self, db: Session):
        self.tools = ChatTools(db)

    @property
    def tool_specs(self) -> Dict[str, Any]:
        return {
            "skill": self.skill_name,
            "description": "Query chat history and counts.",
            "tools": {
                "query_chat_messages": {
                    "description": "Fetch chat messages for a session.",
                    "args": {"session_id": "string", "limit": "integer", "skip": "integer"},
                },
                "count_chat_messages": {
                    "description": "Count messages in a session.",
                    "args": {"session_id": "string"},
                },
            },
        }

    def query_chat_messages(self, session_id: str = "default", limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        return self.tools.query_chat_messages(session_id=session_id, limit=limit, skip=skip)

    def count_chat_messages(self, session_id: str = "default") -> Dict[str, int]:
        return self.tools.count_chat_messages(session_id=session_id)
