import uuid
from datetime import datetime

from pydantic import BaseModel


# ── Vapi webhook payload ───────────────────────────────

class VapiMessage(BaseModel):
    type: str
    call: dict | None = None
    transcript: str | None = None
    summary: str | None = None
    recordingUrl: str | None = None


class VapiWebhookPayload(BaseModel):
    message: VapiMessage


# ── Lead qualification result ──────────────────────────

class QualificationResult(BaseModel):
    qualified: bool
    score: int
    budget: str | None = None
    timeline: str | None = None
    intent: str | None = None
    summary: str | None = None


# ── Voice call response ────────────────────────────────

class VoiceCallResponse(BaseModel):
    call_id: uuid.UUID
    qualified: bool
    score: int
    summary: str | None = None
    created_at: datetime | None = None


# ── Outbound call request ──────────────────────────────

class OutboundCallRequest(BaseModel):
    phone_number: str
    lead_name: str | None = None
    assistant_id: str | None = None