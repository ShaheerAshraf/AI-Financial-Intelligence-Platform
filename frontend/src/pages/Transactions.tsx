import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAsyncData } from "../hooks/useAsyncData";
import {
  claimNewTransactions,
  createTransaction,
  finalizeAnalysisRun,
  getCategories,
  getCompanies,
  getCsvTemplateUrl,
  getNewTransactionCounts,
  getTransactions,
  getVendors,
  importTransactionsCsv,
  processClaimedTransaction,
  runTransactionWorkflow,
} from "../lib/api";
import { formatCurrency, formatDate, riskBadgeTone } from "../lib/format";
import type {
  AnalysisRun,
  CategoryItem,
  CompanyItem,
  ProcessItemResponse,
  TransactionImportResponse,
  VendorItem,
} from "../types/api";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { Pagination } from "../components/ui/Pagination";

type Panel = "none" | "add" | "import";

type ProgressItem = {
  transaction_id: number;
  state: "pending" | "running" | "done" | "failed";
  risk_level?: string | null;
  error?: string | null;
};

type BatchSummary = {
  run: AnalysisRun | null;
  processed: number;
  successful: number;
  failed: number;
  remaining_new: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
};

async function runClaimedBatch(
  limit: number,
  mode: string,
  onProgress: (items: ProgressItem[], done: number, total: number) => void,
): Promise<BatchSummary> {
  const claim = await claimNewTransactions(limit, mode);
  const items: ProgressItem[] = claim.transaction_ids.map((id) => ({
    transaction_id: id,
    state: "pending",
  }));
  onProgress([...items], 0, items.length);

  let successful = 0;
  let failed = 0;
  let high = 0;
  let medium = 0;
  let low = 0;
  let remaining = claim.remaining_new;

  for (let i = 0; i < items.length; i += 1) {
    items[i] = { ...items[i], state: "running" };
    onProgress([...items], i, items.length);

    let result: ProcessItemResponse;
    try {
      result = await processClaimedTransaction(claim.run_id, items[i].transaction_id);
    } catch (err) {
      failed += 1;
      items[i] = {
        ...items[i],
        state: "failed",
        error: err instanceof Error ? err.message : "Failed",
      };
      onProgress([...items], i + 1, items.length);
      continue;
    }

    remaining = result.remaining_new;
    if (result.status === "FAILED") {
      failed += 1;
      items[i] = {
        ...items[i],
        state: "failed",
        risk_level: result.risk_level,
        error: result.error,
      };
    } else {
      successful += 1;
      const risk = (result.risk_level || "").toUpperCase();
      if (risk === "HIGH") high += 1;
      else if (risk === "MEDIUM") medium += 1;
      else if (risk === "LOW") low += 1;
      items[i] = {
        ...items[i],
        state: "done",
        risk_level: result.risk_level,
      };
    }
    onProgress([...items], i + 1, items.length);
  }

  const run = items.length
    ? await finalizeAnalysisRun(claim.run_id)
    : null;

  return {
    run,
    processed: items.length,
    successful: run?.successful ?? successful,
    failed: run?.failed ?? failed,
    remaining_new: run?.remaining_new_after ?? remaining,
    high_risk: run?.high_risk ?? high,
    medium_risk: run?.medium_risk ?? medium,
    low_risk: run?.low_risk ?? low,
  };
}

