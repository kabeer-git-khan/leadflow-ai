import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_client
from app.core.db import get_db
from app.core.models import Client, Conversation, ConversationChannel
from app.core.redis import get_redis, redis_get, redis_set
from app.rag.schemas import ChatRequest, ChatResponse, IngestResponse, SessionResponse
from app.rag.service import ingest_document, retrieve_context
from app.core.config import get_settings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

settings = get_settings()

router = APIRouter()

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    model="gpt-4o-mini",
    temperature=0.3,
)


# ── POST /rag/ingest ───────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()

    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 20MB")

    document = await ingest_document(
        db=db,
        client_id=str(current_client.id),
        filename=file.filename,
        file_bytes=file_bytes,
    )

    return IngestResponse(
        document_id=document.id,
        filename=document.filename,
        chunk_count=document.chunk_count,
        status=document.status.value,
    )


# ── POST /rag/chat ─────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
    redis=Depends(get_redis),
):
    # Load conversation history from Redis
    history = await redis_get(redis, f"session:{request.session_id}") or []

    # Retrieve relevant chunks from ChromaDB
    chunks = await retrieve_context(
        client_id=str(current_client.id),
        question=request.message,
    )

    if not chunks:
        context = "No relevant documents found."
    else:
        context = "\n\n".join(chunks)

    # Build messages for LLM
    messages = [
        SystemMessage(content=f"""You are a helpful assistant. 
Answer the user's question using only the context below.
If the answer is not in the context, say you don't know.

Context:
{context}"""),
    ]

    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=request.message))

    # Get answer from LLM
    response = await llm.ainvoke(messages)
    answer = response.content

    # Update history in Redis
    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": answer})
    await redis_set(redis, f"session:{request.session_id}", history, ttl_seconds=3600)

    # Save conversation to PostgreSQL
    conv = await db.get(Conversation, None)
    from sqlalchemy import select
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == request.session_id
        )
    )
    conversation = result.scalar_one_or_none()

    if conversation:
        conversation.messages = history
    else:
        conversation = Conversation(
            session_id=request.session_id,
            channel=ConversationChannel.chat,
            messages=history,
        )
        db.add(conversation)

    return ChatResponse(
        session_id=request.session_id,
        answer=answer,
        sources=chunks[:3],
    )


# ── GET /rag/sessions/{session_id} ─────────────────────

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    redis=Depends(get_redis),
):
    history = await redis_get(redis, f"session:{session_id}")

    if not history:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.rag.schemas import ChatMessage
    messages = [ChatMessage(role=m["role"], content=m["content"]) for m in history]

    return SessionResponse(
        session_id=session_id,
        messages=messages,
    )