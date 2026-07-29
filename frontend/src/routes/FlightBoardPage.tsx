import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { listAircraftTypes } from "../api/aircraftTypes";
import { listAirports } from "../api/airports";
import { getFlightBoard } from "../api/flights";

const STATUS_LABELS: Record<string, string> = {
  AIRBORNE_OPEN: "Just took off -- betting open",
  AIRBORNE_LOCKED: "In flight -- betting closed",
  LANDING_SUSPECTED: "Landing...",
};

export function FlightBoardPage() {
  const [airportId, setAirportId] = useState<number | "all">("all");
  const [aircraftTypeId, setAircraftTypeId] = useState<number | "all">("all");

  const { data: airports } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const { data: aircraftTypes } = useQuery({
    queryKey: ["aircraft-types"],
    queryFn: listAircraftTypes,
  });
  const { data: flights, isLoading } = useQuery({
    queryKey: ["flights", "board", airportId, aircraftTypeId],
    queryFn: () =>
      getFlightBoard(
        airportId === "all" ? undefined : airportId,
        aircraftTypeId === "all" ? undefined : aircraftTypeId,
      ),
    refetchInterval: 12000,
  });

  const unlockedAirports = airports?.filter((airport) => airport.unlocked) ?? [];
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
          Aircraft type
          <select
            value={aircraftTypeId}
            onChange={(e) =>
              setAircraftTypeId(e.target.value === "all" ? "all" : Number(e.target.value))
            }
          >
            <option value="all">All types</option>
            {aircraftTypes?.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name} {type.unlocked ? "" : "-- locked"}
              </option>
            ))}
          </select>
        </label>
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
          const canBet = flight.bets_open && (aircraftType?.unlocked ?? false);
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
                {aircraftType && !aircraftType.unlocked && " -- pilot license required"}
              </div>
              <div className="flight-meta">
                First seen airborne: {new Date(flight.first_seen_at).toLocaleTimeString()}
              </div>
              {canBet ? (
                <Link className="button" to={`/flights/${flight.id}/bet`}>
                  Place bet
                </Link>
              ) : (
                <span className="muted">
                  {flight.bets_open ? "Pilot license required" : "Betting closed"}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
