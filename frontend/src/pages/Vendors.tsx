import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useAsyncData } from "../hooks/useAsyncData";
import { createVendor, getCompanies, getVendors } from "../lib/api";
import type { CompanyItem } from "../types/api";
import { PageHeader } from "../components/ui/PageHeader";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { EmptyState } from "../components/ui/EmptyState";

export function VendorsPage() {
  const [companyId, setCompanyId] = useState<number | "">("");
  const [showForm, setShowForm] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const companies = useAsyncData(() => getCompanies(), []);
  const vendors = useAsyncData(
    () => getVendors(companyId === "" ? undefined : companyId),
    [companyId, reloadToken],
  );

  const companyMap = useMemo(() => {
    const map = new Map<number, string>();
    (companies.data ?? []).forEach((c: CompanyItem) => map.set(c.id, c.name));
    return map;
  }, [companies.data]);

  return (
    <div className="page">
      <PageHeader
        title="Vendors"
        description="Manage vendor master data used in transaction entry and CSV import."
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowForm((v) => !v)}
          >
            + Add Vendor
          </button>
        }
      />

      <div className="panel filters">
        <label>
          Filter by company
          <select
            value={companyId}
            onChange={(e) =>
              setCompanyId(e.target.value ? Number(e.target.value) : "")
            }
          >
            <option value="">All companies</option>
            {(companies.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {showForm ? (
        <AddVendorForm
          companies={companies.data ?? []}
          defaultCompanyId={companyId === "" ? undefined : companyId}
          onCancel={() => setShowForm(false)}
          onCreated={() => {
            setShowForm(false);
            setReloadToken((n) => n + 1);
          }}
        />
      ) : null}

      {vendors.loading ? <LoadingState label="Loading vendors..." /> : null}
      {vendors.error ? (
        <ErrorAlert message={vendors.error} onRetry={vendors.reload} />
      ) : null}

      {vendors.data ? (
        <article className="panel">
          {vendors.data.length === 0 ? (
            <EmptyState
              title="No vendors yet"
              description="Add vendors so transactions and CSV imports can resolve names."
            />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Company</th>
                    <th>Country</th>
                    <th>Email</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {vendors.data.map((vendor) => (
                    <tr key={vendor.id}>
                      <td>{vendor.name}</td>
                      <td>{companyMap.get(vendor.company_id) ?? vendor.company_id}</td>
                      <td>{vendor.country ?? "—"}</td>
                      <td>{vendor.email ?? "—"}</td>
                      <td>Active</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      ) : null}
    </div>
  );
}

function AddVendorForm({
  companies,
  defaultCompanyId,
  onCancel,
  onCreated,
}: {
  companies: CompanyItem[];
  defaultCompanyId?: number;
  onCancel: () => void;
  onCreated: () => void;
}) {
  const [companyId, setCompanyId] = useState(
    defaultCompanyId ? String(defaultCompanyId) : companies[0] ? String(companies[0].id) : "",
  );
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [country, setCountry] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createVendor({
        company_id: Number(companyId),
        name,
        email: email || undefined,
        country: country || undefined,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create vendor");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="panel form-panel">
      <h2>Add Vendor</h2>
      {error ? <ErrorAlert message={error} /> : null}
      <form className="master-form" onSubmit={handleSubmit}>
        <label>
          Company
          <select
            required
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
          >
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Name
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Country
          <input value={country} onChange={(e) => setCountry(e.target.value)} />
        </label>
        <div className="action-row full-width">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving..." : "Save Vendor"}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </article>
  );
}
