import type {
  AnalysisRun,
  BatchWorkflowResponse,
  CategoryItem,
  ClaimBatchResponse,
  CompanyItem,
  DashboardOverview,
  FinancialInvestigation,
  HealthResponse,
  HumanDecision,
  InvoiceItem,
  InvoiceVerificationResult,
  NewTransactionCounts,
  PaginatedAnalysisRuns,
  PaginatedAnomalies,
  PaginatedInvoices,
  PaginatedReviews,
  PaginatedTransactions,
  ProcessItemResponse,
  TransactionCreatePayload,
  TransactionImportResponse,
  TransactionItem,
  VendorItem,
  WorkflowRunResponse,
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function formatDetail(detail: unknown): string | null {
  if (!detail) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: string }).msg);
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  return String(detail);
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  if (init?.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      const parsed = formatDetail(body.detail);
      if (parsed) message = parsed;
    } catch {
      const text = await response.text();
      if (text) message = text;
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function getHealth() {
  return fetchJson<HealthResponse>("/health");
}

export function getDashboardOverview() {
  return fetchJson<DashboardOverview>("/api/dashboard/overview");
}

export function getAnomalies(params: URLSearchParams) {
  return fetchJson<PaginatedAnomalies>(`/api/anomalies/?${params.toString()}`);
}

export function getTransactions(params: URLSearchParams) {
  return fetchJson<PaginatedTransactions>(`/api/transactions/?${params.toString()}`);
}

export function createTransaction(payload: TransactionCreatePayload) {
  return fetchJson<TransactionItem>("/api/transactions/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function importTransactionsCsv(file: File) {
  const form = new FormData();
  form.append("file", file);
  return fetchJson<TransactionImportResponse>("/api/transactions/import", {
    method: "POST",
    body: form,
  });
}

export function getCsvTemplateUrl() {
  return `${API_BASE}/api/transactions/import/template`;
}

export function getCompanies() {
  return fetchJson<CompanyItem[]>("/api/companies/");
}

export function createCompany(name: string) {
  return fetchJson<CompanyItem>("/api/companies/", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function getVendors(companyId?: number) {
  const params = new URLSearchParams();
  if (companyId != null) params.set("company_id", String(companyId));
  const qs = params.toString();
  return fetchJson<VendorItem[]>(qs ? `/api/vendors/?${qs}` : "/api/vendors/");
}

export function createVendor(payload: {
  company_id: number;
  name: string;
  email?: string;
  country?: string;
}) {
  return fetchJson<VendorItem>("/api/vendors/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCategories(companyId?: number) {
  const params = new URLSearchParams();
  if (companyId != null) params.set("company_id", String(companyId));
  const qs = params.toString();
  return fetchJson<CategoryItem[]>(qs ? `/api/categories/?${qs}` : "/api/categories/");
}

export function createCategory(payload: {
  company_id: number;
  name: string;
  description?: string;
}) {
  return fetchJson<CategoryItem>("/api/categories/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createInvoice(payload: {
  transaction_id: number;
  raw_ocr_text: string;
  ocr_confidence?: number;
  run_extraction?: boolean;
}) {
  return fetchJson<{ invoice: InvoiceItem }>("/api/invoices/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getTransactionInvoice(transactionId: number) {
  return fetchJson<InvoiceItem>(`/api/transactions/${transactionId}/invoice`);
}

export function upsertTransactionInvoice(
  transactionId: number,
  payload: {
    raw_ocr_text?: string;
    run_extraction?: boolean;
    invoice_number?: string;
    vendor_name?: string;
    invoice_date?: string;
    amount?: number;
    currency?: string;
    description?: string;
  },
) {
  return fetchJson<{ invoice: InvoiceItem }>(
    `/api/transactions/${transactionId}/invoice`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function verifyTransactionInvoice(transactionId: number) {
  return fetchJson<InvoiceVerificationResult>(
    `/api/transactions/${transactionId}/invoice/verify`,
    { method: "POST" },
  );
}

export function getReviews(params: URLSearchParams) {
  return fetchJson<PaginatedReviews>(`/api/reviews/?${params.toString()}`);
}

export function getInvestigation(transactionId: number) {
  return fetchJson<FinancialInvestigation>(`/api/reviews/${transactionId}`);
}

export function submitHumanDecision(
  transactionId: number,
  body: { decision: HumanDecision; reviewed_by: string; comment: string },
) {
  return fetchJson<FinancialInvestigation>(
    `/api/reviews/${transactionId}/human-decision`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function runTransactionWorkflow(transactionId: number) {
  return fetchJson<WorkflowRunResponse>(
    `/api/workflows/transactions/${transactionId}/analyze`,
    { method: "POST" },
  );
}

export function analyzeNewTransactions(limit = 10) {
  return fetchJson<BatchWorkflowResponse>(
    `/api/workflows/analyze-new?limit=${limit}`,
    { method: "POST" },
  );
}

export function claimNewTransactions(limit = 10, mode = "NEW") {
  return fetchJson<ClaimBatchResponse>(
    `/api/workflows/claim-new?limit=${limit}&mode=${mode}`,
    { method: "POST" },
  );
}

export function processClaimedTransaction(runId: number, transactionId: number) {
  return fetchJson<ProcessItemResponse>(
    `/api/workflows/runs/${runId}/items/${transactionId}/process`,
    { method: "POST" },
  );
}

export function finalizeAnalysisRun(runId: number) {
  return fetchJson<AnalysisRun>(`/api/workflows/runs/${runId}/finalize`, {
    method: "POST",
  });
}

export function getAnalysisRuns(params: URLSearchParams) {
  return fetchJson<PaginatedAnalysisRuns>(
    `/api/workflows/runs?${params.toString()}`,
  );
}

export function getNewTransactionCounts() {
  return fetchJson<NewTransactionCounts>("/api/workflows/new-count");
}

export function getInvoices(params: URLSearchParams) {
  return fetchJson<PaginatedInvoices>(`/api/invoices/?${params.toString()}`);
}
