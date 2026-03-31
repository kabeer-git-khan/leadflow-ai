from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_client
from app.core.db import get_db
from app.core.models import Client
from app.leads.schemas import DashboardStats, LeadListResponse, LeadResponse
from app.leads.service import get_dashboard_stats, get_lead_by_id, get_leads

router = APIRouter()


# ── GET /leads ─────────────────────────────────────────

@router.get("", response_model=LeadListResponse)
async def list_leads(
    status: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    return await get_leads(
        db=db,
        client_id=str(current_client.id),
        status=status,
        source=source,
        limit=limit,
        offset=offset,
    )


# ── GET /leads/{lead_id} ───────────────────────────────

@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    lead = await get_lead_by_id(db=db, lead_id=lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


# ── GET /leads/dashboard/stats ─────────────────────────

@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    return await get_dashboard_stats(
        db=db,
        client_id=str(current_client.id),
    )