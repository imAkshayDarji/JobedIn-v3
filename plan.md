# JobedIn V3 -- Final Merged Plan

## Progress Tracker

| Day | Phase | Description | Status | Commit |
|-----|-------|-------------|--------|--------|
| Day 1 | Foundation | Project Scaffolding + Docker Compose | DONE | `33bf30b` |
| Day 2 | Foundation | Database Models + Alembic Migrations | DONE | `528ccae` |
| Day 3 | Foundation | Auth + Middleware | DONE | `42bdbb2` |
| Day 4 | Foundation | Onboarding API + Frontend Wizard | DONE | `2649829` |
| Day 5 | AI Pipeline | AI Client Setup + Prompt Engineering | DONE | `24eb87c` |
| Day 6 | AI Pipeline | Resume Generation Pipeline | DONE | `89ed778` |
| Day 7 | AI Pipeline | Cover Letter Generation | DONE | `5b4922a` |
| Day 8 | AI Pipeline | Interactive Interview Coach | DONE | `ed6d652` |
| Day 9 | AI Pipeline | AI Pipeline Testing + Polish | DONE | `2e0b4fd` |
| Day 10 | Job Discovery | LinkedIn Playwright Discovery | DONE | `92ee4ed` |
| Day 11 | Job Discovery | API Sources + Merge/Deduplication | DONE | `50d137a` |
| Day 12 | Job Discovery | Matching + Scoring | DONE | `a90e4d6` |
| Day 13 | Job Discovery | Job Discovery Frontend | DONE | -- |
| Day 14 | Dashboard | Dashboard | DONE | -- |
| Day 15 | Dashboard | Profile Page | DONE | -- |
| Day 16 | Dashboard | Applications Tracker | DONE | -- |
| Day 17 | Auto-Apply | Playwright Setup + ATS Detection | DONE | -- |
| Day 18 | Auto-Apply | ATS Form Fillers | DONE | `6cd71be` |
| Day 19 | Auto-Apply | Auto-Apply Orchestrator | DONE | -- |
| Day 20 | Auto-Apply | Apply Frontend | TODO | -- |
| Day 21 | Polish | Error Handling + Edge Cases | TODO | -- |
| Day 22 | Polish | Testing | TODO | -- |
| Day 23 | Polish | Deployment + Documentation | TODO | -- |

### Day 1 Completion Notes
- FastAPI backend scaffold with health check endpoint
- Next.js 15 frontend scaffold with Tailwind v4
- Docker Compose: backend + postgres:16-alpine + redis:7-alpine
- Sentry SDK initialized in backend
- `pyproject.toml` with all backend dependencies
- All services healthy via Docker health checks

### Day 2 Completion Notes
- 14 SQLModel table models in `backend/app/models/`
- 4 enums: `ExperienceLevel`, `JobSource`, `ApplicationStatus`, `RemotePolicy`
- `TimestampModel` base class with UUID PK + timestamps
- Alembic wired to `SQLModel.metadata` in `env.py`
- Initial migration `b92a4db8bc54` — all 14 tables created in Docker Postgres
- Seed script `backend/scripts/seed.py` with test data
- Upgraded `sqlmodel` from 0.0.24 to >=0.0.38 (Pydantic v2 fix)
- All 12 FK relationships, JSON columns, unique constraints verified
- Backend health check passing, existing tests passing

### Day 3 Completion Notes
- Backend JWT auth via PyJWT with `get_current_user` and `get_optional_user` dependencies
- Auth routes: `GET /api/auth/me`, `GET /api/auth/verify`, `POST /api/auth/sync-profile`
- Health endpoint moved from `main.py` to `backend/app/routes/health.py`
- Supabase SSR client utilities (`client.ts`, `server.ts`, `middleware.ts`)
- Next.js middleware for route protection (8 protected paths, 2 auth-only redirects)
- Login/Register pages with email+password and Google OAuth
- OAuth callback handler at `/auth/callback`
- Protected dashboard page with user info and sign out
- Typed API client (`src/lib/api.ts`) with auto-auth headers
- Landing page buttons wired to `/auth/login` and `/auth/register`
- `.env.example` updated with `NEXT_PUBLIC_SUPABASE_*` vars and `SUPABASE_JWT_SECRET`
- 10 backend tests passing (9 auth + 1 health)
- Frontend builds with zero errors, all routes registered
- Sentry user context set on successful auth

### Day 4 Completion Notes
- Pydantic v2 schemas for onboarding in `backend/app/schemas/onboarding.py`
- `onboarding_step` and `onboarding_completed` fields added to `CandidateProfile`
- Alembic migration `b78895d1fb4b` with server defaults for existing rows
- 3 onboarding endpoints: `POST /api/onboarding/upload-resume`, `POST /api/onboarding/save`, `GET /api/onboarding/status`
- Resume upload extracts text from PDF via PyPDF2, returns structured pre-fill data
- Atomic save: deletes + recreates child records in single transaction with rollback
- Status endpoint returns completion percentage, existing data for pre-fill
- PyPDF2 added to `pyproject.toml` dependencies
- 8 new backend tests (all passing), 18 total tests passing
- Frontend: react-hook-form, zod, lucide-react installed
- 5-step onboarding wizard with step indicator, back/next navigation
- Zod validation schemas matching backend Pydantic schemas
- TypeScript interfaces for all onboarding types
- Client-side redirect to `/dashboard` if onboarding already completed
- Frontend builds with zero errors

### Day 5 Completion Notes
- Model registry (Approach B) with task-to-model routing table in `ai_client.py`
- Custom exception hierarchy: `AIPipelineError`, `AIModelTimeoutError`, `AIModelResponseError`, `AIPipelineExhaustedError`
- Per-call retry with exponential backoff (1s/2s), fallback to alternate model on 5xx, immediate fail on auth errors
- Malformed response handling: retry once with correction prompt
- Prompt hardening with XML-wrapped user data (`<user_data>`) and anti-injection system instructions
- Lazy Redis pool via `get_redis()` function with `close_redis()` in FastAPI lifespan shutdown
- `AIPipeline` accepts session factory callable (not session instance) for worker compatibility
- Stale job sweeper: arq cron (every 5min) + `asyncio.wait_for(timeout=120)` pipeline timeout
- Structured logging: every pipeline step logs `job_id`, `user_id`, `pipeline_step`, `model_used`, `latency_ms`
- Eager loading via `selectinload` for all 7 candidate relations
- User authorization guard in `run_full_pipeline`
- Added SQLAlchemy `Relationship` with `back_populates` to all 7 child models + `CandidateProfile`
- arq worker service added to `docker-compose.yml`
- Pydantic v2 schemas for `JobAnalysis`, `GapAnalysis`, `ResumeContent`, `ATSResult` in `schemas/ai.py`
- `pyproject.toml` + `requirements.txt` updated with `arq==0.26.1`, `redis[hiredis]==5.2.1`
- Fixed 3 pre-existing test failures (auth/onboarding tests: HTTPBearer now returns 401 for missing tokens instead of 403)
- 45 tests passing (27 new Day 5 tests + 18 existing tests)

