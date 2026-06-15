"""Extraction schema for Vendor Contract documents."""

from pydantic import Field

from schemas.common import StrictBase


class ContractParties(StrictBase):
    parties: list[str] | None = None
    effective_date: str | None = None
    expiry_date: str | None = None


class ContractCommercial(StrictBase):
    contract_value: str | None = None
    payment_terms: str | None = None


class ContractRenewal(StrictBase):
    auto_renewal: str | None = Field(
        default=None,
        description='Renewal behaviour as stated, e.g. "Yes — auto-renews for successive 1-year terms"',
    )
    auto_renewal_notice_period: str | None = None
    termination_notice_convenience: str | None = None
    termination_notice_cause: str | None = None


class ContractLegal(StrictBase):
    governing_law: str | None = None
    dispute_resolution: str | None = None
    liability_cap: str | None = None


class ContractFields(StrictBase):
    parties_and_dates: ContractParties = Field(default_factory=ContractParties)
    commercial_terms: ContractCommercial = Field(default_factory=ContractCommercial)
    renewal_and_termination: ContractRenewal = Field(default_factory=ContractRenewal)
    legal: ContractLegal = Field(default_factory=ContractLegal)
