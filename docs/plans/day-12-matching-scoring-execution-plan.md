# Day 12: Matching + Scoring — Execution Plan

**Generated:** 2026-04-28
**Branch:** main
**Status:** APPROVED (CEO Review passed)
**Mode:** SELECTIVE EXPANSION

---

## Overview

Build a weighted fuzzy matching system that scores discovered jobs against the candidate's profile. The scoring runs 4 dimensions: skills match (40%), experience level alignment (25%), role relevance (25%), location compatibility (10%). Scores are cached in a new `job_matches` table so they survive across sessions and can be sorted/filtered efficiently.

Matching is triggered automatically after job discovery completes, and can also be triggered manually via API. Batch scoring runs asynchronously via ARQ worker in chunks of 100.

---

## Architecture

```mermaid
flowchart TD
    subgraph Candidate
        CP[CandidateProfile]
        SK[Skills]
        TR[TargetRoles]
        EL[ExperienceLevel]
        LOC[Location]
    end

    subgraph Scoring
        MS[MatchScorer]
        SKM[skills_match 40%]
        ELA[experience_level 25%]
        RRV[role_relevance 25%]
        LCM[location_compat 10%]
    end

    subgraph Storage
        JM[job_matches table]
    end

    subgraph API
        MATCH[POST /api/jobs/match]
        LIST[GET /api/jobs?sort_by=match_score]
        SCORE[GET /api/jobs/{id}/score]
    end

    subgraph Workers
        DISC[api_discovery_job]
        LINKD[linkedin_discovery_job]
        MW[match_jobs_job]
    end

    CP --> MS
    SK --> MS
    TR --> MS
    EL --> MS
    LOC --> MS
    MS --> SKM
    MS --> ELA
    MS --> RRV
    MS --> LCM
    MS --> JM
    JM --> LIST
    JM --> SCORE
    MATCH --> MW
    DISC -->|auto-enqueue| MW
    LINKD -->|auto-enqueue| MW
    MW --> JM
```

---

## Scoring Algorithm

Each dimension returns 0.0-1.0. Final score = weighted sum (0-100).

| Dimension | Weight | Method |
|-----------|--------|--------|
| Skills match | 40% | Fuzzy match candidate skills against job title + description keywords. Uses `SequenceMatcher` for each skill-to-keyword pair. Best match per skill averaged. Keywords extracted via tokenization + 2-gram phrases. |
| Experience level | 25% | Ordinal distance between candidate level and job level. Same=1.0, 1 step=0.7, 2 steps=0.4, 3+=0.1. Missing either=0.5 (neutral). |
| Role relevance | 25% | Fuzzy match job title against each target role. Best match score used. Keywords from target role also checked against job description. |
| Location | 10% | Exact match=1.0, same city/region=0.8, remote job=0.7 (always compatible), different location=0.3. Missing either=0.5. |

### Experience Level Ordinal Mapping

| Level | Ordinal |
|-------|---------|
| student | 0 |
| fresher | 1 |
| junior | 2 |
| mid | 3 |
| senior | 4 |
| lead | 5 |
| executive | 6 |

### Keyword Extraction Method

`_extract_keywords(text: str) -> list[str]`:
1. Lowercase, split on whitespace and punctuation
2. Remove common English stop words (the, and, or, with, etc.)
3. Generate 2-word phrases (bigrams) from remaining tokens
4. Combine single tokens + bigrams into keyword list
5. This catches multi-word skills like "machine learning", "data analysis", "project management"

---

## Data Flow

### Manual Trigger Flow

1. User triggers `POST /api/jobs/match`
2. Route loads candidate profile (or returns 400 if no profile)
3. Enqueues `match_jobs_job` ARQ task
4. Returns task ID immediately
5. Frontend polls `GET /api/jobs/match/status`

### Auto-Trigger Flow (after discovery)

1. `api_discovery_job` or `linkedin_discovery_job` completes
2. Worker enqueues `match_jobs_job` for the same user
3. Frontend polls discovery status, then match status

### Worker Processing

1. Load candidate profile with `selectinload` for skills, target_roles
2. Query unscored/stale jobs (not in `job_matches` for this user, or `scored_at` > 24h ago)
3. Process in chunks of 100 jobs
4. For each job: compute 4 dimension scores, combine with weights
5. Bulk upsert into `job_matches` table using `on_conflict_do_update`
6. Log batch stats: user_id, jobs_scored, duration_ms, avg_score

---

## CEO Review Amendments

These amendments were accepted during CEO review on 2026-04-28:

