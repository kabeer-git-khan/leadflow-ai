import uuid
from datetime import datetime

from pydantic import BaseModel


# ── Request ────────────────────────────────────────────

class ExtractionRequest(BaseModel):
    document_id: uuid.UUID | None = None


# ── Extracted lead data ────────────────────────────────

class ExtractedLeadData(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    budget: str | None = None
    timeline: str | None = None
    service_interest: str | None = None
    notes: str | None = None


# ── Response ───────────────────────────────────────────

class ExtractionResponse(BaseModel):
    extraction_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    extracted_data: ExtractedLeadData
    tokens_used: int
    created_at: datetime | None = None