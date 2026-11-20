import sqlite3

from src.audit import log_outcome
from src.extraction import extract_enquiry


def test_audit_log_redacts_common_contact_details(tmp_path):
    database = tmp_path / "audit.db"
    message = "My AquaVale tap drips. Email test.person@example.com or call 07700 900123. Photo attached."
    analysis = extract_enquiry(message, False, ["AquaVale"], enquiry_id="ENQ-TEST2001")

    record_id = log_outcome(
        database,
        analysis,
        message,
        "We will reply to test.person@example.com after review.",
        "Escalate for specialist review",
        None,
        "Caller 07700 900123 asked for help.",
    )

    assert record_id == 1
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT original_message_redacted, response_draft, staff_notes FROM audit_log WHERE id = 1"
        ).fetchone()
    combined = " ".join(row)
    assert "test.person@example.com" not in combined
    assert "07700 900123" not in combined
    assert "[EMAIL REDACTED]" in combined
    assert "[PHONE REDACTED]" in combined

