import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAircraftFamilies, type AircraftFamily } from "../api/aircraftFamilies";
import { listAirports, type Airport } from "../api/airports";
import { ApiError } from "../api/client";
import { unlockAircraftFamily, unlockAirport } from "../api/licenses";

export function LicensesPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: airports } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const { data: aircraftFamilies } = useQuery({
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
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["airports"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not unlock airport"),
  });

  const unlockAircraftFamilyMutation = useMutation({
    mutationFn: unlockAircraftFamily,
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["aircraft-families"] });
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
                  onClick={() => unlockAirportMutation.mutate(airport.id)}
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
                  onClick={() => unlockAircraftFamilyMutation.mutate(family.id)}
                  disabled={unlockAircraftFamilyMutation.isPending}
                >
                  Unlock ({family.unlock_cost_credits} cr)
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