### Day 6 Completion Notes
- `GET /api/profile/me` -- returns candidate profile summary (name, onboarding status, experience level)
- Pydantic v2 schemas for resume routes in `backend/app/schemas/resume.py`: 8 schemas with `@model_validator` for generate validation
- Resume routes in `backend/app/routes/resumes.py`:
  - `POST /api/resumes/generate` -- accepts job_id or job_description, enqueues ARQ background job
  - `POST /api/resumes/generate-manual` -- accepts raw job description text (min 50 chars)
  - `GET /api/resumes/{id}/status` -- returns generation status + ATS score
  - `GET /api/resumes` -- list with pagination (limit/offset) + deferred column loading
  - `GET /api/resumes/{id}` -- full resume with ownership check, 202 if still generating
  - `DELETE /api/resumes/{id}` -- delete with ownership check
- Dedup guard: returns cached completed resume if same user+job generated within 5 minutes
- `Resume` model updated with `status` field (generating/completed/failed) + composite index `(user_id, created_at DESC)`
- Alembic migration `c3a1f2e4d56b` for index + status column
- ARQ worker enqueue with failure handling: marks resume as "failed" if Redis unavailable
- `get_current_user` auth dependency fixed: `HTTPBearer(auto_error=False)` + explicit 401 for missing tokens
- 14 new resume route tests + 3 previously failing auth tests fixed = 59 total tests passing
- Frontend: resumes pages (list, generate, detail), API client modules, TypeScript types

---

## Decisions Locked In

| Feature | Approach | Source |
|---------|----------|--------|
| User System | Supabase Auth (email + Google OAuth) | AI Agent Plan |
| Job Discovery | LinkedIn via Playwright (daily) + JSearch/Adzuna/Remotive/Reed APIs | Merged |
| AI Matching | Fuzzy weighted scoring (pgvector optional later) | AI Agent Plan |
| Application Automation | ATS-specific fillers -> simple forms -> manual fallback cascade | Merged |
| Interview Coach | Interactive simulation with progressive difficulty, feedback, coaching tips | User's Plan |
| Resume + Cover Letter | 4-step pipeline with ATS validation loop | AI Agent Plan |
| Queue System | Redis + arq (async-native Python worker for FastAPI) | Discussion |
| Monitoring | Sentry from day one | User's Plan |
| Local Dev | Docker Compose (backend + postgres + redis) | User's Plan |
| Job URLs | All scraped jobs store source URL, clickable in frontend | User's Request |
| LinkedIn Credentials | Settings page + encrypted database storage per user | Discussion |
| Real-time | SSE for AI streaming + WebSocket for apply progress | Discussion |
| AI Models | GLM 5.1 (primary, OpenAI-compatible endpoint) + GPT-4o (resume tailoring only) | Discussion |

---

## Tech Stack

```
Frontend:  Next.js 15 + TypeScript + Tailwind CSS v4 + Supabase Client
Backend:   FastAPI + Python 3.12 + SQLModel + Alembic
Database:  Supabase (PostgreSQL + Auth + Storage + Realtime)
Cache/Queue: Redis + arq (async Python workers)
AI Models: GLM 5.1 (primary) + GPT-4o (resume tailoring only)
Browser:   Local Playwright + playwright-stealth (LinkedIn discovery + auto-apply)
Monitoring: Sentry
Deploy:    Vercel (frontend) + Railway (backend)
Local Dev: Docker Compose
```

### AI Model Routing

| Task | Model | Why |
|------|-------|-----|
| Resume parsing (PDF extraction) | GLM 5.1 | Structured extraction, large context, cheap |
| Job analysis (extract skills, requirements) | GLM 5.1 | Classification task |
| Gap analysis + match scoring | GLM 5.1 | Logic/reasoning |
| **Resume tailoring (generation)** | **GPT-4o** | Best quality for professional writing |
| **Resume retry (after ATS fail)** | **GPT-4o** | Needs best quality on retry |
| Cover letter generation | GLM 5.1 | Good enough, saves money |
| Interview coach (interactive) | GLM 5.1 | Streaming conversation, structured feedback |
| Job deduplication + matching | Local scoring | No AI needed, fuzzy string matching |

---

## Database Schema (Core Models)

```
User (Supabase Auth managed)
CandidateProfile (1:1 with user)
  - personal_info, location, urls, headline, summary
  - experience_level: enum (student/fresher/junior/mid/senior/lead/executive)
  - linkedin_email: encrypted (for Playwright login)
  - linkedin_password_encrypted: encrypted (for Playwright login)
Education (FK -> candidate)
Experience (FK -> candidate)
Project (FK -> candidate)
Skill (FK -> candidate, with category + proficiency)
TargetRole (FK -> candidate, with priority + keywords)
Certification (FK -> candidate)
Language (FK -> candidate)
Job (discovered jobs, shared across users)
  - source: enum (linkedin/adzuna/jsearch/remotive/reed)
  - source_url: string (clickable link to original posting)
  - title, company, description, salary_range
  - location, experience_level, job_type, remote_policy
  - ats_platform (detected), apply_url
  - external_id (for deduplication)
  - scraped_at (timestamp)
Application (FK -> user, FK -> job)
  - status: saved -> generating -> ready -> applied -> screening -> interview -> offer -> rejected -> withdrawn
Resume (FK -> user, FK -> job nullable)
  - content_json (structured sections), ats_score, template_id
CoverLetter (FK -> user, FK -> job)
InterviewPrep (FK -> user, FK -> job)
  - questions: JSONB array of {question, category, difficulty}
InterviewSession (FK -> user, FK -> interview_prep)
  - messages: JSONB array of {role, content, score, feedback}
  - current_difficulty, completed_at
```

---

## Phase 1: Foundation (Days 1-4)

### Day 1: Project Scaffolding + Docker Compose
- Create new project directory `jobedin-v3/`
- `backend/` -- FastAPI, SQLModel, Alembic
- `frontend/` -- Next.js 15, TypeScript, Tailwind v4
- `docker-compose.yml` -- backend + postgres + redis
- `.env.example` with all required env vars
- Sentry SDK initialization in both frontend and backend

### Day 2: Database + Supabase Setup
- Supabase project (PostgreSQL + Auth + Storage)
- Alembic migrations for all models above
- `database.py` connection pool with Supabase
- Seed script for testing

### Day 3: Auth + Middleware
- Supabase Auth client (frontend + backend)
- Backend middleware to validate Supabase tokens
- Login / Register pages (email + Google OAuth)
- Protected route middleware (frontend)
- Sentry user context on login

### Day 4: Onboarding API + Frontend Wizard
- `POST /onboarding/upload-resume` -- AI parsing returns structured data
- `POST /onboarding/save` -- single transaction, all tables, atomic
- `GET /onboarding/status` -- completion percentage
- 5-step onboarding wizard:
  1. Resume upload (optional, auto-fills everything)
  2. Personal details + target roles
  3. Skills + experience level
  4. Education + experience (combined)
  5. Review + confirm
- Session persistence in Supabase, not localStorage

---

## Phase 2: AI Pipeline Core (Days 5-9)

### Day 5: AI Client Setup + Prompt Engineering

**Architecture:** Model registry with task-to-model routing (Approach B) -- a single `AIClient` class with a routing table that maps each pipeline task to its designated model, instead of hardcoded dual-client instances.

**Custom Exceptions** (in `ai_client.py`):
- `AIPipelineError` -- base exception for all pipeline errors
- `AIModelTimeoutError` -- model call exceeded timeout
- `AIModelResponseError` -- model returned malformed/invalid response
- `AIPipelineExhaustedError` -- all retries + fallbacks exhausted