export function TransactionsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [panel, setPanel] = useState<Panel>("none");
  const [reloadToken, setReloadToken] = useState(0);
  const [analyzingBatch, setAnalyzingBatch] = useState(false);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [progressItems, setProgressItems] = useState<ProgressItem[]>([]);
  const [progressDone, setProgressDone] = useState(0);
  const [progressTotal, setProgressTotal] = useState(0);
  const [batchSummary, setBatchSummary] = useState<BatchSummary | null>(null);
  const [newCount, setNewCount] = useState<number | null>(null);

  const params = useMemo(() => {
    const next = new URLSearchParams({ page: String(page), limit: "20" });
    if (statusFilter) next.set("analysis_status", statusFilter);
    return next;
  }, [page, statusFilter]);

  const { data, loading, error, status, reload } = useAsyncData(
    () => getTransactions(params),
    [params.toString(), reloadToken],
  );

  useEffect(() => {
    getNewTransactionCounts()
      .then((c) => setNewCount(c.new))
      .catch(() => setNewCount(null));
  }, [reloadToken, batchSummary]);

  async function runBatches(mode: "NEW" | "ALL") {
    setAnalyzingBatch(true);
    setActionError(null);
    setBatchSummary(null);
    setProgressItems([]);
    setProgressDone(0);
    setProgressTotal(0);

    try {
      let totalProcessed = 0;
      let totalSuccessful = 0;
      let totalFailed = 0;
      let totalHigh = 0;
      let totalMedium = 0;
      let totalLow = 0;
      let remaining = 0;
      let lastRun: AnalysisRun | null = null;
      let safety = 0;

      do {
        const summary = await runClaimedBatch(10, mode === "ALL" ? "ALL" : "NEW", (items, done, total) => {
          setProgressItems(items);
          setProgressDone(done);
          setProgressTotal(total);
        });

        if (summary.processed === 0) {
          remaining = summary.remaining_new;
          break;
        }

        lastRun = summary.run;
        totalProcessed += summary.processed;
        totalSuccessful += summary.successful;
        totalFailed += summary.failed;
        totalHigh += summary.high_risk;
        totalMedium += summary.medium_risk;
        totalLow += summary.low_risk;
        remaining = summary.remaining_new;
        safety += 1;

        if (mode === "NEW") break;
      } while (remaining > 0 && safety < 500);

      setBatchSummary({
        run: lastRun,
        processed: totalProcessed,
        successful: totalSuccessful,
        failed: totalFailed,
        remaining_new: remaining,
        high_risk: totalHigh,
        medium_risk: totalMedium,
        low_risk: totalLow,
      });
      setReloadToken((n) => n + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Batch analysis failed");
    } finally {
      setAnalyzingBatch(false);
    }
  }

  async function handleAnalyzeOne(id: number) {
    setAnalyzingId(id);
    setActionError(null);
    try {
      await runTransactionWorkflow(id);
      setReloadToken((n) => n + 1);
      navigate(`/investigation/${id}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzingId(null);
    }
  }

  const progressPct =
    progressTotal > 0 ? Math.round((progressDone / progressTotal) * 100) : 0;

  return (
    <div className="page">
      <PageHeader
        title="Transactions"
        description={
          newCount != null
            ? `${newCount} NEW transactions waiting for analysis.`
            : "Add or import financial data, then run analysis on new entries."
        }
        actions={
          <>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setPanel(panel === "add" ? "none" : "add")}
            >
              + Add Transaction
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setPanel(panel === "import" ? "none" : "import")}
            >
              Import CSV
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={analyzingBatch}
              onClick={() => runBatches("NEW")}
            >
              {analyzingBatch ? "Analyzing..." : "Analyze New"}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={analyzingBatch}
              onClick={() => runBatches("ALL")}
            >
              Analyze All
            </button>
            <Link to="/analysis-runs" className="btn btn-secondary">
              Analysis Runs
            </Link>
          </>
        }
      />

      {panel === "add" ? (
        <AddTransactionForm
          onCancel={() => setPanel("none")}
          onCreated={(id) => {
            setPanel("none");
            setReloadToken((n) => n + 1);
            navigate(`/investigation/${id}`);
          }}
        />
      ) : null}

      {panel === "import" ? (
        <ImportCsvPanel
          onClose={() => setPanel("none")}
          onImported={() => {
            setReloadToken((n) => n + 1);
            setPage(1);
          }}
        />
      ) : null}

      {actionError ? <ErrorAlert message={actionError} /> : null}

      {(analyzingBatch || progressItems.length > 0) && !batchSummary ? (
        <article className="panel batch-progress">
          <div className="panel-heading">
            <h2>Analyzing transactions...</h2>
            <p className="muted">
              {progressDone} / {progressTotal || "…"}
            </p>
          </div>
          <div className="progress-track" aria-hidden="true">
            <div className="progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <ul className="batch-progress-list">
            {progressItems.map((item) => (
              <li key={item.transaction_id}>
                <span>
                  {item.state === "done"
                    ? "✓"
                    : item.state === "failed"
                      ? "⚠"
                      : item.state === "running"
                        ? "⟳"
                        : "○"}{" "}
                  Transaction #{item.transaction_id}
                </span>
                {item.risk_level ? (
                  <Badge label={item.risk_level} tone={riskBadgeTone(item.risk_level)} />
                ) : null}
              </li>
            ))}
          </ul>
        </article>
      ) : null}

      {batchSummary ? (
        <article className="panel">
          <div className="panel-heading">
            <h2>Analysis complete</h2>
            {batchSummary.run ? (
              <p className="muted">Run #{batchSummary.run.id}</p>
            ) : null}
          </div>
          <p>
            ✓ <strong>{batchSummary.successful}</strong> transactions analyzed
            {batchSummary.failed > 0 ? (
              <>
                {" "}
                · ⚠ <strong>{batchSummary.failed}</strong> failed
              </>
            ) : null}
          </p>
          <p className="muted">
            {batchSummary.high_risk} HIGH · {batchSummary.medium_risk} MEDIUM ·{" "}
            {batchSummary.low_risk} LOW · {batchSummary.remaining_new} NEW remaining
          </p>
        </article>
      ) : null}

      <section className="panel filters" aria-label="Transaction filters">
        <label>
          Status
          <select
            value={statusFilter}
            onChange={(event) => {
              setPage(1);
              setStatusFilter(event.target.value);
            }}
          >
            <option value="">All</option>
            <option value="NEW">NEW</option>
            <option value="ANALYZING">ANALYZING</option>
            <option value="ANALYZED">ANALYZED</option>
            <option value="ANALYSIS_FAILED">ANALYSIS_FAILED</option>
          </select>
        </label>
      </section>

      {loading ? <LoadingState label="Loading transactions..." /> : null}
      {error ? (
        <ErrorAlert message={error} status={status} onRetry={reload} />
      ) : null}

      {data ? (
        <article className="panel">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Vendor</th>
                  <th scope="col">Category</th>
                  <th scope="col">Amount</th>
                  <th scope="col">Date</th>
                  <th scope="col">Status</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((txn) => (
                  <tr key={txn.id}>
                    <td>
                      <Link to={`/investigation/${txn.id}`}>#{txn.id}</Link>
                    </td>
                    <td>{txn.vendor_name ?? "—"}</td>
                    <td>{txn.category_name ?? "—"}</td>
                    <td>{formatCurrency(txn.amount, txn.currency)}</td>
                    <td>{formatDate(txn.transaction_date)}</td>
                    <td>
                      <Badge
                        label={txn.analysis_status}
                        tone={riskBadgeTone(txn.analysis_status)}
                      />
                    </td>
                    <td>
                      <div className="action-row">
                        {txn.analysis_status === "NEW" ||
                        txn.analysis_status === "ANALYSIS_FAILED" ? (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            disabled={analyzingId === txn.id || analyzingBatch}
                            onClick={() => handleAnalyzeOne(txn.id)}
                          >
                            {analyzingId === txn.id ? "..." : "Analyze"}
                          </button>
                        ) : (
                          <Link
                            to={`/investigation/${txn.id}`}
                            className="btn btn-secondary"
                          >
                            View
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={setPage}
          />
        </article>
      ) : null}
    </div>
  );
}

function AddTransactionForm({
  onCancel,
  onCreated,
}: {
  onCancel: () => void;
  onCreated: (id: number) => void;
}) {
  const [companies, setCompanies] = useState<CompanyItem[]>([]);
  const [vendors, setVendors] = useState<VendorItem[]>([]);
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [vendorId, setVendorId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [dateValue, setDateValue] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCompanies()
      .then((items) => {
        setCompanies(items);
        if (items.length === 1) setCompanyId(String(items[0].id));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load companies"));
  }, []);

  useEffect(() => {
    if (!companyId) {
      setVendors([]);
      setCategories([]);
      setVendorId("");
      setCategoryId("");
      return;
    }
    const id = Number(companyId);
    Promise.all([getVendors(id), getCategories(id)])
      .then(([vendorItems, categoryItems]) => {
        setVendors(vendorItems);
        setCategories(categoryItems);
        setVendorId("");
        setCategoryId("");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load master data"));
  }, [companyId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await createTransaction({
        company_id: Number(companyId),
        vendor_id: Number(vendorId),
        category_id: Number(categoryId),
        amount: Number(amount),
        currency,
        transaction_date: dateValue,
        description: description || undefined,
      });
      onCreated(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create transaction");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="panel form-panel">
      <div className="panel-heading">
        <h2>Add Transaction</h2>
        <p className="muted">Select company, vendor, and category by name.</p>
      </div>
      {error ? <ErrorAlert message={error} /> : null}
      <form className="master-form" onSubmit={handleSubmit}>
        <label>
          Company
          <select
            required
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
          >
            <option value="">Select company</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Vendor
          <select
            required
            value={vendorId}
            onChange={(e) => setVendorId(e.target.value)}
            disabled={!companyId}
          >
            <option value="">Select vendor</option>
            {vendors.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select
            required
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            disabled={!companyId}
          >
            <option value="">Select category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Amount
          <input
            required
            type="number"
            step="0.01"
            min="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="1250.50"
          />
        </label>
        <label>
          Currency
          <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
            <option value="EUR">EUR</option>
            <option value="USD">USD</option>
            <option value="GBP">GBP</option>
          </select>
        </label>
        <label>
          Transaction Date
          <input
            required
            type="date"
            value={dateValue}
            onChange={(e) => setDateValue(e.target.value)}
          />
        </label>
        <label className="full-width">
          Description
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Cloud infrastructure"
          />
        </label>
        <div className="action-row full-width">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving..." : "Save Transaction"}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </article>
  );
}

function ImportCsvPanel({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<TransactionImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleImport() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const response = await importTransactionsCsv(file);
      setResult(response);
      if (response.imported > 0) onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="panel form-panel">
      <div className="panel-heading">
        <h2>Import Transactions</h2>
        <p className="muted">
          Upload a CSV with company, vendor, and category names. New rows start as NEW
          until you run analysis.
        </p>
      </div>

      <div className="import-actions">
        <a className="btn btn-secondary" href={getCsvTemplateUrl()} download>
          Download CSV Template
        </a>
        <label className="file-picker">
          Choose CSV
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setResult(null);
            }}
          />
        </label>
        {file ? <span className="muted">{file.name}</span> : null}
      </div>

      {error ? <ErrorAlert message={error} /> : null}

      {result ? (
        <div className="import-result">
          <p>
            ✓ <strong>{result.imported}</strong> transactions imported
          </p>
          {result.failed > 0 ? (
            <p>
              ⚠ <strong>{result.failed}</strong> transactions failed
            </p>
          ) : null}
          {result.errors.length > 0 ? (
            <ul className="error-list">
              {result.errors.map((item) => (
                <li key={`${item.row}-${item.message}`}>
                  Row {item.row}: {item.message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="action-row">
        <button
          type="button"
          className="btn btn-primary"
          disabled={!file || busy}
          onClick={handleImport}
        >
          {busy ? "Importing..." : "Import"}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onClose}>
          Close
        </button>
      </div>
    </article>
  );
}
