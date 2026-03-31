import uuid
from datetime import datetime

from pydantic import BaseModel


# ── Lead response ──────────────────────────────────────

class LeadResponse(BaseModel):
    id: uuid.UUID
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    source: str
    status: str
    score: int
    crm_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ── Lead list response ─────────────────────────────────

class LeadListResponse(BaseModel):
    total: int
    leads: list[LeadResponse]


# ── Dashboard stats ────────────────────────────────────

class DashboardStats(BaseModel):
    total_leads: int
    qualified_leads: int
    new_leads: int
    nurture_leads: int
    converted_leads: int
    leads_by_source: dict
    total_voice_calls: int
    total_documents: int
    total_extractions: int