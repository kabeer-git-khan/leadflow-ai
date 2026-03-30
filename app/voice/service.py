import json
import uuid

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import Lead, LeadSource, LeadStatus, VoiceCall
from app.voice.schemas import QualificationResult, VapiWebhookPayload

settings = get_settings()

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    model="gpt-4o-mini",
    temperature=0,
)


# ── Qualification logic ────────────────────────────────

async def qualify_lead_from_transcript(transcript: str) -> QualificationResult:
    messages = [
        SystemMessage(content="""You are a lead qualification expert.
Analyze the call transcript and extract the following information.
Return ONLY a valid JSON object with these exact keys:
{
    "qualified": true or false,
    "score": number between 0 and 100,
    "budget": "budget mentioned or null",
    "timeline": "timeline mentioned or null",
    "intent": "brief description of what they want",
    "summary": "one sentence summary of the call"
}
A lead is qualified if they have a clear need, budget, and timeline."""),
        HumanMessage(content=f"Transcript:\n{transcript}"),
    ]

    response = await llm.ainvoke(messages)

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return QualificationResult(**data)
    except Exception:
        return QualificationResult(
            qualified=False,
            score=0,
            summary="Could not parse qualification result",
        )


# ── Save call to database ──────────────────────────────

async def save_voice_call(
    db: AsyncSession,
    client_id: str,
    vapi_call_id: str | None,
    transcript: str | None,
    qualification: QualificationResult,
    call_data: dict,
) -> VoiceCall:
    lead = Lead(
        client_id=uuid.UUID(client_id),
        source=LeadSource.voice,
        status=LeadStatus.qualified if qualification.qualified else LeadStatus.nurture,
        score=qualification.score,
        metadata_={
            "budget": qualification.budget,
            "timeline": qualification.timeline,
            "intent": qualification.intent,
        },
    )
    db.add(lead)
    await db.flush()

    call = VoiceCall(
        lead_id=lead.id,
        vapi_call_id=vapi_call_id,
        transcript=transcript,
        qualified=qualification.qualified,
        duration_seconds=call_data.get("duration", 0),
        call_data=call_data,
    )
    db.add(call)
    await db.flush()

    return call