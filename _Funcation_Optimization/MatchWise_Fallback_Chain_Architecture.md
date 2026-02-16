# MatchWise AI — Fallback Chain Architecture Analysis & Recommendation

## Current Architecture

```
Layer 1: Groq (llama-3.3-70b-versatile)     — FREE, capable
Layer 2: Gemini (2.5-flash)                  — FREE, capable
Layer 3: OpenRouter FREE models              — FREE, UNRELIABLE
         ├── openrouter/free (auto-select)
         ├── arcee-ai/trinity-large-preview:free
         ├── stepfun/step-3.5-flash:free
         ├── z-ai/glm-4.5-air:free
         └── meta-llama/llama-3.2-3b:free    ← 3B params, very weak
```

## The Real Question: How Often Does Layer 3 Actually Get Hit?

Before deciding what to do with Layer 3, we need to understand the failure scenarios:

```
Layer 1 (Groq) fails when:
  - Rate limit: 30 RPM / 15,000 TPM on free tier
  - Service outage (rare, ~99.5% uptime)
  - Model overloaded (peak hours)

Layer 2 (Gemini) fails when:
  - Rate limit: 15 RPM on free tier (lower than Groq!)
  - API key quota exhausted (daily limit)
  - Service outage

Layer 3 gets hit when:
  - BOTH Groq AND Gemini fail simultaneously
  - Typical scenario: burst traffic during a demo/presentation
  - Estimated frequency: <5% of total calls in normal use
```

**Key insight**: Layer 3 is your "emergency parachute" — it fires rarely but when it does,
the user is already having a degraded experience. Having a RELIABLE Layer 3 is critical
because it's the last line of defense.

---

## Option Analysis

### Option A: Replace OpenRouter with OpenAI GPT-4o-mini (RECOMMENDED)

```
Layer 1: Groq (llama-3.3-70b)     — FREE
Layer 2: Gemini (2.5-flash)       — FREE  
Layer 3: OpenAI (gpt-4o-mini)     — PAID but cheap, RELIABLE
```

**Cost Analysis for Layer 3 (GPT-4o-mini)**:

| Metric | Value |
|--------|-------|
| Input price | $0.15 / 1M tokens |
| Output price | $0.60 / 1M tokens |
| Avg input per analysis (6 prompts) | ~8,000 tokens |
| Avg output per analysis (6 prompts) | ~6,000 tokens |
| Cost per analysis | ~$0.005 (~0.5 cents) |
| If Layer 3 handles 5% of traffic | |
| → 100 analyses/month × 5% = 5 analyses | ~$0.025/month |
| → 500 analyses/month × 5% = 25 analyses | ~$0.125/month |
| → 1000 analyses/month × 5% = 50 analyses | ~$0.25/month |

**Verdict**: Even in worst case (1000 analyses/month, Layer 3 handles 5%), cost is ~$0.25/month.
This is negligible and completely justifiable for production quality.

**Advantages**:
- GPT-4o-mini has native JSON mode (`response_format: {"type": "json_object"}`)
- Extremely reliable structured output
- Function calling support for even more structured responses
- 128K context window — no truncation risk
- Near-100% uptime SLA

**Code change**:
```python
async def call_openai_api(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.",
    max_tokens: int = 2000,
    json_mode: bool = False
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY not set")

    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2
        }
        if json_mode:
            data["response_format"] = {"type": "json_object"}

        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers, json=data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"OpenAI API error: {response.status} - {error_text}")
            result = await response.json()
            return result["choices"][0]["message"]["content"]
```

---

### Option B: Keep OpenRouter but Curate Better Free Models

```
Layer 1: Groq (llama-3.3-70b)     — FREE
Layer 2: Gemini (2.5-flash)       — FREE  
Layer 3: OpenRouter (curated)     — FREE but inconsistent
```

Replace the current model list with more capable free options:

