import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAirports, type Airport } from "../api/airports";
import { ApiError } from "../api/client";
import { getCrewOverview, hireCrew } from "../api/crew";

export function TheCrewPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const {
    data: airports,
    isError: airportsIsError,
    error: airportsError,
  } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const {
    data: crewOverview,
    isError: crewIsError,
    error: crewError,
  } = useQuery({ queryKey: ["crew"], queryFn: getCrewOverview });

  const crewByAirportId = new Map((crewOverview ?? []).map((entry) => [entry.airport_id, entry]));

  // Unlocked-with-crew-data first, then locked -- same stable-sort convention as LicensesPage.
  const sortedAirports = [...(airports ?? [])].sort(
    (a, b) => Number(b.unlocked) - Number(a.unlocked),
  );

  const hireCrewMutation = useMutation({
    mutationFn: hireCrew,
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["crew"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not hire crew"),
  });

  return (
    <div className="page">
      <h1>The Crew</h1>
      <p>
        Crew members handle the logistics at an airport -- one is tied up for the entire
        duration of each rental originating there. Hire more to run rentals in parallel.
      </p>
      {error && <p className="form-error">{error}</p>}
      {airportsIsError && (
        <p className="form-error">
          Could not load airports:{" "}
          {airportsError instanceof ApiError ? airportsError.message : "unknown error"}
        </p>
      )}
      {crewIsError && (
        <p className="form-error">
          Could not load crew:{" "}
          {crewError instanceof ApiError ? crewError.message : "unknown error"}
        </p>
      )}

      <section className="card">
        <ul className="license-list">
          {sortedAirports.map((airport: Airport) => {
            const crew = crewByAirportId.get(airport.id);
            return (
              <li key={airport.id} className="license-card">
                <div>
                  <strong>{airport.name}</strong> ({airport.icao4}) -- {airport.city},{" "}
                  {airport.country}
                  {airport.unlocked && crew && (
                    <div className="flight-meta">
                      Crew: {crew.crew_count} total -- {crew.free_count} free /{" "}
                      {crew.busy_count} assigned
                    </div>
                  )}
                </div>
                {!airport.unlocked ? (
                  <span className="badge">Unlock this airport first</span>
                ) : (
                  <button
                    onClick={() => hireCrewMutation.mutate(airport.id)}
                    disabled={hireCrewMutation.isPending}
                  >
                    Hire crew ({crew?.next_hire_cost ?? "..."} cr)
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