**Retry Strategy:**
- Per-call retry: 2 attempts with exponential backoff (1s, 2s)
- Fallback to alternate model on 5xx errors (GLM <-> GPT-4o)
- Fail immediately on auth errors (4xx) -- no retry
- Malformed response handling: retry once with correction prompt, then raise `AIModelResponseError`

**Prompt Hardening:**
- XML-wrapped user data: `<user_data>...</user_data>` to separate user input from instructions
- Anti-injection system instructions in every prompt
- All prompts templated in `ai_prompts.py`

**Redis + arq queue** for AI generation tasks with:
- Lazy Redis pool: function-based `get_redis()` initialization (not module-level singleton)
- Worker DB session: `AIPipeline` accepts session factory callable, not session instance
- Stale job sweeper: periodic arq cron (every 5min) + pipeline timeout via `asyncio.wait_for(timeout=120)`

**Structured Logging + Sentry:**
- Every pipeline step logs: `job_id`, `user_id`, `pipeline_step`, `model_used`, `latency_ms`
- Errors captured by Sentry with full pipeline context

**Eager Loading:** `selectinload` for all 7 candidate relations in `run_full_pipeline` (skills, education, experience, projects, target_roles, certifications, languages) to avoid N+1 queries.

**User Authorization Guard:** `run_full_pipeline` verifies the authenticated user owns the candidate profile before processing.

**GLM Compatibility Checkpoint:** Before implementing structured output methods, validate `response_format` support on GLM 5.1's OpenAI-compatible endpoint. Fall back to JSON-in-text extraction if unsupported.

**Dependencies:** `requirements.txt` must stay in sync with `pyproject.toml`.

Resume tailoring prompt -- 4-step pipeline:

```
Step 1: ANALYZE job description
  - Extract: required skills, preferred skills, responsibilities, keywords, tone
  - Output: structured JobAnalysis (JSON schema enforced)

Step 2: MAP candidate profile to job
  - Compare candidate skills vs required skills
  - Identify gaps and strengths
  - Output: structured GapAnalysis with match_score

Step 3: GENERATE tailored resume
  - Input: JobAnalysis + GapAnalysis + candidate full profile
  - Reorder sections by relevance
  - Rewrite bullet points to include job keywords
  - Output: structured ResumeContent (sections as JSON)
  - Each bullet point must contain at least 1 keyword from job description

Step 4: VALIDATE (ATS scoring)
  - Check keyword density (>60% of job keywords present)
  - Check section completeness (all standard sections present)
  - If score < 80, feed feedback back to Step 3 and retry (max 2 retries)
  - Output: final resume JSON + ats_score + ats_breakdown
```

**Files Created/Modified:**
- `backend/app/schemas/ai.py` -- Pydantic v2 schemas: JobAnalysis, GapAnalysis, ResumeContent, ATSResult
- `backend/app/services/ai_client.py` -- AIClient with model registry, retry logic, structured output, custom exceptions
- `backend/app/services/ai_pipeline.py` -- AIPipeline with 4-step resume pipeline, timeout, sweeper, auth guard, eager loading
- `backend/app/services/ai_prompts.py` -- Prompt templates with injection hardening
- `backend/app/services/redis_pool.py` -- Lazy Redis pool with `get_redis()` function
- `backend/app/workers/ai_worker.py` -- arq worker with generate_resume_job + stale job sweeper cron
- `backend/app/config.py` -- Add AI-related config fields (GLM_API_KEY, OPENAI_API_KEY, model URLs, timeouts)
- `backend/app/main.py` -- Wire Redis shutdown, mount worker startup
- `docker-compose.yml` -- Add arq worker service
- `backend/app/tests/test_ai_client.py` -- Unit tests for AIClient (model routing, retry, fallback, error handling)
- `backend/app/tests/test_ai_pipeline.py` -- Unit tests for AIPipeline (pipeline steps, timeout, auth guard)
- `pyproject.toml` + `requirements.txt` -- Add: arq, redis[hiredis], openai, tenacity

**Tests (Day 5 scope):**
- Unit tests for model registry routing (task -> correct model)
- Unit tests for retry strategy (backoff timing, fallback on 5xx, no retry on auth errors)
- Unit tests for custom exceptions (all 4 types)
- Unit tests for prompt injection hardening
- Unit tests for pipeline timeout (mock asyncio.wait_for)
- Unit tests for user authorization guard
- Token limit edge case tests
- Schema validation tests
- Integration tests deferred to Day 9

### Day 6: Resume Generation Pipeline
- `POST /api/resumes/generate` -- job_id or job_description, enqueues ARQ background job
- `POST /api/resumes/generate-manual` -- raw job description text (min 50 chars)
- `GET /api/resumes/{id}/status` -- generation status + ATS score
- `GET /api/resumes` -- list with pagination + deferred column loading
- `GET /api/resumes/{id}` -- full resume with ownership check, 202 if still generating
- `DELETE /api/resumes/{id}` -- delete with ownership check
- Dedup guard: returns cached completed resume within 5-minute window
- `GET /api/profile/me` -- candidate profile summary for resume generation context
- arq background worker for long-running generation
- SSE streaming for progress events (deferred to polish phase)

### Day 7: Cover Letter Generation
- Structured prompt with tone selection (professional/casual/enthusiastic)
- Company-specific research integration
- References specific job requirements
- `POST /api/cover-letters/generate`
- All structured JSON outputs

### Day 7 Completion Notes
- `CoverLetter` model updated: added `status`, `content_json` (JSON), `job_description` fields; made `job_id` and `content` nullable; added composite index `(user_id, created_at DESC)`
- Alembic migration `be0f67fcffd6` for new columns + index + nullable changes
- `CoverLetterContent` + `CoverLetterParagraph` Pydantic schemas in `schemas/ai.py` for structured AI output
- 7 API request/response schemas in `schemas/cover_letter.py` with tone validation (`professional|casual|enthusiastic`)
- `generate_cover_letter_prompt()` in `ai_prompts.py`: hooks, keyword addressing, tone matching, 300-400 word target, anti-fabrication rules
- `generate_cover_letter()` + `run_cover_letter_pipeline()` in `AIPipeline`: single AI call (no ATS loop), reuses `analyze_job()`, `_verify_ownership()`, `_load_candidate()`
- `generate_cover_letter_job()` in `ai_worker.py` with success/failure status updates; registered in `WorkerSettings.functions`
- 6 cover letter routes in `routes/cover_letters.py`:
  - `POST /api/cover-letters/generate` -- job-linked or JD-linked
  - `POST /api/cover-letters/generate-manual` -- raw JD text
  - `GET /api/cover-letters/{id}/status` -- poll status
  - `GET /api/cover-letters` -- paginated list with deferred column loading
  - `GET /api/cover-letters/{id}` -- full detail with ownership check, 202 if generating
  - `DELETE /api/cover-letters/{id}` -- delete with ownership check
- Dedup guard: returns cached completed cover letter within 5-minute window (same user+job)
- Router registered in `main.py`
- 14 backend tests passing (happy paths, dedup, auth, validation, pagination, ownership)
- Frontend: `CoverLetterCard` component, cover letter types, API client, list page, generate page with tone selector (3 radio cards), detail page with polling
- 73 total backend tests passing, frontend builds cleanly

