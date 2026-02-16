# MatchWise AI — Round 2 Diagnosis & Implementation Plan

## Code Analyzed (Latest Commit)

- `smartsuccess-interview-backend/app/api/routes/matchwise.py` (49,984 bytes — updated with v2.1.0 architecture)
- `views/matchwise/components/ResultsDisplay.tsx` (5,308 bytes — updated with DOMPurify)
- Screenshots: Cover Letter (Image 1), Work Experience (Image 2), Job Summary current (Image 3), Job Summary desired (Image 4)

---

## Issue (1): Cover Letter Still Being Cut Short

### What's Happening

The cover letter in Image 1 ends with:
> "My commitment to delivering high-performance, secure, and compliant AI solutions"

This is mid-sentence — clearly truncated. The `TOKEN_BUDGETS["cover_letter"] = 3000` IS correctly set in the code, and the `_run_cover_letter()` function correctly passes it. So why is it still truncating?

### Root Cause: Gemini 2.5 Flash Thinking Tokens

The primary suspect is **Gemini 2.5 Flash's "thinking" feature**. When your code calls Gemini:

```python
# Current code (line ~230):
gen_config = {"maxOutputTokens": max_tokens, "temperature": 0.2}
if json_mode:
    gen_config["responseMimeType"] = "application/json"
data = {
    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
    "generationConfig": gen_config
}
```

**Gemini 2.5 Flash uses "thinking" (internal chain-of-thought) by default.** The thinking tokens are counted WITHIN the `maxOutputTokens` budget. So if you set `maxOutputTokens: 3000`:

```
Gemini's internal allocation:
  Thinking tokens:  ~1500-2000 (hidden, not visible in output)
  Actual output:    ~1000-1500 (what the user sees)
  Total:            3000 (hits limit → TRUNCATION)
```

The cover letter needs ~800-1200 tokens of visible output. With thinking overhead eating 50-65% of the budget, only ~1000-1500 tokens remain for actual content — causing the mid-sentence cutoff.

### Secondary Cause: Groq Parallel Rate Limiting

Your code now runs 4 prompts in parallel via `asyncio.gather()`. All 4 hit Groq simultaneously:

```
t=0s: job_summary → Groq ✅ (sequential, succeeds first)
t=5s: comparison   → Groq (may hit 30 RPM limit)
t=5s: resume_summary → Groq (may hit 30 RPM limit)
t=5s: work_experience → Groq (may hit 30 RPM limit)
t=5s: cover_letter → Groq (likely gets 429 → falls to Gemini)
```

Because cover_letter is the 5th Groq call in rapid succession, it's the most likely to get rate-limited and fall to Gemini (Layer 2), where the thinking token issue kicks in.

### Why STRICT RULES Aren't Followed

The cover letter prompt rules (end with "Sincerely,", 4 paragraphs, 500 words, etc.) are failing because:

1. **Truncation kills the ending** — Rules 2 (Sincerely) and 6 (4 paragraphs) literally can't be followed if the output is cut off at paragraph 1-2.

2. **Rules are positionally buried** — The prompt structure is:
   ```
   [resume_text: ~2000-5000 tokens]  ← LLM focuses here
   [job_text: ~1000-3000 tokens]     ← And here
   [STRICT RULES: ~200 tokens]       ← Loses attention by this point
   ```
   LLMs have a well-documented "lost in the middle" problem — they attend most strongly to the beginning and end of the prompt. Your rules are at the END, but after a massive amount of context, the model's attention to them degrades.

3. **Rule 3/4 (no fabrication) requires reasoning** — The model needs to cross-reference every claim against the resume, which weaker/faster models (Gemini Flash) may skip under token pressure.

### Fix for Issue (1)

**Fix A: Disable Gemini thinking for non-reasoning tasks OR increase token budget:**

