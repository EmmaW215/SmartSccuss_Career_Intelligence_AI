# SmartSuccess Interview Agents — Migration Guide

> **44 fixes across 9 modules, 5 sprints | $0 cost impact | Gemini free tier**
> 
> Generated: 2026-02-16
> Repository: `EmmaW215/SmartSccuss_Career_Intelligence_AI`

---

## 📋 Table of Contents

1. [Pre-Flight Checklist](#1-pre-flight-checklist)
2. [Sprint 1 — Critical/High Priority](#2-sprint-1--criticalhigh-priority)
3. [Sprint 2 — Shared Foundation](#3-sprint-2--shared-foundation)
4. [Sprint 3 — Agent-Specific Fixes](#4-sprint-3--agent-specific-fixes)
5. [Sprint 4 — Customize Enhancements](#5-sprint-4--customize-enhancements)
6. [Sprint 5 — UX & Polish](#6-sprint-5--ux--polish)
7. [Rollback Strategy](#7-rollback-strategy)
8. [File Change Manifest](#8-file-change-manifest)

---

## 1. Pre-Flight Checklist

Before starting integration:

```bash
# 1. Create a feature branch
git checkout -b fix/interview-agents-v2

# 2. Ensure all existing tests pass
cd smartsuccess-interview-backend
python -m pytest tests/ -v  # if tests exist

# 3. Back up current files
cp -r app/ app_backup/

# 4. Verify your .env has required keys
cat .env | grep -E "(GEMINI|GROQ|OPENAI)_API_KEY"
# At minimum you need GEMINI_API_KEY for cost-optimized mode
```

### Environment Requirements

| Variable | Required | Notes |
|----------|----------|-------|
| `GEMINI_API_KEY` | ✅ Yes (cost-optimized) | Free tier: 1500 req/day |
| `GROQ_API_KEY` | Recommended | Free tier: 14400 req/day |
| `OPENAI_API_KEY` | Optional | Paid fallback only |
| `COST_OPTIMIZED_MODE` | Set to `true` | Enables Gemini-first chain |
| `SESSION_DATA_DIR` | Optional | Default: `data/sessions` |

---

## 2. Sprint 1 — Critical/High Priority

**Focus:** Fix the most impactful issues first. Safe to deploy independently.

### Files to Copy

| Source (fix package) | Destination (your repo) | Action |
|---------------------|------------------------|--------|
| `app/utils/__init__.py` | `app/utils/__init__.py` | **NEW** — create `utils/` dir |
| `app/services/session_persistence.py` | `app/services/session_persistence.py` | **NEW** |
| `app/rag/domain_config.py` | `app/rag/domain_config.py` | **NEW** |
| `app/models/__init__.py` | `app/models/__init__.py` | **REPLACE** |

### What Changes & Why

| Fix ID | Issue | Change |
|--------|-------|--------|
| **A-Q4** | Evaluations ignore prior Q&A context | `base_interview.py` adds `_build_evaluation_context()` — injects last 3 Q&A pairs into eval prompt |
| **C-B1** | Behavioral follow-up state on singleton = thread-unsafe | `InterviewSession` model gets `follow_up_count` dict + `follow_ups_used` int |
| **D-T1** | Technical hardcoded to AI/ML only | `domain_config.py` adds 5 domain question banks + keyword-based domain detection |
| **F-A1** | Sessions lost on server restart | `session_persistence.py` provides file-backed store with dict-like interface |
| **E-A2** | GPU STT failure = hard crash | `gpu_client.py` returns `[VOICE_UNAVAILABLE]` guidance instead of raising |

### Integration Steps

```bash
# Step 1: Create new directories
mkdir -p app/utils

# Step 2: Copy NEW files
cp fix_package/app/utils/__init__.py           app/utils/
cp fix_package/app/services/session_persistence.py  app/services/
cp fix_package/app/rag/domain_config.py         app/rag/

# Step 3: REPLACE models (adds new fields to InterviewSession)
cp fix_package/app/models/__init__.py           app/models/__init__.py

# Step 4: Verify import
python -c "from app.models import InterviewSession; s = InterviewSession(session_id='test', user_id='u1', interview_type='screening'); print('follow_up_count' in s.model_fields)"
# Should print: True

# Step 5: Test session persistence
python -c "
from app.services.session_persistence import PersistentSessionStore
store = PersistentSessionStore()
store.save('test_001', {'session_id': 'test_001', 'status': 'ok'})
assert store.get('test_001') is not None
store.delete('test_001')
print('Session persistence OK')
"
```

### ✅ Sprint 1 Validation

- [ ] `app/utils/` directory exists
- [ ] `InterviewSession` has `follow_up_count`, `follow_ups_used`, `detected_domain` fields
- [ ] `PersistentSessionStore` can save/load/delete
- [ ] `domain_config.detect_domain_from_jd()` returns valid domain strings
- [ ] No import errors: `python -c "from app.models import InterviewSession"`

---

## 3. Sprint 2 — Shared Foundation

**Focus:** Centralize LLM calls, add JSON parser, improve prompts. ALL agents benefit.

### Files to Copy

| Source | Destination | Action |
|--------|------------|--------|
| `app/utils/json_parser.py` | `app/utils/json_parser.py` | **NEW** |
| `app/services/llm_service.py` | `app/services/llm_service.py` | **REPLACE** |
| `app/interview/base_interview.py` | `app/interview/base_interview.py` | **REPLACE** |

### What Changes & Why

| Fix ID | Issue | Change |
|--------|-------|--------|
| **A-Q2** | Each agent creates its own OpenAI client | `base_interview.py` adds `_call_llm()` routing through `llm_service.py` fallback chain |
| **A-Q3** | Fragile `split("```")` JSON extraction | `json_parser.py` adds 4-strategy extraction (direct, fenced, balanced brackets, repair) |
| **A-Q1** | Duplicated prompt patterns | System prompts extracted to constants at top of each agent file |
| **A-Q5** | Greeting contains first question = skips evaluation | Greeting methods now take optional `session` param |
| **G-P1/P2/P3** | Prompt engineering gaps | System prompts, JSON-only instructions, calibrated scoring anchors |

### Integration Steps

```bash
# Step 1: Copy new utility
cp fix_package/app/utils/json_parser.py  app/utils/

# Step 2: Replace LLM service (adds provider usage tracking)
cp fix_package/app/services/llm_service.py  app/services/

# Step 3: Replace base interview (CRITICAL — all agents inherit from this)
cp fix_package/app/interview/base_interview.py  app/interview/

# Step 4: Verify centralized LLM import works
python -c "from app.interview.base_interview import BaseInterviewService; print('Base OK')"

# Step 5: Test JSON parser
python -c "
from app.utils.json_parser import extract_json_from_llm
# Test fenced block
assert extract_json_from_llm('\`\`\`json\n{\"score\": 5}\n\`\`\`') == {'score': 5}
# Test raw JSON
assert extract_json_from_llm('{\"score\": 5}') == {'score': 5}
# Test with preamble
assert extract_json_from_llm('Here is the result:\n{\"score\": 5}') == {'score': 5}
print('JSON parser OK')
"
```

### ⚠️ Important Note

After Sprint 2, the old agents will still work BUT they'll be using their own OpenAI clients alongside the new centralized one. Sprint 3 replaces the agents to fully utilize the centralized path.

### ✅ Sprint 2 Validation

- [ ] `json_parser.extract_json_from_llm()` handles all 4 strategies
- [ ] `base_interview.py` has `_call_llm()` and `_build_evaluation_context()`
- [ ] `llm_service.get_usage_stats()` includes `provider_usage` field
- [ ] No import errors from base

---

## 4. Sprint 3 — Agent-Specific Fixes

**Focus:** Replace all 3 agent files with improved versions. This is the biggest change.

### Files to Copy

| Source | Destination | Action |
|--------|------------|--------|
| `app/interview/screening_interview.py` | `app/interview/screening_interview.py` | **REPLACE** |
| `app/interview/behavioral_interview.py` | `app/interview/behavioral_interview.py` | **REPLACE** |
| `app/interview/technical_interview.py` | `app/interview/technical_interview.py` | **REPLACE** |

### What Changes Per Agent

#### Screening Agent
| Fix ID | Change |
|--------|--------|
| **B-S1** | Follow-up decision by LLM (not word count < 20) |
| **B-S2** | Personalized greeting with JD context |
| **B-S3** | Criteria: "confidence" → "specificity", "enthusiasm" → "self_awareness" |

#### Behavioral Agent
| Fix ID | Change |
|--------|--------|
| **C-B1** | Follow-up state on session object (was on singleton) |
| **C-B2** | STAR coaching templates for follow-ups |
| **C-B3** | Competency coverage tracking in summary |

#### Technical Agent
| Fix ID | Change |
|--------|--------|
| **D-T1** | Multi-domain question banks (5 domains) |
| **D-T2** | Dynamic opener based on detected domain |
| **D-T3** | Difficulty progression (basic → intermediate → advanced) |
| **D-T4** | Penalize generic/textbook answers in eval prompt |

### Integration Steps

```bash
# Replace all 3 agent files
cp fix_package/app/interview/screening_interview.py   app/interview/
cp fix_package/app/interview/behavioral_interview.py   app/interview/
cp fix_package/app/interview/technical_interview.py    app/interview/

# Verify imports
python -c "
from app.interview.screening_interview import get_screening_interview_service
from app.interview.behavioral_interview import get_behavioral_interview_service
from app.interview.technical_interview import get_technical_interview_service
print('All agents import OK')
"
```

### ✅ Sprint 3 Validation

- [ ] Screening agent uses `safe_parse_evaluation()` not `json.loads()`
- [ ] Behavioral agent reads follow-up count from `session.follow_up_count`
- [ ] Technical agent calls `detect_domain_from_jd()` in greeting
- [ ] All 3 agents use `self._call_llm()` not direct OpenAI client
- [ ] No `self.llm_client` references remain in agent files

---

## 5. Sprint 4 — Customize Enhancements

**Focus:** Phase 2 stub files for Customize Interview feature.

### Files to Copy

| Source | Destination | Action |
|--------|------------|--------|
| `smartsuccess-phase2/render-backend/app/feedback/customize_feedback.py` | Phase 2 repo | **NEW** |
| `smartsuccess-phase2/render-backend/app/services/gpu_client.py` | Phase 2 repo | **REPLACE** |

### Notes

- `customize_feedback.py` is a **STUB** — returns structured placeholder data
- GPU client E-A2 fix is safe to deploy (graceful degradation only)
- Full Customize Interview backend routing (E-Phase2-A1) requires additional work beyond these files

### ✅ Sprint 4 Validation

- [ ] `customize_feedback.py` importable without errors
- [ ] GPU client `transcribe()` returns tuple instead of raising on failure

---

## 6. Sprint 5 — UX & Polish

**Focus:** Input validation, rate limiting, analytics, remaining polish.

### Files to Copy

| Source | Destination | Action |
|--------|------------|--------|
| `app/utils/input_validator.py` | `app/utils/input_validator.py` | **NEW** |
| `app/utils/rate_limiter.py` | `app/utils/rate_limiter.py` | **NEW** |
| `app/utils/response_analytics.py` | `app/utils/response_analytics.py` | **NEW** |

### What Changes

| Fix ID | Change |
|--------|--------|
| **A-Q7** | Empty/gibberish response validation before LLM call |
| **F-A2** | Thread-safe singletons via `@lru_cache` |
| **F-A3** | Rate limiting: 30 LLM calls/min/user |
| **I-D1** | Score normalization to 0-100 scale |
| **I-D2** | Score distribution metrics (std_dev, trend, consistency) |
| **I-D3** | Anti-gaming heuristics (analytics only, no penalties) |

### ✅ Sprint 5 Validation

- [ ] `validate_response("")` returns `(False, guidance_message)`
- [ ] `validate_response("My experience at Bell...")` returns `(True, None)`
- [ ] Rate limiter allows 30 calls, blocks 31st
- [ ] `compute_score_summary([4,3,5,4])` returns dict with consistency/trend

---

## 7. Rollback Strategy

Each sprint is independently rollbackable:

```bash
# Rollback Sprint 3 (agents only)
git checkout app_backup/app/interview/screening_interview.py
git checkout app_backup/app/interview/behavioral_interview.py
git checkout app_backup/app/interview/technical_interview.py

# Rollback Sprint 2 (base + LLM)
git checkout app_backup/app/interview/base_interview.py
git checkout app_backup/app/services/llm_service.py

# Rollback Sprint 1 (models + new files)
git checkout app_backup/app/models/__init__.py
rm -rf app/utils/
rm app/services/session_persistence.py
rm app/rag/domain_config.py
```

---

## 8. File Change Manifest

### New Files (7)

| File | Sprint | Purpose |
|------|--------|---------|
| `app/utils/__init__.py` | 1 | Package init |
| `app/utils/json_parser.py` | 2 | Robust LLM JSON extraction |
| `app/utils/input_validator.py` | 5 | User response validation |
| `app/utils/rate_limiter.py` | 5 | LLM call rate limiting |
| `app/utils/response_analytics.py` | 5 | Score analytics + anti-gaming |
| `app/services/session_persistence.py` | 1 | File-backed session store |
| `app/rag/domain_config.py` | 1 | Multi-domain config + detection |

### Modified Files (7)

| File | Sprint | Key Changes |
|------|--------|-------------|
| `app/models/__init__.py` | 1 | New session fields, renamed criteria |
| `app/interview/base_interview.py` | 2 | Centralized LLM, context builder, persistence |
| `app/interview/screening_interview.py` | 3 | LLM follow-up, text criteria, centralized eval |
| `app/interview/behavioral_interview.py` | 3 | Session-scoped state, STAR coaching, competency tracking |
| `app/interview/technical_interview.py` | 3 | Multi-domain, difficulty progression, generic-answer penalty |
| `app/services/llm_service.py` | 2 | Usage tracking, enhanced logging |
| `smartsuccess-phase2/.../gpu_client.py` | 4 | Graceful STT fallback |

### New Phase 2 Files (1)

| File | Sprint | Purpose |
|------|--------|---------|
| `smartsuccess-phase2/.../customize_feedback.py` | 4 | Customize interview feedback stub |
