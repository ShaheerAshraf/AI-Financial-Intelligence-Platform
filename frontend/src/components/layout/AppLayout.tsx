import { useState } from "react";
import { Outlet } from "react-router-dom";
import { useApiHealth } from "../../hooks/useApiHealth";
import { Sidebar } from "./Sidebar";

export function AppLayout() {
  const apiState = useApiHealth();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      <button
        type="button"
        className="mobile-nav-toggle"
        aria-expanded={mobileOpen}
        aria-controls="app-sidebar"
        onClick={() => setMobileOpen((open) => !open)}
      >
        Menu
      </button>

      <div
        id="app-sidebar"
        className={mobileOpen ? "sidebar-panel open" : "sidebar-panel"}
      >
        <Sidebar apiState={apiState} onNavigate={() => setMobileOpen(false)} />
      </div>

      {mobileOpen ? (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
