import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAsyncData } from "../hooks/useAsyncData";
import { getAnomalies } from "../lib/api";
import { formatCurrency, formatDate, riskBadgeTone } from "../lib/format";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { Pagination } from "../components/ui/Pagination";

export function AnomaliesPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const params = useMemo(() => {
    const next = new URLSearchParams({ page: String(page), limit: "20" });
    if (status) next.set("status", status);
    if (startDate) next.set("start_date", startDate);
    if (endDate) next.set("end_date", endDate);
    return next;
  }, [page, status, startDate, endDate]);

  const { data, loading, error, status: httpStatus, reload } = useAsyncData(
    () => getAnomalies(params),
    [params.toString()],
  );

  function resetFilters() {
    setPage(1);
    setStatus("");
    setStartDate("");
    setEndDate("");
  }

  return (
    <div className="page">
      <PageHeader
        title="Anomalies"
        description="Unusual transactions flagged against historical spending patterns."
        actions={
          <button type="button" className="btn btn-secondary" onClick={resetFilters}>
            Clear filters
          </button>
        }
      />

      <section className="panel filters" aria-label="Anomaly filters">
        <label>
          Risk level
          <select
            value={status}
            onChange={(event) => {
              setPage(1);
              setStatus(event.target.value);
            }}
          >
            <option value="">All</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </label>
        <label>
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(event) => {
              setPage(1);
              setStartDate(event.target.value);
            }}
          />
        </label>
        <label>
          End date
          <input
            type="date"
            value={endDate}
            onChange={(event) => {
              setPage(1);
              setEndDate(event.target.value);
            }}
          />
        </label>
      </section>

      {loading ? <LoadingState label="Loading anomalies..." /> : null}
      {error ? (
        <ErrorAlert message={error} status={httpStatus} onRetry={reload} />
      ) : null}

      {data ? (
        <article className="panel">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Transaction</th>
                  <th scope="col">Vendor</th>
                  <th scope="col">Category</th>
                  <th scope="col">Amount</th>
                  <th scope="col">Date</th>
                  <th scope="col">Risk</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.transaction_id}>
                    <td>
                      <Link to={`/investigation/${item.transaction_id}`}>
                        #{item.transaction_id}
                      </Link>
                    </td>
                    <td>{item.vendor_name ?? "—"}</td>
                    <td>{item.category_name ?? "—"}</td>
                    <td>{formatCurrency(item.amount)}</td>
                    <td>{formatDate(item.transaction_date)}</td>
                    <td>
                      <Badge label={item.status} tone={riskBadgeTone(item.status)} />
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
