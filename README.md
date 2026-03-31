# LeadFlow AI

Full-stack AI platform for marketing and lead gen agencies. Unifies four lead channels — website chat, voice calls, email, and document uploads — into one backend with a unified lead database.

## Modules

- **RAG Chatbot** — upload client docs, answer visitor questions from that knowledge base
- **Voice Agent** — Vapi webhook handler, qualifies leads from call transcripts automatically
- **Automation** — n8n webhook receiver, classifies and enriches inbound emails
- **PDF Extraction** — extracts structured lead data from uploaded PDFs

## Tech Stack

Python 3.13 · FastAPI · PostgreSQL · Redis · ChromaDB · LangChain · OpenAI · Vapi · Docker

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.13
- uv

### 1. Clone the repo
```bash
git clone https://github.com/kabeer-git-khan/leadflow-ai.git
cd leadflow-ai
```

### 2. Set up environment
```bash
cp .env.example .env
```

Fill in your values in `.env`:
- `SECRET_KEY` — random 64 char string
- `JWT_SECRET_KEY` — random 64 char string
- `DATABASE_URL` — PostgreSQL connection string
- `OPENAI_API_KEY` — your OpenAI key
- `VAPI_API_KEY` — your Vapi private key

### 3. Start infrastructure
```bash
docker compose up -d
```

### 4. Install dependencies
```bash
uv sync
```

### 5. Run migrations
```bash
uv run alembic upgrade head
```

### 6. Start the server
```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 7. Open API docs
```
http://localhost:8000/docs
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /rag/ingest | Upload PDF to knowledge base |
| POST | /rag/chat | Chat with knowledge base |
| GET | /rag/sessions/{id} | Get conversation history |
| POST | /voice/webhook | Vapi end-of-call webhook |
| POST | /voice/call | Trigger outbound call |
| POST | /extraction/extract | Extract data from PDF |
| POST | /automation/webhook | n8n inbound webhook |
| POST | /automation/classify | Classify and enrich message |
| GET | /leads | List all leads |
| GET | /leads/{id} | Get single lead |
| GET | /leads/dashboard/stats | Dashboard statistics |

## Project Structure
```
app/
├── core/          # Shared — config, db, auth, redis, models
├── rag/           # RAG chatbot module
├── voice/         # Voice agent module
├── extraction/    # PDF extraction module
├── automation/    # n8n automation module
└── leads/         # Admin leads module
```

## License

MIT