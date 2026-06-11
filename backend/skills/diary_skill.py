from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from services.diary_service import DiaryRetrievalService, DiaryStorageService


class DiarySkill:
    skill_name = "diary-manager"

    def __init__(self, db: Session):
        self.db = db
        self.storage_service = DiaryStorageService(db)
        self.retrieval_service = DiaryRetrievalService(db)

    @property
    def tool_specs(self) -> Dict[str, Any]:
        return {
            "skill": self.skill_name,
            "description": "Search and add diary entries using the persistence and retrieval stack.",
            "tools": {
                "search_diaries": {
                    "description": "Search diary entries with hybrid retrieval.",
                    "args": {"query": "string", "limit": "integer"},
                },
                "add_diary": {
                    "description": "Add a diary entry and trigger indexing pipelines.",
                    "args": {"content": "string", "occurred_at": "ISO8601 string or null"},
                },
            },
        }

    def search_diaries(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.retrieval_service.search(query, limit=limit)

    def add_diary(self, content: str, occurred_at: Optional[str] = None) -> Dict[str, Any]:
        parsed_occurred_at = None
        if occurred_at:
            try:
                from datetime import datetime

                parsed_occurred_at = datetime.fromisoformat(occurred_at)
            except ValueError:
                parsed_occurred_at = None

        entry = self.storage_service.add_diary(content, occurred_at=parsed_occurred_at)
        return {
            "id": entry.id,
            "title": entry.title,
            "created_at": entry.created_at.isoformat(),
            "metadata": entry.metadata_json,
        }
