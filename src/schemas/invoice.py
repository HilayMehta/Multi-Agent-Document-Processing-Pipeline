"""Extraction schema for Invoice documents."""

from pydantic import Field

from schemas.common import StrictBase


class InvoiceLineItem(StrictBase):
    description: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    amount: str | None = None


class InvoiceTotals(StrictBase):
    subtotal: str | None = None
    gst_rate: str | None = Field(default=None, description='e.g. "18%"')
    gst_amount: str | None = None
    total_due: str | None = None


class InvoicePayment(StrictBase):
    bank: str | None = None
    account_name: str | None = None
    account_number: str | None = None
    ifsc_code: str | None = None
    upi_or_email: str | None = None


class InvoiceFields(StrictBase):
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    payment_terms: str | None = None
    reference_sow: str | None = None
    vendor: str | None = None
    client: str | None = None
    line_items: list[InvoiceLineItem] | None = None
    totals: InvoiceTotals = Field(default_factory=InvoiceTotals)
    payment_instructions: InvoicePayment = Field(default_factory=InvoicePayment)