### Day 8 Completion Notes
- `InterviewPrep` model updated: added `status`, `job_description`, `job_title`, `company_name` fields; made `job_id` nullable; added composite index `(user_id, created_at DESC)`
- `InterviewSession` model updated: added `status`, `overall_score`, `questions_answered` fields; added composite index `(user_id, created_at DESC)`
- Alembic migration `d4e5f6a7b8c9` for new columns + indexes + nullable changes
- `InterviewQuestion`, `InterviewPrepResult`, `CoachEvaluation`, `CoachResponse` Pydantic schemas in `schemas/ai.py`
- 3 new prompt functions in `ai_prompts.py`: `generate_interview_questions_prompt()`, `evaluate_answer_prompt()`, `session_summary_prompt()`
- 4 new pipeline methods in `ai_pipeline.py`: `generate_interview_questions()`, `evaluate_interview_answer()`, `generate_session_summary()`, `run_interview_prep_pipeline()`
- 15 route schemas in `schemas/interview.py` (setup, chat, status, list, session detail)
- 7 API endpoints in `routes/interview.py`:
  - `POST /api/interview/setup` -- job-linked or JD-linked, enqueues ARQ job for question bank generation
  - `GET /api/interview/preps/{id}/status` -- poll question generation status
  - `GET /api/interview/preps` -- paginated list of interview preps
  - `POST /api/interview/chat` -- interactive coaching turn (synchronous AI call per turn)
  - `GET /api/interview/sessions` -- paginated list of practice sessions
  - `GET /api/interview/sessions/{id}` -- full session detail with messages and scores
  - `DELETE /api/interview/preps/{id}` -- delete with ownership check
- Chat endpoint logic: validates prep completed, creates/reuses session, evaluates answers synchronously, progressive difficulty (score >= 7 bumps up, < 4 bumps down), category rotation for variety
- Question bank: 12 questions across 4 categories (company_research, technical, behavioral, culture_fit) at 3 difficulty levels
- `generate_interview_prep_job()` in `ai_worker.py`; registered in `WorkerSettings.functions`
- Router registered in `main.py`
- 16 backend tests passing (setup with job_id, setup with manual JD, validation, dedup, status polling, list preps, chat first turn, chat ownership, prep not found, prep still generating, list sessions, session detail, delete prep, delete unauthorized)
- Frontend: `InterviewCard`, `InterviewChat`, `InterviewScoreCard`, `DifficultyIndicator` components
- Frontend: interview types, API client, 3 pages (list with inline setup form, interactive coach with chat UI + polling, session detail review)
- "Interview Coach" added to navigation in `AppLayout.tsx`
- Key design decision: question bank generation is async (ARQ job), but interactive chat turns are synchronous AI calls within the route handler (~3-5s each, fast enough without streaming)

### Day 8: Interactive Interview Coach
- `POST /api/interview/setup` -- generates question bank from job description
  - Categories: company research, role-specific technical, behavioral (STAR), culture fit
  - Difficulty levels: basic -> intermediate -> advanced
- `POST /api/interview/chat` -- interactive coaching session
  - AI asks question -> user answers -> AI evaluates -> AI gives feedback + score
  - Progressive difficulty: next question is harder if score > 7/10
  - Coaching tips between questions
  - Streaming responses (SSE)
- `GET /api/interview/session/{id}` -- full session history with scores
- `GET /api/interview/sessions` -- list all practice sessions

### Day 9: AI Pipeline Testing + Polish
- Integration tests for every AI pipeline step
- Prompt regression tests (golden outputs)
- Error handling: model timeout, rate limit, invalid output
- Fallback: GLM <-> GPT-4o mutual retry
- Token usage tracking per user

### Day 9 Completion Notes
- `AIResult` dataclass introduced in `ai_client.py`: wraps all AI call results with `content`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `model_used`, `latency_ms`
- `AIClient.call()` and `AIClient._call_with_structured_output()` now return `AIResult` instead of raw content
- Token usage extraction from OpenAI-compatible API response `usage` fields
- `AIPipeline._token_usage` list tracks per-call usage; `get_token_usage()` returns aggregated stats
- All pipeline methods (`analyze_job`, `gap_analysis`, `generate_resume`, `validate_ats`, `generate_cover_letter`, `evaluate_interview_answer`, `generate_session_summary`) now record token usage via `_record_usage()`
- `run_full_pipeline`, `run_cover_letter_pipeline`, `run_interview_prep_pipeline` all inject `token_usage` into returned dict
- `AITokenUsage` SQLModel for database persistence of per-task usage
- Alembic migration `e5f6a7b8c9d0` creates `ai_token_usage` table with indexes on `user_id` and `(user_id, created_at DESC)`
- `_persist_token_usage()` helper in `ai_worker.py` creates `AITokenUsage` records after each pipeline run
- All 3 worker jobs (`generate_resume_job`, `generate_cover_letter_job`, `generate_interview_prep_job`) persist token usage
- 7 golden output fixture files in `tests/fixtures/golden_outputs/`: `analyze_job.json`, `gap_analysis.json`, `generate_resume.json`, `validate_ats.json`, `generate_cover_letter.json`, `interview_questions.json`, `evaluate_answer.json`
- Integration test files: `test_resume_pipeline_integration.py` (5 tests), `test_cover_letter_pipeline_integration.py` (5 tests), `test_interview_pipeline_integration.py` (5 tests)
- Error handling tests in `test_error_handling.py` (8 tests): timeout, rate limit, invalid output, GLM-to-OpenAI fallback, OpenAI-to-GLM fallback, all models exhausted, empty response, model refusal
- Prompt regression tests in `test_prompt_regression.py` (11 tests): golden output schema validation, structural requirements (anti-injection, user_data wrapping), template stability via SHA-256 hash
- Token tracking tests in `test_token_tracking.py` (6 tests): extraction from response, aggregation across calls, AIResult field behavior
- `requirements.txt` synced with `pyproject.toml` (`sqlmodel>=0.0.38`)
- Fixed missing `Any` import in `test_ai_client.py`
- 142 total backend tests passing, frontend builds with zero errors, all Docker services healthy

---

## Phase 3: Job Discovery (Days 10-13)

### Day 10: LinkedIn Playwright Discovery
- `LinkedInDiscovery` class with playwright-stealth
- Login flow with CAPTCHA detection + user notification
- Search by target roles, filter by "Past Week"
- Scrape top 25-50 jobs per role
- Store `source_url` for every job (clickable link back to LinkedIn)
- Credentials stored encrypted in database, input via Settings page
- One session per day maximum (timestamp guard)
- Random delay jitter (1-4s between actions)

