import { Link } from "react-router-dom";
import { useAsyncData } from "../hooks/useAsyncData";
import { getDashboardOverview } from "../lib/api";
import { formatCurrency, formatNumber } from "../lib/format";
import { PageHeader } from "../components/ui/PageHeader";
import { StatCard } from "../components/ui/StatCard";
import { Badge } from "../components/ui/Badge";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { EmptyState } from "../components/ui/EmptyState";

export function DashboardPage() {
  const { data, loading, error, status, reload } = useAsyncData(
    getDashboardOverview,
    [],
  );

  if (loading) {
    return (
      <div className="page">
        <PageHeader
          title="Dashboard"
          description="Operational overview of transactions, anomalies, and reviews."
        />
        <LoadingState label="Loading dashboard metrics..." />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page">
        <PageHeader title="Dashboard" />
        <ErrorAlert message={error ?? "Dashboard unavailable"} status={status} onRetry={reload} />
      </div>
    );
  }

  const { summary, anomaly_trend, risk_distribution, recent_high_risk, recent_reviews } =
    data;
  const maxTrend = Math.max(...anomaly_trend.map((point) => point.count), 1);
  const maxDistribution = Math.max(...risk_distribution.map((item) => item.count), 1);

  return (
    <div className="page">
      <PageHeader
        title="Dashboard"
        description="Financial overview — investigate high-risk items and pending reviews."
      />

      <section className="stats-grid" aria-label="Key metrics">
        <StatCard label="Total Transactions" value={formatNumber(summary.total_transactions)} />
        <StatCard label="Anomalies" value={formatNumber(summary.total_anomalies)} tone="warning" />
        <StatCard label="High Risk" value={formatNumber(summary.high_risk_transactions)} tone="danger" />
        <StatCard label="Pending Reviews" value={formatNumber(summary.pending_reviews)} tone="warning" hint="Awaiting human decision" />
        <StatCard label="Invoice Mismatches" value={formatNumber(summary.invoice_mismatches)} tone="danger" />
      </section>

      <section className="grid-2">
        <article className="panel">
          <div className="panel-heading">
            <h2>Anomaly Trend</h2>
            <p className="muted">Detections grouped by day</p>
          </div>
          {anomaly_trend.length === 0 ? (
            <EmptyState title="No trend data yet" description="Run analysis on new transactions to populate this chart." />
          ) : (
            <div className="bar-chart">
              {anomaly_trend.map((point) => (
                <div key={point.date} className="bar-row">
                  <span className="bar-label">{point.date}</span>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{ width: `${(point.count / maxTrend) * 100}%` }}
                    />
                  </div>
                  <span className="bar-value">{point.count}</span>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading">
            <h2>Risk Distribution</h2>
            <p className="muted">Anomaly severity breakdown</p>
          </div>
          <div className="distribution-list">
            {risk_distribution.map((item) => (
              <div key={item.status} className="distribution-row">
                <Badge
                  label={item.status}
                  tone={
                    item.status === "HIGH"
                      ? "high"
                      : item.status === "MEDIUM"
                        ? "medium"
                        : "low"
                  }
                />
                <div className="distribution-track">
                  <div
                    className="distribution-fill"
                    style={{ width: `${(item.count / maxDistribution) * 100}%` }}
                  />
                </div>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="panel">
          <div className="panel-heading">
            <h2>Recent High-Risk Transactions</h2>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Transaction</th>
                  <th scope="col">Vendor</th>
                  <th scope="col">Amount</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {recent_high_risk.map((item) => (
                  <tr key={item.transaction_id}>
                    <td>
                      <Link to={`/investigation/${item.transaction_id}`}>
                        #{item.transaction_id}
                      </Link>
                    </td>
                    <td>{item.vendor_name ?? "—"}</td>
                    <td>{formatCurrency(item.amount)}</td>
                    <td>
                      <Badge label={item.status} tone="high" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <h2>Recent Financial Reviews</h2>
          </div>
          {recent_reviews.length === 0 ? (
            <EmptyState
              title="No reviews yet"
              description="Analyze unusual transactions to generate recommendations."
            />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Transaction</th>
                    <th scope="col">Final Risk</th>
                    <th scope="col">AI Decision</th>
                    <th scope="col">Human</th>
                  </tr>
                </thead>
                <tbody>
                  {recent_reviews.map((item) => (
                    <tr key={item.transaction_id}>
                      <td>
                        <Link to={`/investigation/${item.transaction_id}`}>
                          #{item.transaction_id}
                        </Link>
                      </td>
                      <td>
                        <Badge label={item.final_risk} tone="high" />
                      </td>
                      <td>{item.decision}</td>
                      <td>{item.review_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      </section>
    </div>
  );
}
