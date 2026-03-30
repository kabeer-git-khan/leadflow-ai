<<<<<<< HEAD
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


# ── Enums ──────────────────────────────────────────────

class LeadSource(str, PyEnum):
    chat = "chat"
    voice = "voice"
    email = "email"
    pdf = "pdf"


class LeadStatus(str, PyEnum):
    new = "new"
    qualified = "qualified"
    nurture = "nurture"
    converted = "converted"
    lost = "lost"


class DocumentStatus(str, PyEnum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class ConversationChannel(str, PyEnum):
    chat = "chat"
    voice = "voice"
    email = "email"


# ── Models ─────────────────────────────────────────────

class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    crm_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    leads: Mapped[list["Lead"]] = relationship(back_populates="client")
    documents: Mapped[list["Document"]] = relationship(back_populates="client")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource), default=LeadSource.chat
    )
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.new
    )
    score: Mapped[int] = mapped_column(Integer, default=0)
    crm_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="leads")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="lead")
    voice_calls: Mapped[list["VoiceCall"]] = relationship(back_populates="lead")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True
    )
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel: Mapped[ConversationChannel] = mapped_column(
        Enum(ConversationChannel), default=ConversationChannel.chat
    )
    messages: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lead: Mapped["Lead | None"] = relationship(back_populates="conversations")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.pending
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="documents")
    extractions: Mapped[list["Extraction"]] = relationship(back_populates="document")


class VoiceCall(Base):
    __tablename__ = "voice_calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True
    )
    vapi_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualified: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    call_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lead: Mapped["Lead | None"] = relationship(back_populates="voice_calls")


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    extracted_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="extractions")
=======
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
>>>>>>> origin/feature/phase1-alembic
