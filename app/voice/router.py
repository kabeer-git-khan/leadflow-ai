import hmac
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.auth import get_current_client
from app.core.models import Client
from app.voice.schemas import (
    OutboundCallRequest,
    VapiWebhookPayload,
    VoiceCallResponse,
)
from app.voice.service import qualify_lead_from_transcript, save_voice_call
import httpx

settings = get_settings()
router = APIRouter()


# ── POST /voice/webhook ────────────────────────────────

@router.post("/webhook")
async def vapi_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()

    # Verify webhook signature if secret is set
    if settings.vapi_webhook_secret:
        signature = request.headers.get("x-vapi-signature", "")
        expected = hmac.new(
            settings.vapi_webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json
    raw = json.loads(body)
    payload = VapiWebhookPayload(**raw)

    # Only process end-of-call reports
    if payload.message.type != "end-of-call-report":
        return {"status": "ignored", "type": payload.message.type}

    transcript = payload.message.transcript or ""
    call_data = payload.message.call or {}
    vapi_call_id = call_data.get("id")

    # Get client_id from call metadata
    client_id = call_data.get("metadata", {}).get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="Missing client_id in call metadata")

    # Qualify the lead from transcript
    qualification = await qualify_lead_from_transcript(transcript)

    # Save to database
    call = await save_voice_call(
        db=db,
        client_id=client_id,
        vapi_call_id=vapi_call_id,
        transcript=transcript,
        qualification=qualification,
        call_data=call_data,
    )

    return VoiceCallResponse(
        call_id=call.id,
        qualified=call.qualified,
        score=qualification.score,
        summary=qualification.summary,
        created_at=call.created_at,
    )


# ── POST /voice/call ───────────────────────────────────

@router.post("/call")
async def make_outbound_call(
    request: OutboundCallRequest,
    current_client: Client = Depends(get_current_client),
):
    if not settings.vapi_api_key:
        raise HTTPException(status_code=400, detail="Vapi API key not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.vapi.ai/call",
            headers={
                "Authorization": f"Bearer {settings.vapi_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "assistantId": request.assistant_id,
                "customer": {
                    "number": request.phone_number,
                    "name": request.lead_name,
                },
                "metadata": {
                    "client_id": str(current_client.id),
                },
            },
        )

    if response.status_code != 201:
        raise HTTPException(
            status_code=400,
            detail=f"Vapi call failed: {response.text}",
        )

    return {"status": "call_initiated", "data": response.json()}


# ── GET /voice/calls/{call_id} ─────────────────────────

@router.get("/calls/{call_id}")
async def get_call(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    from sqlalchemy import select
    from app.core.models import VoiceCall

    result = await db.execute(
        select(VoiceCall).where(VoiceCall.vapi_call_id == call_id)
    )
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return VoiceCallResponse(
        call_id=call.id,
        qualified=call.qualified,
        score=0,
        summary=None,
        created_at=call.created_at,
    )