from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .models import EnquiryAnalysis
from .privacy import redact_pii


SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enquiry_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    category TEXT NOT NULL,
    completeness_score INTEGER NOT NULL,
    confidence_score REAL NOT NULL,
    review_status TEXT NOT NULL,
    staff_decision TEXT NOT NULL,
    selected_sku TEXT,
    staff_notes TEXT,
    original_message_redacted TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    response_draft TEXT NOT NULL
)
"""


def initialise_database(database_path: str | Path) -> Path:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(SCHEMA)
        connection.commit()
    return path


def log_outcome(
    database_path: str | Path,
    analysis: EnquiryAnalysis,
    original_message: str,
    response_draft: str,
    staff_decision: str,
    selected_sku: str | None,
    staff_notes: str,
) -> int:
    path = initialise_database(database_path)
    with sqlite3.connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO audit_log (
                enquiry_id, created_at, category, completeness_score, confidence_score,
                review_status, staff_decision, selected_sku, staff_notes,
                original_message_redacted, analysis_json, response_draft
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis.enquiry_id,
                datetime.now(timezone.utc).isoformat(),
                analysis.enquiry_category.value,
                analysis.information_completeness_score,
                analysis.confidence_score,
                analysis.human_review_status.value,
                staff_decision,
                selected_sku or None,
                redact_pii(staff_notes),
                redact_pii(original_message),
                json.dumps(analysis.as_json_dict(), ensure_ascii=False),
                redact_pii(response_draft),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def recent_audit_entries(database_path: str | Path, limit: int = 100) -> pd.DataFrame:
    path = initialise_database(database_path)
    with sqlite3.connect(path) as connection:
        return pd.read_sql_query(
            """
            SELECT created_at, enquiry_id, category, completeness_score,
                   ROUND(confidence_score * 100, 0) AS confidence_percent,
                   staff_decision, selected_sku, staff_notes
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            connection,
            params=(limit,),
        )

