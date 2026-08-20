import { useEffect, useState } from "react";
import { getHealth } from "../lib/api";

type HealthState = "checking" | "online" | "offline";

export function useApiHealth(pollMs = 30_000) {
  const [state, setState] = useState<HealthState>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const health = await getHealth();
        if (!cancelled) {
          setState(health.status === "ok" ? "online" : "offline");
        }
      } catch {
        if (!cancelled) setState("offline");
      }
    }

    check();
    const timer = window.setInterval(check, pollMs);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [pollMs]);

  return state;
}