1. **Async batch scoring with ARQ worker + partial results** — `POST /api/jobs/match` enqueues ARQ job, returns task ID. Frontend polls. Worker processes in chunks of 100.
2. **Tokenize + 2-gram keyword extraction** — Catches multi-word skills like "machine learning". No external dependencies.
3. **Auto-trigger matching after discovery** — When discovery worker completes, it enqueues `match_jobs_job` for the same user.
4. **Composite index on job_matches** — `(user_id, match_score DESC)` for efficient sorting.
5. **Keep frontend in Day 12** — No scope split. Ships visible user value.
6. **`GET /api/jobs/{id}/score` computes inline if no cache** — Returns computed score rather than 404.
7. **Sort by score uses `DESC NULLS LAST`** — Unscored jobs appear at the bottom.
8. **Profile-not-found guard** — Returns 400 if user has no candidate profile.
9. **sort_by whitelist** — Only `match_score`, `created_at`, `salary_max` allowed. Never interpolate raw input.
10. **Test count ~26** — Full coverage of all dimension scorers, pipeline, caching, edge cases, routes, worker.

---

## Files to Create

### 1. `backend/app/models/job_match.py` — Score cache model

```python
class JobMatch(TimestampModel, table=True):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", "uq_job_matches_user_job"),
        Index("ix_job_matches_user_score", "user_id", "match_score"),
    )

    user_id: UUID = Field(index=True)
    job_id: UUID = Field(foreign_key="jobs.id", ondelete="CASCADE")
    match_score: float          # 0.0-100.0
    skills_score: float         # 0.0-1.0
    experience_score: float     # 0.0-1.0
    role_relevance_score: float # 0.0-1.0
    location_score: float       # 0.0-1.0
    matched_skills: list | None = Field(default=None, sa_column=Column(JSON))
    missing_skills: list | None = Field(default=None, sa_column=Column(JSON))
    scored_at: datetime         # set explicitly by scorer
```

### 2. `backend/app/services/match_scorer.py` — Core scoring engine

```python
class MatchScorer:
    def __init__(self, session: AsyncSession): ...

    # Public API
    async def score_job(self, user_id: UUID, job_id: UUID) -> JobMatchResult: ...
    async def score_jobs_batch(self, user_id: UUID, job_ids: list[UUID] | None = None, chunk_size: int = 100) -> list[JobMatchResult]: ...
    async def get_cached_score(self, user_id: UUID, job_id: UUID) -> JobMatchResult | None: ...

    # Dimension scorers (pure functions, no DB access)
    def _compute_skills_score(self, skills: list[Skill], job: Job) -> tuple[float, list[str], list[str]]: ...
    def _compute_experience_score(self, candidate_level: ExperienceLevel | None, job_level: ExperienceLevel | None) -> float: ...
    def _compute_role_relevance(self, target_roles: list[TargetRole], job: Job) -> float: ...
    def _compute_location_score(self, candidate_location: str | None, job: Job) -> float: ...

    # Keyword extraction
    @staticmethod
    def _extract_keywords(text: str) -> list[str]: ...
```

- Reuses `SequenceMatcher` from `job_dedup.py` pattern
- `_normalize_text` imported from `job_dedup`
- `_extract_keywords` does tokenization + 2-gram generation + stop word removal
- `_compute_skills_score` returns (score, matched_skills, missing_skills)
- Skills score: extract keywords from job title + description, fuzzy match against each candidate skill, average the best matches
- Batch scoring: fetch all unscored jobs, process in chunks of `chunk_size`, bulk upsert per chunk
- Score caching: check `job_matches` table first, recompute if >24h old
- Structured logging: every batch logs `user_id`, `jobs_scored`, `duration_ms`, `avg_score`

### 3. `backend/alembic/versions/c3d4e5f6a7b8_add_job_matches_table.py`

Migration for the `job_matches` table with composite index `(user_id, match_score)`.

### 4. `backend/app/schemas/match.py` — Match schemas

```python
class MatchBreakdown(BaseModel):
    skills_score: float
    experience_score: float
    role_relevance_score: float
    location_score: float

class JobMatchResult(BaseModel):
    job_id: UUID
    match_score: float
    breakdown: MatchBreakdown
    matched_skills: list[str]
    missing_skills: list[str]

class MatchRequest(BaseModel):
    job_ids: list[UUID] | None = None  # None = score all unscored

class MatchResponse(BaseModel):
    task_id: str        # ARQ job ID for polling
    message: str

class MatchStatusResponse(BaseModel):
    status: str         # pending / in_progress / completed / failed
    scored_count: int
    total_count: int
    results: list[JobMatchResult] | None = None  # populated when completed
```

### 5. `backend/tests/test_match_scorer.py` — ~26 tests

