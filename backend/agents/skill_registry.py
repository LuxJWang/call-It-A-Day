from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from agents.chat_agent import ChatAgent
from agents.diary_agent import DiaryAgent
from agents.soul_agent import SoulAgent


SKILL_SPECS = [
    {
        "skill": "chat-manager",
        "description": "查询 chat 记录和数量。",
        "tools": {
            "query_chat_messages": {
                "args": {"session_id": "string", "limit": "integer", "skip": "integer"},
            },
            "count_chat_messages": {
                "args": {"session_id": "string"},
            },
        },
    },
    {
        "skill": "diary-manager",
        "description": "查询 diary 记录，或添加 diary 并按 PostgreSQL/Milvus/ES 模式存储。",
        "tools": {
            "search_diaries": {
                "args": {"query": "string", "limit": "integer"},
            },
            "add_diary": {
                "args": {"content": "string", "occurred_at": "ISO8601 string or null"},
            },
        },
    },
    {
        "skill": "soul-manager",
        "description": "查询和校验修改 diary-soul.md、user-soul.md。",
        "tools": {
            "read_soul_docs": {
                "args": {"names": "array of document names or null"},
            },
            "apply_soul_change": {
                "args": {"document_name": "string", "proposed_content": "string", "reason": "string"},
            },
        },
    },
]


class SkillRegistry:
    def __init__(self, db: Session):
        self.chat_agent = ChatAgent(db)
        self.diary_agent = DiaryAgent(db)
        self.soul_agent = SoulAgent(db)

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        args = args or {}
        if tool_name == "query_chat_messages":
            return self.chat_agent.query_chat_messages(**args)
        if tool_name == "count_chat_messages":
            return self.chat_agent.count_chat_messages(**args)
        if tool_name == "search_diaries":
            return self.diary_agent.search_diaries(**args)
        if tool_name == "add_diary":
            return self.diary_agent.add_diary(**args)
        if tool_name == "read_soul_docs":
            return self.soul_agent.read_soul_docs(**args)
        if tool_name == "apply_soul_change":
            return self.soul_agent.apply_soul_change(**args)
        return {"error": f"Unknown tool: {tool_name}"}

    def specs(self):
        return SKILL_SPECS
