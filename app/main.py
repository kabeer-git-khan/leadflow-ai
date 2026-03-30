from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup ──
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    print("✓ Database connection OK")

    yield

    # ── Shutdown ──
    await engine.dispose()
    print("✓ Database connections closed")


app = FastAPI(
    title="LeadFlow AI",
    description="Full-stack AI platform for marketing and lead gen agencies",
    version="0.1.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ───────────────────────────────────────

@app.get("/health", tags=["system"])
async def health() -> dict:
    return {
        "status": "ok",
        "env": settings.app_env,
        "version": "0.1.0",
    }


# ── Routers (uncomment as each phase is built) ─────────
# from app.rag.router import router as rag_router
# app.include_router(rag_router, prefix="/rag", tags=["rag"])

from app.voice.router import router as voice_router
app.include_router(voice_router, prefix="/voice", tags=["voice"])

# from app.extraction.router import router as extraction_router
# app.include_router(extraction_router, prefix="/extraction", tags=["extraction"])

# from app.automation.router import router as automation_router
# app.include_router(automation_router, prefix="/automation", tags=["automation"])

# from app.leads.router import router as leads_router
# app.include_router(leads_router, prefix="/leads", tags=["leads"])