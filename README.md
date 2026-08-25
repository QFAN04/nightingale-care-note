# Nightingale Care Note

Nightingale Care Note is a local-first, synthetic-data clinical collaboration prototype for the Nightingale 72HR Build.

The product is designed around three questions:

1. What matters now?
2. Where did this information come from?
3. Who verified or acted on it?

## Status

Repository foundation is being initialized. Backend, frontend, database migrations, tests, setup instructions, and demo workflows will be added gate by gate.

## Planned stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS, TanStack Query
- Backend: FastAPI, Python 3.11+, SQLAlchemy 2, Pydantic v2, Alembic, psycopg
- Database: a dedicated Supabase PostgreSQL project
- LLM: DeepSeek behind a replaceable provider interface
- Testing: pytest with strict red-green-refactor development

## Safety boundary

Only synthetic patient data may be used. Names, phone numbers, and IC/ID-like identifiers must be deterministically redacted before any transcript is sent to an LLM. Secrets belong only in local `.env` files and must never be committed.

