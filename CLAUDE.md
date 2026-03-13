# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BluEye is an AI-powered hurricane safety chatbot backend — a FastAPI microservice that accepts questions via POST `/ask`, forwards them to OpenRouter (Meta LLaMA 3.3 70B), and returns bilingual (Spanish/English) hurricane safety guidance. Logs all interactions to SQLite. Built for the [BluEye MVP](https://github.com/DiegoCM1/MetaQuetzal) Expo/React Native mobile app.

## Commands

| Action | Command |
|---|---|
| Install dependencies | `pip install -r requirements.txt` |
| Run dev server | `uvicorn main:app --reload` |
| Run all tests | `pytest` |
| Run a single test | `pytest tests/test_main.py::test_ask_endpoint` |

## Architecture

**Single-file app** — all application logic lives in `main.py` (~200 lines). No packages, no modules, no service layers.

**Request flow:** Mobile app → `POST /ask` → log to SQLite → call OpenRouter API → update SQLite with response → return JSON.

### Key areas in `main.py`

- **Lines 1-28:** App init, env vars, CORS middleware (allows localhost:8081 and Expo Go LAN)
- **Lines 30-64:** Async SQLite lifecycle (`@app.on_event` startup/shutdown), schema migration via `PRAGMA table_info`
- **Lines 67-69:** `QuestionRequest` Pydantic model
- **Lines 72-201:** `POST /ask` — the only route; contains the entire system prompt inline

### System prompt

The system prompt embedded in the `/ask` handler is the core product. It defines a "Protocol Mode" with three hurricane stages (Preparation, During, Recovery), bilingual behavior, emotional de-escalation, and mobile-optimized response length (~140-180 words).

### Database

SQLite (`prompts.db`) is used purely as a request log (question, answer, IP, timestamp) — not for sessions or user state. DB path is computed as absolute to work regardless of process CWD.

## Configuration

- **Environment:** `OPENROUTER_API_KEY` (required), `OPENROUTER_TIMEOUT` (optional, defaults to 30s). See `.env.example`.
- **Model selection:** Hardcoded in the `/ask` handler body dict (~line 81). Change model by editing that line.
- **Deployment:** Railway via `railway.json` — runs `uvicorn main:app --host 0.0.0.0 --port $PORT`.

## Testing

Tests use `pytest` with `AsyncMock` to patch `httpx.AsyncClient.post` (no real network calls). Tests manually call `startup`/`shutdown` events and use `importlib.reload(main)` for fresh state. The `tmp_path` fixture provides ephemeral SQLite databases.