```python
# CURRENT (problematic):
OPENROUTER_FREE_MODELS = [
    "openrouter/free",                        # Auto-select — unpredictable
    "arcee-ai/trinity-large-preview:free",    # May go offline anytime
    "stepfun/step-3.5-flash:free",            # Limited availability
    "z-ai/glm-4.5-air:free",                 # Weak on English structured output
    "meta-llama/llama-3.2-3b-instruct:free",  # 3B params — TOO SMALL
]

# IMPROVED (if staying free):
OPENROUTER_FREE_MODELS = [
    "google/gemma-3-27b-it:free",             # 27B, strong instruction following
    "mistralai/mistral-small-3.1-24b-instruct:free",  # 24B, good at structured
    "qwen/qwen3-32b:free",                    # 32B, strong reasoning
]
```

**Problems with this approach**:
- Free model availability on OpenRouter changes WITHOUT notice
- Models rotate in/out of free tier weekly
- No SLA, no uptime guarantee
- You'd need to maintain the list manually
- Still no JSON mode guarantee

**Verdict**: Fragile. Not recommended for production.

---

### Option C: Architectural Fix ONLY (No Model Change)

The argument: "If prompts are properly decomposed, even weak models can handle them."

This is PARTIALLY true. If you:
1. Ask for JSON instead of HTML tables
2. Keep each prompt to a single task
3. Use server-side rendering for structured output

Then yes, even a 3B model can return passable JSON for simple tasks.

**But**: For cover letters, resume summaries, and nuanced skill matching, model quality 
DIRECTLY impacts output quality. A 3B model will still produce:
- Repetitive phrasing
- Generic, non-specific content
- Poor reasoning about skill transferability
- Grammatical awkwardness

**Verdict**: Necessary but NOT sufficient. You need BOTH better architecture AND reliable models.

---

### Option D: HYBRID — Best of All Worlds (STRONGLY RECOMMENDED)

```
                    ┌─────────────────────────────────────────┐
                    │        RECOMMENDED ARCHITECTURE          │
                    └─────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────┐
    │  Layer 1: Groq (llama-3.3-70b)              FREE            │
    │  ├── Primary provider                                       │
    │  ├── 30 RPM free tier                                       │
    │  ├── JSON mode supported ✅                                  │
    │  └── Fastest inference (~1-3s)                               │
    ├──────────────────────────────────────────────────────────────┤
    │  Layer 2: Gemini (2.5-flash)                FREE            │
    │  ├── Secondary provider                                     │
    │  ├── 15 RPM free tier                                       │
    │  ├── Structured output via prompt ⚠️                         │
    │  └── Good quality, moderate speed (~3-5s)                   │
    ├──────────────────────────────────────────────────────────────┤
    │  Layer 3: OpenAI (gpt-4o-mini)              ~$0.005/call    │
    │  ├── Emergency fallback                                     │
    │  ├── JSON mode native ✅                                     │
    │  ├── Function calling ✅                                     │
    │  ├── Near-100% uptime                                       │
    │  └── Only fires when BOTH free tiers fail (~5% of traffic)  │
    ├──────────────────────────────────────────────────────────────┤
    │  Layer 4: GRACEFUL DEGRADATION              FREE/ZERO       │
    │  ├── If ALL 3 providers fail                                │
    │  ├── Return partial results (whatever succeeded)            │
    │  ├── Show user-friendly error for failed sections           │
    │  └── Log incident for monitoring                            │
    └──────────────────────────────────────────────────────────────┘

    Monthly Cost Estimate:
    ┌────────────────────┬──────────┬───────────┬────────────────┐
    │ Monthly Analyses    │ Layer 3  │ Cost      │ vs Current     │
    │                    │ Hit Rate │           │                │
    ├────────────────────┼──────────┼───────────┼────────────────┤
    │ 100 (light)        │ 5%       │ $0.025    │ $0 → $0.03    │
    │ 500 (moderate)     │ 5%       │ $0.125    │ $0 → $0.13    │
    │ 1000 (heavy)       │ 5%       │ $0.25     │ $0 → $0.25    │
    │ 1000 (worst case)  │ 20%      │ $1.00     │ $0 → $1.00    │
    └────────────────────┴──────────┴───────────┴────────────────┘
```

