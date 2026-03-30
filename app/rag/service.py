import uuid

import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import Document, DocumentStatus
from app.rag.chroma import add_chunks, search_chunks

settings = get_settings()

embeddings_model = OpenAIEmbeddings(
    api_key=settings.openai_api_key,
    model="text-embedding-3-small",
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "],
)


# ── PDF parsing ────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


# ── Ingest ─────────────────────────────────────────────

async def ingest_document(
    db: AsyncSession,
    client_id: str,
    filename: str,
    file_bytes: bytes,
) -> Document:
    document = Document(
        client_id=uuid.UUID(client_id),
        filename=filename,
        status=DocumentStatus.processing,
    )
    db.add(document)
    await db.flush()

    try:
        text = extract_text_from_pdf(file_bytes)
        chunks = text_splitter.split_text(text)
        embeddings = await embeddings_model.aembed_documents(chunks)
        count = add_chunks(
            client_id=client_id,
            chunks=chunks,
            embeddings=embeddings,
            document_id=str(document.id),
            filename=filename,
        )
        document.chunk_count = count
        document.status = DocumentStatus.ready

    except Exception as e:
        document.status = DocumentStatus.failed
        raise e

    return document


# ── Retrieval ──────────────────────────────────────────

async def retrieve_context(
    client_id: str,
    question: str,
    top_k: int = 5,
) -> list[str]:
    query_embedding = await embeddings_model.aembed_query(question)
    return search_chunks(
        client_id=client_id,
        query_embedding=query_embedding,
        top_k=top_k,
    )