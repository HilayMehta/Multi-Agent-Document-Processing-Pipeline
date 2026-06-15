"""Extraction schema for Statement of Work documents."""

from pydantic import Field

from schemas.common import StrictBase


class SOWMilestone(StrictBase):
    milestone: str | None = Field(default=None, description='Label, e.g. "Milestone 1"')
    name: str | None = Field(
        default=None, description="Short title for the milestone deliverable"
    )
    amount: str | None = None
    due_date: str | None = None


class SOWContact(StrictBase):
    role: str | None = Field(default=None, description='e.g. "Client — Exec Sponsor"')
    name: str | None = None
    email: str | None = None


class SOWFields(StrictBase):
    project_name: str | None = None
    sow_number: str | None = None
    client: str | None = None
    vendor: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    total_budget: str | None = None
    deliverables: list[str] | None = None
    payment_milestones: list[SOWMilestone] | None = None
    key_contacts: list[SOWContact] | None = None
