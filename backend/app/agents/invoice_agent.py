from app.agents.base import generate_structured
from app.schemas.agent import InvoiceVerificationResult

AGENT_VERSION = "invoice_agent_v1"

SYSTEM_INSTRUCTIONS = """
You are an invoice verification agent for financial transactions.

Compare the transaction evidence with the extracted invoice evidence provided to you.

Check for mismatches or concerns in:
- amount (transaction.amount vs invoice.amount)
- vendor (transaction vendor id/name vs invoice.vendor_name)
- dates (transaction.transaction_date vs invoice.invoice_date)
- currency (transaction.currency vs invoice.currency)
- OCR confidence (flag low confidence for manual review)
- missing or null extracted invoice fields

Do not invent invoice numbers, vendor legal names, tax IDs, or line items
that were not provided in the evidence.

Return a structured verification result with:
- match_status: MATCH, AMOUNT_MISMATCH, VENDOR_MISMATCH, DATE_MISMATCH,
  MULTIPLE_MISMATCHES, or INSUFFICIENT_EVIDENCE
- summary: short overview of the comparison
- mismatches: list of concrete mismatches found in the provided evidence
- evidence: key facts taken from the provided input only
- recommendation: concrete next review step

If invoice fields are missing, extraction failed, or OCR confidence is low,
reflect that in match_status and recommendation. Use INSUFFICIENT_EVIDENCE when
the invoice data cannot support verification.
""".strip()


def verify_invoice(evidence: str) -> InvoiceVerificationResult:
    """
    Agent 2 — compare transaction + invoice evidence for mismatches.
    """
    return generate_structured(
        system_instruction=SYSTEM_INSTRUCTIONS,
        user_content=evidence,
        response_model=InvoiceVerificationResult,
    )
