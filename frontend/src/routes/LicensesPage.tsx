import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAircraftFamilies, type AircraftFamily } from "../api/aircraftFamilies";
import { listAirports, type Airport } from "../api/airports";
import { ApiError } from "../api/client";
import { unlockAircraftFamily, unlockAirport } from "../api/licenses";
import { Modal } from "../components/Modal";
import { useToast } from "../lib/ToastContext";

export function LicensesPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [confirmingAirport, setConfirmingAirport] = useState<Airport | null>(null);
  const [confirmingFamily, setConfirmingFamily] = useState<AircraftFamily | null>(null);

  const {
    data: airports,
    isLoading: airportsIsLoading,
    isError: airportsIsError,
    error: airportsError,
  } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const {
    data: aircraftFamilies,
    isLoading: aircraftFamiliesIsLoading,
    isError: aircraftFamiliesIsError,
    error: aircraftFamiliesError,
  } = useQuery({
    queryKey: ["aircraft-families"],
    queryFn: listAircraftFamilies,
  });

  // Unlocked first, then locked -- stable sort so a freshly-unlocked item
  // just moves into the unlocked group instead of the whole list reordering.
  const sortedAirports = [...(airports ?? [])].sort(
    (a, b) => Number(b.unlocked) - Number(a.unlocked),
  );
  const sortedAircraftFamilies = [...(aircraftFamilies ?? [])].sort(
    (a, b) => Number(b.unlocked) - Number(a.unlocked),
  );

  const unlockAirportMutation = useMutation({
    mutationFn: unlockAirport,
    onSuccess: (airport) => {
      setError(null);
      setConfirmingAirport(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["airports"] });
      showToast(`Unlocked ${airport.name}`);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not unlock airport"),
  });

  const unlockAircraftFamilyMutation = useMutation({
    mutationFn: unlockAircraftFamily,
    onSuccess: (family) => {
      setError(null);
      setConfirmingFamily(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["aircraft-families"] });
      showToast(`Unlocked ${family.name}`);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Could not unlock aircraft family"),
  });

  return (
    <div className="page">
      <h1>Licenses</h1>
      {error && <p className="form-error">{error}</p>}

      <section className="card">
        <h2>Airport Licenses</h2>
        {airportsIsLoading && <p>Loading airports...</p>}
        {airportsIsError && (
          <p className="form-error">
            Could not load airports:{" "}
            {airportsError instanceof ApiError ? airportsError.message : "unknown error"}
          </p>
        )}
        <ul className="license-list">
          {sortedAirports.map((airport: Airport) => (
            <li key={airport.id} className="license-card">
              <div>
                <strong>{airport.name}</strong> ({airport.icao4}) -- {airport.city},{" "}
                {airport.country}
              </div>
              {airport.unlocked ? (
                <span className="badge badge-unlocked">Unlocked</span>
              ) : (
                <button
                  onClick={() => setConfirmingAirport(airport)}
                  disabled={unlockAirportMutation.isPending}
                >
                  Unlock ({airport.unlock_cost_credits} cr)
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Pilot Licenses</h2>
        {aircraftFamiliesIsLoading && <p>Loading aircraft licenses...</p>}
        {aircraftFamiliesIsError && (
          <p className="form-error">
            Could not load aircraft licenses:{" "}
            {aircraftFamiliesError instanceof ApiError ? aircraftFamiliesError.message : "unknown error"}
          </p>
        )}
        <ul className="license-list">
          {sortedAircraftFamilies.map((family: AircraftFamily) => (
            <li key={family.id} className="license-card">
              <div>
                <strong>{family.name}</strong>
                <div className="flight-meta">
                  Covers: {family.member_types.map((t) => t.name).join(", ")}
                </div>
              </div>
              {family.unlocked ? (
                <span className="badge badge-unlocked">Unlocked</span>
              ) : (
                <button
                  onClick={() => setConfirmingFamily(family)}
                  disabled={unlockAircraftFamilyMutation.isPending}
                >
                  Unlock ({family.unlock_cost_credits} cr)
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>

      {confirmingAirport && (
        <Modal title="Confirm airport license" onClose={() => setConfirmingAirport(null)}>
          <p>
            Unlock <strong>{confirmingAirport.name}</strong> ({confirmingAirport.icao4}) for{" "}
            <strong>{confirmingAirport.unlock_cost_credits} credits</strong>?
          </p>
          <div className="modal-row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button onClick={() => setConfirmingAirport(null)}>Cancel</button>
            <button
              className="button"
              disabled={unlockAirportMutation.isPending}
              onClick={() => unlockAirportMutation.mutate(confirmingAirport.id)}
            >
              {unlockAirportMutation.isPending ? "Unlocking..." : "Confirm"}
            </button>
          </div>
        </Modal>
      )}

      {confirmingFamily && (
        <Modal title="Confirm pilot license" onClose={() => setConfirmingFamily(null)}>
          <p>
            Unlock <strong>{confirmingFamily.name}</strong> for{" "}
            <strong>{confirmingFamily.unlock_cost_credits} credits</strong>?
          </p>
          <div className="modal-row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button onClick={() => setConfirmingFamily(null)}>Cancel</button>
            <button
              className="button"
              disabled={unlockAircraftFamilyMutation.isPending}
              onClick={() => unlockAircraftFamilyMutation.mutate(confirmingFamily.id)}
            >
              {unlockAircraftFamilyMutation.isPending ? "Unlocking..." : "Confirm"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
