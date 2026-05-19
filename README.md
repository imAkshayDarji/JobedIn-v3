# JobedIn v3

AI-assisted job search platform: discover roles, score fit, tailor resumes and cover letters, practice interviews, and run browser-based auto-apply flows.

Monorepo with a **FastAPI** API (`backend/`), **Next.js** web app (`frontend/`), **PostgreSQL**, **Redis**, and **ARQ** background workers.

## Features

| Area | Capabilities |
|------|----------------|
| Auth | [Clerk](https://clerk.com) JWT validation on the API; Next.js sign-in/up |
| Onboarding | Profile wizard, resume upload, AI parsing |
| Job discovery | LinkedIn (Playwright), JSearch, Adzuna, Reed, and related adapters; deduplication and matching |
| Applications | Tracker, apply URL resolution, generic and ATS-specific auto-apply (Playwright) |
| AI | Resume/cover letter generation, interview coach (GLM / OpenAI via env-configured keys) |
| Dashboard | Jobs, profile, applications, interview practice |

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLModel, Alembic, asyncpg, ARQ, Playwright
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS v4
- **Data:** PostgreSQL 16, Redis 7
- **Auth:** Clerk (JWKS on API)
- **Deploy:** Railway (API + workers + Postgres + Redis), Vercel (frontend)

## Repository layout

```
backend/          FastAPI app, models, workers, Playwright apply pipeline
frontend/         Next.js UI (set Vercel root directory to frontend/)
docs/             DEPLOY.md, design specs (public engineering docs)
docker-compose.yml   Local Postgres, Redis, API, ai/job/apply workers
.env.example      Environment variable template (copy to .env locally)
```

Private planning notes (`plan.md`, `docs/plans/`) and interview prep materials stay **local only** (see `.gitignore`).

## Prerequisites

- Docker and Docker Compose
- Node.js 20+ (frontend)
- Python 3.12+ (backend, if running outside Docker)
- [Clerk](https://dashboard.clerk.com) application (Development for local)
- API keys as needed: AI (GLM/OpenAI), job sources (JSearch, Adzuna, Reed, etc.) — see `.env.example`

## Local development

1. **Clone and configure env**

   ```bash
   cp .env.example .env
   # Fill Clerk, AI, and job API keys in .env
   ```

2. **Clerk (frontend)**

   From `frontend/`:

   ```bash
   npm install
   npm run clerk:link
   npm run clerk:env:dev
   ```

   Set matching `CLERK_JWKS_URL`, `CLERK_SECRET_KEY`, and `CLERK_PUBLISHABLE_KEY` in the root `.env` for the API.

3. **Start stack**

   ```bash
   docker compose up --build
   ```

   - API: http://localhost:8000 (health: `GET /health`)
   - Frontend: http://localhost:3000 (`cd frontend && npm run dev` if not in Compose)

4. **Database migrations** (first run or after model changes)

   ```bash
   docker compose exec backend alembic upgrade head
   ```

## Testing

**Backend** (from `backend/` with dev dependencies installed):

```bash
pytest
```

**Frontend** (from `frontend/`):

```bash
npm test
```

## Production

| Layer | Platform |
|-------|----------|
| API | Railway — `backend/railway.toml`, root directory `backend` |
| Workers | Railway — `backend/railway.worker.json` (ai, job, apply) |
| Frontend | Vercel — root directory `frontend` |

Full checklist, smoke tests, and troubleshooting: [docs/DEPLOY.md](docs/DEPLOY.md).

## Documentation

| Topic | Location |
|--------|----------|
| Deploy and operations | [docs/DEPLOY.md](docs/DEPLOY.md) |
| Environment variables | [.env.example](.env.example) |
| Frontend (Clerk, scripts) | [frontend/README.md](frontend/README.md) |

## Security

- Never commit `.env`, `.env.local`, or real API keys. Use `.env.example` placeholders only.
- Do not commit `resumes/`, `screenshots/`, or other runtime artifacts (may contain PII).
- Rotate keys if they were ever committed; production secrets live in Railway/Vercel/Clerk dashboards.

## License

Public repository — [imAkshayDarji/JobedIn-v3](https://github.com/imAkshayDarji/JobedIn-v3). Add a license file if you intend open-source redistribution.
