"""
Independent smoke tests for Agents 2 and 3 (no DB required).

    python -m app.scripts.test_invoice_agent
    python -m app.scripts.test_review_agent
"""

from app.agents.invoice_agent import verify_invoice
from app.agents.review_agent import review_transaction


SAMPLE_INVOICE_EVIDENCE = """
Transaction:
- Transaction ID: 3028
- Amount: €107,199.73
- Vendor ID: 41
- Transaction date: 2026-08-19

Invoice:
- Invoice number: INV-10028
- Billed vendor ID: 41
- Invoice amount: €97,199.73
- Invoice date: 2026-08-18
""".strip()


SAMPLE_REVIEW_EVIDENCE = """
Agent 1 — Transaction Analysis:
{
  "risk_level": "HIGH",
  "summary": "Transaction amount is far above historical vendor and category norms.",
  "findings": [
    "Amount is many times the vendor historical average.",
    "Amount is many times the category historical average."
  ],
  "evidence": [
    "Amount €107,199.73",
    "Anomaly score -0.196859",
    "Status HIGH"
  ],
  "recommendation": "Escalate for manual finance review."
}

Agent 2 — Invoice Verification:
{
  "match_status": "AMOUNT_MISMATCH",
  "summary": "Invoice amount does not match the transaction amount.",
  "mismatches": [
    "Transaction amount €107,199.73 vs invoice amount €97,199.73"
  ],
  "evidence": [
    "Transaction vendor ID 41",
    "Invoice vendor ID 41",
    "Transaction date 2026-08-19",
    "Invoice date 2026-08-18"
  ],
  "recommendation": "Request corrected invoice or payment explanation before approval."
}
""".strip()


def main() -> None:
    print("=== Agent 2: Invoice Verification ===\n")
    invoice_result = verify_invoice(SAMPLE_INVOICE_EVIDENCE)
    print(invoice_result.model_dump_json(indent=2))

    print("\n=== Agent 3: Financial Review ===\n")
    review_result = review_transaction(SAMPLE_REVIEW_EVIDENCE)
    print(review_result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
