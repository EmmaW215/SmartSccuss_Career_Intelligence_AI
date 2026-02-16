# MatchWise AI v2 — Quality Diagnosis & Solution Plan

## Source Code Analyzed

- **Backend**: `smartsuccess-interview-backend/app/api/routes/matchwise.py` → `compare_texts()` function (6 sequential AI calls)
- **Frontend**: `views/matchwise/components/ResultsDisplay.tsx` → `dangerouslySetInnerHTML` rendering
- **LLM Chain**: `call_ai_api()` → Groq (llama-3.3-70b) → Gemini (2.5-flash) → OpenRouter (free models)

---

## (1) Root Cause Analysis — Why These Quality Issues Occur

### Issue A: Comparison Table Missing in Report 1, Present in Report 2

**Root Cause: Non-deterministic LLM output + no output validation**

The `resume_summary_prompt` asks the LLM to produce an HTML `<table>` AND a match score calculation in a single prompt. The problem is:

```python
# matchwise.py line ~270
resume_summary_prompt = (
    "...Output a comparison table... in HTML format, with <table>, <tr>, <th>, <td> tags..."
    "...Below the table, based on the Match Weight column..."
    "...calculates the percentage of the matching score..."
)
```

This single prompt asks the LLM to do THREE things simultaneously:
1. Generate a complex HTML table with 4 columns
2. Perform arithmetic (sum, count, divide)
3. Return only HTML with no extra text

