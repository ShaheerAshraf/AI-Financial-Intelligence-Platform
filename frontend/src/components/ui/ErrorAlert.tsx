interface ErrorAlertProps {
  message: string;
  status?: number | null;
  onRetry?: () => void;
}

export function ErrorAlert({ message, status, onRetry }: ErrorAlertProps) {
  return (
    <div className="error-alert" role="alert">
      <div>
        <strong>Unable to load data</strong>
        <p>{message}</p>
        {status ? <p className="muted">HTTP {status}</p> : null}
      </div>
      {onRetry ? (
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
