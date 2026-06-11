from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from tools.soul_tools import SoulTools


class SoulSkill:
    skill_name = "soul-manager"

    def __init__(self, db: Session):
        self.tools = SoulTools(db)

    @property
    def tool_specs(self) -> Dict[str, Any]:
        return {
            "skill": self.skill_name,
            "description": "Read soul documents and validate proposed soul updates.",
            "tools": {
                "read_soul_docs": {
                    "description": "Read soul documents and return their latest content.",
                    "args": {"names": "array of document names or null"},
                },
                "apply_soul_change": {
                    "description": "Validate and apply a proposed change to a soul document.",
                    "args": {"document_name": "string", "proposed_content": "string", "reason": "string"},
                },
            },
        }

    def read_soul_docs(self, names: Optional[List[str]] = None) -> Dict[str, str]:
        return self.tools.read_soul_docs(names)

    def apply_soul_change(self, document_name: str, proposed_content: str, reason: str = "") -> Dict[str, Any]:
        return self.tools.apply_soul_change(document_name, proposed_content, reason=reason)
