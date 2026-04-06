# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


## Output
- Return code first. Explanation after, only if non-obvious.
- No inline prose. Use comments sparingly - only where logic is unclear.
- No boilerplate unless explicitly requested.

## Code Rules
- Simplest working solution. No over-engineering.
- No abstractions for single-use operations.
- No speculative features or "you might also want..."
- Read the file before modifying it. Never edit blind.
- No docstrings or type annotations on code not being changed.
- No error handling for scenarios that cannot happen.
- Three similar lines is better than a premature abstraction.

## Review Rules
- State the bug. Show the fix. Stop.
- No suggestions beyond the scope of the review.
- No compliments on the code before or after the review.

## Debugging Rules
- Never speculate about a bug without reading the relevant code first.
- State what you found, where, and the fix. One pass.
- If cause is unclear: say so. Do not guess.

## Simple Formatting
- No em dashes, smart quotes, or decorative Unicode symbols.
- Plain hyphens and straight quotes only.
- Natural language characters (accented letters, CJK, etc.) are fine when the content requires them.
- Code output must be copy-paste safe.


## Commands

```bash
# Run locally (requires MongoDB + ngrok on port 8000 for webhooks)
uvicorn src.main:app --reload --port 8000

# Run with Docker
docker-compose up -d --force-recreate --remove-orphans --build

# Install dependencies
pip install -r requirements.txt
```

No test framework is configured.

## Architecture

FastAPI application for processing Telegram Stars payments across multiple bots. Uses aiogram for Telegram bot integration, MongoDB via Beanie ODM, and Motor async driver.

### Request Flow

1. **API clients** create payments via `POST /api/bot/{id}/create-payment` (API-key protected) → saves a `Payment` document → calls Telegram `create_invoice_link` → returns payment link
2. **Telegram** sends webhook updates to `POST /bot/{id}/webhook` (validated via `X-Telegram-Bot-Api-Secret-Token` header) → fed into a shared aiogram `Dispatcher`
3. On successful payment, the handler optionally POSTs payment data to a caller-specified webhook URL; on webhook failure, auto-refunds the user

### Key Singletons

- **`BotsService`** (`src/services/bots.py`, instantiated as `bots_service`): manages bot lifecycle — loads encrypted tokens from DB, maintains an in-memory `bots_map` (bot_id → aiogram Bot), creates payment links, sets webhooks. New bots can be added at runtime via `POST /api/bots`.
- **`Dispatcher`** (`src/bot/bot.py`): single shared aiogram dispatcher handles updates for all bots. Handlers are registered via routers in `src/bot/handlers/`.

### Data Layer

- Beanie `Document` models in `src/models/` — register new models in `ALL_DB_MODELS` (`src/models/__init__.py`) for auto-init
- `Payment` tracks status transitions: `pending` → `completed` or `error`
- `BotRecord` stores Fernet-encrypted bot tokens (key: `BOT_TOKEN_ENCRYPTION_KEY` env var)

### Routing Convention

- `src/routers/` — API routes, mounted under `/api` with `X-API-Key` auth
- `src/bot/bot.py` — webhook endpoint, mounted at root `/bot/{id}/webhook`, no API key (uses Telegram secret token instead)
- New API routers go in `src/routers/` and must be added to `ALL_ROUTERS` in `src/routers/__init__.py`
- New bot handlers go in `src/bot/handlers/` and must be added to `ALL_ROUTERS` in `src/bot/handlers/__init__.py`

### Environment Variables

Configured via `pydantic-settings` in `src/utils/settings.py`. Key vars: `API_URL`, `API_KEY`, `TELEGRAM_SECRET`, `MONGO_DB_URI`, `MONGO_DB_NAME`, `BOT_TOKEN_ENCRYPTION_KEY`. Bot tokens can be seeded from env (`BOT_TOKEN_1`, `BOT_TOKEN_2`, …) but the preferred method is the API.
