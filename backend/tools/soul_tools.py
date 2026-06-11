from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from services.soul_service import SoulService


class SoulTools:
    def __init__(self, db: Session):
        self.service = SoulService(db)

    def read_soul_docs(self, names: Optional[List[str]] = None) -> Dict[str, str]:
        return self.service.read_docs(names)

    def apply_soul_change(self, document_name: str, proposed_content: str, reason: str = "") -> Dict[str, Any]:
        return self.service.propose_and_apply(document_name, proposed_content, reason=reason)
