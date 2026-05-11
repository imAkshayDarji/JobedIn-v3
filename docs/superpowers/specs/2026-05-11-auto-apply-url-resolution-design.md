# Auto-Apply URL Resolution & Generic Form Detection

**Date:** 2026-05-11
**Status:** Approved
**Approach:** Source URL navigation + web search fallback (Approach A)

## Problem

Jobs imported from jsearch, adzuna, reed, and remotive have a `source_url` pointing to the job listing, but many lack an `apply_url` pointing to the actual application form. The current auto-apply pipeline requires `apply_url` and rejects jobs without one. Additionally, only 3 ATS platforms (Greenhouse, Lever, Workday) have form fillers, so jobs on other platforms cannot be auto-applied to.

## Solution Overview

Add a 3-tier URL resolution pipeline that finds the apply page from `source_url` or web search, plus a generic form detection system that can partially fill forms on unknown career pages, handing off to manual completion when needed.

## Architecture

### URL Resolution Pipeline

Priority order for finding the apply page URL:

1. **`apply_url`** (direct) - Use if already stored on the Job
2. **`source_url` navigation** - Navigate to the job listing via Playwright, find and follow the apply button/link
3. **Web search** - Search `{company} {title} careers apply` via Playwright, navigate to results, find apply link

### Form Filling Strategy

After reaching an apply page:

1. **Known ATS** (Greenhouse, Lever, Workday) - Use existing platform-specific fillers
2. **Unknown platform** - Use generic form detection:
   - Detect `<form>` elements, map fields by labels/placeholders
   - Fill name, email, phone, resume upload, address
   - Set status to `manual_required` with instructions for remaining fields

### Status Flow

```
saved -> generating -> ready -> applying -> applied
                                       -> applied_with_issues
                                       -> manual_required (with instructions)
                                       -> failed
```

No new statuses needed. The `generating` status already covers the URL resolution + ATS detection phase. `manual_required` already exists in the enum.

## Components

### 1. URL Resolver Service (`backend/app/services/url_resolver.py`)

```python
class URLResolver:
    async def resolve(job: Job) -> URLResolution:
        """3-tier URL resolution pipeline."""

    async def _try_source_url(source_url: str) -> str | None:
        """Navigate to source_url, find apply button/link."""

    async def _try_web_search(company: str, title: str) -> str | None:
        """Search for career page, find apply link."""

    async def _find_apply_link_on_page(page) -> str | None:
        """CSS selector matching for apply buttons/links."""

@dataclass
class URLResolution:
    apply_url: str | None
    method: str  # "direct" | "source_navigation" | "web_search" | "failed"
    error: str | None = None
```

**Source URL navigation strategy:**
- Navigate to `source_url` via Playwright (using existing `BrowserService`)
- Wait for page load
- Search for apply-related elements using CSS selectors:
  - `a` tags with text matching `/apply/i`, `/submit/i`
  - `a` tags with `href` containing `/apply`, `/application`
  - Buttons with apply-related text
  - Links matching known ATS URL patterns
- If found, return the `href`
- If page requires login (LinkedIn), skip to web search

**Web search strategy:**
- Use Playwright to navigate to Google
- Search: `"{company}" "{title}" apply careers`
- Parse top 5 organic results for career page URLs
- Navigate to each result (max 3 attempts), looking for:
  - Job listing matching our title
  - Apply button/link on the page
- 30-second total timeout

### 2. Generic Form Detector (`backend/app/services/generic_form_detector.py`)

```python
class GenericFormDetector:
    def detect_fields(page) -> list[FormFieldInfo]:
        """Scan page for form fields, return structured info."""

    def fill_fields(page, profile, fields, resume_path) -> FillResult:
        """Fill detected fields with profile data."""

    def get_unfilled_required(fields, filled) -> list[str]:
        """Return list of required fields that weren't filled."""

@dataclass
class FormFieldInfo:
    selector: str
    field_type: str  # "text" | "email" | "tel" | "file" | "textarea" | "select"
    label: str | None
    placeholder: str | None
    required: bool
    mapped_to: str | None  # "first_name", "email", "resume_upload", etc.

@dataclass
class FillResult:
    filled_fields: list[str]
    unfilled_required: list[str]
    screenshot_path: str | None
```

