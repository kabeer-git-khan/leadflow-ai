import uuid
from datetime import datetime

from pydantic import BaseModel


# ── Ingest ─────────────────────────────────────────────

class IngestResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    chunk_count: int
    status: str


# ── Chat ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[str]


# ── Session ────────────────────────────────────────────

class SessionResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]
    created_at: datetime | None = None