| Category | Tests |
|----------|-------|
| Keyword extraction | 3 (normal text, empty, multi-word skills) |
| Skills score | 3 (normal match, empty skills, multi-word matching) |
| Experience score | 4 (same level, 1-step, 2-step, missing levels) |
| Role relevance | 2 (match found, no target roles) |
| Location score | 3 (exact, remote job, missing) |
| Weighted combination | 1 (all dimensions together) |
| score_job | 2 (happy path, profile not found) |
| score_jobs_batch | 2 (batch of 5, batch of 0) |
| get_cached_score | 2 (cache hit, stale rescore) |
| POST /api/jobs/match route | 3 (success, no profile, not authenticated) |
| GET /api/jobs/{id}/score | 2 (cached, compute inline) |
| GET /api/jobs with scores | 2 (with score, sort by score) |
| match_jobs_job worker | 1 (happy path) |
| **Total** | **~30** |

### 6. `frontend/src/types/job.ts` — TypeScript types

Interfaces for `JobListItem`, `JobDetail`, `JobMatchScore`, `MatchBreakdown`, `SavedJob`, `MatchStatus`.

### 7. `frontend/src/app/jobs/page.tsx` — Jobs listing page

- Filter bar: source, experience level, job type, remote policy
- Sort by: match score (default), date, salary (whitelisted values)
- Job cards with match score badge
- "Discover Jobs" button triggering discovery flow
- Discovery + match status polling
- Empty state: "No jobs found. Discover jobs to get started."
- Loading: skeleton cards

### 8. `frontend/src/app/jobs/[id]/page.tsx` — Job detail page

- Full job description
- Match score circular gauge (reuse `InterviewScoreCard` SVG pattern)
- Breakdown bars per dimension
- Matched/missing skills pills (reuse `ResumeDetail` keyword pattern)
- "Generate Resume" / "Generate Cover Letter" / "Save" action buttons
- If no cached score: compute inline and show

### 9. `frontend/src/components/features/JobCard.tsx` — Job list card

- Title, company, location, source badge
- Match score ring (color-coded: 80+ green, 60-79 yellow, <60 red)
- Salary range if available
- Remote/hybrid/onsite badge
- "Not scored" badge if no match_score

### 10. `frontend/src/components/features/JobMatchScore.tsx` — Score visualization

- SVG donut chart (copy pattern from `InterviewScoreCard`)
- Dimension breakdown bars (4 horizontal bars)
- Skills matched/missing pills

---

## Files to Modify

### 11. `backend/app/models/__init__.py`
- Add `JobMatch` import

### 12. `backend/app/routes/jobs.py`
- Add `POST /api/jobs/match` — enqueue ARQ job, return task ID
- Add `GET /api/jobs/match/status` — poll match job status
- Add `GET /api/jobs/{job_id}/score` — get cached score, or compute inline if no cache
- Update `GET /api/jobs` list — LEFT JOIN `job_matches`, include `match_score`, support `sort_by` with whitelist (`match_score`, `created_at`, `salary_max`). Sort uses `DESC NULLS LAST` for match_score.

### 13. `backend/app/schemas/jobs.py`
- Add `match_score: float | None` to `JobListItem`
- Add `match_score: float | None` + `match_breakdown: MatchBreakdown | None` to `JobDetailResponse`

### 14. `backend/app/workers/job_worker.py`
- Add `match_jobs_job` ARQ worker function (processes in chunks of 100)
- Update `api_discovery_job` — after completion, enqueue `match_jobs_job` for same user
- Update `linkedin_discovery_job` — after completion, enqueue `match_jobs_job` for same user
- Register `match_jobs_job` in `JobWorkerSettings.functions`

### 15. `backend/app/config.py`
- Add `MATCH_SCORE_STALENESS_HOURS: int = 24`
- Add `MATCH_SCORE_CHUNK_SIZE: int = 100`

### 16. `frontend/src/components/layout/AppLayout.tsx`
- Add `{ href: "/jobs", label: "Jobs" }` to `navLinks`

### 17. `frontend/src/app/dashboard/page.tsx`
- Replace "Coming soon" Jobs card with real `<Link href="/jobs">` card
- Remove `opacity-60`

---

## Execution Order

| Step | What | Depends On | Tests |
|------|------|------------|-------|
| 1 | Create `JobMatch` model + migration with composite index | -- | -- |
| 2 | Create `match_scorer.py` with keyword extraction + 4 dimensions | Step 1 | Unit: keyword extraction, dimension scorers |
| 3 | Create `schemas/match.py` (MatchBreakdown, JobMatchResult, etc.) | -- | Schema validation |
| 4 | Add `POST /api/jobs/match` + `GET /api/jobs/match/status` + `GET /api/jobs/{id}/score` | Steps 2, 3 | Route tests |
| 5 | Update `GET /api/jobs` list with score join + sort_by whitelist | Step 4 | Route tests |
| 6 | Add `match_jobs_job` worker + auto-trigger after discovery | Step 2 | Worker test |
| 7 | Update `JobListItem` / `JobDetailResponse` with score fields | Step 4 | -- |
| 8 | Full test suite — ~30 tests | Steps 1-7 | Integration tests |
| 9 | Frontend: `types/job.ts` + API client | Step 7 | -- |
| 10 | Frontend: `JobCard` + `JobMatchScore` components | Step 9 | -- |
| 11 | Frontend: Jobs list page + detail page | Step 10 | -- |
| 12 | Frontend: Nav + dashboard activation | Step 11 | -- |
| 13 | Update `plan.md` Day 11 as DONE + Day 12 completion notes | Step 12 | -- |

