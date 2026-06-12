"""
Phase 3 — document text extraction (PRD 03 §A3).

Ported from smartsuccess-phase2/gpu-server/services/rag_service.py, adapted
to the backend's existing extraction stack (pdfplumber + python-docx, both
already required by MatchWise).
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

MAX_DOC_CHARS = 20000


def extract_text(content: bytes, filename: str, content_type: str = "") -> str:
    """Extract normalized text from raw file bytes (pdf / docx / txt)."""
    name_lower = (filename or "").lower()

    if name_lower.endswith(".pdf") or "pdf" in (content_type or ""):
        return _extract_pdf_text(content)

    if name_lower.endswith(".docx"):
        return _extract_docx_text(content)

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="ignore")


def _extract_pdf_text(content: bytes) -> str:
    try:
        import pdfplumber

        text_parts: List[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("pdfplumber not installed — PDF extraction unavailable")
        return ""
    except Exception as exc:
        logger.warning("PDF extraction failed: %s", exc)
        return ""


def _extract_docx_text(content: bytes) -> str:
    try:
        import docx

        document = docx.Document(io.BytesIO(content))
        return "\n".join(para.text for para in document.paragraphs)
    except ImportError:
        logger.warning("python-docx not installed — DOCX extraction unavailable")
        return ""
    except Exception as exc:
        logger.warning("DOCX extraction failed: %s", exc)
        return ""


def detect_doc_type(filename: str, text: str) -> str:
    """Classify a document as resume / job_description / supporting."""
    fname_lower = (filename or "").lower()
    text_lower = (text or "").lower()

    if any(word in fname_lower for word in ("resume", "cv")):
        return "resume"
    if any(word in fname_lower for word in ("job", "jd", "description")):
        return "job_description"

    resume_words = ("experience", "education", "skills", "employment")
    jd_words = ("requirements", "responsibilities", "qualifications")
    resume_score = sum(1 for word in resume_words if word in text_lower)
    jd_score = sum(1 for word in jd_words if word in text_lower)

    if resume_score > jd_score:
        return "resume"
    if jd_score > resume_score:
        return "job_description"
    return "supporting"


def load_documents(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize uploaded files into {"filename", "text", "doc_type"} dicts.

    `files` entries carry: filename, content (bytes or str), content_type.
    Files whose extraction produces no text are skipped (logged).
    """
    documents: List[Dict[str, Any]] = []
    for file_info in files:
        filename = file_info.get("filename", "unknown")
        content = file_info.get("content", b"")
        content_type = file_info.get("content_type", "")

        if isinstance(content, bytes):
            text = extract_text(content, filename, content_type)
        else:
            text = str(content or "")

        text = text.strip()[:MAX_DOC_CHARS]
        if not text:
            logger.warning("No text extracted from %s — skipping", filename)
            continue

        documents.append(
            {
                "filename": filename,
                "text": text,
                "doc_type": detect_doc_type(filename, text),
            }
        )
    return documents
