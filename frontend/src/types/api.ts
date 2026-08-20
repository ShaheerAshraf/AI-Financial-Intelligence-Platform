export interface DashboardSummary {
  total_transactions: number;
  total_anomalies: number;
  high_risk_transactions: number;
  pending_reviews: number;
  invoice_mismatches: number;
  manual_reviews: number;
}

export interface AnomalyTrendPoint {
  date: string;
  count: number;
}

export interface RiskDistributionItem {
  status: string;
  count: number;
}

export interface RecentHighRiskItem {
  transaction_id: number;
  amount: string;
  vendor_id: number | null;
  category_id: number | null;
  vendor_name?: string | null;
  anomaly_score: number;
  status: string;
  transaction_date: string;
}

export interface RecentReviewItem {
  transaction_id: number;
  amount: string;
  final_risk: string;
  decision: string;
  review_status: string;
  created_at: string;
}

export interface DashboardOverview {
  summary: DashboardSummary;
  anomaly_trend: AnomalyTrendPoint[];
  risk_distribution: RiskDistributionItem[];
  recent_high_risk: RecentHighRiskItem[];
  recent_reviews: RecentReviewItem[];
}

export interface AnomalyListItem {
  transaction_id: number;
  amount: string;
  vendor_id: number | null;
  category_id: number | null;
  vendor_name?: string | null;
  category_name?: string | null;
  anomaly_score: number;
  status: string;
  reason: string | null;
  transaction_date: string;
}

export interface PaginatedAnomalies {
  items: AnomalyListItem[];
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface TransactionItem {
  id: number;
  company_id: number;
  vendor_id: number | null;
  category_id: number | null;
  amount: string;
  currency: string;
  description: string | null;
  transaction_date: string;
  analysis_status: string;
  company_name?: string | null;
  vendor_name?: string | null;
  category_name?: string | null;
}

export interface PaginatedTransactions {
  items: TransactionItem[];
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface CompanyItem {
  id: number;
  name: string;
  created_at: string;
}

export interface VendorItem {
  id: number;
  company_id: number;
  name: string;
  email: string | null;
  tax_id: string | null;
  country: string | null;
  created_at: string;
}

export interface CategoryItem {
  id: number;
  company_id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export interface TransactionCreatePayload {
  company_id: number;
  vendor_id: number;
  category_id: number;
  amount: number;
  currency: string;
  transaction_date: string;
  description?: string;
}

export interface TransactionImportRowError {
  row: number;
  field: string | null;
  message: string;
  company: string | null;
  vendor: string | null;
  category: string | null;
}

export interface TransactionImportResponse {
  imported: number;
  failed: number;
  total_rows: number;
  created_ids: number[];
  errors: TransactionImportRowError[];
}

export interface InvoiceItem {
  id: number;
  transaction_id: number;
  invoice_number: string | null;
  vendor_name: string | null;
  invoice_date: string | null;
  amount: string | null;
  currency: string | null;
  extraction_status: string;
  extraction_error: string | null;
  description?: string | null;
}

export interface FieldComparisonItem {
  field: string;
  label: string;
  transaction_value: string;
  invoice_value: string;
  status: string;
  detail?: string | null;
}

export interface InvoiceVerificationResult {
  id: number;
  transaction_id: number;
  invoice_id: number | null;
  match_status: string;
  summary: string;
  mismatches: string[];
  field_comparisons: FieldComparisonItem[];
  recommendation: string;
  agent_version: string;
  created_at: string;
}

export interface InvoiceListItem {
  id: number;
  transaction_id: number;
  invoice_number: string | null;
  vendor_name: string | null;
  amount: string | null;
  currency: string | null;
  invoice_date: string | null;
  extraction_status: string;
  match_status: string | null;
}

export interface PaginatedInvoices {
  items: InvoiceListItem[];
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface ReviewListItem {
  transaction_id: number;
  amount: string;
  vendor_name?: string | null;
  category_name?: string | null;
  anomaly_status: string | null;
  invoice_status: string | null;
  final_risk: string | null;
  decision: string | null;
  review_status: string | null;
}

export interface PaginatedReviews {
  items: ReviewListItem[];
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface FinancialInvestigation {
  transaction: {
    id: number;
    amount: string;
    vendor_id: number | null;
    category_id: number | null;
    date: string;
    currency: string;
    description: string | null;
    analysis_status?: string;
    vendor_name?: string | null;
    category_name?: string | null;
    company_name?: string | null;
  };
  anomaly: {
    score: number;
    status: string;
    reason: string | null;
    model_version: string | null;
  } | null;
  transaction_analysis: {
    risk_level: string;
    summary: string;
    recommendation: string;
    findings: string[];
  } | null;
  invoice: {
    id: number | null;
    invoice_number: string | null;
    amount: string | null;
    vendor_name: string | null;
    invoice_date: string | null;
    currency: string | null;
    extraction_status?: string | null;
  } | null;
  invoice_verification: {
    status: string;
    reason: string | null;
    summary: string | null;
    mismatches: string[];
    field_comparisons?: FieldComparisonItem[];
    invoice_id: number | null;
    recommendation?: string | null;
    amount_difference?: string | null;
  } | null;
  financial_review: {
    risk_level: string;
    decision: string;
    summary: string;
    recommendation: string;
    findings: string[];
    review_status: string;
    reviewed_by: string | null;
    reviewed_at: string | null;
    review_comment: string | null;
  } | null;
}

export type HumanDecision = "APPROVED" | "REJECTED" | "ESCALATED";

export interface WorkflowStepResult {
  name: string;
  label: string;
  status: string;
  detail: string | null;
}

export interface WorkflowRunResponse {
  transaction_id: number;
  workflow_status: string;
  workflow_version: string;
  steps: WorkflowStepResult[];
  error: string | null;
  investigation: FinancialInvestigation | null;
}

export interface BatchWorkflowItem {
  transaction_id: number;
  workflow_status: string;
  status?: string | null;
  risk_level?: string | null;
  error: string | null;
}

export interface BatchWorkflowResponse {
  status: string;
  run_id?: number | null;
  requested: number;
  processed: number;
  successful: number;
  completed: number;
  normal: number;
  failed: number;
  remaining_new: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  results: BatchWorkflowItem[];
}

export interface ClaimBatchResponse {
  run_id: number;
  mode: string;
  status: string;
  claimed: number;
  remaining_new: number;
  transaction_ids: number[];
}

export interface ProcessItemResponse {
  run_id: number;
  transaction_id: number;
  status: string;
  workflow_status: string | null;
  risk_level: string | null;
  error: string | null;
  remaining_new: number;
}

export interface AnalysisRunItem {
  id: number;
  transaction_id: number;
  status: string;
  workflow_status: string | null;
  risk_level: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface AnalysisRun {
  id: number;
  started_at: string;
  completed_at: string | null;
  mode: string;
  status: string;
  batch_size: number;
  total_transactions: number;
  successful: number;
  failed: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  remaining_new_after: number | null;
  items: AnalysisRunItem[];
}

export interface PaginatedAnalysisRuns {
  items: AnalysisRun[];
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface NewTransactionCounts {
  new: number;
  analyzing: number;
  failed: number;
}

export interface HealthResponse {
  status: string;
  service?: string;
}
