import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="page">
      <h1>Page not found</h1>
      <p>
        That page doesn't exist. <Link to="/">Back to Dashboard</Link>
      </p>
    </div>
  );
}
