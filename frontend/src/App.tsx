import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { AppLayout } from "./components/layout/AppLayout";
import { DashboardPage } from "./pages/Dashboard";
import { TransactionsPage } from "./pages/Transactions";
import { VendorsPage } from "./pages/Vendors";
import { CategoriesPage } from "./pages/Categories";
import { InvoicesPage } from "./pages/Invoices";
import { AnomaliesPage } from "./pages/Anomalies";
import { ReviewsPage } from "./pages/Reviews";
import { AnalysisRunsPage } from "./pages/AnalysisRuns";
import { InvestigationPage } from "./pages/Investigation";
import { NotFoundPage } from "./pages/NotFound";

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="transactions" element={<TransactionsPage />} />
            <Route path="analysis-runs" element={<AnalysisRunsPage />} />
            <Route path="invoices" element={<InvoicesPage />} />
            <Route path="vendors" element={<VendorsPage />} />
            <Route path="categories" element={<CategoriesPage />} />
            <Route path="anomalies" element={<AnomaliesPage />} />
            <Route path="reviews" element={<ReviewsPage />} />
            <Route path="investigation/:transactionId" element={<InvestigationPage />} />
            <Route path="404" element={<NotFoundPage />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
