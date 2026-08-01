import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAirports, type Airport } from "../api/airports";
import { ApiError } from "../api/client";
import { getCrewOverview, hireCrew } from "../api/crew";
import { Modal } from "../components/Modal";
import { useToast } from "../lib/ToastContext";

export function TheCrewPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [confirmingAirport, setConfirmingAirport] = useState<Airport | null>(null);

  const {
    data: airports,
    isLoading: airportsIsLoading,
    isError: airportsIsError,
    error: airportsError,
  } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const {
    data: crewOverview,
    isLoading: crewIsLoading,
    isError: crewIsError,
    error: crewError,
  } = useQuery({ queryKey: ["crew"], queryFn: getCrewOverview });

  const crewByAirportId = new Map((crewOverview ?? []).map((entry) => [entry.airport_id, entry]));

  const totalCrew = (crewOverview ?? []).reduce((sum, c) => sum + c.crew_count, 0);
  const busyCrew = (crewOverview ?? []).reduce((sum, c) => sum + c.busy_count, 0);
  const idleCrew = totalCrew - busyCrew;

  // Unlocked-with-crew-data first, then locked -- same stable-sort convention as LicensesPage.
  const sortedAirports = [...(airports ?? [])].sort(
    (a, b) => Number(b.unlocked) - Number(a.unlocked),
  );

  const hireCrewMutation = useMutation({
    mutationFn: hireCrew,
    onSuccess: (crew) => {
      setError(null);
      setConfirmingAirport(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["crew"] });
      showToast(`Crew hired at ${crew.icao4} -- ${crew.free_count} now free`);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not hire crew"),
  });

  return (
    <div className="page">
      <h1>Crew</h1>
      <p>
        Crew members handle the logistics at an airport -- one is tied up for the entire
        duration of each rental originating there. Hire more to run rentals in parallel.
      </p>
      {error && <p className="form-error">{error}</p>}
      {(airportsIsLoading || crewIsLoading) && <p>Loading crew...</p>}
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

      <section className="card stat-row">
        <div className="stat-card">
          <p className="stat-value">{idleCrew}</p>
          <p className="stat-label">Idle Crew Members</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{busyCrew}</p>
          <p className="stat-label">Busy Crew Members</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{totalCrew}</p>
          <p className="stat-label">Total Crew Members</p>
        </div>
      </section>

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
                    onClick={() => setConfirmingAirport(airport)}
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

      {confirmingAirport && (
        <Modal title="Confirm crew hire" onClose={() => setConfirmingAirport(null)}>
          <p>
            Hire a new crew member at <strong>{confirmingAirport.name}</strong> (
            {confirmingAirport.icao4}) for{" "}
            <strong>{crewByAirportId.get(confirmingAirport.id)?.next_hire_cost ?? "..."} credits</strong>?
          </p>
          <div className="modal-row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button onClick={() => setConfirmingAirport(null)}>Cancel</button>
            <button
              className="button"
              disabled={hireCrewMutation.isPending}
              onClick={() => hireCrewMutation.mutate(confirmingAirport.id)}
            >
              {hireCrewMutation.isPending ? "Hiring..." : "Confirm"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
