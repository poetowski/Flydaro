import { useQuery } from "@tanstack/react-query";
import { getPollerHealth } from "../api/admin";
import { ApiError } from "../api/client";

export function AdminPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["pollerHealth"],
    queryFn: getPollerHealth,
    refetchInterval: 15000,
  });

  if (error instanceof ApiError && error.status === 403) {
    return (
      <div className="page">
        <h1>Poller Health</h1>
        <p className="form-error">Admin access required.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="page">
        <h1>Poller Health</h1>
        <p>Loading...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page">
        <h1>Poller Health</h1>
        <p className="form-error">Could not load poller health.</p>
      </div>
    );
  }

  const { heartbeat, status_counts, recent_flights, active_airports } = data;
  const staleThresholdSeconds = heartbeat.expected_interval_seconds * 3;
  const isHealthy =
    heartbeat.seconds_since_last_tick != null &&
    heartbeat.seconds_since_last_tick < staleThresholdSeconds &&
    heartbeat.last_error == null;
  const hasEverTicked = heartbeat.last_tick_at != null;

  return (
    <div className="page">
      <h1>Poller Health</h1>

      <section className="card">
        <h2>
          Heartbeat{" "}
          {hasEverTicked ? (
            <span className={`badge ${isHealthy ? "badge-unlocked" : "badge-danger"}`}>
              {isHealthy ? "Healthy" : "Stale"}
            </span>
          ) : (
            <span className="badge">No ticks yet</span>
          )}
        </h2>
        <p className="flight-meta">
          Last tick: {heartbeat.last_tick_at ? new Date(heartbeat.last_tick_at).toLocaleString() : "never"}
        </p>
        <p className="flight-meta">
          Last success:{" "}
          {heartbeat.last_success_at ? new Date(heartbeat.last_success_at).toLocaleString() : "never"}
        </p>
        {heartbeat.last_error && <p className="form-error">Last error: {heartbeat.last_error}</p>}
        <p className="flight-meta">
          OpenSky credits remaining:{" "}
          {heartbeat.credits_remaining != null ? heartbeat.credits_remaining : "unknown"}
        </p>
        <p className="flight-meta">
          Last OpenSky call:{" "}
          {heartbeat.last_opensky_status != null ? (
            <span className={`badge ${heartbeat.last_opensky_status < 400 ? "badge-unlocked" : "badge-danger"}`}>
              HTTP {heartbeat.last_opensky_status}
            </span>
          ) : heartbeat.last_opensky_detail != null ? (
            <span className="badge badge-danger">No response</span>
          ) : (
            "never attempted"
          )}
        </p>
        {heartbeat.last_opensky_detail && (
          <p className="form-error">OpenSky response: {heartbeat.last_opensky_detail}</p>
        )}
        <p className="muted">Expected poll interval: {heartbeat.expected_interval_seconds}s</p>
      </section>

      <section className="card">
        <h2>Tracked Flights by Status</h2>
        <ul className="license-list">
          {status_counts.length === 0 && <li className="muted">No tracked flights yet.</li>}
          {status_counts.map((s) => (
            <li key={s.status} className="license-card">
              <span>{s.status}</span>
              <span className="badge">{s.count}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Recent Flights</h2>
        <ul className="flight-list">
          {recent_flights.length === 0 && <li className="muted">No tracked flights yet.</li>}
          {recent_flights.map((f) => (
            <li key={f.id} className="flight-card">
              <div>
                <strong>{f.callsign ?? f.icao24}</strong>
                <span className="flight-status">{f.status}</span>
              </div>
              <div className="flight-meta">
                {f.origin_airport_name} -- {f.aircraft_type_name ?? "Unresolved aircraft type"}
              </div>
              <div className="flight-meta">
                First seen: {new Date(f.first_seen_at).toLocaleString()}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Active Airports</h2>
        <ul className="license-list">
          {active_airports.map((a) => (
            <li key={a.id} className="license-card">
              {a.name} ({a.icao4})
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
