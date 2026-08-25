# Nightingale Care Note - Project Rules

## Frozen product boundary

- Build a local-first longitudinal patient care-note system, not a generic chatbot or Notion clone.
- Preserve the frozen Sarah Lim synthetic story, domain model, database schema, API contracts, DeepSeek/PHI/RBAC/revision/glance/importance/self-learning rules, and gate order.
- Do not invent or change product behavior unless the frozen specification cannot resolve a product-direction decision.
- Use only synthetic data.

## Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS; TanStack Query is allowed.
- Backend: Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, psycopg, pytest.
- Database: dedicated Supabase PostgreSQL project `nightingale-care-note`; never modify `chat-langchain-study`.
- LLM: DeepSeek through a replaceable provider abstraction. Automated tests use a deterministic fake provider.

## Engineering workflow

- Follow the frozen implementation-plan task order.
- For behavior changes, write a failing test and verify the expected failure before production code.
- Implement the minimum code needed to pass, then refactor while tests remain green.
- Run fresh verification before every completion claim and before every commit.
- Commit small, independently verifiable tasks with the frozen commit intent.

## Security and trust

- Never commit `.env`, API keys, database credentials, or secrets.
- PHI redaction happens before every LLM call. First-version required identifiers: known patient names/aliases, Singapore-style phone numbers, and IC/ID-like values.
- The LLM extracts supported information; it never invents diagnoses or treatments, marks facts clinician-confirmed, or determines final Glance ranking.
- Server-side clinic-scoped RBAC is authoritative. UI hiding is never an authorization control.
- Audit events contain metadata only, not full clinical text.
- Clinician UI does not display raw importance scores.

## Data and workflow invariants

- CareState/Glance is a runtime read model, not a table, and never invokes DeepSeek on reads.
- Highlight provenance must resolve Highlight -> ClinicalFact -> Entry -> ConsultSession, including an exact source quote.
- Revision storage uses immutable full snapshots. Revert appends a new version and never deletes history.
- Entry updates use optimistic concurrency and return `409` on stale `expected_version`.
- Failed scribe sessions remain recorded as failed, but create no partial Entry, Fact, Task, Highlight, or Conflict data.
- Self-learning changes only a bounded ranking bonus (`0..3`); it never changes clinical risk labels.
- Admin is read-only in the first version.

## Project location

The repository must remain at `D:\nightingale-care-note`. Do not relocate or duplicate the project onto C:.
