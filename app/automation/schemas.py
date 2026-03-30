from pydantic import BaseModel


# ── Inbound webhook payload ────────────────────────────

class InboundEmailPayload(BaseModel):
    from_email: str | None = None
    from_name: str | None = None
    subject: str | None = None
    body: str | None = None
    company: str | None = None


class N8nWebhookPayload(BaseModel):
    source: str = "email"
    data: dict


# ── Classification result ──────────────────────────────

class ClassificationResult(BaseModel):
    category: str
    confidence: int
    reason: str | None = None


# ── Enrichment result ──────────────────────────────────

class EnrichmentResult(BaseModel):
    name: str | None = None
    email: str | None = None
    company: str | None = None
    budget: str | None = None
    intent: str | None = None
    urgency: str | None = None


# ── Webhook response ───────────────────────────────────

class AutomationResponse(BaseModel):
    status: str
    category: str
    enriched: EnrichmentResult
    lead_created: bool
    lead_id: str | None = None