```python
async def call_gemini_api(prompt: str, system_prompt: str = "...",
                          max_tokens: int = 2000, json_mode: bool = False) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    async with aiohttp.ClientSession() as session:
        headers = {"Content-Type": "application/json"}
        gen_config = {
            "maxOutputTokens": max_tokens,
            "temperature": 0.2,
            # ═══════════════════════════════════════════════════
            # FIX: Disable thinking to prevent token budget theft
            # Thinking tokens consume maxOutputTokens silently.
            # For structured/creative output (cover letters, summaries),
            # thinking provides minimal benefit but steals ~50% of tokens.
            # ═══════════════════════════════════════════════════
            "thinkingConfig": {
                "thinkingBudget": 0  # 0 = disable thinking entirely
            }
        }
        if json_mode:
            gen_config["responseMimeType"] = "application/json"
        data = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
            "generationConfig": gen_config
        }
        # ... rest unchanged
```

> **Why `thinkingBudget: 0`?** For MatchWise prompts (cover letters, summaries, bullet points), the LLM doesn't need chain-of-thought reasoning. These are generation tasks, not logic puzzles. Disabling thinking gives 100% of `maxOutputTokens` to actual output.

**Fix B: Restructure cover letter prompt — put RULES FIRST, context SECOND:**

```python
cover_letter_prompt = f"""You are writing a professional cover letter. Follow ALL rules below EXACTLY.

═══ MANDATORY FORMAT RULES ═══
1. Start EXACTLY with "Dear Hiring Manager,"
2. Write EXACTLY 4 paragraphs:
   - Paragraph 1: Opening hook — state the position title and company name, express enthusiasm
   - Paragraph 2: Relevant technical experience — highlight 3-4 specific skills/projects from the resume that match job requirements
   - Paragraph 3: Soft skills, leadership, and cultural fit
   - Paragraph 4: Closing — express enthusiasm for interview opportunity
3. End EXACTLY with:
   <p>Sincerely,</p>
   <p>[Your Name]</p>
4. Total length: 400-500 words (4 paragraphs)
5. Output ONLY in HTML using <p> tags. No markdown, no ```html.

═══ CONTENT INTEGRITY RULES ═══
6. ONLY reference skills, technologies, and experiences that ACTUALLY appear in the RESUME below.
7. DO NOT fabricate or invent any experience, certification, or achievement.
8. If the applicant lacks a required skill, frame adjacent experience as transferable
   (e.g., "My experience in X provides a strong foundation for Y").
9. Extract the correct job title and company name from the JOB POSTING below.
10. Tone: confident, honest, professional. First person.