**Field detection logic:**
- Find all `<form>` elements
- For each `<input>`, `<textarea>`, `<select>`:
  - Check `type`, `name`, `id` attributes
  - Check associated `<label>` text
  - Check `placeholder` attribute
  - Check `aria-label` attribute
  - Check `required` attribute
- Map to profile fields using keyword matching:
  - Name: first_name, last_name, full_name
  - Contact: email, phone
  - File: resume, cv, cover_letter
  - URLs: linkedin, github, portfolio
  - Address: city, state, country, zipcode

**Fill strategy:**
- Use existing `BaseATSFiller` helper methods (`fill_text_field`, `upload_file`, etc.)
- Character-by-character typing with random delays (anti-detection)
- Upload resume to file inputs
- Skip fields that can't be mapped to profile data

### 3. Modified ATS Detector (`backend/app/services/ats_detector.py`)

Add "generic" platform type for unknown career pages:
- When URL doesn't match any known ATS pattern
- When DOM doesn't contain any known ATS selectors
- Set `ats_platform = "generic"`, `ats_difficulty = "manual_assist"`

### 4. Modified Apply Orchestrator (`backend/app/services/apply_orchestrator.py`)

Update `_attempt_ats_apply`:
- After ATS detection, if platform is "generic":
  - Run `GenericFormDetector.detect_fields`
  - Run `GenericFormDetector.fill_fields`
  - If unfilled required fields remain:
    - Set status to `manual_required`
    - Store instructions in `application.notes`
    - Store career page URL for manual continuation
  - If all required fields filled:
    - Attempt submission
    - Set status to `applied` or `applied_with_issues`

### 5. Modified Apply Endpoint (`backend/app/routes/apply.py`)

Update `apply_single`:
- When `application.status == saved`:
  - First try `job.apply_url`
  - If None, call `URLResolver.resolve(job)`
  - If resolution succeeds, store resolved URL as `ats_form_url` and proceed with ATS detection
  - If resolution fails, set status to `manual_required` with error message
- Remove the "Job has no apply URL" hard rejection

### 6. Frontend Updates

**ApplyModal:**
- Show `manual_required` status with clear instructions
- Display list of unfilled fields
- "Open Career Page" button to continue manually
- Show screenshot of partial fill state

**Applications page:**
- New filter/status badge for `manual_required`
- Expandable instructions section per application

## Error Handling

| Scenario | Resolution |
|----------|------------|
| `source_url` is dead/404 | Fall back to web search |
| `source_url` requires login (LinkedIn) | Fall back to web search |
| Web search finds no results | Set `manual_required` with instructions |
| Generic form has no fillable fields | Set `manual_required` with career page URL |
| Generic form partially filled | Set `manual_required` with list of remaining fields |
| Playwright timeout (30s) | Move to next resolution tier or `manual_required` |

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/services/url_resolver.py` | Create | URL resolution pipeline |
| `backend/app/services/generic_form_detector.py` | Create | Generic form field detection and filling |
| `backend/app/routes/apply.py` | Modify | Use URL resolver instead of rejecting no-URL jobs |
| `backend/app/services/ats_detector.py` | Modify | Add "generic" platform type |
| `backend/app/services/apply_orchestrator.py` | Modify | Handle generic platform in apply flow |
| `backend/app/workers/job_worker.py` | Modify | Use URL resolver in ats_detect_job |
| `backend/app/models/base.py` | No change | No new statuses needed |
| `backend/app/services/job_discovery.py` | Modify | Fix: store `apply_url` from `source_url` during ingestion |
| `frontend/src/components/features/ApplyModal.tsx` | Modify | Handle `manual_required` status |
| `frontend/src/app/applications/page.tsx` | Modify | Show manual_required instructions |

## Scope

**In scope:**
- URL resolution pipeline (source_url navigation + web search)
- Generic form detection and partial fill
- Manual handoff with instructions
- Frontend display of manual_required state
- Fix ingestion bug (apply_url not stored from source_url)

**Out of scope:**
- Adding more platform-specific ATS fillers (Taleo, iCIMS, etc.)
- Re-processing existing jobs to populate apply_url
- LinkedIn authenticated apply (requires stored credentials + session management)
- Bulk apply changes (works automatically with single apply improvements)
- CAPTCHA solving
