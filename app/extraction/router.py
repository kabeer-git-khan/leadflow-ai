from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_client
from app.core.db import get_db
from app.core.models import Client, Extraction
from app.extraction.schemas import ExtractedLeadData, ExtractionResponse
from app.extraction.service import process_pdf_extraction

router = APIRouter()


# ── POST /extraction/extract ───────────────────────────

@router.post("/extract", response_model=ExtractionResponse)
async def extract_from_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()

    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 20MB")

    extraction, document = await process_pdf_extraction(
        db=db,
        client_id=str(current_client.id),
        filename=file.filename,
        file_bytes=file_bytes,
    )

    return ExtractionResponse(
        extraction_id=extraction.id,
        document_id=document.id,
        filename=document.filename,
        extracted_data=ExtractedLeadData(**extraction.extracted_data),
        tokens_used=extraction.tokens_used,
        created_at=extraction.created_at,
    )


# ── GET /extraction/{extraction_id} ───────────────────

@router.get("/{extraction_id}", response_model=ExtractionResponse)
async def get_extraction(
    extraction_id: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(
        select(Extraction).where(Extraction.id == extraction_id)
    )
    extraction = result.scalar_one_or_none()

    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    return ExtractionResponse(
        extraction_id=extraction.id,
        document_id=extraction.document_id,
        filename="unknown",
        extracted_data=ExtractedLeadData(**extraction.extracted_data),
        tokens_used=extraction.tokens_used,
        created_at=extraction.created_at,
    )