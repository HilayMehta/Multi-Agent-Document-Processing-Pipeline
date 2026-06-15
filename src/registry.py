"""Registry mapping document_type -> (schema, prompt). Routing is code, not LLM.

Prompts live in prompts.py; the Pydantic schemas live in schemas/. This file only wires them.
"""

from dataclasses import dataclass

from pydantic import BaseModel

from prompts import CONTRACT_PROMPT, INVOICE_PROMPT, SOW_PROMPT, TICKET_PROMPT
from schemas.invoice import InvoiceFields
from schemas.statement_of_work import SOWFields
from schemas.support_ticket import TicketFields
from schemas.vendor_contract import ContractFields


@dataclass(frozen=True)
class ExtractorConfig:
    """One extraction configuration: a closed schema plus its prompt."""

    schema: type[BaseModel]
    prompt: str


EXTRACTORS: dict[str, ExtractorConfig] = {
    "Vendor Contract": ExtractorConfig(ContractFields, CONTRACT_PROMPT),
    "Support Ticket": ExtractorConfig(TicketFields, TICKET_PROMPT),
    "Statement of Work": ExtractorConfig(SOWFields, SOW_PROMPT),
    "Invoice": ExtractorConfig(InvoiceFields, INVOICE_PROMPT),
}
