# Deployment and operations

## Production topology (verified)

| Layer | Platform | Notes |
|-------|----------|--------|
| API | Railway | FastAPI service; healthcheck `GET /health` |
| Workers | Railway | Separate services (`arq`); use [`backend/railway.worker.json`](../backend/railway.worker.json) (no HTTP healthcheck) |
| Postgres | Railway | Plugin database; `DATABASE_URL` on API and workers |
| Redis | Railway | Plugin; `REDIS_URL` for workers and API |
| Frontend | Vercel | Next.js app; set **Root Directory** to `frontend` |

**Smoke checks (2026-05-10):**

- API: `curl -sS https://jobedin-v3-production.up.railway.app/health` → `200` and `{"status":"ok",...}`
- CLI: from `backend/`, `railway status` shows project `satisfied-serenity`, service `JobedIn-v3` **Online** with URL above; Postgres and Redis **Online**; additional services (e.g. worker stacks) should appear as separate Railway services.
- Vercel: `vercel ls` in linked `frontend/` shows project `jobedin-v3-1`, Production **Ready** (e.g. `https://jobedin-v3-1-7ac8hvwht-imakshaydarjis-projects.vercel.app`).

URLs and deployment IDs change per deploy; re-check with `railway status` and `vercel ls` if documentation drifts.

## Repository layout for hosts

### Railway (API)

- **Root Directory:** `backend` (in Railway service settings).
- **Config as code:** [`backend/railway.toml`](../backend/railway.toml) — path from repo root `/backend/railway.toml` (see comments in file).
- **Dockerfile:** [`backend/Dockerfile`](../backend/Dockerfile) (builder `DOCKERFILE` in TOML).

### Railway (workers)

- Duplicate service from same repo; set **Root Directory** `backend`.
- Point **Railway config** to `railway.worker.json` for that service so HTTP healthchecks are disabled.
- Start command must match what you use locally / `docker-compose` for `arq` workers (`job_worker`, `ai_worker`, `apply_worker` as applicable).

### Vercel (frontend)

- **Root Directory:** `frontend`.
- Optional: [`frontend/vercel.json`](../frontend/vercel.json) pins `framework`, `installCommand`, `buildCommand`.
- The directory `.vercel/` is gitignored; run `vercel link` in `frontend/` on each machine that should use the CLI against this project.

## Environment variables

Authoritative template: [`.env.example`](../.env.example). Production checklist:

**Backend (Railway API + workers)**

- `DATABASE_URL` — Railway Postgres (non-empty; blank overrides break startup).
- `REDIS_URL` — Railway Redis (workers required; API if using Redis).
- `SECRET_KEY`, `ENVIRONMENT=production`.
- Clerk: `CLERK_JWKS_URL`, `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY` (same Clerk **Production** instance as the Next app).
- `CORS_ORIGINS` — comma-separated origins, include the live Vercel URL (and custom domain if any).
- AI keys, job API keys, `ENCRYPTION_KEY`, Sentry DSN as needed.

**Frontend (Vercel)**

- `NEXT_PUBLIC_API_URL` — public Railway API base URL (e.g. `https://jobedin-v3-production.up.railway.app`, no trailing slash unless your code expects it).
- `NEXT_PUBLIC_*` Clerk URLs and keys for the **Production** Clerk application.
- Sentry frontend DSN if used.

**Clerk**

- Production instance: allowed origins / domains must include the Vercel production URL (and custom domain).
- Mirror keys to Vercel (public + server-only as per Clerk Next.js docs) and JWKS + secrets to the backend.

## Supabase

The current app uses **Postgres on Railway** for the API. There is no separate Supabase client in this repository. If you introduce Supabase (auth storage, realtime, etc.), add a Production project there and document new env vars in [`.env.example`](../.env.example).

## Runbook — common issues

### API returns 5xx or Railway shows crash loop

1. Read **Deploy** and **HTTP** logs in Railway for the API service.
2. Confirm `DATABASE_URL` is set and reachable (migrations applied: run Alembic against prod DB from a secure shell or one-off job).
3. Confirm `CLERK_JWKS_URL` matches the Clerk instance issuing tokens.

### Frontend calls API but CORS or network errors

1. Verify `CORS_ORIGINS` on the backend includes the exact browser origin (scheme + host, port if any).
2. Verify `NEXT_PUBLIC_API_URL` matches the Railway API base URL.

### 401 on Vercel homepage when `curl`ing `/`

Vercel or middleware may enforce auth or deployment protection. Use the browser for user flows; unauthenticated `curl` to `/` may not reflect health of static assets.

### Workers not processing jobs

1. Confirm worker service is **Online** and uses `railway.worker.json` (no failing HTTP healthcheck).
2. Confirm `REDIS_URL` and worker start commands match [`docker-compose.yml`](../docker-compose.yml) patterns.
3. Check worker logs in Railway.

### Clerk sign-in fails in production

1. Clerk Dashboard → **Domains** / allowed origins for the Production instance.
2. Vercel env vars match that instance (not Development keys).

## CLI quick reference

```bash
# Railway (from backend/ or linked repo root)
cd backend && railway status

# Vercel (from frontend/)
cd frontend && vercel ls
```

Refresh local env from Clerk (from `frontend/`):

```bash
clerk link
clerk env pull --file .env.local
clerk doctor
```
