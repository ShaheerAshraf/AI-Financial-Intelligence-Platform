type BadgeTone = "high" | "medium" | "low" | "match" | "mismatch" | "neutral" | "success" | "warning";

interface BadgeProps {
  label: string;
  tone?: BadgeTone;
}

export function Badge({ label, tone = "neutral" }: BadgeProps) {
  return <span className={`badge badge-${tone}`}>{label}</span>;
}
