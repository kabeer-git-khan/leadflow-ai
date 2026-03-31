from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import (
    Conversation,
    Document,
    Extraction,
    Lead,
    LeadSource,
    LeadStatus,
    VoiceCall,
)
from app.leads.schemas import DashboardStats, LeadListResponse, LeadResponse


# ── Get all leads ──────────────────────────────────────

async def get_leads(
    db: AsyncSession,
    client_id: str,
    status: str | None = None,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> LeadListResponse:
    query = select(Lead).where(Lead.client_id == client_id)

    if status:
        query = query.where(Lead.status == status)
    if source:
        query = query.where(Lead.source == source)

    query = query.order_by(Lead.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    leads = result.scalars().all()

    count_query = select(func.count()).select_from(Lead).where(
        Lead.client_id == client_id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return LeadListResponse(
        total=total,
        leads=[
            LeadResponse(
                id=lead.id,
                name=lead.name,
                email=lead.email,
                phone=lead.phone,
                company=lead.company,
                source=lead.source.value,
                status=lead.status.value,
                score=lead.score,
                crm_id=lead.crm_id,
                created_at=lead.created_at,
                updated_at=lead.updated_at,
            )
            for lead in leads
        ],
    )


# ── Get single lead ────────────────────────────────────

async def get_lead_by_id(
    db: AsyncSession,
    lead_id: str,
) -> LeadResponse | None:
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()

    if not lead:
        return None

    return LeadResponse(
        id=lead.id,
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
        source=lead.source.value,
        status=lead.status.value,
        score=lead.score,
        crm_id=lead.crm_id,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


# ── Dashboard stats ────────────────────────────────────

async def get_dashboard_stats(
    db: AsyncSession,
    client_id: str,
) -> DashboardStats:
    # Lead counts by status
    leads_result = await db.execute(
        select(Lead.status, func.count()).where(
            Lead.client_id == client_id
        ).group_by(Lead.status)
    )
    status_counts = {row[0].value: row[1] for row in leads_result.all()}

    # Lead counts by source
    source_result = await db.execute(
        select(Lead.source, func.count()).where(
            Lead.client_id == client_id
        ).group_by(Lead.source)
    )
    source_counts = {row[0].value: row[1] for row in source_result.all()}

    # Total voice calls
    calls_result = await db.execute(select(func.count()).select_from(VoiceCall))
    total_calls = calls_result.scalar()

    # Total documents
    docs_result = await db.execute(
        select(func.count()).select_from(Document).where(
            Document.client_id == client_id
        )
    )
    total_docs = docs_result.scalar()

    # Total extractions
    extractions_result = await db.execute(
        select(func.count()).select_from(Extraction)
    )
    total_extractions = extractions_result.scalar()

    total_leads = sum(status_counts.values())

    return DashboardStats(
        total_leads=total_leads,
        qualified_leads=status_counts.get("qualified", 0),
        new_leads=status_counts.get("new", 0),
        nurture_leads=status_counts.get("nurture", 0),
        converted_leads=status_counts.get("converted", 0),
        leads_by_source=source_counts,
        total_voice_calls=total_calls,
        total_documents=total_docs,
        total_extractions=total_extractions,
    )