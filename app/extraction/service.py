import json
import uuid

import fitz
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import Document, DocumentStatus, Extraction
from app.extraction.schemas import ExtractedLeadData

settings = get_settings()

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    model="gpt-4o-mini",
    temperature=0,
)


# ── PDF text extraction ────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


# ── LLM extraction ─────────────────────────────────────

async def extract_lead_data(text: str) -> tuple[ExtractedLeadData, int]:
    messages = [
        SystemMessage(content="""You are a data extraction expert.
Extract lead information from the document text below.
Return ONLY a valid JSON object with these exact keys:
{
    "name": "full name or null",
    "email": "email address or null",
    "phone": "phone number or null",
    "company": "company name or null",
    "budget": "budget mentioned or null",
    "timeline": "timeline mentioned or null",
    "service_interest": "what service they need or null",
    "notes": "any other relevant info or null"
}
If a field is not found in the document, use null."""),
        HumanMessage(content=f"Document text:\n{text[:4000]}"),
    ]

    response = await llm.ainvoke(messages)
    tokens_used = response.usage_metadata.get("total_tokens", 0) if hasattr(response, "usage_metadata") else 0

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return ExtractedLeadData(**data), tokens_used
    except Exception:
        return ExtractedLeadData(), tokens_used


# ── Save to database ───────────────────────────────────

async def process_pdf_extraction(
    db: AsyncSession,
    client_id: str,
    filename: str,
    file_bytes: bytes,
) -> tuple[Extraction, Document]:
    document = Document(
        client_id=uuid.UUID(client_id),
        filename=filename,
        status=DocumentStatus.processing,
    )
    db.add(document)
    await db.flush()

    text = extract_text_from_pdf(file_bytes)
    extracted_data, tokens_used = await extract_lead_data(text)

    extraction = Extraction(
        document_id=document.id,
        extracted_data=extracted_data.model_dump(),
        model_used="gpt-4o-mini",
        tokens_used=tokens_used,
    )
    db.add(extraction)

    document.status = DocumentStatus.ready
    await db.flush()

    return extraction, document