### Day 10 Completion Notes
- **Config / deps:** `CREDENTIAL_ENCRYPTION_KEY`, LinkedIn tuning and API placeholders in `config.py`; `rapidfuzz` in `requirements.txt` / `pyproject.toml`; `.env.example` updated.
- **Crypto:** `backend/app/services/credential_crypto.py` (Fernet encrypt/decrypt for LinkedIn fields).
- **LinkedIn source:** `backend/app/services/job_sources/linkedin.py` with `LinkedInDiscovery`, stealth helpers, `LinkedInSessionCooldownError` and related exceptions in `exceptions.py`.
- **Ingestion:** `backend/app/services/job_discovery.py` — normalize LinkedIn URLs, PostgreSQL upsert, `run_linkedin_discovery`, merged scrape errors; naive UTC timestamps for `Job` columns (`scraped_at`, row `created_at`/`updated_at`) to match existing `TIMESTAMP WITHOUT TIME ZONE` schema.
- **Worker:** `backend/app/workers/job_worker.py` (ARQ `linkedin_discovery_job`); `docker-compose.yml` service `job-worker`; `backend/Dockerfile.worker` (Python 3.12 + Playwright Chromium).
- **APIs:** `backend/app/routes/settings.py` (LinkedIn credential save/delete/status); `backend/app/routes/jobs.py` (discover enqueue, list with filters, save/unsave); Pydantic schemas in `schemas/settings.py`, `schemas/jobs.py`; discover path eager-loads `target_roles` to avoid async lazy-load errors.
- **App wiring:** `main.py` registers jobs + settings routers.
- **Model / migration:** `CandidateProfile.linkedin_last_scraped_at` as timezone-aware (`DateTime(timezone=True)`); Alembic `f1a2b3c4d5e6_add_linkedin_last_scraped_at_to_candidate.py`.
- **Tests:** `backend/tests/test_credential_crypto.py`, `test_linkedin_discovery_unit.py`, `test_job_discovery_unit.py`, `test_settings_routes.py`, `test_jobs_routes.py` — **193** backend tests passing (`pytest tests/ -o addopts=`).
- **Ops note:** Run `alembic upgrade head` where Postgres matches app URL; full LinkedIn E2E requires Redis + `job-worker` + real credentials (manual checklist).

### Day 11: API Sources + Merge/Deduplication
- JSearch API (covers Indeed + multiple boards)
- Adzuna API
- Remotive API
- Reed API (UK-specific)
- All fire in parallel with `asyncio.gather(return_exceptions=True)`
- Merge all sources + LinkedIn results
- Deduplication by fuzzy matching on `(title, company, location)`
- Every job stores `source_url` + `source` enum

