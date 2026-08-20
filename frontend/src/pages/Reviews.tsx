import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAsyncData } from "../hooks/useAsyncData";
import { getReviews } from "../lib/api";
import { formatCurrency, riskBadgeTone } from "../lib/format";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { EmptyState } from "../components/ui/EmptyState";
import { Pagination } from "../components/ui/Pagination";

export function ReviewsPage() {
  const [page, setPage] = useState(1);

  const params = useMemo(() => {
    return new URLSearchParams({ page: String(page), limit: "20" });
  }, [page]);

  const { data, loading, error, status, reload } = useAsyncData(
    () => getReviews(params),
    [params.toString()],
  );

  return (
    <div className="page">
      <PageHeader
        title="Reviews"
        description="Pending and completed human decisions on AI recommendations."
      />

      {loading ? <LoadingState label="Loading reviews..." /> : null}
      {error ? <ErrorAlert message={error} status={status} onRetry={reload} /> : null}

      {data ? (
        <article className="panel">
          {data.items.length === 0 ? (
            <EmptyState
              title="No reviews yet"
              description="Analyze unusual transactions to generate review recommendations."
            />
          ) : (
            <>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Transaction</th>
                      <th scope="col">Vendor</th>
                      <th scope="col">Amount</th>
                      <th scope="col">Risk</th>
                      <th scope="col">Recommendation</th>
                      <th scope="col">Invoice</th>
                      <th scope="col">Decision</th>
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
                        <td>{formatCurrency(item.amount)}</td>
                        <td>
                          {item.final_risk ? (
                            <Badge
                              label={item.final_risk}
                              tone={riskBadgeTone(item.final_risk)}
                            />
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          {item.decision
                            ? item.decision.replaceAll("_", " ")
                            : "—"}
                        </td>
                        <td>
                          {item.invoice_status
                            ? item.invoice_status.replaceAll("_", " ")
                            : "—"}
                        </td>
                        <td>{item.review_status ?? "—"}</td>
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
