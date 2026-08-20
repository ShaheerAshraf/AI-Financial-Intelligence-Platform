import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useAsyncData } from "../hooks/useAsyncData";
import { createCategory, getCategories, getCompanies } from "../lib/api";
import type { CompanyItem } from "../types/api";
import { PageHeader } from "../components/ui/PageHeader";
import { LoadingState } from "../components/ui/LoadingState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { EmptyState } from "../components/ui/EmptyState";

export function CategoriesPage() {
  const [companyId, setCompanyId] = useState<number | "">("");
  const [showForm, setShowForm] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const companies = useAsyncData(() => getCompanies(), []);
  const categories = useAsyncData(
    () => getCategories(companyId === "" ? undefined : companyId),
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
        title="Categories"
        description="Manage spend categories used when creating and importing transactions."
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowForm((v) => !v)}
          >
            + Add Category
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
        <AddCategoryForm
          companies={companies.data ?? []}
          defaultCompanyId={companyId === "" ? undefined : companyId}
          onCancel={() => setShowForm(false)}
          onCreated={() => {
            setShowForm(false);
            setReloadToken((n) => n + 1);
          }}
        />
      ) : null}

      {categories.loading ? <LoadingState label="Loading categories..." /> : null}
      {categories.error ? (
        <ErrorAlert message={categories.error} onRetry={categories.reload} />
      ) : null}

      {categories.data ? (
        <article className="panel">
          {categories.data.length === 0 ? (
            <EmptyState
              title="No categories yet"
              description="Add categories so transaction forms and CSV imports can resolve names."
            />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Company</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.data.map((category) => (
                    <tr key={category.id}>
                      <td>{category.name}</td>
                      <td>
                        {companyMap.get(category.company_id) ?? category.company_id}
                      </td>
                      <td>{category.description ?? "—"}</td>
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

function AddCategoryForm({
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
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createCategory({
        company_id: Number(companyId),
        name,
        description: description || undefined,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create category");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="panel form-panel">
      <h2>Add Category</h2>
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
        <label className="full-width">
          Description
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <div className="action-row full-width">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving..." : "Save Category"}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </article>
  );
}