---

## Error & Rescue Map

| METHOD/CODEPATH | WHAT CAN GO WRONG | EXCEPTION | RESCUE | USER SEES |
|---|---|---|---|---|
| `POST /api/jobs/match` | No profile | HTTPException 400 | Check profile exists before enqueuing | "Complete onboarding first" |
| `POST /api/jobs/match` | Not authenticated | HTTPException 401 | Auth dependency | "Not authenticated" |
| `score_jobs_batch` | DB connection fails | OperationalError | Raise, worker retries via ARQ | Task status = "failed" |
| `score_jobs_batch` | 0 unscored jobs | No exception | Return empty list | "0 jobs scored" |
| `GET /api/jobs/{id}/score` | No cached score | None | Compute inline for single job | Score appears normally |
| `GET /api/jobs/{id}/score` | Job not found | HTTPException 404 | Standard lookup | "Job not found" |
| `GET /api/jobs?sort_by=` | Invalid sort value | HTTPException 422 | Whitelist validation | "Invalid sort field" |
| `match_jobs_job` | Redis down | ConnectionError | ARQ retry with backoff | Task status = "failed" |
| `match_jobs_job` | Partial chunk failure | OperationalError | Continue to next chunk, log failed | Partial results returned |

---

## Security Notes

- `sort_by` parameter is whitelisted: only `match_score`, `created_at`, `salary_max` allowed. Never interpolated into SQL.
- `POST /api/jobs/match` requires authentication. `user_id` comes from JWT, not request body.
- `GET /api/jobs/{id}/score` scoped to authenticated user. Users can only see their own scores.
- No PII in `job_matches` table. Only scores and skill name lists.
- Consider rate limiting `POST /api/jobs/match` (deferred to Day 21).

---

## Observability

- Every batch scoring logs: `user_id`, `jobs_scored`, `duration_ms`, `avg_score`
- Individual job scoring failures logged with `job_id`, `error`
- Cache hit/miss ratio logged for inline scoring
- Follows existing structured logging pattern from AI pipeline

---

## NOT in Scope (explicitly deferred)

- AI-powered semantic matching (pgvector embeddings) — future enhancement
- Real-time score updates via SSE/WebSocket
- Salary matching dimension — salary data is sparse in current sources
- Natural language score explanations ("This job matches you because...")
- Job recommendation engine ("Similar jobs you might like")
- Email notifications for high-match jobs
- Per-user weight customization
- Multi-user scoring on discovery (score for all users, not just triggering user)
- Rate limiting on match endpoint — deferred to Day 21
- Bulk apply from matched list — deferred to Days 17-20

---

## What Already Exists (reused)

| Pattern | Source File | What's Reused |
|---------|-----------|---------------|
| Fuzzy matching | `job_dedup.py` | `SequenceMatcher`, `_normalize_text()` |
| Eager loading | `ai_pipeline.py` | `selectinload` for candidate relations |
| ARQ worker pattern | `job_worker.py` | `async_session_factory()`, function registration |
| SVG donut chart | `InterviewScoreCard.tsx` | Score ring visualization |
| Keyword pills | `ResumeDetail.tsx` | Matched/missing skills display |
| Card layout | `ResumeCard.tsx` | Job card layout template |
| Bulk upsert | `job_discovery.py` | `on_conflict_do_update` pattern |
| Async polling | Resume/Cover Letter | Task ID + status polling pattern |

---

## Acceptance Criteria

1. `POST /api/jobs/match` enqueues async scoring job, returns task ID
2. `GET /api/jobs/match/status` returns progress (pending/in_progress/completed/failed)
3. `GET /api/jobs` returns `match_score` per job when authenticated, sortable by score
4. `GET /api/jobs/{id}/score` returns full breakdown; computes inline if not cached
5. Scores cached in `job_match` table, auto-refreshed after 24h
6. Matching auto-triggers after discovery completes
7. Scoring handles edge cases: no skills (0.0), no target roles (0.0), missing levels (0.5), missing location (0.5)
8. sort_by parameter whitelisted, no SQL injection
9. Profile-not-found returns 400, not 500
10. ~30 new backend tests, all existing tests still pass
11. Frontend `/jobs` page renders job list with match scores and filters
12. Frontend `/jobs/[id]` page shows full match breakdown with visualization
13. "Jobs" appears in navigation, dashboard card links to `/jobs`
14. Unscored jobs sort last (NULLS LAST) when sorting by match_score
