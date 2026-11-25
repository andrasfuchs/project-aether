"""
SQLite-backed patent review store for George's 0-100 grades and notes,
plus few-shot calibration prompt generation and JSON export/import.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from project_aether.core.config import get_config


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def get_reviews_db_path() -> Path:
    return get_config().database_path


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_reviews_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS patent_reviews (
            record_id TEXT PRIMARY KEY,
            doc_number TEXT NOT NULL DEFAULT '',
            jurisdiction TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            title_en TEXT NOT NULL DEFAULT '',
            abstract TEXT NOT NULL DEFAULT '',
            provider_name TEXT NOT NULL DEFAULT '',
            provider_record_url TEXT,
            llm_score REAL,
            user_score REAL NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            use_for_calibration INTEGER NOT NULL DEFAULT 1,
            reviewed_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def save_review(
    *,
    record_id: str,
    user_score: float,
    notes: str = "",
    doc_number: str = "",
    jurisdiction: str = "",
    title: str = "",
    title_en: str = "",
    abstract: str = "",
    provider_name: str = "",
    provider_record_url: str | None = None,
    llm_score: float | None = None,
    use_for_calibration: bool = True,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Insert or update George's 0-100 review grade and notes for a patent."""
    rid = (record_id or "").strip()
    if not rid:
        raise ValueError("record_id is required to save a review.")

    clamped_score = max(0.0, min(100.0, float(user_score)))
    now = _utc_now()

    with _connect(db_path) as conn:
        existing = conn.execute(
            "SELECT reviewed_at FROM patent_reviews WHERE record_id = ?", (rid,)
        ).fetchone()
        reviewed_at = existing["reviewed_at"] if existing else now

        conn.execute(
            """
            INSERT INTO patent_reviews (
                record_id, doc_number, jurisdiction, title, title_en, abstract,
                provider_name, provider_record_url, llm_score, user_score,
                notes, use_for_calibration, reviewed_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(record_id) DO UPDATE SET
                doc_number = COALESCE(NULLIF(excluded.doc_number, ''), patent_reviews.doc_number),
                jurisdiction = COALESCE(NULLIF(excluded.jurisdiction, ''), patent_reviews.jurisdiction),
                title = COALESCE(NULLIF(excluded.title, ''), patent_reviews.title),
                title_en = COALESCE(NULLIF(excluded.title_en, ''), patent_reviews.title_en),
                abstract = COALESCE(NULLIF(excluded.abstract, ''), patent_reviews.abstract),
                provider_name = COALESCE(NULLIF(excluded.provider_name, ''), patent_reviews.provider_name),
                provider_record_url = COALESCE(excluded.provider_record_url, patent_reviews.provider_record_url),
                llm_score = COALESCE(excluded.llm_score, patent_reviews.llm_score),
                user_score = excluded.user_score,
                notes = excluded.notes,
                use_for_calibration = excluded.use_for_calibration,
                updated_at = excluded.updated_at;
            """,
            (
                rid,
                doc_number or "",
                jurisdiction or "",
                title or "",
                title_en or "",
                abstract or "",
                provider_name or "",
                provider_record_url,
                llm_score,
                clamped_score,
                (notes or "").strip(),
                1 if use_for_calibration else 0,
                reviewed_at,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM patent_reviews WHERE record_id = ?", (rid,)
        ).fetchone()
        return dict(row) if row else {}


def get_review(record_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    rid = (record_id or "").strip()
    if not rid:
        return None
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM patent_reviews WHERE record_id = ?", (rid,)
        ).fetchone()
        return dict(row) if row else None


def get_reviews_map(
    record_ids: Iterable[str] | None = None,
    db_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    with _connect(db_path) as conn:
        if record_ids is None:
            rows = conn.execute("SELECT * FROM patent_reviews").fetchall()
        else:
            ids = [str(r).strip() for r in record_ids if str(r).strip()]
            if not ids:
                return {}
            placeholders = ",".join("?" for _ in ids)
            rows = conn.execute(
                f"SELECT * FROM patent_reviews WHERE record_id IN ({placeholders})",
                ids,
            ).fetchall()
        return {row["record_id"]: dict(row) for row in rows}


def list_reviews(
    *,
    min_score: float | None = None,
    max_score: float | None = None,
    search_text: str = "",
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM patent_reviews WHERE 1=1"
    params: list[Any] = []

    if min_score is not None:
        query += " AND user_score >= ?"
        params.append(float(min_score))
    if max_score is not None:
        query += " AND user_score <= ?"
        params.append(float(max_score))
    if search_text and search_text.strip():
        like = f"%{search_text.strip()}%"
        query += " AND (record_id LIKE ? OR doc_number LIKE ? OR title LIKE ? OR title_en LIKE ? OR notes LIKE ?)"
        params.extend([like, like, like, like, like])

    query += " ORDER BY updated_at DESC"
    with _connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def delete_review(record_id: str, db_path: Path | None = None) -> bool:
    rid = (record_id or "").strip()
    if not rid:
        return False
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM patent_reviews WHERE record_id = ?", (rid,))
        conn.commit()
        return cur.rowcount > 0


def build_calibration_prompt_block(
    db_path: Path | None = None,
    max_positive: int = 6,
    max_negative: int = 6,
) -> str:
    """
    Build a deterministic few-shot calibration block from George's reviewed patents.
    """
    with _connect(db_path) as conn:
        positives = conn.execute(
            """
            SELECT record_id, title, title_en, abstract, user_score, notes
            FROM patent_reviews
            WHERE use_for_calibration = 1 AND user_score >= 60
            ORDER BY user_score DESC, updated_at DESC, record_id ASC
            LIMIT ?
            """,
            (max_positive,),
        ).fetchall()
        negatives = conn.execute(
            """
            SELECT record_id, title, title_en, abstract, user_score, notes
            FROM patent_reviews
            WHERE use_for_calibration = 1 AND user_score <= 30
            ORDER BY user_score ASC, updated_at DESC, record_id ASC
            LIMIT ?
            """,
            (max_negative,),
        ).fetchall()

    if not positives and not negatives:
        return ""

    lines = [
        "Human expert calibration examples (use these to align your 0-100 scoring):"
    ]
    for row in list(positives) + list(negatives):
        display_title = (row["title_en"] or row["title"] or "Untitled").strip()
        snippet = (row["abstract"] or "").strip().replace("\n", " ")[:220]
        note = (row["notes"] or "").strip()
        note_part = f" | Reviewer note: {note}" if note else ""
        lines.append(
            f"- Score {row['user_score']:.0f}/100 | Title: {display_title} | "
            f"Abstract: {snippet}{note_part}"
        )
    return "\n".join(lines) + "\n"


def export_reviews_json(db_path: Path | None = None) -> str:
    """Export all reviews as formatted JSON for backup or sharing."""
    reviews = list_reviews(db_path=db_path)
    return json.dumps(reviews, indent=2, ensure_ascii=False)


def import_reviews_json(raw_json: str, db_path: Path | None = None) -> int:
    """Import reviews from a JSON array string. Returns number of imported rows."""
    items = json.loads(raw_json)
    if not isinstance(items, list):
        raise TypeError("Expected a JSON array of review objects.")
    imported = 0
    for item in items:
        if not isinstance(item, dict) or not item.get("record_id"):
            continue
        save_review(
            record_id=str(item["record_id"]),
            user_score=float(item.get("user_score", 0.0)),
            notes=str(item.get("notes") or ""),
            doc_number=str(item.get("doc_number") or ""),
            jurisdiction=str(item.get("jurisdiction") or ""),
            title=str(item.get("title") or ""),
            title_en=str(item.get("title_en") or ""),
            abstract=str(item.get("abstract") or ""),
            provider_name=str(item.get("provider_name") or ""),
            provider_record_url=item.get("provider_record_url"),
            llm_score=item.get("llm_score"),
            use_for_calibration=bool(item.get("use_for_calibration", True)),
            db_path=db_path,
        )
        imported += 1
    return imported
