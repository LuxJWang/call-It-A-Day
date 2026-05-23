from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from llm import get_llm_for_purpose
from models import SoulChangeLog, SoulDocument

SOUL_DIR = os.path.join(os.path.dirname(__file__), "..", "soul")


class SoulService:
    def __init__(self, db: Session):
        self.db = db

    def read_docs(self, names: List[str] | None = None) -> Dict[str, str]:
        query = self.db.query(SoulDocument)
        if names:
            query = query.filter(SoulDocument.name.in_(names))
        return {doc.name: doc.content for doc in query.all()}

    def propose_and_apply(self, document_name: str, proposed_content: str, reason: str = "") -> Dict[str, Any]:
        doc = self.db.query(SoulDocument).filter(SoulDocument.name == document_name).first()
        previous = doc.content if doc else ""
        validation = self._validate(document_name, previous, proposed_content, reason)
        status = "rejected"
        applied_content = None

        if validation.get("allowed"):
            if doc:
                doc.content = proposed_content
            else:
                doc = SoulDocument(name=document_name, content=proposed_content)
                self.db.add(doc)
            applied_content = proposed_content
            status = "applied"
            self._write_snapshot(document_name, proposed_content)

        log = SoulChangeLog(
            document_name=document_name,
            previous_content=previous,
            proposed_content=proposed_content,
            applied_content=applied_content,
            validation_json=validation,
            status=status,
            reason=validation.get("reason"),
        )
        self.db.add(log)
        self.db.commit()
        return {"status": status, "validation": validation, "document_name": document_name}

    def _validate(self, document_name: str, previous: str, proposed: str, reason: str) -> Dict[str, Any]:
        docs = self.read_docs(["soul_system_prompt.md"])
        system_prompt = docs.get("soul_system_prompt.md", "")
        prompt = f"""请校验 proposed content 是否适合作为 {document_name} 的新内容。

修改原因：{reason}

原内容：
{previous}

新内容：
{proposed}

返回 JSON only：
{{"allowed": true/false, "reason": "原因", "suggestions": []}}"""
        try:
            llm = get_llm_for_purpose("tool_enrichment")
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ])
            return json.loads(_extract_json(response.content))
        except Exception as exc:
            return {
                "allowed": False,
                "reason": f"validation failed: {exc}",
                "suggestions": ["请稍后重试，或检查模型配置。"],
            }

    def _write_snapshot(self, document_name: str, content: str):
        os.makedirs(SOUL_DIR, exist_ok=True)
        path = os.path.join(SOUL_DIR, document_name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def _extract_json(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        return content[start:end]
    return content
