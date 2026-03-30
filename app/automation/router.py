from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_client
from app.core.db import get_db
from app.core.models import Client
from app.automation.schemas import AutomationResponse, N8nWebhookPayload
from app.automation.service import (
    classify_inbound,
    enrich_lead_data,
    save_lead_from_automation,
)

router = APIRouter()


# ── POST /automation/webhook ───────────────────────────

@router.post("/webhook", response_model=AutomationResponse)
async def automation_webhook(
    payload: N8nWebhookPayload,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    # Build text from payload data
    data = payload.data
    text = f"""
From: {data.get('from_name', '')} <{data.get('from_email', '')}>
Subject: {data.get('subject', '')}
Message: {data.get('body', '')}
Company: {data.get('company', '')}
""".strip()

    if not text:
        raise HTTPException(status_code=400, detail="Empty payload data")

    # Classify the inbound message
    classification = await classify_inbound(text)

    # If spam — return early, don't save
    if classification.category == "spam":
        return AutomationResponse(
            status="ignored",
            category="spam",
            enriched={},
            lead_created=False,
        )

    # Enrich the lead data
    enriched = await enrich_lead_data(text)

    # Save lead to database
    lead = await save_lead_from_automation(
        db=db,
        client_id=str(current_client.id),
        enriched=enriched,
    )

    return AutomationResponse(
        status="processed",
        category=classification.category,
        enriched=enriched,
        lead_created=True,
        lead_id=str(lead.id),
    )


# ── POST /automation/classify ──────────────────────────

@router.post("/classify")
async def classify_message(
    request: Request,
    current_client: Client = Depends(get_current_client),
):
    body = await request.json()
    text = body.get("text", "")

    if not text:
        raise HTTPException(status_code=400, detail="Missing text field")

    classification = await classify_inbound(text)
    enriched = await enrich_lead_data(text)

    return {
        "classification": classification,
        "enriched": enriched,
    }