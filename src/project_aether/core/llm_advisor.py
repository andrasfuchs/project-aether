"""
On-demand LLM helpers for Deep Technical Briefs (full-text or PDF) and
Query Refinement Suggestions, plus local PDF storage per patent.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
from google.genai import types
from pydantic import BaseModel

from project_aether.core.config import get_config
from project_aether.core.llm import generate_content


class QueryRefinementSuggestions(BaseModel):
    suggested_excludes: list[str]
    suggested_include_synonyms: list[list[str]]
    summary: str


def get_patent_pdf_dir() -> Path:
    """Return directory storing uploaded patent PDFs associated with record IDs."""
    return get_config().database_path.parent / "patent_pdfs"


def get_patent_pdf_path(record_id: str, pdf_dir: Path | None = None) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "_", (record_id or "UNKNOWN").strip())
    target_dir = pdf_dir or get_patent_pdf_dir()
    return target_dir / f"{safe_id}.pdf"


def save_patent_pdf(record_id: str, pdf_bytes: bytes, pdf_dir: Path | None = None) -> Path:
    """Persist an uploaded patent PDF on disk associated with `record_id`."""
    path = get_patent_pdf_path(record_id, pdf_dir=pdf_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf_bytes)
    return path


def load_patent_pdf(record_id: str, pdf_dir: Path | None = None) -> bytes | None:
    """Load a previously stored patent PDF if present."""
    path = get_patent_pdf_path(record_id, pdf_dir=pdf_dir)
    if path.exists():
        return path.read_bytes()
    return None


def delete_patent_pdf(record_id: str, pdf_dir: Path | None = None) -> bool:
    """Delete a stored patent PDF if present."""
    path = get_patent_pdf_path(record_id, pdf_dir=pdf_dir)
    if path.exists():
        path.unlink()
        return True
    return False


def fetch_google_patents_pdf(jurisdiction: str, doc_number: str) -> bytes | None:
    """
    Attempt to automatically download the full patent PDF from Google Patents
    (no sign-in required). Returns PDF bytes if found, else None.
    """
    pub_id = re.sub(r"\s+", "", f"{jurisdiction}{doc_number}")
    if not pub_id:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ProjectAether/1.0)",
        "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
    }
    page_url = f"https://patents.google.com/patent/{pub_id}/en"
    with httpx.Client(follow_redirects=True, timeout=20.0, headers=headers) as client:
        page_resp = client.get(page_url)
        if page_resp.status_code != 200:
            return None

        html_text = page_resp.text
        pdf_url: str | None = None

        meta_match = re.search(
            r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
            html_text,
            re.IGNORECASE,
        )
        if not meta_match:
            meta_match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
                html_text,
                re.IGNORECASE,
            )
        if meta_match:
            pdf_url = meta_match.group(1).strip()
        else:
            img_match = re.search(
                r'https://patentimages\.storage\.googleapis\.com/[^"\'\s<>]+\.pdf',
                html_text,
            )
            if img_match:
                pdf_url = img_match.group(0).strip()

        if not pdf_url:
            return None

        pdf_resp = client.get(pdf_url)
        if pdf_resp.status_code == 200 and pdf_resp.content.startswith(b"%PDF"):
            return pdf_resp.content
    return None


def generate_technical_brief(
    *,
    title: str,
    abstract: str,
    claims: str,
    jurisdiction: str,
    status_summary: str,
    classifications: list[str],
    output_language: str,
    api_key: str,
    description: str = "",
    pdf_bytes: bytes | None = None,
    model: str | None = None,
    thinking_level: str | None = None,
) -> str:
    """
    Generate a structured physicist's technical brief for an inspected patent
    in English or Hungarian, using the uploaded PDF (preferred) or full text.
    """
    config = get_config()
    chosen_model = model or config.llm_brief_model
    chosen_thinking = thinking_level or config.llm_brief_thinking_level

    system_prompt = (
        "You are a senior experimental physicist specializing in plasma physics, "
        "electrical discharges in hydrogen/water vapor, and LENR / anomalous heat claims. "
        f"Write a concise, rigorous technical brief in {output_language} using Markdown sections:\n"
        "1. **Apparatus & Materials** (electrodes, catalysts, working gas/liquid, geometry, key figures/schematics if PDF provided)\n"
        "2. **Operating Regime** (voltage, current, frequency/pulses, pressure, temperature)\n"
        "3. **Claimed Effect & Quantitative Evidence** (COP, excess heat, transmutation, radiation, experimental tables/graphs, or lack of data)\n"
        "4. **Noise vs. Signal Assessment** (is this conventional engineering or genuinely anomalous?)\n"
        "Do not invent parameters not present in the patent; state 'Not specified' when omitted."
    )

    if pdf_bytes:
        source_note = "Uploaded Full Patent PDF"
        user_prompt = (
            f"Analyze the attached full patent PDF.\n"
            f"Jurisdiction: {jurisdiction}\n"
            f"Legal Status: {status_summary}\n"
            f"IPC/CPC: {', '.join(classifications) or 'None'}\n"
            f"Title: {title}\n"
        )
        contents: Any = [
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            user_prompt,
        ]
    else:
        desc_excerpt = (description or "").strip()[:60000]
        claims_excerpt = (claims or "").strip()[:15000]
        if desc_excerpt and claims_excerpt:
            source_note = "Full Description + Claims"
        elif desc_excerpt:
            source_note = "Full Description + Abstract"
        elif claims_excerpt:
            source_note = "Abstract + Claims"
        else:
            source_note = "Abstract Only (full text unavailable from API)"

        contents = (
            f"Jurisdiction: {jurisdiction}\n"
            f"Legal Status: {status_summary}\n"
            f"IPC/CPC: {', '.join(classifications) or 'None'}\n\n"
            f"Title:\n{title}\n\n"
            f"Abstract:\n{abstract or 'Not available'}\n\n"
            f"Description:\n{desc_excerpt or 'Not available'}\n\n"
            f"Claims:\n{claims_excerpt or 'Not available'}"
        )

    response = generate_content(
        api_key=api_key,
        model=chosen_model,
        contents=contents,
        system_instruction=system_prompt,
        temperature=0.2,
        thinking_level=chosen_thinking,
    )
    body = (response.text or "").strip()
    return f"*Source analyzed: {source_note}*\n\n{body}"


def suggest_query_refinements(
    *,
    reviews: list[dict[str, Any]],
    active_include: list[list[str]],
    active_exclude: list[str],
    api_key: str,
    model: str | None = None,
    thinking_level: str | None = None,
) -> dict[str, Any]:
    """
    Analyze George's reviewed patents (high-scored vs low-scored noise) and propose
    concrete exclude terms and positive evasive-terminology synonyms.
    """
    config = get_config()
    chosen_model = model or config.llm_advisor_model
    chosen_thinking = thinking_level or config.llm_advisor_thinking_level

    low_items = [r for r in reviews if float(r.get("user_score", 50)) <= 30][:15]
    high_items = [r for r in reviews if float(r.get("user_score", 50)) >= 60][:15]

    payload = {
        "active_include_groups": active_include,
        "active_exclude_terms": active_exclude,
        "noise_examples": [
            {
                "title": r.get("title_en") or r.get("title"),
                "score": r.get("user_score"),
                "notes": r.get("notes"),
            }
            for r in low_items
        ],
        "relevant_examples": [
            {
                "title": r.get("title_en") or r.get("title"),
                "score": r.get("user_score"),
                "notes": r.get("notes"),
            }
            for r in high_items
        ],
    }

    system_prompt = (
        "You are a patent search strategist for anomalous hydrogen/plasma energy research. "
        "Inspect the noise examples (scored <=30) and relevant examples (scored >=60) along with "
        "the current keyword set. Propose:\n"
        "- `suggested_excludes`: short English phrases that filter out recurring noise clusters without harming relevant hits.\n"
        "- `suggested_include_synonyms`: optional new or expanded English synonym groups.\n"
        "- `summary`: 2-3 concise sentences explaining the pattern."
    )

    response = generate_content(
        api_key=api_key,
        model=chosen_model,
        contents=json.dumps(payload, ensure_ascii=False),
        system_instruction=system_prompt,
        temperature=0.3,
        thinking_level=chosen_thinking,
        response_schema=QueryRefinementSuggestions,
        response_mime_type="application/json",
    )

    text = (response.text or "{}").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {"suggested_excludes": [], "suggested_include_synonyms": [], "summary": text}