---

## Implementation: Enhanced `call_ai_api()` with Provider Tracking

```python
async def call_ai_api(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant specializing in job application analysis.",
    max_tokens: int = 2000,
    json_mode: bool = False,
    call_label: str = "unknown"
) -> tuple[str, str]:
    """
    Zero-Cost Triple Fallback: Groq → Gemini → OpenAI (gpt-4o-mini)
    
    Returns: (response_text, provider_used)
    """
    import time
    
    providers = [
        ("groq",    lambda: call_groq_api(prompt, system_prompt, max_tokens, json_mode)),
        ("gemini",  lambda: call_gemini_api(prompt, system_prompt, max_tokens)),
        ("openai",  lambda: call_openai_api(prompt, system_prompt, max_tokens, json_mode)),
    ]
    
    errors = []
    for provider_name, provider_fn in providers:
        start = time.time()
        try:
            print(f"🔵 [{call_label}] Trying {provider_name}...")
            result = await provider_fn()
            elapsed = time.time() - start
            print(f"✅ [{call_label}] {provider_name} succeeded in {elapsed:.1f}s "
                  f"(output: {len(result)} chars)")
            return result, provider_name
        except Exception as e:
            elapsed = time.time() - start
            errors.append(f"{provider_name}: {str(e)}")
            print(f"⚠️ [{call_label}] {provider_name} failed in {elapsed:.1f}s: {e}")
    
    # Layer 4: Graceful degradation
    raise Exception(
        f"All AI providers failed for [{call_label}]. Errors: {'; '.join(errors)}"
    )
```

## Implementation: Groq JSON Mode Support

```python
async def call_groq_api(
    prompt: str,
    system_prompt: str,
    max_tokens: int = 2000,
    json_mode: bool = False
) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise Exception("GROQ_API_KEY not set")

    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2
        }
        # Groq supports JSON mode for structured output
        if json_mode:
            data["response_format"] = {"type": "json_object"}

        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 429:
                raise Exception("Groq rate limit exceeded (429)")
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Groq API error: {response.status} - {error_text}")
            result = await response.json()
            return result["choices"][0]["message"]["content"]
```

## Implementation: Per-Prompt Configuration

```python
# Define optimal settings per prompt type
PROMPT_CONFIGS = {
    "job_summary": {
        "max_tokens": 1500,
        "json_mode": False,
        "system_prompt": "You are a job posting analyst. Extract structured information accurately."
    },
    "comparison": {
        "max_tokens": 2500,
        "json_mode": True,   # ← CRITICAL: Force JSON for comparison data
        "system_prompt": "You are a resume-to-job matching analyst. Return ONLY valid JSON."
    },
    "resume_summary": {
        "max_tokens": 800,
        "json_mode": False,
        "system_prompt": "You are a professional resume writer. Write honest, accurate summaries."
    },
    "work_experience": {
        "max_tokens": 1500,
        "json_mode": False,
        "system_prompt": "You are a career coach. Reframe real experiences honestly."
    },
    "cover_letter": {
        "max_tokens": 3000,  # ← CRITICAL: Cover letters need more tokens
        "json_mode": False,
        "system_prompt": "You are a professional cover letter writer. Write compelling, honest letters."
    },
}

# Usage in compare_texts():
async def compare_texts(job_text: str, resume_text: str) -> dict:
    # Each call uses its own optimal config
    config = PROMPT_CONFIGS["comparison"]
    comparison_raw, provider = await call_ai_api(
        prompt=comparison_prompt,
        system_prompt=config["system_prompt"],
        max_tokens=config["max_tokens"],
        json_mode=config["json_mode"],
        call_label="comparison"
    )
    # ...
```

