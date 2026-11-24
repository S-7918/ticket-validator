from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from amc_ticket_guard.models import ServiceTicket

logger = logging.getLogger(__name__)


@dataclass
class RejectedRow:
    row_number: int
    raw_row: dict[str, Any]
    reasons: list[str]


@dataclass
class TicketIngestResult:
    valid_tickets: list[ServiceTicket] = field(default_factory=list)
    rejected_rows: list[RejectedRow] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return len(self.valid_tickets) + len(self.rejected_rows)


def load_tickets_from_csv(csv_path: str | Path) -> TicketIngestResult:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Ticket CSV not found: {path}")

    result = TicketIngestResult()
    logger.info("Starting AMC ticket ingestion from %s", path)

    with path.open(mode="r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV file is missing a header row.")

        for row_idx, row in enumerate(reader, start=2):
            try:
                ticket = ServiceTicket.model_validate(row)
                result.valid_tickets.append(ticket)
            except ValidationError as exc:
                reasons = [f"{err['loc']}: {err['msg']}" for err in exc.errors()]
                result.rejected_rows.append(
                    RejectedRow(row_number=row_idx, raw_row=dict(row), reasons=reasons)
                )
                logger.warning(
                    "Rejected invalid ticket at row %d (%s): %s",
                    row_idx,
                    row.get("ticket_id", "<missing>"),
                    "; ".join(reasons),
                )

    logger.info(
        "Completed ingestion: %d valid, %d rejected (total=%d)",
        len(result.valid_tickets),
        len(result.rejected_rows),
        result.total_processed,
    )
    return result
