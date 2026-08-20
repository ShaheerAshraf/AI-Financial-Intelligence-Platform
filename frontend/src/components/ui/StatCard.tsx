interface StatCardProps {
  label: string;
  value: number | string;
  hint?: string;
  tone?: "default" | "danger" | "warning" | "success";
}

export function StatCard({ label, value, hint, tone = "default" }: StatCardProps) {
  return (
    <article className={`stat-card stat-${tone}`}>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {hint ? <span className="stat-hint">{hint}</span> : null}
    </article>
  );
}
