"""Extraction schema for Support Ticket documents."""

from pydantic import Field

from schemas.common import StrictBase


class TicketMetadata(StrictBase):
    ticket_id: str | None = None
    submitted_by: str | None = None
    submitted_date: str | None = None
    priority: str | None = None
    category: str | None = None
    affected_system: str | None = None
    assigned_to: str | None = None
    current_status: str | None = None


class TicketIssueDetails(StrictBase):
    description: str | None = Field(
        default=None,
        description="Issue description synthesized from the description, steps, and context sections",
    )


class TicketResolution(StrictBase):
    root_cause: str | None = None
    resolved_by: str | None = None
    resolution_time: str | None = None
    resolution_notes: str | None = None


class TicketFields(StrictBase):
    ticket_metadata: TicketMetadata = Field(default_factory=TicketMetadata)
    issue_details: TicketIssueDetails = Field(default_factory=TicketIssueDetails)
    resolution: TicketResolution = Field(default_factory=TicketResolution)
