import json
import uuid

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import Lead, LeadSource, LeadStatus
from app.automation.schemas import ClassificationResult, EnrichmentResult

settings = get_settings()

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    model="gpt-4o-mini",
    temperature=0,
)


# ── Classification ─────────────────────────────────────

async def classify_inbound(text: str) -> ClassificationResult:
    messages = [
        SystemMessage(content="""You are a lead classification expert.
Classify the inbound message into one of these categories:
- lead: genuine business inquiry with potential to convert
- support: existing customer needing help
- spam: irrelevant or promotional message

Return ONLY a valid JSON object:
{
    "category": "lead or support or spam",
    "confidence": number between 0 and 100,
    "reason": "one sentence explanation"
}"""),
        HumanMessage(content=f"Message:\n{text}"),
    ]

    response = await llm.ainvoke(messages)

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return ClassificationResult(**data)
    except Exception:
        return ClassificationResult(
            category="spam",
            confidence=0,
            reason="Could not parse classification",
        )


# ── Enrichment ─────────────────────────────────────────

async def enrich_lead_data(text: str) -> EnrichmentResult:
    messages = [
        SystemMessage(content="""You are a data enrichment expert.
Extract lead information from the message below.
Return ONLY a valid JSON object:
{
    "name": "full name or null",
    "email": "email address or null",
    "company": "company name or null",
    "budget": "budget mentioned or null",
    "intent": "what they are looking for or null",
    "urgency": "high, medium, low or null"
}"""),
        HumanMessage(content=f"Message:\n{text}"),
    ]

    response = await llm.ainvoke(messages)

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return EnrichmentResult(**data)
    except Exception:
        return EnrichmentResult()


# ── Save lead ──────────────────────────────────────────

async def save_lead_from_automation(
    db: AsyncSession,
    client_id: str,
    enriched: EnrichmentResult,
) -> Lead:
    lead = Lead(
        client_id=uuid.UUID(client_id),
        name=enriched.name,
        email=enriched.email,
        company=enriched.company,
        source=LeadSource.email,
        status=LeadStatus.new,
        metadata_={
            "budget": enriched.budget,
            "intent": enriched.intent,
            "urgency": enriched.urgency,
        },
    )
    db.add(lead)
    await db.flush()
    return lead