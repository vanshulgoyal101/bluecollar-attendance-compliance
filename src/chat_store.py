"""Conversation + query audit log (F-34).

Appends one JSON object per answered question to ``data/chat_log.jsonl`` so the
team has an append-only audit trail of what was asked, which employees were
referenced, which provider answered and how large the answer was.

Privacy: the only personal identifiers stored are employee IDs (e.g. ``EMP101``)
extracted from the question. Full answer text is not persisted — just its length
— so the log stays free of derived PII while remaining useful for auditing.
"""

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DEFAULT_CHAT_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "chat_log.jsonl"
)

_EMP_ID_RE = re.compile(r"EMP\d+", re.IGNORECASE)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ChatStore:
    """Append-only JSONL store for chat queries and their audit metadata."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or DEFAULT_CHAT_LOG_PATH
        self._lock = threading.Lock()

    def new_conversation_id(self) -> str:
        return uuid.uuid4().hex

    def log_query(
        self,
        question: str,
        result: Dict[str, Any],
        conversation_id: Optional[str] = None,
        employee_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Append an audit record for one answered question and return it."""
        answer = result.get("answer") or ""
        suggestions = result.get("suggestions") or []
        record = {
            "ts": _utc_now_iso(),
            "conversation_id": conversation_id or self.new_conversation_id(),
            "question": question,
            "employee_ids": employee_ids
            if employee_ids is not None
            else self.extract_employee_ids(question),
            "provider": result.get("provider"),
            "model": result.get("model"),
            "grounded": bool(result.get("grounded")),
            "answer_chars": len(answer),
            "suggestions": len(suggestions),
        }
        self.append(record)
        return record

    def append(self, record: Dict[str, Any]) -> None:
        """Append one JSON record as a line. Creates the file/dir if needed."""
        line = json.dumps(record, ensure_ascii=False)
        with self._lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def read_all(self) -> List[Dict[str, Any]]:
        """Read every logged record. Skips malformed lines defensively."""
        if not os.path.exists(self.path):
            return []
        records: List[Dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    @staticmethod
    def extract_employee_ids(text: str) -> List[str]:
        """Return de-duplicated, upper-cased EMP ids referenced in the text."""
        seen: List[str] = []
        for match in _EMP_ID_RE.findall(text or ""):
            token = match.upper()
            if token not in seen:
                seen.append(token)
        return seen
