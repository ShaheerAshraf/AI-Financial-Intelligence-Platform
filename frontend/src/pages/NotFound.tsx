import { Link } from "react-router-dom";
import { PageHeader } from "../components/ui/PageHeader";

export function NotFoundPage() {
  return (
    <div className="page">
      <PageHeader
        title="Page not found"
        description="The page you requested does not exist in this dashboard."
      />
      <div className="panel">
        <Link to="/" className="btn btn-primary">
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