With the Groq→Gemini→OpenRouter fallback chain, **different models hit on different runs**. If Groq is rate-limited and Gemini handles the request, the output format may differ completely. Free-tier models (especially OpenRouter's `llama-3.2-3b`) are particularly unreliable for complex structured output.

**There is zero validation** after the LLM returns — the code just does:
```python
resume_summary = f"\n\n{resume_summary}"  # Raw insert, no HTML validation
```

### Issue B: "Dear Mahaboob M," — Hallucinated Recipient Name

**Root Cause: No grounding constraint in cover letter prompt**

```python
# matchwise.py line ~320
cover_letter_prompt = (
    "...Provide a formal cover letter for the job application..."
    "The job position and the company name in the cover letter for applying "
    "should be the same as what being used in the job_text..."
)
```

The prompt sends the full `job_text` which likely contains a recruiter name ("Mahaboob M" from Intellectt Inc.'s job posting). The LLM then **hallucinates** this as the letter recipient because:
1. The prompt never says "Do NOT address the letter to any specific person"
2. The prompt never provides the user's name for the signature
3. The LLM extracts any name-like string from the JD and uses it as the salutation
4. There is no post-processing to sanitize or template the greeting/closing

### Issue C: Tailored Resume Summary Quality is Poor/Inconsistent

**Root Cause: Weak prompt constraints + no resume structure awareness**

```python
# matchwise.py line ~295
tailored_resume_summary_prompt = (
    "...Provide a revised one-paragraph summary based on the original summary in resume_text..."
    "...If the user's resume does not have a summary or highlight section, write a new summary..."
    "...Please limit the overall summary to 1700 characters..."
)
```

Problems:
1. **No persona grounding** — the prompt doesn't tell the LLM WHO the user is (their name, seniority level, core identity)
2. **No "DO NOT fabricate" guardrail** — the LLM freely invents skills the user doesn't have (e.g., "Nokia Policy Controller experience" in Report 1 when the resume has none)
3. **1700 character limit** is only in the prompt text — there's no programmatic truncation
4. **"First person" instruction** contradicts the output (Report 1 says "I bring extensive expertise" but reads like a third-person blurb)

### Issue D: Cover Letter is Truncated / Incomplete

**Root Cause: `max_tokens: 2000` hard cap**

```python
# matchwise.py line ~167 (Groq)
data = {
    "model": "llama-3.3-70b-versatile",
    "max_tokens": 2000,     # ← HARD LIMIT for ALL outputs
    "temperature": 0.3
}
```

A professional cover letter typically requires 600-800 words (~2400-3200 tokens). With `max_tokens: 2000` applied uniformly to ALL 6 prompts, the cover letter (the longest output) gets **silently truncated mid-sentence**. The first report's cover letter literally ends at "...managing the full product lifecycle from design to testing and" — cut off.

### Issue E: Suggested Work Experience Contains Fabricated Content

**Root Cause: No factual grounding / "stay within resume" constraint**

Report 1's work experience says:
> "Led the deployment and integration of Nokia Policy Controller (PCF/PCRF)"

But the actual resume has ZERO Nokia PCF/PCRF experience. The prompt says:
```python
"Find the latest work experiences from the resume and modify them to better match the job requirements"
```

"Modify to better match" gives the LLM permission to **fabricate alignment** rather than **honestly reframe** existing experience.

---

## (2) Issue Classification — Technical Categories

| # | Issue | Category | Technical Classification |
|---|-------|----------|------------------------|
| 1 | Comparison table missing/malformed | **Prompt Engineering — Structured Output** | Single prompt overloaded with 3 tasks; no output schema enforcement (JSON mode / function calling) |
| 2 | "Dear Mahaboob M" hallucination | **Prompt Engineering — Grounding & Guardrails** | Missing negative constraints; no input sanitization; no output templating |
| 3 | Poor resume summary quality | **Prompt Engineering — Persona & Context Injection** | No user identity grounding; no factual boundary; inconsistent voice |
| 4 | Truncated cover letter | **LLM Configuration — Token Budget Management** | Uniform `max_tokens: 2000` for all prompts regardless of output length needs |
| 5 | Fabricated work experience | **Prompt Engineering — Hallucination Prevention** | "Modify to match" instruction enables fabrication; no "only use facts from resume" guardrail |
| 6 | Inconsistent output format across runs | **Architecture — Multi-Model Consistency** | Groq/Gemini/OpenRouter produce different output styles; no normalization layer |
| 7 | No output validation | **Architecture — Missing Validation Layer** | Raw LLM output passed directly to frontend via `dangerouslySetInnerHTML` |
| 8 | Match score extraction fragile | **Engineering — Fragile Parsing** | Regex on last line of free-form text; breaks when LLM adds extra text after score |

---

## (3) Solution Plan — Technical Details for Each Issue Type

### Solution Group A: Prompt Engineering Overhaul

#### A1. Decompose the Overloaded Comparison Prompt

**Current**: 1 prompt → table + arithmetic + score
**Solution**: Split into 2 calls with structured output

```python
# Step 1: Generate comparison data as JSON (not HTML)
comparison_prompt = f"""Analyze the resume against the job requirements.

JOB REQUIREMENTS:
{job_summary}

RESUME:
{resume_text}

Return ONLY a valid JSON array. Each element represents one job requirement:
[
  {{
    "category": "requirement name",
    "match_status": "strong|moderate|partial|lack",
    "comment": "brief explanation",
    "weight": 1.0  // strong=1.0, moderate=0.8, partial=0.5, lack=0.1
  }}
]

Rules:
- Include ALL technical skills, responsibilities, certifications, education from the job
- "strong" = explicitly mentioned and well-matched in resume
- "moderate" = closely related experience exists
- "partial" = tangentially related
- "lack" = not found in resume
- Return ONLY the JSON array, no markdown, no explanation
"""

# Step 2: Parse JSON programmatically → compute score → render HTML server-side
import json
raw = await call_ai_api(comparison_prompt)
comparison_data = json.loads(sanitize_json(raw))  # with error handling
match_score = round(
    sum(item["weight"] for item in comparison_data) / len(comparison_data) * 100, 2
)
# Generate HTML table in Python, not LLM
comparison_html = render_comparison_table(comparison_data)
```

**Why this works**: The LLM only does what it's good at (semantic matching). The math and HTML rendering are deterministic code.

#### A2. Fix Cover Letter Hallucination with Template + Guardrails

```python
cover_letter_prompt = f"""Write a professional cover letter for this job application.

APPLICANT NAME: [To be filled by the applicant]
TARGET POSITION: {extracted_job_title}
TARGET COMPANY: {extracted_company_name}

APPLICANT'S ACTUAL BACKGROUND (from resume):
{resume_text}

JOB REQUIREMENTS:
{job_text}

STRICT RULES:
1. Start with "Dear Hiring Manager," — do NOT use any person's name from the job posting
2. End with "Sincerely," followed by a blank line for the applicant's signature
3. ONLY reference skills and experiences that ACTUALLY appear in the resume
4. Do NOT fabricate or invent any experience the applicant doesn't have
5. If the applicant lacks a required skill, frame adjacent experience as transferable
6. Write 4 paragraphs: hook, relevant experience, cultural fit, closing
7. Keep within 500 words
8. Output in HTML using <p> tags only. No markdown.
"""
```

#### A3. Add Factual Grounding to Resume Summary & Work Experience

```python
tailored_resume_summary_prompt = f"""Rewrite this person's professional summary to better target the job below.

ORIGINAL RESUME CONTENT:
{resume_text}

TARGET JOB:
{job_text}

STRICT RULES:
1. Write in first person ("I")
2. ONLY mention skills, technologies, and experiences that are ACTUALLY in the resume above
3. DO NOT fabricate any experience — if a required skill is missing, DO NOT claim it
4. Emphasize the CLOSEST matching experiences from the resume
5. Frame transferable skills honestly (e.g., "My experience in X provides a strong foundation for Y")
6. Keep to one paragraph, maximum 150 words
7. Output as a single HTML <p> tag. No markdown.
"""
```

```python
tailored_work_experience_prompt = f"""Rewrite the applicant's most relevant work experiences to better align with this job.

RESUME WORK EXPERIENCES:
{resume_text}

TARGET JOB:
{job_text}

STRICT RULES:
1. Select 5-7 bullet points from the ACTUAL work experience in the resume
2. Reframe wording to highlight relevance to the target job
3. DO NOT invent projects, tools, or achievements that aren't in the original resume
4. Use strong action verbs (Led, Designed, Implemented, Optimized)
5. Each bullet: action + context + measurable result (if available in resume)
6. Output as HTML <ul><li> list. No markdown, no preamble.
"""
```

### Solution Group B: LLM Configuration Fixes

#### B1. Per-Prompt Token Budget

```python
# Define token budgets per output type
TOKEN_BUDGETS = {
    "job_summary": 1500,
    "comparison": 2000,
    "resume_summary": 800,
    "work_experience": 1500,
    "cover_letter": 3000,   # ← Cover letter needs MORE tokens
}

async def call_ai_api(prompt: str, system_prompt: str, max_tokens: int = 2000) -> str:
    """Accept per-call max_tokens parameter"""
    # ... pass max_tokens to each provider
```

```python
# In compare_texts():
cover_letter = await call_ai_api(
    cover_letter_prompt,
    system_prompt="You are a professional career consultant...",
    max_tokens=TOKEN_BUDGETS["cover_letter"]  # 3000, not 2000
)
```

#### B2. Model-Specific System Prompts

Different models in the fallback chain respond differently to the same prompt. Add model-aware behavior:

```python
async def call_groq_api(prompt: str, system_prompt: str, max_tokens: int = 2000) -> str:
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,         # Lower temp for more deterministic output
        "response_format": {"type": "text"}  # Groq supports this
    }
```

For the comparison JSON prompt specifically, use Groq's JSON mode:
```python
data["response_format"] = {"type": "json_object"}  # Forces valid JSON output
```

### Solution Group C: Architecture — Output Validation Layer

#### C1. Add Post-Processing & Validation

```python
def validate_and_sanitize_html(raw_html: str, expected_tags: list[str]) -> str:
    """Validate LLM output contains expected HTML structure"""
    from bs4 import BeautifulSoup
    
    # Strip markdown code fences if LLM included them
    cleaned = re.sub(r'```html?\s*', '', raw_html)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    
    soup = BeautifulSoup(cleaned, 'html.parser')
    
    # Verify expected structure exists
    for tag in expected_tags:
        if not soup.find(tag):
            raise ValueError(f"Missing expected HTML tag: <{tag}>")
    
    # Remove any script tags (XSS prevention for dangerouslySetInnerHTML)
    for script in soup.find_all('script'):
        script.decompose()
    
    return str(soup)


def validate_comparison_json(raw: str) -> list[dict]:
    """Parse and validate comparison data"""
    # Strip markdown fences
    cleaned = re.sub(r'```json?\s*', '', raw)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    
    data = json.loads(cleaned)
    
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Comparison must be a non-empty array")
    
    valid_statuses = {"strong", "moderate", "partial", "lack"}
    for item in data:
        assert "category" in item, "Missing 'category'"
        assert "match_status" in item, "Missing 'match_status'"
        assert item["match_status"] in valid_statuses, f"Invalid status: {item['match_status']}"
        item["weight"] = {"strong": 1.0, "moderate": 0.8, "partial": 0.5, "lack": 0.1}[item["match_status"]]
    
    return data
```

#### C2. Add Retry-with-Correction Loop

```python
async def call_ai_with_validation(
    prompt: str, 
    validator: callable, 
    max_retries: int = 2,
    **kwargs
) -> any:
    """Call LLM and validate output; retry with error feedback if invalid"""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw = await call_ai_api(prompt if attempt == 0 else 
                f"{prompt}\n\n⚠️ Your previous response was invalid: {last_error}\nPlease fix and try again.",
                **kwargs)
            return validator(raw)
        except (json.JSONDecodeError, ValueError, AssertionError) as e:
            last_error = str(e)
            print(f"⚠️ Validation failed (attempt {attempt+1}): {e}")
    
    raise Exception(f"Output validation failed after {max_retries+1} attempts: {last_error}")
```

#### C3. Server-Side HTML Table Rendering (Deterministic)

```python
def render_comparison_table(data: list[dict]) -> str:
    """Render comparison table in Python — never trust LLM for HTML structure"""
    status_icons = {
        "strong": "✅ Strong",
        "moderate": "🔷 Moderate",
        "partial": "⚠️ Partial",
        "lack": "❌ Lack"
    }
    
    rows = ""
    for item in data:
        rows += f"""<tr>
            <td>{item['category']}</td>
            <td>{status_icons[item['match_status']]}</td>
            <td>{item['comment']}</td>
            <td>{item['weight']}</td>
        </tr>"""
    
    return f"""<table class="matchwise-comparison">
        <thead><tr>
            <th>Category</th><th>Match Status</th><th>Comments</th><th>Weight</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>"""
```

### Solution Group D: Frontend Hardening

#### D1. Replace `dangerouslySetInnerHTML` with Sanitized Rendering

```typescript
// Install: npm install dompurify @types/dompurify
import DOMPurify from 'dompurify';

const SafeHTML: React.FC<{ html: string; className?: string }> = ({ html, className }) => {
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'ul', 'ol', 'li', 'strong', 'em', 'table', 
                   'thead', 'tbody', 'tr', 'th', 'td', 'h3', 'span'],
    ALLOWED_ATTR: ['class', 'style'],
  });
  return <div className={className} dangerouslySetInnerHTML={{ __html: clean }} />;
};