## Implementation: Graceful Partial Results

```python
async def compare_texts(job_text: str, resume_text: str) -> dict:
    """Run all analyses with graceful degradation for individual failures"""
    
    result = {
        "job_summary": None,
        "resume_summary": None,
        "match_score": None,
        "tailored_resume_summary": None,
        "tailored_work_experience": None,
        "cover_letter": None,
        "providers_used": {},    # Track which provider handled each section
        "warnings": [],          # Track any partial failures
    }
    
    # Step 1: Job summary (required — others depend on it)
    try:
        job_summary, provider = await call_ai_api(
            job_summary_prompt, 
            call_label="job_summary",
            **PROMPT_CONFIGS["job_summary"]
        )
        result["job_summary"] = job_summary
        result["providers_used"]["job_summary"] = provider
    except Exception as e:
        # If job summary fails, we can't do comparison — but try other sections
        result["warnings"].append(f"Job summary failed: {str(e)}")
        result["job_summary"] = "<p>Unable to generate job summary. Please try again.</p>"
    
    # Step 2: Run remaining sections in parallel with individual error handling
    async def safe_call(key, prompt, config):
        try:
            text, provider = await call_ai_api(
                prompt, call_label=key, **config
            )
            return key, text, provider, None
        except Exception as e:
            return key, None, None, str(e)
    
    tasks = [
        safe_call("comparison", comparison_prompt, PROMPT_CONFIGS["comparison"]),
        safe_call("resume_summary", tailored_resume_summary_prompt, PROMPT_CONFIGS["resume_summary"]),
        safe_call("work_experience", tailored_work_experience_prompt, PROMPT_CONFIGS["work_experience"]),
        safe_call("cover_letter", cover_letter_prompt, PROMPT_CONFIGS["cover_letter"]),
    ]
    
    results = await asyncio.gather(*tasks)
    
    for key, text, provider, error in results:
        if error:
            result["warnings"].append(f"{key} generation failed: {error}")
            # Provide user-friendly fallback message per section
            fallback_messages = {
                "comparison": "<p>Comparison table temporarily unavailable.</p>",
                "resume_summary": "<p>Resume summary temporarily unavailable.</p>",
                "work_experience": "<p>Work experience suggestions temporarily unavailable.</p>",
                "cover_letter": "<p>Cover letter temporarily unavailable. Please try again.</p>",
            }
            result[key] = fallback_messages.get(key, "<p>Section unavailable.</p>")
        else:
            result[key] = text
            result["providers_used"][key] = provider
    
    return result
```

---

## Decision Matrix Summary

| Criteria              | Option A       | Option B          | Option C       | Option D (Hybrid) |
|-----------------------|----------------|-------------------|----------------|-------------------|
|                       | OpenAI L3      | Better Free Models| Arch Fix Only  | Arch + OpenAI L3  |
| Output quality        | ⭐⭐⭐⭐⭐          | ⭐⭐⭐               | ⭐⭐⭐⭐            | ⭐⭐⭐⭐⭐             |
| Cost                  | ~$0.25/mo      | $0               | $0             | ~$0.25/mo         |
| Reliability           | ⭐⭐⭐⭐⭐          | ⭐⭐                | ⭐⭐⭐⭐            | ⭐⭐⭐⭐⭐             |
| Maintenance effort    | Low            | High (model rot) | Medium         | Low-Medium        |
| Structured output     | JSON mode ✅    | No guarantee     | Server-side ✅  | Both ✅            |
| Implementation effort | 1 hour         | 30 min           | 4-6 hours      | 5-7 hours         |
| Long-term viability   | ⭐⭐⭐⭐⭐          | ⭐⭐                | ⭐⭐⭐⭐            | ⭐⭐⭐⭐⭐             |
| **RECOMMENDATION**    |                |                   |                | **✅ WINNER**      |
