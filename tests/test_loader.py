from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pytest

from amc_ticket_guard.loader import load_tickets_from_csv
from amc_ticket_guard.models import ServiceTicket

SAMPLE_CSV_PATH = Path(__file__).parent / "data" / "sample_tickets.csv"


def test_valid_tickets_parsed_and_normalized() -> None:
    """Valid rows should deserialize into typed ServiceTicket models with uppercase IDs."""
    result = load_tickets_from_csv(SAMPLE_CSV_PATH)

    assert len(result.valid_tickets) == 3
    first = result.valid_tickets[0]
    assert isinstance(first, ServiceTicket)
    assert first.ticket_id == "TKT-1001"
    assert first.contract_id == "AMC-2026-01"
    assert first.asset_serial == "SRV-9821"
    assert first.severity == "P1"
    assert first.status == "RESOLVED"
    assert first.created_at == datetime(2026, 11, 20, 9, 15, 0)
    assert first.sla_hours == 4
    assert first.resolution_hours == 3.5


def test_invalid_rows_are_quarantined_without_crashing() -> None:
    """Corrupt rows should be isolated in rejected_rows with exact CSV line numbers."""
    result = load_tickets_from_csv(SAMPLE_CSV_PATH)

    assert result.total_processed == 5
    assert len(result.rejected_rows) == 2

    assert result.rejected_rows[0].row_number == 5
    assert result.rejected_rows[0].raw_row["ticket_id"] == "tkt-1004"
    assert any("severity" in reason for reason in result.rejected_rows[0].reasons)
    assert any("sla_hours" in reason for reason in result.rejected_rows[0].reasons)

    assert result.rejected_rows[1].row_number == 6
    assert result.rejected_rows[1].raw_row["ticket_id"] == "tkt-1005"


def test_invalid_status_or_timestamp_rejected(tmp_path: Path) -> None:
    """Unsupported status literals or malformed ISO timestamps must fail validation."""
    csv_file = tmp_path / "bad_status_time.csv"
    csv_file.write_text(
        "ticket_id,contract_id,asset_serial,severity,status,created_at,sla_hours,resolution_hours\n"
        "TKT-2001,AMC-01,ASSET-1,P2,CLOSED,2026-11-24T10:00:00,12,2.0\n"
        "TKT-2002,AMC-01,ASSET-2,P2,OPEN,24-11-2026 99:99,12,\n",
        encoding="utf-8",
    )

    result = load_tickets_from_csv(csv_file)

    assert len(result.valid_tickets) == 0
    assert len(result.rejected_rows) == 2
    assert any("status" in r for r in result.rejected_rows[0].reasons)
    assert any("created_at" in r for r in result.rejected_rows[1].reasons)


def test_missing_csv_raises_file_not_found(tmp_path: Path) -> None:
    """Passing a non-existent CSV path should raise FileNotFoundError immediately."""
    missing_path = tmp_path / "does_not_exist.csv"

    with pytest.raises(FileNotFoundError, match="Ticket CSV not found"):
        load_tickets_from_csv(missing_path)


def test_logs_ingestion_summary_and_warnings(caplog: pytest.LogCaptureFixture) -> None:
    """Loader should emit warning logs for rejected rows and an info summary at completion."""
    with caplog.at_level(logging.INFO, logger="amc_ticket_guard.loader"):
        load_tickets_from_csv(SAMPLE_CSV_PATH)

    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]

    assert len(warning_messages) == 2
    assert "row 5" in warning_messages[0]
    assert "row 6" in warning_messages[1]
    assert any("Completed ingestion: 3 valid, 2 rejected (total=5)" in msg for msg in info_messages)
