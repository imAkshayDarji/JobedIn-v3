# JobedIn V3 -- Final Merged Plan

## Progress Tracker

| Day | Phase | Description | Status | Commit |
|-----|-------|-------------|--------|--------|
| Day 1 | Foundation | Project Scaffolding + Docker Compose | DONE | `33bf30b` |
| Day 2 | Foundation | Database Models + Alembic Migrations | DONE | `528ccae` |
| Day 3 | Foundation | Auth + Middleware | TODO | -- |
| Day 4 | Foundation | Onboarding API + Frontend Wizard | TODO | -- |
| Day 5 | AI Pipeline | AI Client Setup + Prompt Engineering | TODO | -- |
| Day 6 | AI Pipeline | Resume Generation Pipeline | TODO | -- |
| Day 7 | AI Pipeline | Cover Letter Generation | TODO | -- |
| Day 8 | AI Pipeline | Interactive Interview Coach | TODO | -- |
| Day 9 | AI Pipeline | AI Pipeline Testing + Polish | TODO | -- |
| Day 10 | Job Discovery | LinkedIn Playwright Discovery | TODO | -- |
| Day 11 | Job Discovery | API Sources + Merge/Deduplication | TODO | -- |
| Day 12 | Job Discovery | Matching + Scoring | TODO | -- |
| Day 13 | Job Discovery | Job Discovery Frontend | TODO | -- |
| Day 14 | Dashboard | Dashboard | TODO | -- |
| Day 15 | Dashboard | Profile Page | TODO | -- |
| Day 16 | Dashboard | Applications Tracker | TODO | -- |
| Day 17 | Auto-Apply | Playwright Setup + ATS Detection | TODO | -- |
| Day 18 | Auto-Apply | ATS Form Fillers | TODO | -- |
| Day 19 | Auto-Apply | Auto-Apply Orchestrator | TODO | -- |
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
- Two AI clients: GLM 5.1 (OpenAI-compatible API) and GPT-4o (OpenAI API)
- `AIPipeline` service with structured Pydantic outputs
- Redis + arq queue for AI generation tasks
- Resume tailoring prompt -- 4-step pipeline:

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

### Day 6: Resume Generation Pipeline
- `POST /api/resumes/generate` -- job_id + user_id, runs 4-step pipeline
- `POST /api/resumes/generate-manual` -- raw job description text
- `GET /api/resumes/{id}` + `GET /api/resumes` -- retrieve/list
- SSE streaming for progress events
- arq background worker for long-running generation

### Day 7: Cover Letter Generation
- Structured prompt with tone selection (professional/casual/enthusiastic)
- Company-specific research integration
- References specific job requirements
- `POST /api/cover-letters/generate`
- All structured JSON outputs

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

### Day 11: API Sources + Merge/Deduplication
- JSearch API (covers Indeed + multiple boards)
- Adzuna API
- Remotive API
- Reed API (UK-specific)
- All fire in parallel with `asyncio.gather(return_exceptions=True)`
- Merge all sources + LinkedIn results
- Deduplication by fuzzy matching on `(title, company, location)`
- Every job stores `source_url` + `source` enum

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

---

## Phase 4: Dashboard + Core Pages (Days 14-16)

### Day 14: Dashboard
- Overview cards: applications sent, interviews scheduled, response rate
- Recent activity feed (real-time via Supabase Realtime)
- Quick actions: Discover Jobs, Generate Resume, Start Interview Coach
- Empty states with CTAs for new users

### Day 15: Profile Page
- Editable sections with inline CRUD
- Sections: Personal Info, Target Roles, Skills, Education, Experience, Projects, Certifications, Languages
- Each section loads independently
- Resume upload button that re-parses and suggests updates
- Settings page for LinkedIn credentials (encrypted storage)

### Day 16: Applications Tracker
- Pipeline view: Saved -> Generating -> Ready -> Applied -> Screening -> Interview -> Offer -> Rejected
- Drag-and-drop status updates
- Filter by status, date, company
- Quick actions: view resume, view cover letter, start interview prep
- Application detail modal with full timeline

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
- WebSocket for real-time apply progress

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

## Changelog from Original Plan File

Two corrections applied based on discussion decisions:

1. **Queue system**: Changed from BullMQ (Node.js) to **arq** (Python async-native, built for FastAPI). Updated tech stack, Phase 2 Day 5, Phase 5 Day 17, file structure (workers/).

2. **LinkedIn credentials**: Changed from "OS keychain" to **encrypted database storage via Settings page**. Updated Day 10, added `credential_crypto.py` service, added `settings.py` route, added `settings/` frontend page, added `linkedin_password_encrypted` to CandidateProfile model.
