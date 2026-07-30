import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { listAircraftFamilies } from "../api/aircraftFamilies";
import { listAircraftTypes } from "../api/aircraftTypes";
import { listAirports } from "../api/airports";
import { getFlightBoard } from "../api/flights";

const STATUS_LABELS: Record<string, string> = {
  AIRBORNE_OPEN: "Just took off -- capacity open to rent",
  AIRBORNE_LOCKED: "In flight -- capacity closed",
  LANDING_SUSPECTED: "Landing...",
};

export function FlightBoardPage() {
  const queryClient = useQueryClient();
  const [airportId, setAirportId] = useState<number | "all">("all");
  const [aircraftFamilyId, setAircraftFamilyId] = useState<number | "all">("all");

  const { data: airports } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const { data: aircraftFamilies } = useQuery({
    queryKey: ["aircraft-families"],
    queryFn: listAircraftFamilies,
  });
  // Separate from the family filter control -- still needed to resolve each
  // flight card's specific real model name (e.g. "Airbus A321neo"), since a
  // flight's actual aircraft is always an individual type, only the filter
  // itself is family-scoped.
  const { data: aircraftTypes } = useQuery({
    queryKey: ["aircraft-types"],
    queryFn: listAircraftTypes,
  });
  const boardQueryKey = ["flights", "board", airportId, aircraftFamilyId];
  const { data: flights, isLoading, isFetching } = useQuery({
    queryKey: boardQueryKey,
    queryFn: () =>
      getFlightBoard(
        airportId === "all" ? undefined : airportId,
        aircraftFamilyId === "all" ? undefined : aircraftFamilyId,
      ),
    // No auto-refetch interval: OpenSky is only called ad hoc, when this
    // request is actually made -- loading the page, changing a filter, or
    // pressing Refresh below, not on a timer from every open tab.
  });

  const unlockedAirports = airports?.filter((airport) => airport.unlocked) ?? [];
  const unlockedAircraftFamilies = aircraftFamilies?.filter((family) => family.unlocked) ?? [];
  const aircraftTypeById = new Map((aircraftTypes ?? []).map((type) => [type.id, type]));

  return (
    <div className="page">
      <h1>Flight Board</h1>

      <div className="board-filters">
        <label className="airport-filter">
          Airport
          <select
            value={airportId}
            onChange={(e) =>
              setAirportId(e.target.value === "all" ? "all" : Number(e.target.value))
            }
          >
            <option value="all">All unlocked airports</option>
            {unlockedAirports.map((airport) => (
              <option key={airport.id} value={airport.id}>
                {airport.name} ({airport.icao4})
              </option>
            ))}
          </select>
        </label>

        <label className="airport-filter">
          Aircraft family
          <select
            value={aircraftFamilyId}
            onChange={(e) =>
              setAircraftFamilyId(e.target.value === "all" ? "all" : Number(e.target.value))
            }
          >
            <option value="all">All unlocked families</option>
            {unlockedAircraftFamilies.map((family) => (
              <option key={family.id} value={family.id}>
                {family.name}
              </option>
            ))}
          </select>
        </label>

        <button
          className="button"
          disabled={isFetching}
          onClick={() => queryClient.invalidateQueries({ queryKey: boardQueryKey })}
        >
          {isFetching ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <p className="muted">
        Want more airports or planes? Visit <Link to="/licenses">Licenses</Link>.
      </p>

      {isLoading && <p>Loading flights...</p>}
      {!isLoading && flights?.length === 0 && (
        <p>No aircraft currently airborne near your unlocked airports. Check back shortly.</p>
      )}

      <ul className="flight-list">
        {flights?.map((flight) => {
          const aircraftType = flight.aircraft_type_id
            ? aircraftTypeById.get(flight.aircraft_type_id)
            : undefined;
          const canRent = flight.capacity_open;
          return (
            <li key={flight.id} className="flight-card">
              <div>
                <strong>{flight.callsign ?? flight.icao24}</strong>
                <span className="flight-status">
                  {STATUS_LABELS[flight.status] ?? flight.status}
                </span>
              </div>
              <div className="flight-meta">
                {aircraftType ? aircraftType.name : "Unknown aircraft type"}
              </div>
              <div className="flight-meta">
                First seen airborne: {new Date(flight.first_seen_at).toLocaleTimeString()}
              </div>
              {canRent ? (
                <Link className="button" to={`/flights/${flight.id}/rent`}>
                  Rent capacity
                </Link>
              ) : (
                <span className="muted">Capacity closed</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