// Usage in ResultsDisplay.tsx:
<SafeHTML html={data.cover_letter || 'No cover letter available.'} className="..." />
```

---

## (4) Additional Issues You Should Know

### Issue 9: Sequential 6-Call Chain = Single Point of Failure + Slow

**Current architecture**: `compare_texts()` makes 6 sequential AI calls. If call #4 fails, calls 1-3 are wasted. Total latency: ~6 × 5-10s = 30-60 seconds.

**Solution**: Use `asyncio.gather()` for independent calls:

```python
async def compare_texts(job_text: str, resume_text: str) -> dict:
    # Step 1: Job summary must run first (others depend on it)
    job_summary = await call_ai_api(job_summary_prompt)
    
    # Step 2: Run remaining 4 calls in PARALLEL (they all depend on job_text + resume_text)
    comparison, tailored_summary, work_exp, cover_letter = await asyncio.gather(
        call_ai_with_validation(comparison_prompt, validate_comparison_json),
        call_ai_api(tailored_resume_summary_prompt, max_tokens=800),
        call_ai_api(tailored_work_experience_prompt, max_tokens=1500),
        call_ai_api(cover_letter_prompt, max_tokens=3000),
    )
    # ...
```

**Result**: Latency drops from ~60s to ~15-20s (1 serial + 4 parallel).

### Issue 10: PDF Text Extraction Quality

```python
def extract_text_from_pdf(file: UploadFile) -> str:
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""  # ← PyPDF2 is notoriously poor at extraction
    return text.strip()
