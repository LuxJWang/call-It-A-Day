from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from skills.chat_skill import ChatSkill
from skills.diary_skill import DiarySkill
from skills.soul_skill import SoulSkill


class SkillRegistry:
    def __init__(self, db: Session):
        self.chat_skill = ChatSkill(db)
        self.diary_skill = DiarySkill(db)
        self.soul_skill = SoulSkill(db)
        self._tool_map = {
            "query_chat_messages": self.chat_skill.query_chat_messages,
            "count_chat_messages": self.chat_skill.count_chat_messages,
            "search_diaries": self.diary_skill.search_diaries,
            "add_diary": self.diary_skill.add_diary,
            "read_soul_docs": self.soul_skill.read_soul_docs,
            "apply_soul_change": self.soul_skill.apply_soul_change,
        }

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        args = args or {}
        tool = self._tool_map.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        return tool(**args)

    def specs(self) -> List[Dict[str, Any]]:
        return [
            self.chat_skill.tool_specs,
            self.diary_skill.tool_specs,
            self.soul_skill.tool_specs,
        ]
