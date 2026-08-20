export function formatCurrency(amount: string | number, currency = "EUR"): string {
  const value = typeof amount === "string" ? parseFloat(amount) : amount;
  if (Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-EU", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-EU").format(value);
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function parseReasons(reason: string | null | undefined): string[] {
  if (!reason) return [];
  return reason
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);
}

export function riskBadgeTone(
  status: string | null | undefined,
): "high" | "medium" | "low" | "neutral" {
  if (!status) return "neutral";
  const upper = status.toUpperCase();
  if (upper === "NOT_PROVIDED" || upper === "NEW" || upper === "ANALYZING") return "neutral";
  if (
    upper.includes("HIGH") ||
    upper.includes("MISMATCH") ||
    upper.includes("REJECT") ||
    upper === "FAILED" ||
    upper === "ANALYSIS_FAILED"
  ) {
    return "high";
  }
  if (upper.includes("MEDIUM") || upper.includes("MANUAL") || upper.includes("ESCALAT") || upper === "PENDING") {
    return "medium";
  }
  if (
    upper.includes("LOW") ||
    upper === "MATCH" ||
    upper.includes("APPROV") ||
    upper === "ANALYZED" ||
    upper === "NORMAL"
  ) {
    return "low";
  }
  return "neutral";
}