### Day 11 Completion Notes
- **API adapters:** `JobSourceAdapter` ABC with `JSearchAdapter`, `AdzunaAdapter`, `RemotiveAdapter`, `ReedAdapter` in `backend/app/services/job_sources/`. Each implements `build_url()`, `build_params()`, `build_headers()`, `_map_response()`. Registry pattern via `ADAPTER_REGISTRY`.
- **Parallel fetch:** `run_api_discovery()` in `job_discovery.py` uses `asyncio.gather(return_exceptions=True)` for all sources, per-source ingest.
- **Job dedup:** `backend/app/services/job_dedup.py` — `SequenceMatcher` fuzzy matching on `(title, company)` with thresholds 0.85/0.80. Duplicate sources merged into `alternate_sources` JSON field.
- **Bulk upsert:** PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` via SQLAlchemy for job ingestion.
- **Model updates:** `Job.alternate_sources` JSON column, `JobSource` enum with 5 values. Alembic migrations `a1b2c3d4e5f6` and `b2c3d4e5f6a7` (alternate_sources + discovery_logs).
- **Discovery log:** `DiscoveryLog` model tracks each API discovery run (sources, keywords, counts, duration, errors).
- **Tests:** `test_api_sources.py` (adapter unit tests), `test_api_discovery_integration.py`, `test_job_dedup.py` — all passing.

### Day 12 Completion Notes
- **Scoring engine:** `backend/app/services/match_scorer.py` — `MatchScorer` class with 4 weighted dimensions: skills (40%), experience level (25%), role relevance (25%), location (10%). `SequenceMatcher` fuzzy matching, bigram keyword extraction, stop word filtering.
- **Score cache:** `JobMatch` SQLModel in `backend/app/models/job_match.py` with composite unique constraint `(user_id, job_id)` and index `(user_id, match_score)`. Bulk upsert via PostgreSQL `on_conflict_do_update`. 24h staleness window.
- **Alembic migration:** `c3d4e5f6a7b8` creates `job_matches` table with all indexes and foreign key.
- **API routes (new):** `POST /api/jobs/match` (enqueue ARQ job), `GET /api/jobs/match/status` (poll progress), `GET /api/jobs/{id}/score` (cached or inline computed breakdown).
- **API routes (updated):** `GET /api/jobs` — LEFT JOIN `job_matches`, returns `match_score` per job, `sort_by` whitelist (`match_score`, `created_at`, `salary_max`) with `DESC NULLS LAST`. `GET /api/jobs/{id}` — includes `match_score` + `match_breakdown`.
- **Worker:** `match_jobs_job` in `job_worker.py` — processes unscored jobs in chunks of 100, bulk upserts results. Auto-triggered after `linkedin_discovery_job` completes.
- **Config:** `MATCH_SCORE_STALENESS_HOURS=24`, `MATCH_SCORE_CHUNK_SIZE=100`.
- **Schemas:** `backend/app/schemas/match.py` — `MatchBreakdown`, `JobMatchResultSchema`, `MatchRequest`, `MatchResponse`, `MatchStatusResponse`, `JobScoreResponse`.
- **Frontend types:** `frontend/src/types/job.ts` — interfaces for all job/match/discover types.
- **Frontend API client:** `frontend/src/lib/api/jobs.ts` — typed wrappers for all job endpoints.
- **Frontend components:** `JobCard.tsx` (score ring, source badge, remote badge, salary range), `JobMatchScore.tsx` (SVG donut chart + 4 dimension bars + skill pills).
- **Frontend pages:** `frontend/src/app/jobs/page.tsx` (listing with filters, sorting, discover + match buttons, polling), `frontend/src/app/jobs/[id]/page.tsx` (detail with match breakdown, apply actions).
- **Nav:** "Jobs" added to `AppLayout.tsx` navLinks. Dashboard Jobs card activated with link.
- **Tests:** 29 new tests in `test_match_scorer.py` covering keyword extraction, all 4 dimension scorers, weighted combination, score_job, score_jobs_batch, get_cached_score, edge cases. 152 total unit tests passing.

### Day 12: Matching + Scoring
- `POST /api/jobs/match` -- score candidate profile against discovered jobs
- Weighted fuzzy scoring:
  - Skills match: 40% (fuzzy string matching, "React.js" matches "React")
  - Experience level alignment: 25%
  - Role relevance: 25%
  - Location compatibility: 10%
- Store match scores in DB for sorting
- Auto-filter by user's target roles and experience level

### Day 13: Job Discovery Frontend
- Jobs page with real-time search
- Filters: source, experience level, job type, remote/hybrid/onsite, date posted
- Job cards: match score, salary range, source badge, experience level, clickable source URL
- "Generate Resume" and "Generate Cover Letter" buttons per job card
- Save/unsave jobs with bookmark
- Skeleton loading + error states
- "Discover Jobs" button triggers LinkedIn + API sources (shows LinkedIn status)

### Day 13 Completion Notes
- **Backend `is_saved`:** Added `is_saved: bool = False` to `JobListItem` and `JobDetailResponse` schemas. `list_jobs()` OUTER JOINs `Application` (status=saved) to compute per-job. `get_job()` queries `Application` separately.
- **Backend search validation:** Added `max_length=200` to `search` Query param in `list_jobs()`.
- **Frontend search:** Debounced text input (300ms) on jobs page, passes `search` param to API.
- **Frontend filters:** All 5 filters wired: source, experience level, job type, remote policy, sort by. Reset offset to 0 on filter change.
- **Frontend pagination:** "Load More" button showing remaining count, disabled during loading to prevent double-click.
- **Frontend polling cleanup:** `useRef` for interval IDs, cleaned up in `useEffect` return. No memory leaks.
- **Frontend AbortController:** In-flight `loadJobs()` fetch cancelled when new one fires, preventing stale response overwrites.
- **Frontend error state:** Error banner with retry button when API fails.
- **Frontend source status:** `getSourcesStatus()` loaded on mount, LinkedIn availability shown near Discover button.
- **Frontend save/unsave:** Optimistic UI toggle on job detail page. Reverts on error, handles 409/404 gracefully.
- **Frontend generate links:** "Generate Resume" -> `/resumes/generate?job_id={id}`, "Generate Cover Letter" -> `/cover-letters/generate?job_id={id}`.
- **JobCard:** Optional `isSaved` prop, bookmark icon indicator in top-right corner.
- **Integration tests:** 7 new tests in `test_jobs_list.py` covering `is_saved` (false/true), search, source filter, remote_policy filter, search max_length rejection, detail `is_saved`.
- **TypeScript:** Zero errors on `tsc --noEmit`.

---

## Phase 4: Dashboard + Core Pages (Days 14-16)

### Day 14: Dashboard
- Overview cards: applications sent, interviews scheduled, response rate
- Recent activity feed (real-time via Supabase Realtime)
- Quick actions: Discover Jobs, Generate Resume, Start Interview Coach
- Empty states with CTAs for new users

#### Day 14 Completion Notes
- `GET /api/dashboard` endpoint with `asyncio.gather(return_exceptions=True)` for graceful degradation
- Aggregated stats: jobs matched, applications, resumes, cover letters, interview sessions, avg ATS/match/session scores
- Recent activity feed: 10 most recent items across 4 entity types, sorted by created_at DESC
- Activity items include `job_id` for linking applications to `/jobs/{job_id}`
- Frontend: 6 stat cards (null -> "--"), ActivityFeed, QuickActions, skeleton loading, empty state, error state
- AbortController 10s timeout on dashboard API call
- "Cover Letters" added to navigation
- 16 backend tests covering auth, empty, with-data, activity, profile, partial failure scenarios
- Structured logging at endpoint entry/exit with latency_ms

### Day 15: Profile Page
- Editable sections with inline CRUD
- Sections: Personal Info, Target Roles, Skills, Education, Experience, Projects, Certifications, Languages
- Single `GET /api/profile/full` fetch strategy (eager-loads all 7 child entities)
- Resume re-upload button that re-parses and suggests updates
- LinkedIn credentials section (encrypted storage)
- User avatar with initials dropdown in header

#### Day 15 Completion Notes
- **Backend schemas:** `backend/app/schemas/profile.py` (NEW) — 21 CRUD schemas (Create/Update/Response for 7 entities) + `ProfileUpdateRequest`, `ProfileMeResponse` (migrated from `resume.py`), `ProfileDetailResponse`
- **Backend routes:** `backend/app/routes/profile.py` expanded from 1 to 22 endpoints: `GET /full` (eager-loaded via `selectinload`), `PATCH /me`, and CRUD (POST/PUT/DELETE) for educations, experiences, skills, projects, target-roles, certifications, languages
- **Ownership check:** `_get_owned_item()` helper queries by `id` AND `candidate_id`, returns 404 if not owned
- **Frontend types:** `frontend/src/types/profile.ts` expanded from 1 to 29 interfaces matching all backend schemas
- **Frontend API clients:** `frontend/src/lib/api/profile.ts` expanded from 1 to 22 functions; `frontend/src/lib/api/settings.ts` (NEW) for LinkedIn credentials
- **Frontend components:** `ProfileSection.tsx` (reusable section card), `ProfilePersonalInfo.tsx` (view/edit toggle), `ProfileChildList.tsx` (generic CRUD list with hover actions)
- **Frontend page:** `frontend/src/app/profile/page.tsx` — 10 sections rendered from single `getProfileFull()` call, refetches after any child entity mutation
- **Navigation:** `AppLayout.tsx` updated with user avatar dropdown (initials from user metadata, Profile link, Sign Out) + Profile link in mobile nav
- **API client:** Added `patch` method to base `api.ts` client
- **Tests:** 33 backend tests covering auth, full profile, PATCH, CRUD for all 7 entities, ownership checks, validation; 0 TypeScript errors; 0 linter errors

### Day 16: Applications Tracker
- Pipeline view: Saved -> Generating -> Ready -> Applied -> Screening -> Interview -> Offer -> Rejected
- Drag-and-drop status updates
- Filter by status, date, company
- Quick actions: view resume, view cover letter, start interview prep
- Application detail modal with full timeline

#### Day 16 Completion Notes
- **Backend schemas:** `backend/app/schemas/applications.py` (NEW) — `ApplicationStatusEnum`, `ApplicationUpdate`, `ApplicationNotesUpdate`, `ApplicationJobInfo`, `ApplicationListItem`, `ApplicationListResponse`, `ApplicationDetail`, `ApplicationStats`
- **Backend routes:** `backend/app/routes/applications.py` (NEW) — 6 endpoints: `GET /api/applications` (paginated list with filters: status, company, sort_by), `GET /api/applications/stats`, `GET /api/applications/{id}`, `PATCH /api/applications/{id}`, `DELETE /api/applications/{id}`, `POST /api/applications/{id}/notes`
- **Router registration:** `main.py` updated with `applications_router`
- **Frontend types:** `frontend/src/types/application.ts` (NEW) — `ApplicationStatus`, `ApplicationJobInfo`, `ApplicationListItem`, `ApplicationListResponse`, `ApplicationDetail`, `ApplicationStats`, `ApplicationUpdate`
- **Frontend API client:** `frontend/src/lib/api/applications.ts` (NEW) — `listApplications()`, `getApplication()`, `updateApplication()`, `deleteApplication()`, `getApplicationStats()`, `updateApplicationNotes()`
- **Frontend components:** `ApplicationCard.tsx` (card with status badge, match score, artifact dots), `PipelineColumn.tsx` (Kanban column with count badge), `ApplicationDetailModal.tsx` (full detail with status transitions, notes, quick-action links, delete)
- **Frontend page:** `frontend/src/app/applications/page.tsx` — Kanban board with 7 pipeline columns + collapsible terminal statuses, company search, status filter pills, pipeline/list view toggle, loading skeletons, empty state with CTA
- **Navigation:** `AppLayout.tsx` updated — "Applications" added between "Jobs" and "Resumes"
- **Dashboard:** Applications stat card now links to `/applications` instead of `/jobs`
- **Tests:** 21 backend tests covering list (filter, search, pagination), stats, detail, update status, notes, delete, ownership checks, auth, sort; 0 TypeScript errors; 0 linter errors

#### Day 17 Completion Notes
- **BrowserService:** `backend/app/services/browser_service.py` (NEW) — Async context manager for Playwright with stealth, lifecycle management, screenshot capture, directory creation, safe navigation, random delay
- **ATSDetector:** `backend/app/services/ats_detector.py` (NEW) — URL pattern matching (Greenhouse, Lever, Workday) + DOM inspection fallback + ATS difficulty classification (easy_apply / multi_step / manual_only) + CAPTCHA detection
- **URL Validator:** `backend/app/services/url_validator.py` (NEW) — SSRF protection blocking private IPs, loopback, link-local, reserved, multicast addresses and non-http(s) schemes
- **ATS Fillers ABC:** `backend/app/services/ats_fillers/` (NEW) — Abstract base class with `can_handle`, `fill`, `submit`, `verify` + exception hierarchy (ATSError, ATSDetectionError, ATSFormError, ATSSubmitError, ATSTimeoutError, ATSCAPTCHAError)
- **Application model:** Added 8 ATS fields (ats_platform, ats_detection_method, ats_confidence, ats_form_url, ats_detected_fields, ats_screenshot_path, ats_detection_error, ats_difficulty) + composite index on (user_id, status)
- **Alembic migration:** `e7a8b9c0d1e2` — adds all ATS fields + index to applications table
- **Schemas:** `backend/app/schemas/apply.py` (NEW) — ATSDetectRequest, ATSDetectResponse, ATSDetectionStatusResponse, ATSDifficultyEnum
- **Routes:** `backend/app/routes/apply.py` (NEW) — 3 endpoints: POST /api/apply/detect (concurrency guard: status check + ARQ job_id dedup), GET /api/apply/detect/{id}/status, GET /api/apply/detect/{id}/screenshot (path traversal guard)
- **Worker:** `ats_detect_job` added to `job_worker.py` — catch-all rescue (reverts status on error), deleted-row guard (graceful exit), full detection pipeline with BrowserService + ATSDetector
- **Stale sweeper:** `sweep_stale_ats_detections` cron in `job_worker.py` — reverts Applications stuck in 'generating' for >10 minutes
- **Auto-detect on save:** `routes/jobs.py` save_job enqueues `ats_detect_job` when job has apply_url
- **Ingestion-time detection:** `job_discovery.py` runs URL-pattern ATS detection during job ingestion (no browser needed)
- **Config:** ATS_SCREENSHOT_DIR, ATS_DETECT_TIMEOUT_MS, ATS_DETECT_HEADLESS, ATS_STALE_DETECTION_MINUTES added to settings
- **Dockerfile.worker:** Added `mkdir -p /app/screenshots`
- **Router registration:** `apply_router` registered in `main.py`
- **Tests:** 37 new tests (13 url_validator + 14 ats_detector + 10 apply_routes); 355 total tests passing

### Day 18 Completion Notes
- **BaseATSFiller:** `backend/app/services/ats_fillers/base_filler.py` (NEW) — Plain utility class (not an ATSFiller subclass) with 10 shared helpers: `fill_text_field`, `select_dropdown`, `upload_file`, `check_checkbox`, `fill_name_fields`, `fill_contact_fields`, `fill_education_fields`, `fill_experience_fields`, `normalize_phone`, `wait_and_screenshot`
- **FieldResult / FillResult:** Added to `exceptions.py` — Pydantic models for per-field and per-form results; individual field helpers return `FieldResult` (never raise on missing fields); `fill()` returns `FillResult` with `filled` and `skipped` lists
- **ATSFillerRegistry:** `backend/app/services/ats_fillers/registry.py` (NEW) — Dict-based routing from platform name to concrete filler instance; `get_filler()` returns None for unknown platforms; `supported_platforms()` lists all 3
- **GreenhouseFiller:** `backend/app/services/ats_fillers/greenhouse.py` (NEW) — Single-page form filling; class-level `SELECTORS` dict; auto-declines EEO/voluntary fields; fills name, contact, education (max 3), experience (max 3), resume upload; verification via confirmation text or URL
- **LeverFiller:** `backend/app/services/ats_fillers/lever.py` (NEW) — React-rendered form support; fills full name (combined), email, phone, org, URLs (LinkedIn, GitHub, portfolio, website); simplest ATS form; verification via `.application-complete` class or thanks/applied URL
- **WorkdayFiller:** `backend/app/services/ats_fillers/workday.py` (NEW) — Multi-step wizard navigation (5+ steps); `data-automation-id` selectors; 180s total timeout with `asyncio.timeout`; step-by-step fill with `wait_for_load_state("networkidle")` between transitions; verification via confirmation container or "Application Submitted" text
- **Security:** `upload_file` validates path is within `ATS_RESUME_DIR` (path traversal protection); logging uses field names only, never PII values
- **Config:** Added `ATS_FILL_TIMEOUT_SECONDS=120` and `ATS_RESUME_DIR=./resumes` to `config.py`
- **`__init__.py` update:** Updated `fill()` return type to `FillResult` in `ATSFiller` ABC
- **MAX_ENTRIES = 3** for experience/education entries across all fillers
- **Tests:** 87 new tests (31 base_filler + 13 greenhouse + 14 lever + 14 workday + 8 registry + 7 model/misc); **442 total tests passing**; 0 regressions

---

## Phase 5: Auto-Apply (Days 17-20)

### Day 17: Playwright Setup + ATS Detection
- `BrowserService` with async context manager
- `detect_ats(url)` -- identify Greenhouse/Lever/Workday
- Stealth mode for all browser sessions
- Redis + arq queue for apply tasks

### Day 18: ATS Form Fillers
- Greenhouse form filler (detect -> fill -> submit -> verify)
- Lever form filler
- Workday form filler (multi-page navigation)
- Each as standalone class with: `detect()`, `fill()`, `submit()`, `verify()`

### Day 19: Auto-Apply Orchestrator
- Cascade logic:
  1. Try company career page (ATS form filler)
  2. Try simple direct forms
  3. Fallback to manual (open URL for user)
- `POST /api/apply/single` -- apply to one job
- `POST /api/apply/bulk` -- apply to multiple jobs via arq queue
- Orchestrator flow: load profile -> generate resume -> generate cover letter -> detect ATS -> fill form -> screenshot proof -> update status
- SSE endpoint for real-time progress (GET /api/apply/{id}/stream)
- Redis lock + step tracking for idempotent ARQ retries
- Session-per-step DB pattern to prevent pool exhaustion
- Skip ATS re-detection if application.ats_platform already populated
- Resume failure = failed status (cascade stops), CL failure = continue
- Bulk apply continues on individual failures (max 10 per request)
- Sweep cron for stale applying jobs (every 5 min)
- Doc-only Alembic migration for new ApplicationStatus values
- 31 tests (19 orchestrator + 12 route) -- all passing

#### Files Created/Modified:
- `backend/app/models/base.py` -- Added applying, applied_with_issues, manual_required, failed to ApplicationStatus
- `backend/app/config.py` -- Added ATS_APPLY_MAX_BULK, ATS_APPLY_STALE_MINUTES, ATS_RESUME_FILE_FORMAT
- `backend/app/schemas/apply.py` -- Added 8 new schemas (ApplySingle*, ApplyBulk*, ApplyStatus*, ApplyOrchestratorResult, ApplySSEEvent)
- `backend/app/services/apply_orchestrator.py` -- NEW: Full orchestrator with Redis lock, step tracking, session-per-step
- `backend/app/workers/apply_worker.py` -- NEW: ARQ worker with apply_single_job, apply_bulk_job, sweep_stale_apply_jobs
- `backend/app/routes/apply.py` -- Added POST /single, POST /bulk, GET /{id}/status, GET /{id}/stream (SSE), GET /bulk/{task_id}/status
- `docker-compose.yml` -- Added apply-worker service
- `backend/alembic/versions/f2a3b4c5d6e7_add_apply_status_values.py` -- Doc-only migration
- `backend/tests/test_apply_orchestrator.py` -- NEW: 19 tests
- `backend/tests/test_apply_auto_routes.py` -- NEW: 12 tests

### Day 20: Apply Frontend
- Apply modal: progress steps in real-time
- Bulk apply: select jobs, confirm, watch progress
- Queue visualization: "3 jobs in queue, applying to #2..."
- Result summary: X succeeded, Y failed, Z need manual attention
- Manual fallback: opens source URL in new tab for user to apply themselves

---

## Phase 6: Polish + Production (Days 21-23)

### Day 21: Error Handling + Edge Cases
- Every API endpoint has proper error responses
- Rate limiting (100/min general, 10/min auth, 5/min AI generation)
- Input validation on all endpoints (Pydantic v2)
- File upload limits (10MB max for resumes)
- Sentry error tracking with proper context

### Day 22: Testing
- Backend: pytest with 80%+ coverage on AI pipeline and job discovery
- Frontend: vitest component tests for critical flows
- E2E: register -> onboard -> discover -> generate -> apply
- AI pipeline: golden output tests for prompt regressions

### Day 23: Deployment + Documentation
- Deploy frontend to Vercel
- Deploy backend to Railway
- Configure Supabase production instance
- Environment variable documentation
- Runbook for common issues

---

## File Structure

```
jobedin-v3/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── candidate.py
│   │   │   ├── education.py
│   │   │   ├── experience.py
│   │   │   ├── project.py
│   │   │   ├── skill.py
│   │   │   ├── target_role.py
│   │   │   ├── certification.py
│   │   │   ├── language.py
│   │   │   ├── job.py
│   │   │   ├── application.py
│   │   │   ├── resume.py
│   │   │   ├── cover_letter.py
│   │   │   └── interview.py          # InterviewPrep + InterviewSession
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── onboarding.py
│   │   │   ├── profile.py
│   │   │   ├── settings.py           # LinkedIn credentials management
│   │   │   ├── jobs.py
│   │   │   ├── resumes.py
│   │   │   ├── cover_letters.py
│   │   │   ├── interview.py
│   │   │   ├── applications.py
│   │   │   ├── apply.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── ai_pipeline.py
│   │   │   ├── ai_prompts.py
│   │   │   ├── resume_parser.py
│   │   │   ├── job_discovery.py
│   │   │   ├── job_sources/
│   │   │   │   ├── linkedin.py       # Playwright-based
│   │   │   │   ├── adzuna.py
│   │   │   │   ├── jsearch.py
│   │   │   │   ├── remotive.py
│   │   │   │   └── reed.py
│   │   │   ├── match_scorer.py
│   │   │   ├── ats_scorer.py
│   │   │   ├── pdf_generator.py
│   │   │   ├── interview_coach.py    # Interactive coach engine
│   │   │   ├── browser_service.py
│   │   │   ├── credential_crypto.py  # Encrypt/decrypt LinkedIn creds
│   │   │   └── ats_fillers/
│   │   │       ├── greenhouse.py
│   │   │       ├── lever.py
│   │   │       └── workday.py
│   │   ├── workers/                  # arq background workers
│   │   │   ├── ai_worker.py
│   │   │   ├── job_worker.py         # LinkedIn discovery jobs
│   │   │   └── apply_worker.py
│   │   └── schemas/
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx               # Dashboard
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   ├── onboarding/
│   │   │   ├── jobs/
│   │   │   ├── applications/
│   │   │   ├── resumes/
│   │   │   ├── cover-letters/
│   │   │   ├── interview/             # Interactive coach UI
│   │   │   ├── settings/              # LinkedIn credentials page
│   │   │   └── profile/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── layout/
│   │   │   └── features/
│   │   │       ├── JobCard.tsx         # Includes source URL link
│   │   │       ├── ResumePreview.tsx
│   │   │       ├── ApplyModal.tsx
│   │   │       ├── InterviewChat.tsx   # Interactive coach UI
│   │   │       └── InterviewScoreCard.tsx
│   │   ├── lib/
│   │   │   ├── supabase.ts
│   │   │   ├── api.ts
│   │   │   └── utils.ts
│   │   └── hooks/
│   ├── package.json
│   └── next.config.ts
├── docker-compose.yml                  # backend + postgres + redis
├── .env.example
└── README.md
```

---

## Estimated Timeline

| Phase | Days | What Ships |
|-------|------|-----------|
| 1. Foundation | 4 | Auth, DB, onboarding E2E |
| 2. AI Pipeline | 5 | Resume + cover letter + interview coach |
| 3. Job Discovery | 4 | LinkedIn + API sources + matching + frontend |
| 4. Dashboard + Pages | 3 | All core UI pages |
| 5. Auto-Apply | 4 | ATS fillers + cascade + bulk apply |
| 6. Polish + Deploy | 3 | Testing, error handling, production |
| **Total** | **23 days** | |

---

## Monthly Cost

| Service | Cost |
|---------|------|
| Supabase (free tier) | $0 |
| Railway (backend) | $5-10 |
| Vercel (hobby) | $0 |
| Redis (Upstash free) | $0 |
| GLM 5.1 (parsing, analysis, cover letters, interview coach) | ~$3 |
| GPT-4o (resume tailoring only) | ~$5 |
| Sentry (developer tier) | $0 |
| Job APIs (Adzuna, JSearch, Remotive, Reed) | $0 |
| Local Playwright | $0 |
| **Total** | **$8-15/month** |

---

## CEO Review Amendments (Day 5)

The following amendments were applied during a HOLD SCOPE CEO review of Day 5:

1. **Model registry (Approach B):** Replaced hardcoded dual-client with task-to-model routing table inside a single `AIClient` class.
2. **Custom exceptions:** Added `AIPipelineError`, `AIModelTimeoutError`, `AIModelResponseError`, `AIPipelineExhaustedError` hierarchy in `ai_client.py`.
3. **Retry strategy:** Per-call retry with exponential backoff (1s/2s), fallback to alternate model on 5xx, immediate fail on auth errors.
4. **Malformed response handling:** Retry once with correction prompt before raising `AIModelResponseError`.
5. **Prompt hardening:** XML-wrapped user data (`<user_data>`) and anti-injection system instructions in every prompt.
6. **Eager loading:** `selectinload` for all 7 candidate relations to avoid N+1 in `run_full_pipeline`.
7. **Lazy Redis pool:** Function-based `get_redis()` initialization instead of module-level singleton.
8. **Worker DB session:** `AIPipeline` accepts session factory callable, not a session instance.
9. **Stale job sweeper:** Periodic arq cron (every 5min) + `asyncio.wait_for(timeout=120)` for pipeline timeout.
10. **Structured logging + Sentry:** Every step logs `job_id`, `user_id`, `pipeline_step`, `model_used`, `latency_ms`.
11. **Additional unit tests:** Token limit edge cases, schema validation tests. Integration tests deferred to Day 9.
12. **requirements.txt sync:** Explicit instruction to keep `requirements.txt` matching `pyproject.toml`.
13. **GLM compatibility checkpoint:** Validate `response_format` support before implementing structured output methods.
14. **User authorization guard:** `run_full_pipeline` verifies user owns the candidate profile before processing.

---

## Changelog from Original Plan File

Two corrections applied based on discussion decisions:

1. **Queue system**: Changed from BullMQ (Node.js) to **arq** (Python async-native, built for FastAPI). Updated tech stack, Phase 2 Day 5, Phase 5 Day 17, file structure (workers/).

2. **LinkedIn credentials**: Changed from "OS keychain" to **encrypted database storage via Settings page**. Updated Day 10, added `credential_crypto.py` service, added `settings.py` route, added `settings/` frontend page, added `linkedin_password_encrypted` to CandidateProfile model.