```

PyPDF2 often produces garbled text from multi-column resumes, tables, and styled PDFs. This means the LLM receives **corrupted input**, which cascades into all 6 outputs.

**Solution**: Replace with `pdfplumber` or `pymupdf (fitz)`:

```python
import pdfplumber

def extract_text_from_pdf(file: UploadFile) -> str:
    content = file.file.read()
    text = ""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text += page.extract_text(layout=True) or ""
    return text.strip()
```

### Issue 11: No Prompt-Level Logging / Observability

When output quality is bad, you currently have no way to know:
- Which LLM provider handled each call (Groq? Gemini? OpenRouter?)
- What the raw LLM output was before post-processing
- How long each call took

**Solution**: Add structured logging:

```python
import time, uuid

async def call_ai_api(prompt: str, system_prompt: str, max_tokens: int = 2000, 
                      call_id: str = None) -> str:
    call_id = call_id or str(uuid.uuid4())[:8]
    providers = ["groq", "gemini", "openrouter"]
    
    for i, (provider, fn) in enumerate([(providers[0], call_groq_api), ...]):
        start = time.time()
        try:
            result = await fn(prompt, system_prompt, max_tokens)
            elapsed = time.time() - start
            print(f"✅ [{call_id}] {provider} succeeded in {elapsed:.1f}s, "
                  f"output_len={len(result)} chars")
            return result
        except Exception as e:
            elapsed = time.time() - start
            print(f"⚠️ [{call_id}] {provider} failed in {elapsed:.1f}s: {e}")
