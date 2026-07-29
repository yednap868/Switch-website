# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vance is an LLM-powered AI networking agent that facilitates intelligent introductions between professionals. It operates via WhatsApp as the primary interface, uses Claude AI for decision-making, and manages user onboarding, profile matching, and email introduction workflows.

## Build & Development Commands

```bash
# Install dependencies (UV is the package manager)
uv pip install -r requirements.txt
#scripts/sync_extractions_to_qdrant.py or
uv sync

# Run the application
./run.sh
# or directly:
python main.py
# or:
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info

# Run tests
pytest

# Deploy with health checks
./deploy.sh

# Run admin dashboard (port 5001)
ADMIN_USERNAME=admin ADMIN_PASSWORD=<password> python admin_routes.py
```

**API Documentation:** `http://localhost:8000/api/docs` (Swagger UI)

## Architecture

### Core Application Flow

1. **Entry Point (`main.py`)** - Loads env vars, creates FastAPI app, starts uvicorn
2. **FastAPI App (`api/app.py`)** - CORS middleware, session handling, router aggregation
3. **WhatsApp Router (`api/whatsapp_modules/router_v2.py`)** - Active service-based webhook handler (40KB)
4. **Service Layer (`services/`)** - Business logic with dependency injection

### Key Services

| Service                               | Purpose                                                             |
| ------------------------------------- | ------------------------------------------------------------------- |
| `conversation_service.py` (101KB)     | Conversation flow orchestration, state machine, user classification |
| `claude_profile_service.py` (52KB)    | Claude-powered profile matching and suggestions                     |
| `claude_onboarding_service.py` (23KB) | AI-driven user onboarding                                           |
| `data_extraction_service.py` (27KB)   | Intelligent field extraction from natural language                  |
| `email_service.py` (12KB)             | Email workflow management                                           |
| `logging_service.py` (7KB)            | Data persistence to Firestore/Qdrant                                |

### WhatsApp Modules (`api/whatsapp_modules/`)

- `router_v2.py` - **Active** service-based router
- `webhook_handler.py` - Webhook processing & message deduplication
- `state_manager.py` - Firebase-backed user conversation state
- `email_workflow.py` (42KB) - Email introduction flow
- `conversation_history.py` - Message history tracking

### Database Layer

- **Firestore** (`utils/db.py`) - Primary database for users, profiles, extraction data
- **Qdrant** (`utils/qdrant.py`) - Vector database for semantic profile search
- **Redis** (`utils/redis_client.py`) - Caching, deduplication, sessions

### Configuration (`config/`)

- `conversation_config.py` (46KB) - Conversation states & patterns
- `conversation_flow.json` - State definitions (JSON)
- `intent_mappings.json` - Intent classification
- `system_prompt_text.md` (23KB) - AI system prompt for text
- `system_prompt_voice.md` (42KB) - AI system prompt for voice

## Tech Stack

- **Backend:** FastAPI, Uvicorn, Python 3.11+
- **AI/LLM:** Claude 3.7 Sonnet (primary), OpenAI/Mistral/Cohere (fallbacks)
- **Databases:** Firestore, Qdrant (vectors), Redis
- **APIs:** WhatsApp Business, Gmail, ElevenLabs (voice), ScrapingDog (LinkedIn)
- **Package Manager:** UV (Rust-based)

## Key Architectural Patterns

1. **Service-based architecture** - All business logic through services with dependency injection
2. **State machine in Firebase** - User conversation state persists across sessions
3. **Claude AI first** - Primary AI provider with fallbacks to other models
4. **Single worker mode** - Use 1 uvicorn worker to avoid race conditions
5. **Async throughout** - FastAPI + aiohttp for high concurrency

## Environment Variables

Required variables in `env_vars.sh`:

- `GOOGLE_APPLICATION_CREDENTIALS`, `FIREBASE_CREDENTIALS_PATH` - Firebase
- `QDRANT_API_KEY`, `QDRANT_BASE_URL` - Vector DB
- `PHONE_NUMBER_ID`, `META_SYS_USER_TOKEN`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN` - WhatsApp
- `ANTHROPIC_API_KEY` - Claude AI
- `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID` - Voice
- `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` - Email

## Important Files to Understand First

1. `api/app.py` - App initialization and middleware
2. `api/whatsapp_modules/router_v2.py` - Active webhook handler
3. `services/conversation_service.py` - Core conversation orchestration
4. `services/claude_profile_service.py` - Profile matching AI
5. `api/whatsapp_modules/state_manager.py` - User state persistence
6. `config/conversation_config.py` - Conversation state definitions

## Git Workflow

- **Main branch:** `prod` (production)
- **Remote:** `git@github.com:Vance-2025/Vance.git`

## Critical Call Path — DO NOT BREAK

The voice calling feature (Switch/Jyoti) is the most fragile and important feature. These rules MUST be followed:

### The call flow (inbound)
```
Caller → Vobiz → POST /api/webhooks/vobiz/answer → returns <Stream> XML
       → Vobiz opens WebSocket to /ws/vobiz-bridge
       → Bridge opens WebSocket to ElevenLabs Conversation API
       → Audio relayed bidirectionally (mulaw 8kHz ↔ PCM 16kHz)
```

### Rules for the call path

1. **NEVER put synchronous Firestore/DB calls in the answer webhook response path** (`api/vobiz_routes.py` — `vobiz_answer_url`). The XML must be returned instantly. All logging/tracking goes in background threads. Vobiz has a short timeout — if we don't return XML fast, the call drops silently.

2. **NEVER put synchronous Firestore/DB calls on the event loop in bridge code** (`api/vobiz_bridge.py`). Use `asyncio.to_thread()` for any sync I/O. The event loop is shared with audio relay — blocking it causes audio drops and disconnects.

3. **The answer webhook (`vobiz_answer_url`) must only do:** parse request → cache CallUUID (in-memory) → build XML → return XML. Everything else in background threads.

4. **Files on the critical call path** (changes here can break calls):
   - `api/vobiz_routes.py` — answer/hangup webhooks
   - `api/vobiz_bridge.py` — WebSocket audio bridge
   - `services/vobiz_service.py` — Vobiz API calls (make_call, hangup, transfer)
   - `services/incoming_call_service.py` — builds Stream XML

5. **Test after ANY change to these files** by making an actual phone call.

6. **Vobiz phone number format**: digits only, NO `+` prefix. E.g. `919876543210` not `+919876543210`.

7. **playAudio format** for sending audio back to caller:
   - `contentType`: `"audio/x-mulaw"` (NOT `"audio/x-mulaw;rate=8000"`)
   - `sampleRate`: integer `8000` (NOT string)
   - `streamId`: REQUIRED at top level

## Things to Avoid

- Do not use inline imports anywhere in the codebase. They are FORBIDDEN. Use only top-level imports.
- Do not add comments that are unrelated to the code. Only add comments to explain what the code does. NEVER explain what you did using a comment.
