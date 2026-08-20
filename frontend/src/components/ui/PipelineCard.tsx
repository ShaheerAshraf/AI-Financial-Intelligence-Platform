import type { ReactNode } from "react";

interface PipelineCardProps {
  step: number;
  title: string;
  subtitle?: string;
  status?: "complete" | "missing" | "warning";
  children: ReactNode;
}

export function PipelineCard({
  step,
  title,
  subtitle,
  status = "complete",
  children,
}: PipelineCardProps) {
  return (
    <section className={`pipeline-card pipeline-${status}`}>
      <header className="pipeline-card-header">
        <span className="pipeline-step">{step}</span>
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      </header>
      <div className="pipeline-card-body">{children}</div>
    </section>
  );
}
