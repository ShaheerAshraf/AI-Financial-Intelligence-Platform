import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAsyncData } from "../hooks/useAsyncData";
import { getAnalysisRuns } from "../lib/api";
import { formatDateTime, riskBadgeTone } from "../lib/format";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { EmptyState } from "../components/ui/EmptyState";
import { Pagination } from "../components/ui/Pagination";

export function AnalysisRunsPage() {
  const [page, setPage] = useState(1);

  const params = useMemo(() => {
    return new URLSearchParams({ page: String(page), limit: "20" });
  }, [page]);

  const { data, loading, error, status, reload } = useAsyncData(
    () => getAnalysisRuns(params),
    [params.toString()],
  );

  return (
    <div className="page">
      <PageHeader
        title="Analysis Runs"
        description="History of batch analysis jobs — what was processed and what failed."
        actions={
          <Link to="/transactions" className="btn btn-secondary">
            Back to transactions
          </Link>
        }
      />

      {loading ? <LoadingState label="Loading analysis runs..." /> : null}
      {error ? <ErrorAlert message={error} status={status} onRetry={reload} /> : null}

      {data ? (
        <article className="panel">
          {data.items.length === 0 ? (
            <EmptyState
              title="No analysis runs yet"
              description="Use Analyze New or Analyze All on the Transactions page."
            />
          ) : (
            <>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Run #</th>
                      <th scope="col">Date</th>
                      <th scope="col">Mode</th>
                      <th scope="col">Processed</th>
                      <th scope="col">Successful</th>
                      <th scope="col">Failed</th>
                      <th scope="col">Risk mix</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((run) => (
                      <tr key={run.id}>
                        <td>#{run.id}</td>
                        <td>{formatDateTime(run.started_at)}</td>
                        <td>{run.mode}</td>
                        <td>{run.total_transactions}</td>
                        <td>{run.successful}</td>
                        <td>{run.failed}</td>
                        <td className="muted">
                          {run.high_risk}H / {run.medium_risk}M / {run.low_risk}L
                        </td>
                        <td>
                          <Badge label={run.status} tone={riskBadgeTone(run.status)} />
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
            </>
          )}
        </article>
      ) : null}
    </div>
  );
}
