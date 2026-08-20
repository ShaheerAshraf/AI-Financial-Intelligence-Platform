import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAsyncData } from "../hooks/useAsyncData";
import { getInvoices } from "../lib/api";
import { formatCurrency, formatDate, riskBadgeTone } from "../lib/format";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { EmptyState } from "../components/ui/EmptyState";
import { Pagination } from "../components/ui/Pagination";

export function InvoicesPage() {
  const [page, setPage] = useState(1);

  const params = useMemo(() => {
    return new URLSearchParams({ page: String(page), limit: "20" });
  }, [page]);

  const { data, loading, error, status, reload } = useAsyncData(
    () => getInvoices(params),
    [params.toString()],
  );

  return (
    <div className="page">
      <PageHeader
        title="Invoices"
        description="Extracted invoice details linked to transactions (PDF not stored)."
      />

      {loading ? <LoadingState label="Loading invoices..." /> : null}
      {error ? <ErrorAlert message={error} status={status} onRetry={reload} /> : null}

      {data ? (
        <article className="panel">
          {data.items.length === 0 ? (
            <EmptyState
              title="No invoices yet"
              description="Attach invoice text from a transaction investigation page."
            />
          ) : (
            <>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Invoice #</th>
                      <th scope="col">Vendor</th>
                      <th scope="col">Amount</th>
                      <th scope="col">Date</th>
                      <th scope="col">Extraction</th>
                      <th scope="col">Match</th>
                      <th scope="col">Transaction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((item) => (
                      <tr key={item.id}>
                        <td>{item.invoice_number ?? `INV-${item.id}`}</td>
                        <td>{item.vendor_name ?? "—"}</td>
                        <td>
                          {item.amount
                            ? formatCurrency(item.amount, item.currency ?? "EUR")
                            : "—"}
                        </td>
                        <td>
                          {item.invoice_date ? formatDate(item.invoice_date) : "—"}
                        </td>
                        <td>
                          <Badge
                            label={item.extraction_status}
                            tone={riskBadgeTone(item.extraction_status)}
                          />
                        </td>
                        <td>
                          {item.match_status ? (
                            <Badge
                              label={item.match_status.replaceAll("_", " ")}
                              tone={
                                item.match_status === "MATCH"
                                  ? "match"
                                  : "mismatch"
                              }
                            />
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          <Link to={`/investigation/${item.transaction_id}`}>
                            #{item.transaction_id}
                          </Link>
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
