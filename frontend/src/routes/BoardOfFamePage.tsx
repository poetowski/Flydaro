import { useQuery } from "@tanstack/react-query";
import { ApiError } from "../api/client";
import { getLeaderboard } from "../api/leaderboard";

export function BoardOfFamePage() {
  const {
    data: entries,
    isLoading,
    isError,
    error,
  } = useQuery({ queryKey: ["leaderboard"], queryFn: getLeaderboard });

  return (
    <div className="page">
      <h1>Board of Fame in the Sky</h1>
      <p className="muted">The top 10 pilots by credits, ranked -- exact fortunes stay private.</p>

      {isError && (
        <p className="form-error">
          Could not load the board of fame: {error instanceof ApiError ? error.message : "unknown error"}
        </p>
      )}
      {isLoading && <p>Loading leaderboard...</p>}
      {!isLoading && !isError && entries?.length === 0 && <p>No players yet.</p>}

      <ul className="leaderboard-list">
        {entries?.map((entry) => (
          <li key={entry.rank} className="leaderboard-entry">
            <span className="leaderboard-rank">#{entry.rank}</span>
            <span className="leaderboard-name">{entry.display_name}</span>
            <span className="badge badge-airport">{entry.credit_bracket}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
