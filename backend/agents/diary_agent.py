from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from services.diary_service import DiaryRetrievalService, DiaryStorageService


class DiaryAgent:
    skill_name = "diary-manager"

    def __init__(self, db: Session):
        self.db = db

    def search_diaries(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        return DiaryRetrievalService(self.db).search(query, limit=limit)

    def add_diary(self, content: str, occurred_at: Optional[str] = None) -> Dict[str, Any]:
        parsed = None
        if occurred_at:
            try:
                parsed = datetime.fromisoformat(occurred_at)
            except ValueError:
                parsed = None
        entry = DiaryStorageService(self.db).add_diary(content, occurred_at=parsed)
        return {
            "id": entry.id,
            "title": entry.title,
            "created_at": entry.created_at.isoformat(),
            "metadata": entry.metadata_json,
        }
