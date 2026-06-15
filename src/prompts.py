"""Extraction prompts — the shared preamble plus one prompt per document type.

This is the single place to read/tune what the extractor is told to pull from each file type.
The per-stage prompts (classify / tag / summarize) live with their agents in agents/.
The document_type -> (schema, prompt) wiring lives in registry.py.
"""

EXTRACTION_PREAMBLE = """\
You are a precise document data extractor. Populate the provided schema from the document.

Rules:
- Dates: normalize to ISO format YYYY-MM-DD.
- Currency and numbers: copy EXACTLY as written in the document. Keep the ₹ symbol, keep
  Indian digit grouping (₹40,00,000 stays ₹40,00,000, NOT ₹4,000,000), keep styles like
  "$120,000 USD/year".
- If a value is genuinely absent from the document, leave the field null. Never guess.
- You may synthesize a value from multiple sections of the document, and repair obvious
  text-extraction artifacts (e.g. an email address broken across lines).
"""

CONTRACT_PROMPT = """\
The document is a vendor contract / master services agreement.
- parties: the legal entity names of all contracting parties.
- contract_value: the headline contract value — the total or recurring fee that defines the
  contract's worth, with its period or unit if stated. Capture this whenever a fee appears;
  keep it distinct from the detailed payment schedule.
- payment_terms: the full payment arrangement as written — billing schedule/cadence, net
  payment terms, and any late-payment penalty. Include every part even if the headline amount
  also appears in contract_value.
- auto_renewal: the renewal behaviour as written, or null if it does not auto-renew.
- auto_renewal_notice_period: the advance notice a party must give to PREVENT automatic
  renewal. Distinct from the termination notice periods.
- liability_cap: the cap as described in the limitation-of-liability clause.
"""


TICKET_PROMPT = """\
The document is an IT support / incident ticket.
- issue_details.description: synthesize 2-4 sentences from the issue description, steps to
  reproduce, and additional context sections: who is affected, since when, the exact error,
  and the suspected cause.
- priority: the priority level as a single word (e.g. Critical/High/Medium/Low). Strip any
  stray leading glyph or icon character the PDF extraction may have attached to it.
- submitted_by / resolved_by: "Full Name (email)" — repair emails broken across lines.
- resolution fields: from the resolution notes section.
"""


SOW_PROMPT = """\
The document is a statement of work.
- deliverables: summarize the scope at the section level — produce ONE deliverable per
  numbered scope subsection (e.g. 2.1, 2.2, ...), consolidating that subsection's bullet
  points into a single capability statement that includes its key spec (supported formats,
  accuracy target, named integrations). Do not emit a separate item for every bullet.
- payment_milestones: from the milestone table. milestone = the label in the first column
  (e.g. "Milestone 1"); name = a short title for the deliverable (a few words, title case);
  amount and due_date from their columns. Do not include the total row as a milestone.
- key_contacts: role = side + function (e.g. "Client — Exec Sponsor", "Vendor — Technical
  Lead"); include each person's email.
"""

INVOICE_PROMPT = """\
The document is an invoice.
- line_items: one entry per table row; quantity/unit_price/amount exactly as written.
- reference_sow: the SOW number this invoice bills against.
- totals: subtotal, GST rate and amount, and total due exactly as written.
- payment_instructions: bank, account name/number, IFSC, and UPI/email from the payment
  instructions section.
"""