```

### Issue 12: XSS Vulnerability via `dangerouslySetInnerHTML`

The frontend renders ALL LLM output with `dangerouslySetInnerHTML`. If an attacker injects `<script>` tags into a job description or resume, it executes in the user's browser.

**Solution**: DOMPurify (see D1 above) — this is a **security-critical** fix.

### Issue 13: Prompt Leaks Full Resume to Every AI Provider

The current code sends the full resume text to Groq, Gemini, AND OpenRouter free models. Free-tier APIs have weaker data privacy guarantees.

**Solution**: 
- Add a privacy notice to the UI
- Consider extracting only structured data (skills, experience bullets) from the resume before sending to free APIs
- Log which provider processed which data for compliance

---

## Priority Implementation Order

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| 🔴 P0 | B1: Per-prompt token budgets (cover letter truncation) | 30min | High — fixes broken output |
| 🔴 P0 | A2: Cover letter guardrails (hallucinated names) | 1hr | High — fixes embarrassing output |
| 🔴 P0 | D1 + Issue 12: DOMPurify XSS protection | 30min | Critical — security |
| 🟡 P1 | A1: Decompose comparison prompt → JSON + server-side table | 3hr | High — fixes missing table |
| 🟡 P1 | A3: Factual grounding for summary + work experience | 1hr | High — fixes fabrication |
| 🟡 P1 | Issue 10: Replace PyPDF2 with pdfplumber | 30min | Medium — fixes bad input |
| 🟢 P2 | C2: Retry-with-correction loop | 2hr | Medium — improves reliability |
| 🟢 P2 | Issue 9: Parallel AI calls | 1hr | Medium — 3x faster |
| 🟢 P2 | Issue 11: Observability logging | 1hr | Medium — debuggability |
| ⚪ P3 | B2: Model-specific system prompts | 2hr | Low-Medium — consistency |
| ⚪ P3 | Issue 13: Privacy-aware data handling | 3hr | Low — compliance |
