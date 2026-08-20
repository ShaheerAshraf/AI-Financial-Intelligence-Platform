import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useAsyncData } from "../hooks/useAsyncData";
import {
  getInvestigation,
  upsertTransactionInvoice,
  verifyTransactionInvoice,
  runTransactionWorkflow,
  submitHumanDecision,
} from "../lib/api";
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  parseReasons,
  riskBadgeTone,
} from "../lib/format";
import type { FieldComparisonItem, HumanDecision, WorkflowRunResponse } from "../types/api";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { PipelineCard } from "../components/ui/PipelineCard";

function fieldTone(status: string): "match" | "mismatch" | "warning" | "neutral" {
  const upper = status.toUpperCase();
  if (upper === "MATCH") return "match";
  if (upper === "MISMATCH") return "mismatch";
  if (upper === "MISSING") return "warning";
  return "neutral";
}

function FieldComparisonTable({ items }: { items: FieldComparisonItem[] }) {
  if (items.length === 0) return null;
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Field</th>
            <th scope="col">Transaction</th>
            <th scope="col">Invoice</th>
            <th scope="col">Result</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.field}>
              <td>{item.label}</td>
              <td>{item.transaction_value}</td>
              <td>{item.invoice_value}</td>
              <td>
                <Badge label={item.status} tone={fieldTone(item.status)} />
                {item.detail ? <p className="muted">{item.detail}</p> : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function InvestigationPage() {
  const { transactionId } = useParams();
  const id = Number(transactionId);
  const validId = Number.isFinite(id) && id > 0;

  const { data, loading, error, status, reload } = useAsyncData(
    () => getInvestigation(id),
    [id],
    { enabled: validId },
  );

  const [reviewedBy, setReviewedBy] = useState("Finance Analyst");
  const [comment, setComment] = useState("");
  const [selectedDecision, setSelectedDecision] = useState<HumanDecision>("APPROVED");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [workflowResult, setWorkflowResult] = useState<WorkflowRunResponse | null>(null);
  const [workflowError, setWorkflowError] = useState<string | null>(null);

  const [showInvoiceForm, setShowInvoiceForm] = useState(false);
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceVendor, setInvoiceVendor] = useState("");
  const [invoiceAmount, setInvoiceAmount] = useState("");
  const [invoiceCurrency, setInvoiceCurrency] = useState("EUR");
  const [invoiceDate, setInvoiceDate] = useState("");
  const [invoiceOcr, setInvoiceOcr] = useState("");
  const [invoiceBusy, setInvoiceBusy] = useState(false);
  const [verifyBusy, setVerifyBusy] = useState(false);
  const [invoiceMessage, setInvoiceMessage] = useState<string | null>(null);

  async function handleAnalyze() {
    if (!validId) return;
    setAnalyzing(true);
    setWorkflowError(null);
    try {
      const result = await runTransactionWorkflow(id);
      setWorkflowResult(result);
      if (result.workflow_status === "FAILED") {
        setWorkflowError(result.error ?? "Analysis failed.");
      } else {
        reload();
      }
    } catch (err) {
      setWorkflowError(err instanceof Error ? err.message : "Analysis request failed.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleInvoiceSave(event: FormEvent) {
    event.preventDefault();
    if (!validId) return;
    setInvoiceBusy(true);
    setInvoiceMessage(null);
    try {
      const result = await upsertTransactionInvoice(id, {
        raw_ocr_text: invoiceOcr || undefined,
        run_extraction: Boolean(invoiceOcr) && !invoiceAmount,
        invoice_number: invoiceNumber || undefined,
        vendor_name: invoiceVendor || undefined,
        amount: invoiceAmount ? Number(invoiceAmount) : undefined,
        currency: invoiceCurrency || undefined,
        invoice_date: invoiceDate || undefined,
      });
      setInvoiceMessage(
        `Invoice saved${result.invoice.invoice_number ? ` (#${result.invoice.invoice_number})` : ""}. Extraction: ${result.invoice.extraction_status}`,
      );
      setShowInvoiceForm(false);
      reload();
    } catch (err) {
      setInvoiceMessage(err instanceof Error ? err.message : "Failed to save invoice");
    } finally {
      setInvoiceBusy(false);
    }
  }

  async function handleVerifyInvoice() {
    if (!validId) return;
    setVerifyBusy(true);
    setInvoiceMessage(null);
    try {
      const result = await verifyTransactionInvoice(id);
      setInvoiceMessage(`Verification: ${result.match_status.replaceAll("_", " ")}`);
      reload();
    } catch (err) {
      setInvoiceMessage(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setVerifyBusy(false);
    }
  }

  async function handleDecisionSubmit(event: FormEvent) {
    event.preventDefault();
    if (!validId) return;
    if (!comment.trim()) {
      setSubmitError("Please add a comment for the audit trail.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      await submitHumanDecision(id, {
        decision: selectedDecision,
        reviewed_by: reviewedBy,
        comment: comment.trim(),
      });
      reload();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to submit decision.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!validId) {
    return (
      <div className="page">
        <ErrorAlert message="Invalid transaction in URL." />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page">
        <LoadingState label={`Loading transaction #${id}...`} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page">
        <ErrorAlert
          message={error ?? `Transaction #${id} not found`}
          status={status}
          onRetry={reload}
        />
      </div>
    );
  }

  const {
    transaction,
    anomaly,
    transaction_analysis,
    invoice,
    invoice_verification,
    financial_review,
  } = data;
  const reasons = parseReasons(anomaly?.reason);
  const heroRisk = financial_review?.risk_level ?? anomaly?.status ?? "UNKNOWN";
  const analysisStatus = transaction.analysis_status ?? "NEW";
  const fieldComparisons = invoice_verification?.field_comparisons ?? [];
  const verificationStatus = invoice_verification?.status;

  return (
    <div className="page investigation-page">
      <PageHeader
        title={`Transaction #${transaction.id}`}
        description={
          transaction.description ??
          "Unified AI analysis and human decision for this transaction."
        }
        actions={
          <>
            <button
              type="button"
              className="btn btn-primary"
              disabled={analyzing}
              onClick={handleAnalyze}
            >
              {analyzing
                ? "Analyzing..."
                : analysisStatus === "NEW"
                  ? "Run Analysis"
                  : "Re-run Analysis"}
            </button>
            <Link to="/transactions" className="btn btn-secondary">
              Back to transactions
            </Link>
          </>
        }
      />

      {workflowError ? <ErrorAlert message={workflowError} onRetry={handleAnalyze} /> : null}

      {workflowResult ? (
        <section className="panel workflow-log">
          <div className="panel-heading">
            <h2>Analysis progress</h2>
            <p className="muted">
              {workflowResult.workflow_status === "COMPLETED"
                ? "Analysis complete — review required"
                : workflowResult.workflow_status === "NORMAL"
                  ? "Analysis complete — no unusual activity"
                  : `Status: ${workflowResult.workflow_status}`}
            </p>
          </div>
          <ol className="workflow-steps">
            {workflowResult.steps.map((step) => (
              <li key={`${step.name}-${step.label}`}>
                <strong>
                  {step.status === "OK" || step.status === "SKIPPED" || step.status === "NOT_PROVIDED" || step.status === "MATCH"
                    ? "✓"
                    : step.status.includes("MISMATCH")
                      ? "✗"
                      : step.status === "RUNNING"
                        ? "⟳"
                        : "•"}{" "}
                  {step.label}
                </strong>
                {step.detail ? <p className="muted">{step.detail}</p> : null}
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <section className="investigation-hero">
        <div>
          <p className="hero-kicker">
            {transaction.company_name ?? "Financial investigation"}
          </p>
          <p className="hero-amount">
            {formatCurrency(transaction.amount, transaction.currency)}
          </p>
          <p className="hero-meta">
            {transaction.vendor_name ?? "Unknown vendor"} ·{" "}
            {transaction.category_name ?? "Uncategorized"} ·{" "}
            {formatDate(transaction.date)}
          </p>
        </div>
        <div className="hero-badges">
          <Badge label={`${heroRisk} RISK`} tone={riskBadgeTone(heroRisk)} />
          {financial_review ? (
            <Badge
              label={financial_review.decision.replaceAll("_", " ")}
              tone={riskBadgeTone(financial_review.decision)}
            />
          ) : null}
        </div>
      </section>

      <div className="pipeline-stack">
        <PipelineCard
          step={1}
          title="Anomaly Detection"
          subtitle="Compared against historical spending patterns"
          status={anomaly ? "complete" : "missing"}
        >
          {anomaly ? (
            <>
              <p>
                <Badge label={anomaly.status} tone={riskBadgeTone(anomaly.status)} />
              </p>
              {reasons.length > 0 ? (
                <>
                  <h3>Why?</h3>
                  <ul className="check-list">
                    {reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </>
              ) : anomaly.reason ? (
                <p>{anomaly.reason}</p>
              ) : (
                <p className="muted">No detailed reasons recorded.</p>
              )}
            </>
          ) : (
            <p className="muted">Run analysis to check this transaction for unusual patterns.</p>
          )}
        </PipelineCard>

        <PipelineCard
          step={2}
          title="Transaction Analysis"
          subtitle="AI assessment of risk and next steps"
          status={transaction_analysis ? "complete" : "missing"}
        >
          {transaction_analysis ? (
            <>
              <p>
                <strong>Risk:</strong>{" "}
                <Badge
                  label={transaction_analysis.risk_level}
                  tone={riskBadgeTone(transaction_analysis.risk_level)}
                />
              </p>
              <p>{transaction_analysis.summary}</p>
              {transaction_analysis.findings.length > 0 ? (
                <ul>
                  {transaction_analysis.findings.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
              <p>
                <strong>Recommendation:</strong> {transaction_analysis.recommendation}
              </p>
            </>
          ) : (
            <p className="muted">Available after analysis for flagged transactions.</p>
          )}
        </PipelineCard>

        <PipelineCard
          step={3}
          title="Invoice"
          subtitle="Optional — attach OCR or structured invoice data"
          status={invoice ? "complete" : "warning"}
        >
          {!invoice && !showInvoiceForm ? (
            <>
              <p className="muted">No invoice provided.</p>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setInvoiceVendor(transaction.vendor_name ?? "");
                  setInvoiceCurrency(transaction.currency || "EUR");
                  setShowInvoiceForm(true);
                }}
              >
                Add Invoice Data
              </button>
            </>
          ) : null}

          {showInvoiceForm ? (
            <form className="master-form invoice-upload" onSubmit={handleInvoiceSave}>
              <label>
                Invoice number
                <input
                  value={invoiceNumber}
                  onChange={(e) => setInvoiceNumber(e.target.value)}
                  placeholder="INV-2026-0192"
                />
              </label>
              <label>
                Vendor
                <input
                  value={invoiceVendor}
                  onChange={(e) => setInvoiceVendor(e.target.value)}
                  placeholder="Vendor name"
                />
              </label>
              <label>
                Amount
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={invoiceAmount}
                  onChange={(e) => setInvoiceAmount(e.target.value)}
                  placeholder="95000"
                />
              </label>
              <label>
                Currency
                <select
                  value={invoiceCurrency}
                  onChange={(e) => setInvoiceCurrency(e.target.value)}
                >
                  <option value="EUR">EUR</option>
                  <option value="USD">USD</option>
                  <option value="GBP">GBP</option>
                </select>
              </label>
              <label>
                Invoice date
                <input
                  type="date"
                  value={invoiceDate}
                  onChange={(e) => setInvoiceDate(e.target.value)}
                />
              </label>
              <label className="full-width">
                Raw OCR text (optional)
                <textarea
                  rows={3}
                  value={invoiceOcr}
                  onChange={(e) => setInvoiceOcr(e.target.value)}
                  placeholder="Paste OCR text if available. Structured fields above are enough for demos."
                />
              </label>
              <div className="action-row full-width">
                <button type="submit" className="btn btn-primary" disabled={invoiceBusy}>
                  {invoiceBusy ? "Saving..." : "Save Invoice"}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowInvoiceForm(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : null}

          {invoice ? (
            <>
              <dl className="detail-grid">
                <div>
                  <dt>Invoice number</dt>
                  <dd>{invoice.invoice_number ?? "—"}</dd>
                </div>
                <div>
                  <dt>Vendor</dt>
                  <dd>{invoice.vendor_name ?? "—"}</dd>
                </div>
                <div>
                  <dt>Amount</dt>
                  <dd>
                    {invoice.amount
                      ? formatCurrency(invoice.amount, invoice.currency ?? transaction.currency)
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt>Currency</dt>
                  <dd>{invoice.currency ?? "—"}</dd>
                </div>
                <div>
                  <dt>Invoice date</dt>
                  <dd>{invoice.invoice_date ? formatDate(invoice.invoice_date) : "—"}</dd>
                </div>
                <div>
                  <dt>OCR status</dt>
                  <dd>
                    <Badge
                      label={invoice.extraction_status ?? "PENDING"}
                      tone={riskBadgeTone(invoice.extraction_status)}
                    />
                  </dd>
                </div>
              </dl>

              <div className="action-row">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={verifyBusy}
                  onClick={handleVerifyInvoice}
                >
                  {verifyBusy ? "Verifying..." : "Verify Invoice"}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setInvoiceNumber(invoice.invoice_number ?? "");
                    setInvoiceVendor(invoice.vendor_name ?? "");
                    setInvoiceAmount(invoice.amount ?? "");
                    setInvoiceCurrency(invoice.currency ?? "EUR");
                    setInvoiceDate(invoice.invoice_date ?? "");
                    setShowInvoiceForm(true);
                  }}
                >
                  Edit Invoice Data
                </button>
              </div>
            </>
          ) : null}

          {invoiceMessage ? <p className="muted">{invoiceMessage}</p> : null}
        </PipelineCard>

        <PipelineCard
          step={4}
          title="Invoice Verification"
          subtitle="Vendor, amount, currency, and date comparison"
          status={
            verificationStatus === "NOT_PROVIDED"
              ? "warning"
              : verificationStatus && verificationStatus !== "PENDING"
                ? "complete"
                : "missing"
          }
        >
          {verificationStatus ? (
            <>
              <p>
                <Badge
                  label={verificationStatus.replaceAll("_", " ")}
                  tone={
                    verificationStatus === "MATCH"
                      ? "match"
                      : verificationStatus === "NOT_PROVIDED" || verificationStatus === "PENDING"
                        ? "warning"
                        : "mismatch"
                  }
                />
              </p>
              {invoice_verification?.amount_difference &&
              verificationStatus !== "MATCH" &&
              verificationStatus !== "NOT_PROVIDED" ? (
                <p>
                  Difference:{" "}
                  <strong>
                    {formatCurrency(
                      invoice_verification.amount_difference,
                      transaction.currency,
                    )}
                  </strong>
                </p>
              ) : null}
              <FieldComparisonTable items={fieldComparisons} />
              {invoice_verification?.summary ? (
                <p>{invoice_verification.summary}</p>
              ) : null}
              {invoice_verification?.recommendation ? (
                <p>
                  <strong>Recommendation:</strong> {invoice_verification.recommendation}
                </p>
              ) : null}
            </>
          ) : (
            <p className="muted">
              No verification yet. Attach an invoice and click Verify Invoice, or run full analysis.
            </p>
          )}
        </PipelineCard>

        <PipelineCard
          step={5}
          title="Final Financial Review"
          subtitle="Combined recommendation for finance"
          status={financial_review ? "complete" : "missing"}
        >
          {financial_review ? (
            <>
              <dl className="detail-grid">
                <div>
                  <dt>Risk level</dt>
                  <dd>
                    <Badge
                      label={financial_review.risk_level}
                      tone={riskBadgeTone(financial_review.risk_level)}
                    />
                  </dd>
                </div>
                <div>
                  <dt>Recommendation</dt>
                  <dd>{financial_review.decision.replaceAll("_", " ")}</dd>
                </div>
              </dl>
              <p>{financial_review.summary}</p>
              {financial_review.findings.length > 0 ? (
                <>
                  <h3>Reasons</h3>
                  <ul>
                    {financial_review.findings.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              <p>
                <strong>Next step:</strong> {financial_review.recommendation}
              </p>
            </>
          ) : (
            <p className="muted">
              Final review appears after analysis runs on a flagged transaction.
            </p>
          )}
        </PipelineCard>

        {financial_review ? (
          <PipelineCard
            step={6}
            title="Your Decision"
            subtitle="Approve, reject, or escalate — AI recommends, you decide"
            status={financial_review.review_status === "PENDING" ? "warning" : "complete"}
          >
            <p>
              AI recommendation:{" "}
              <strong>{financial_review.decision.replaceAll("_", " ")}</strong>
            </p>
            <p>
              Decision status:{" "}
              <Badge
                label={financial_review.review_status}
                tone={riskBadgeTone(financial_review.review_status)}
              />
            </p>
            {financial_review.reviewed_by ? (
              <p>
                Reviewed by {financial_review.reviewed_by}
                {financial_review.reviewed_at
                  ? ` on ${formatDateTime(financial_review.reviewed_at)}`
                  : ""}
              </p>
            ) : null}
            {financial_review.review_comment ? (
              <p>
                <strong>Comment:</strong> {financial_review.review_comment}
              </p>
            ) : null}

            {submitError ? <ErrorAlert message={submitError} /> : null}

            {financial_review.review_status === "PENDING" ? (
              <form className="human-review-form" onSubmit={handleDecisionSubmit}>
                <fieldset className="decision-fieldset">
                  <legend>Decision</legend>
                  <label className="radio-row">
                    <input
                      type="radio"
                      name="decision"
                      checked={selectedDecision === "APPROVED"}
                      onChange={() => setSelectedDecision("APPROVED")}
                    />
                    Approve
                  </label>
                  <label className="radio-row">
                    <input
                      type="radio"
                      name="decision"
                      checked={selectedDecision === "REJECTED"}
                      onChange={() => setSelectedDecision("REJECTED")}
                    />
                    Reject
                  </label>
                  <label className="radio-row">
                    <input
                      type="radio"
                      name="decision"
                      checked={selectedDecision === "ESCALATED"}
                      onChange={() => setSelectedDecision("ESCALATED")}
                    />
                    Escalate
                  </label>
                </fieldset>
                <label>
                  Reviewed by
                  <input
                    value={reviewedBy}
                    onChange={(event) => setReviewedBy(event.target.value)}
                    required
                  />
                </label>
                <label>
                  Comment
                  <textarea
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="Verified with vendor by email."
                    rows={3}
                    required
                  />
                </label>
                <div className="action-row">
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    {submitting ? "Saving..." : "Submit Decision"}
                  </button>
                </div>
              </form>
            ) : null}
          </PipelineCard>
        ) : null}
      </div>
    </div>
  );
}
