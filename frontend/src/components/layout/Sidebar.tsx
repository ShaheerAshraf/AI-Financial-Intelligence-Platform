import { NavLink } from "react-router-dom";

const NAV_ITEMS: Array<{ to: string; label: string; end?: boolean }> = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/transactions", label: "Transactions" },
  { to: "/analysis-runs", label: "Analysis Runs" },
  { to: "/invoices", label: "Invoices" },
  { to: "/anomalies", label: "Anomalies" },
  { to: "/reviews", label: "Reviews" },
  { to: "/vendors", label: "Vendors" },
  { to: "/categories", label: "Categories" },
];

interface SidebarProps {
  apiState: "checking" | "online" | "offline";
  onNavigate?: () => void;
}

export function Sidebar({ apiState, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          FI
        </span>
        <div>
          <strong>Financial Intelligence</strong>
          <p>Multi-agent review platform</p>
        </div>
      </div>

      <nav className="nav" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              isActive ? "nav-link active" : "nav-link"
            }
            onClick={onNavigate}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <footer className="sidebar-footer">
        <div className={`api-status api-${apiState}`}>
          <span className="api-dot" aria-hidden="true" />
          <span>
            API{" "}
            {apiState === "checking"
              ? "checking..."
              : apiState === "online"
                ? "connected"
                : "offline"}
          </span>
        </div>
        <p className="sidebar-note">
          Add data · Run analysis · Investigate · Decide
        </p>
      </footer>
    </aside>
  );
}
