from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

TicketStatus = Literal["OPEN", "IN_PROGRESS", "RESOLVED", "BREACHED"]
SeverityLevel = Literal["P1", "P2", "P3", "P4"]


class ServiceTicket(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ticket_id: str = Field(min_length=3, max_length=32)
    contract_id: str = Field(min_length=3, max_length=32)
    asset_serial: str = Field(min_length=2, max_length=64)
    severity: SeverityLevel
    status: TicketStatus
    created_at: datetime
    sla_hours: int = Field(gt=0, le=720)
    resolution_hours: float | None = Field(default=None, ge=0.0)

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings_and_empty_resolution(cls, value: object, info) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if info.field_name == "resolution_hours" and stripped == "":
                return None
            return stripped
        return value

    @field_validator("ticket_id", "contract_id")
    @classmethod
    def uppercase_ids(cls, value: str) -> str:
        return value.upper()
