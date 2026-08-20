from decimal import Decimal


def _norm_name(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, Decimal):
        return f"{float(value):,.2f}"
    return str(value)


def compute_field_comparisons(
    *,
    transaction_amount: Decimal,
    transaction_currency: str,
    transaction_date,
    transaction_vendor_name: str | None,
    invoice_amount: Decimal | None,
    invoice_currency: str | None,
    invoice_date,
    invoice_vendor_name: str | None,
) -> list[dict]:
    """
    Deterministic field-level MATCH / MISMATCH / MISSING comparisons.
    """
    comparisons: list[dict] = []

    # Vendor
    txn_vendor = transaction_vendor_name
    inv_vendor = invoice_vendor_name
    if not inv_vendor:
        vendor_status = "MISSING"
    elif not txn_vendor:
        vendor_status = "MISSING"
    else:
        a = _norm_name(txn_vendor)
        b = _norm_name(inv_vendor)
        vendor_status = "MATCH" if (a == b or a in b or b in a) else "MISMATCH"
    comparisons.append(
        {
            "field": "vendor",
            "label": "Vendor",
            "transaction_value": txn_vendor or "—",
            "invoice_value": inv_vendor or "—",
            "status": vendor_status,
        }
    )

    # Amount
    if invoice_amount is None:
        amount_status = "MISSING"
        detail = None
    else:
        diff = abs(float(transaction_amount) - float(invoice_amount))
        amount_status = "MATCH" if diff < 0.01 else "MISMATCH"
        detail = None if amount_status == "MATCH" else f"Difference: {diff:,.2f}"
    comparisons.append(
        {
            "field": "amount",
            "label": "Amount",
            "transaction_value": _fmt(transaction_amount),
            "invoice_value": _fmt(invoice_amount),
            "status": amount_status,
            "detail": detail,
        }
    )

    # Currency
    txn_cur = (transaction_currency or "").upper()
    inv_cur = (invoice_currency or "").upper() if invoice_currency else None
    if not inv_cur:
        currency_status = "MISSING"
    else:
        currency_status = "MATCH" if txn_cur == inv_cur else "MISMATCH"
    comparisons.append(
        {
            "field": "currency",
            "label": "Currency",
            "transaction_value": txn_cur or "—",
            "invoice_value": inv_cur or "—",
            "status": currency_status,
        }
    )

    # Invoice date vs transaction date
    if invoice_date is None:
        date_status = "MISSING"
    else:
        date_status = "MATCH" if str(transaction_date) == str(invoice_date) else "MISMATCH"
    comparisons.append(
        {
            "field": "invoice_date",
            "label": "Invoice date",
            "transaction_value": str(transaction_date) if transaction_date else "—",
            "invoice_value": str(invoice_date) if invoice_date else "—",
            "status": date_status,
        }
    )

    return comparisons


def derive_match_status(field_comparisons: list[dict]) -> str:
    statuses = {item["status"] for item in field_comparisons}
    mismatch_fields = {
        item["field"]
        for item in field_comparisons
        if item["status"] == "MISMATCH"
    }

    if "MISSING" in statuses and not mismatch_fields:
        return "INSUFFICIENT_EVIDENCE"
    if not mismatch_fields:
        return "MATCH"
    if mismatch_fields == {"amount"}:
        return "AMOUNT_MISMATCH"
    if mismatch_fields == {"vendor"}:
        return "VENDOR_MISMATCH"
    if mismatch_fields == {"invoice_date"}:
        return "DATE_MISMATCH"
    return "MULTIPLE_MISMATCHES"


def mismatches_from_comparisons(field_comparisons: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in field_comparisons:
        if item["status"] == "MISMATCH":
            detail = item.get("detail")
            if detail:
                lines.append(f"{item['label']}: {detail}")
            else:
                lines.append(
                    f"{item['label']}: transaction={item['transaction_value']} "
                    f"vs invoice={item['invoice_value']}"
                )
        elif item["status"] == "MISSING":
            lines.append(f"{item['label']}: missing on invoice")
    return lines
