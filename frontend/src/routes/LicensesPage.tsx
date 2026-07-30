import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAircraftTypes, type AircraftType } from "../api/aircraftTypes";
import { listAirports, type Airport } from "../api/airports";
import { ApiError } from "../api/client";
import { unlockAircraftType, unlockAirport } from "../api/licenses";

export function LicensesPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: airports } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const { data: aircraftTypes } = useQuery({
    queryKey: ["aircraft-types"],
    queryFn: listAircraftTypes,
  });

  // Unlocked first, then locked -- stable sort so a freshly-unlocked item
  // just moves into the unlocked group instead of the whole list reordering.
  const sortedAirports = [...(airports ?? [])].sort(
    (a, b) => Number(b.unlocked) - Number(a.unlocked),
  );
  const sortedAircraftTypes = [...(aircraftTypes ?? [])].sort(
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

  const unlockAircraftTypeMutation = useMutation({
    mutationFn: unlockAircraftType,
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["aircraft-types"] });
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Could not unlock aircraft type"),
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
          {sortedAircraftTypes.map((type: AircraftType) => (
            <li key={type.id} className="license-card">
              <div>
                <strong>{type.name}</strong> -- {type.manufacturer} ({type.icao_type_code})
              </div>
              {type.unlocked ? (
                <span className="badge badge-unlocked">Unlocked</span>
              ) : (
                <button
                  onClick={() => unlockAircraftTypeMutation.mutate(type.id)}
                  disabled={unlockAircraftTypeMutation.isPending}
                >
                  Unlock ({type.unlock_cost_credits} cr)
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
