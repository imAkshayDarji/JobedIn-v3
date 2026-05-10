# JobedIn v3

Monorepo: **FastAPI** backend (`backend/`) and **Next.js** frontend (`frontend/`). Local development typically uses Docker Compose for Postgres and Redis.

## Quick links

| Topic | Location |
|--------|----------|
| Frontend dev | [frontend/README.md](frontend/README.md) |
| **Production deploy & runbook** | [docs/DEPLOY.md](docs/DEPLOY.md) |
| Env template | [.env.example](.env.example) |
| Product / engineering plan | [plan.md](plan.md) |

## Production (summary)

- **Backend API and workers:** [Railway](https://railway.app) — see [`backend/railway.toml`](backend/railway.toml) and [`backend/railway.worker.json`](backend/railway.worker.json).
- **Frontend:** [Vercel](https://vercel.com) — root directory `frontend`; see [`frontend/vercel.json`](frontend/vercel.json).

Live endpoints and variable checklists are documented in [docs/DEPLOY.md](docs/DEPLOY.md).

## License / ownership

Private project (`imAkshayDarji/JobedIn-v3`). Deployment status and URLs are confirmed via Railway/Vercel CLIs as described in the deploy doc.