═══ RESUME (applicant's actual background) ═══
{resume_text}

═══ JOB POSTING ═══
{job_text}

Now write the cover letter following ALL rules above. Start with "Dear Hiring Manager,"
"""
```

> **Key change**: Rules are at the TOP of the prompt, before the long context. The LLM sees the constraints first, then the data. The final line re-anchors attention to Rule 1.

**Fix C: Increase cover letter token budget as safety margin:**

```python
TOKEN_BUDGETS = {
    "job_summary": 1500,
    "comparison": 2500,
    "resume_summary": 1000,     # Slight increase for safety
    "work_experience": 1500,
    "cover_letter": 4096,       # Increased from 3000 → 4096
}
```

> Even with thinking disabled, 4096 gives ample headroom. A 500-word cover letter is ~700 tokens, so 4096 ensures zero truncation risk.

**Fix D: Add truncation detection:**

```python
async def _run_cover_letter():
    result, provider = await call_ai_api(
        cover_letter_prompt,
        system_prompt=PROMPT_CONFIGS["cover_letter"]["system_prompt"],
        max_tokens=TOKEN_BUDGETS["cover_letter"],
        call_label="cover_letter",
    )
    # ─── Truncation detection ───
    # A properly completed cover letter must end with signature
    if "Sincerely" not in result and "sincerely" not in result:
        print(f"⚠️ [Matchwise] Cover letter may be truncated (no 'Sincerely' found). "
              f"Provider: {provider}, output length: {len(result)} chars")
        # Append a graceful ending if truncated
        result += "\n<p>Sincerely,</p>\n<p>[Your Name]</p>"
    return result, provider
```

---

## Issue (2): Tailored Resume Summary — "I" Pronoun Issue

### Current Problem

The current system prompt says:
```python
"Write honest, accurate summaries... Write in first person."
```

And the prompt rule 7 says:
```python
"7. Write in the first person.\n"
```

This produces output like: *"I am confident that my expertise in Agentic AI..."*

### The "Implied First Person" Rule

The standard North American resume convention is **implied first person** — no pronouns (I, my, me, we), start with action verbs. This applies to BOTH the summary and work experience sections.

### Fix for Issue (2)

**Change the system prompt for `resume_summary`:**

```python
PROMPT_CONFIGS = {
    # ...
    "resume_summary": {
        "system_prompt": (
            "You are a professional resume writer following North American resume conventions. "
            "Write in the 'implied first person' — NEVER use personal pronouns (I, my, me, we, our). "
            "Start sentences with strong action verbs or descriptive phrases. "
            "Write honest, accurate summaries that highlight real qualifications. "
            "Never fabricate experience. Frame transferable skills truthfully."
        ),
    },
    # ...
}
```

**Change the `tailored_resume_summary_prompt` — replace rule 7 and add explicit guidance:**

```python
tailored_resume_summary_prompt = f"""You are revising a professional resume summary to better match a specific job posting.

═══ RESUME WRITING CONVENTION (CRITICAL) ═══
Use "implied first person" — this is the standard North American resume format:
- NEVER use personal pronouns: I, my, me, we, our
- Start sentences with action verbs or descriptive noun phrases
- The subject "I" is implied and never written
- Examples:
  ✅ CORRECT: "Senior AI Solution Architect with 14+ years of experience..."
  ❌ WRONG:  "I am a Senior AI Solution Architect with 14+ years..."
  ✅ CORRECT: "Proven track record in designing production-grade RAG pipelines..."
  ❌ WRONG:  "I have a proven track record in designing..."
  ✅ CORRECT: "Adept at leveraging cloud-native architectures to deliver scalable AI solutions."
  ❌ WRONG:  "I am adept at leveraging my cloud-native architecture skills..."

═══ CONTENT RULES ═══
1. Write ONE paragraph, maximum 150 words.
2. ONLY mention skills, technologies, and experiences that ACTUALLY appear in the resume below.
3. DO NOT fabricate or invent any certifications, years of experience, tools, or achievements.
4. If the applicant lacks a required skill, frame adjacent experience as transferable
   (e.g., "Leveraging background in X to rapidly adapt to Y" — no "I" or "my").
5. If the resume has an existing summary section, use it as a base and enhance it.
6. If no summary exists, write a new one based solely on actual resume content.
7. Highlight key skills and experiences that best match the job requirements.
8. Output a single HTML <p> tag. No markdown, no ```html, no preamble text.

═══ APPLICANT'S ACTUAL RESUME ═══
{resume_text}

═══ TARGET JOB POSTING ═══
{job_text}

Now write the revised summary following ALL conventions above. Do NOT use any personal pronouns.
"""
```

---

## Issue (3): Suggested Work Experience — Format & Content Disaster

### Current Problems (Image 2)

1. **No bullet points visible** — Output appears as plain paragraphs despite prompt asking for `<ul><li>`
2. **Fully rewritten** — The experiences are completely rewritten rather than extracted-then-reframed
3. **Generic content** — Reads like a new resume rather than strategically reframed existing bullets

### Root Cause

The current prompt says:
```python
"Find the most recent and relevant work experiences from the resume and revise them"
```

The word "revise" is too vague. The LLM interprets this as "rewrite from scratch to match the job" rather than "take the actual bullet points and tweak the wording."

### Fix for Issue (3)

**Complete replacement of `tailored_work_experience_prompt`:**

```python
tailored_work_experience_prompt = f"""You are a career coach helping reframe existing resume bullet points for a specific job application.

═══ RESUME WRITING CONVENTION (CRITICAL) ═══
Use "implied first person" — standard North American resume format:
- NEVER use personal pronouns: I, my, me, we, our
- Start EVERY bullet with a strong past-tense action verb (Led, Designed, Implemented, Engineered, Directed, Built, Optimized, Architected, Developed, Managed)
- The subject "I" is implied and never written

═══ TASK: TWO-STEP PROCESS ═══

STEP 1 — EXTRACT: Identify the 5-7 most relevant work experience bullet points
from the resume that best align with the target job requirements.
Pick ACTUAL bullet points or descriptions from the resume's work history.

STEP 2 — REFRAME: For each extracted bullet, lightly reframe the wording to:
  - Highlight relevance to the target job
  - Add relevant keywords from the job posting ONLY IF the skill genuinely exists in the resume
  - Strengthen the action verb if needed
  - Preserve the original achievement, metric, or context

═══ STRICT RULES ═══
1. Every bullet MUST be traceable to a REAL experience in the resume. If you cannot point to the source, do not include it.
2. DO NOT invent projects, tools, technologies, metrics, team sizes, or dollar amounts that aren't in the resume.
3. DO NOT fully rewrite or create new experiences. ONLY reframe existing ones.
4. Each bullet: strong action verb + context + measurable result (if available in resume).
5. Keep each bullet to 1-2 concise sentences maximum.
6. Frame transferable skills honestly (e.g., "Applied RF propagation modeling methodologies to..." rather than inventing a new role).

═══ OUTPUT FORMAT (CRITICAL — MUST FOLLOW EXACTLY) ═══
Output as an HTML unordered list. EVERY experience must be a <li> inside a <ul>.
Do NOT output plain text paragraphs. Do NOT output markdown.
Do NOT add any preamble, title, or explanation outside the list.
Output ONLY this structure:

<ul>
<li>Bullet point 1 here</li>
<li>Bullet point 2 here</li>
<li>Bullet point 3 here</li>
<li>Bullet point 4 here</li>
<li>Bullet point 5 here</li>
<li>Bullet point 6 here</li>
<li>Bullet point 7 here</li>
</ul>

═══ APPLICANT'S ACTUAL RESUME ═══
{resume_text}

═══ TARGET JOB POSTING ═══
{job_text}

Now output ONLY the <ul>...</ul> list. No other text.
"""
```

**Also update the system prompt:**

```python
PROMPT_CONFIGS = {
    # ...
    "work_experience": {
        "system_prompt": (
            "You are a career coach specializing in resume optimization. "
            "Your job is to EXTRACT real work experiences from resumes and LIGHTLY REFRAME "
            "them to highlight relevance to specific job postings. "
            "NEVER invent new experiences. NEVER use personal pronouns (I, my, me, we). "
            "Always start bullets with strong past-tense action verbs. "
            "Output ONLY HTML <ul><li> lists with no extra text."
        ),
    },
    # ...
}
```

**Add HTML format enforcement in the post-processing:**

```python
async def _run_work_experience():
    result, provider = await call_ai_api(
        tailored_work_experience_prompt,
        system_prompt=PROMPT_CONFIGS["work_experience"]["system_prompt"],
        max_tokens=TOKEN_BUDGETS["work_experience"],
        call_label="work_experience",
    )
    # ─── Ensure proper HTML list format ───
    # Strip markdown fences if present
    cleaned = re.sub(r'```html?\s*', '', result)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    # If LLM output doesn't contain <ul>, wrap it
    if '<ul' not in cleaned.lower():
        # Split by newlines and wrap each non-empty line as <li>
        lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
        # Remove any leading bullets/numbers/dashes
        lines = [re.sub(r'^[\-\*\d\.•Ø]+\s*', '', l) for l in lines if l]
        cleaned = '<ul>' + ''.join(f'<li>{l}</li>' for l in lines) + '</ul>'
    return cleaned, provider
```

---

## Issue (4): Job Requirement Summary — Improve HTML Format

### Current vs Desired

**Current (Image 3):** Uses `Ø` symbols, `<strong>` bold labels inline, `<ul><li>` with `• Ø` prefixes. Functional but cluttered.

**Desired (Image 4):** Clean nested bullet list with `<strong>` bold key labels (`Position Title:`, `Company Name:`, `Key Responsibilities:`), proper indentation, no `Ø` symbols, professional formatting.

### Root Cause

The current `job_summary_prompt` explicitly embeds the `Ø` symbols and messy formatting in its template:

```python
# Current prompt literally contains:
"<li><strong> Ø Position Title: </strong> [extract the job title]</li>"
"<li>•     Ø [responsibility 1]</li>"
```

The LLM faithfully reproduces these `Ø` symbols because the prompt TELLS it to.

### Fix for Issue (4)

**Complete replacement of `job_summary_prompt`:**

```python
job_summary_prompt = f"""Analyze the following job posting and extract key information.

═══ JOB POSTING CONTENT ═══
{job_text}

═══ OUTPUT INSTRUCTIONS ═══
Extract and organize the information into a clean, professional HTML bullet list.
Use the EXACT structure below. Replace bracketed placeholders with actual content from the job posting.
If any information is not available, write "Not specified" for that item.

Output ONLY the HTML below — no markdown, no ```html, no preamble:

<ul style="list-style-type: disc; padding-left: 20px; line-height: 1.8;">
  <li><strong>Position Title:</strong> [exact job title]</li>
  <li><strong>Company Name:</strong> [company name and any client info if mentioned]</li>
  <li><strong>Department:</strong> [department if mentioned, else "Not specified"]</li>
  <li><strong>Location:</strong> [location and work arrangement (remote/onsite/hybrid)]</li>
  <li><strong>Employment Type:</strong> [full-time/contract/etc., else "Not specified"]</li>
  <li><strong>Compensation:</strong>
    <ul style="list-style-type: circle; padding-left: 20px;">
      <li><strong>Salary/Rate:</strong> [salary info if available, else "Not specified"]</li>
      <li><strong>Benefits:</strong> [benefits if mentioned, else "Not specified"]</li>
    </ul>
  </li>
  <li><strong>Environment/Company Culture:</strong> [company culture/vision if available, else "Not specified"]</li>
  <li><strong>Key Responsibilities:</strong>
    <ul style="list-style-type: circle; padding-left: 20px;">
      <li>[responsibility 1]</li>
      <li>[responsibility 2]</li>
      <li>[responsibility 3]</li>
      <li>[up to 8 responsibilities]</li>
    </ul>
  </li>
  <li><strong>Technical Skills Required:</strong>
    <ul style="list-style-type: circle; padding-left: 20px;">
      <li>[tech skill 1]</li>
      <li>[tech skill 2]</li>
      <li>[up to 10 technical skills]</li>
    </ul>
  </li>
  <li><strong>Soft Skills Required:</strong>
    <ul style="list-style-type: circle; padding-left: 20px;">
      <li>[soft skill 1]</li>
      <li>[soft skill 2]</li>
      <li>[up to 7 soft skills]</li>
    </ul>
  </li>
  <li><strong>Certifications Required:</strong> [certifications if any, else "Not specified"]</li>
  <li><strong>Education Required:</strong> [education requirements, else "Not specified"]</li>
</ul>
"""
```

**Also update the system prompt to reinforce clean formatting:**

```python
PROMPT_CONFIGS = {
    "job_summary": {
        "system_prompt": (
            "You are a job posting analyst. Extract structured information accurately "
            "from job descriptions. Output clean, well-organized HTML bullet lists "
            "with professional formatting. Use <strong> tags for labels. "
            "Do NOT use Ø symbols or decorative characters. Keep output clean and scannable."
        ),
    },
    # ...
}
```

---

## Complete Implementation Plan

### Phase 1: Critical Fixes (Immediate — ~2 hours)

| # | Fix | File | Change |
|---|-----|------|--------|
| 1a | Disable Gemini thinking tokens | `matchwise.py` → `call_gemini_api()` | Add `"thinkingConfig": {"thinkingBudget": 0}` to `gen_config` |
| 1b | Increase cover letter token budget | `matchwise.py` → `TOKEN_BUDGETS` | `"cover_letter": 3000` → `4096` |
| 1c | Restructure cover letter prompt | `matchwise.py` → `cover_letter_prompt` | Move RULES to top, context to bottom, add re-anchor |
| 1d | Add truncation detection | `matchwise.py` → `_run_cover_letter()` | Check for "Sincerely", append if missing |

### Phase 2: Resume Content Quality (Same session — ~1.5 hours)

| # | Fix | File | Change |
|---|-----|------|--------|
| 2a | Resume summary: implied first person | `matchwise.py` → `tailored_resume_summary_prompt` | Full prompt replacement with "no pronouns" convention |
| 2b | Resume summary: system prompt | `matchwise.py` → `PROMPT_CONFIGS["resume_summary"]` | Add "NEVER use personal pronouns" |
| 2c | Work experience: extract-then-reframe | `matchwise.py` → `tailored_work_experience_prompt` | Full prompt replacement with 2-step process |
| 2d | Work experience: system prompt | `matchwise.py` → `PROMPT_CONFIGS["work_experience"]` | Add "EXTRACT real experiences, LIGHTLY REFRAME" |
| 2e | Work experience: HTML enforcement | `matchwise.py` → `_run_work_experience()` | Add post-processing to ensure `<ul><li>` format |

### Phase 3: Visual Polish (~30 min)

| # | Fix | File | Change |
|---|-----|------|--------|
| 3a | Job summary: clean format | `matchwise.py` → `job_summary_prompt` | Full prompt replacement — remove Ø, use Image 4 style |
| 3b | Job summary: system prompt | `matchwise.py` → `PROMPT_CONFIGS["job_summary"]` | Add "Do NOT use Ø symbols" |

### Phase 4: Test & Validate (~30 min)

| # | Step | Action |
|---|------|--------|
| 4a | Deploy to Render | Push to main branch, wait for auto-deploy |
| 4b | Test with AI Architect JD | Upload the same Arkhya Tech JD + AI Solution Architect resume |
| 4c | Verify cover letter | Check: starts "Dear Hiring Manager,", ends "Sincerely,", 4 paragraphs, no fabrication |
| 4d | Verify resume summary | Check: no "I/my/me", starts with action verb or noun phrase |
| 4e | Verify work experience | Check: `<ul><li>` format, bullets visible, content from actual resume |
| 4f | Verify job summary | Check: clean bullet format matching Image 4 style, no Ø symbols |
| 4g | Check server logs | Verify which provider handled each section, check for warnings |

---

## Summary of All Changes

```
Files to modify:
  1. smartsuccess-interview-backend/app/api/routes/matchwise.py
     ├── call_gemini_api()         → Add thinkingConfig
     ├── TOKEN_BUDGETS             → cover_letter: 3000 → 4096
     ├── PROMPT_CONFIGS            → Update 4 system prompts
     ├── job_summary_prompt        → Full replacement (clean format)
     ├── tailored_resume_summary_prompt → Full replacement (implied first person)
     ├── tailored_work_experience_prompt → Full replacement (extract-then-reframe)
     ├── cover_letter_prompt       → Full replacement (rules-first structure)
     ├── _run_cover_letter()       → Add truncation detection
     └── _run_work_experience()    → Add HTML format enforcement

Total estimated time: ~4 hours (including testing)
```
