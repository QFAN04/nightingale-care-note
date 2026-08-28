# Nightingale Frontend

This directory contains the Next.js/React interface for Nightingale Care Note. For the complete setup, architecture, security model, and demo flow, see the [repository README](../README.md).

## Run locally

Start the FastAPI backend on port `8000`, then run:

```bash
npm ci
npm run dev
```

Open `http://localhost:3000`. The application rewrites `/api/*` to `BACKEND_API_URL`, which defaults to `http://127.0.0.1:8000`.

## Verify

```bash
npm test
npm run typecheck
npm run lint
npm run build
```

No DeepSeek or database credential belongs in this directory. If a non-default backend URL is required, copy `.env.example` to `.env.local` and change only `BACKEND_API_URL`.
