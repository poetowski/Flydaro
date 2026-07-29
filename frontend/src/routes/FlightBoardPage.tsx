import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { listAirports } from "../api/airports";
import { getFlightBoard } from "../api/flights";

const STATUS_LABELS: Record<string, string> = {
  AIRBORNE_OPEN: "Just took off -- betting open",
  AIRBORNE_LOCKED: "In flight -- betting closed",
  LANDING_SUSPECTED: "Landing...",
};

export function FlightBoardPage() {
  const [airportId, setAirportId] = useState<number | "all">("all");

  const { data: airports } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const { data: flights, isLoading } = useQuery({
    queryKey: ["flights", "board", airportId],
    queryFn: () => getFlightBoard(airportId === "all" ? undefined : airportId),
    refetchInterval: 12000,
  });

  return (
    <div className="page">
      <h1>Flight Board</h1>

      <label className="airport-filter">
        Airport
        <select
          value={airportId}
          onChange={(e) => setAirportId(e.target.value === "all" ? "all" : Number(e.target.value))}
        >
          <option value="all">All starter airports</option>
          {airports?.map((airport) => (
            <option key={airport.id} value={airport.id}>
              {airport.name} ({airport.icao4})
            </option>
          ))}
        </select>
      </label>

      {isLoading && <p>Loading flights...</p>}
      {!isLoading && flights?.length === 0 && (
        <p>No aircraft currently airborne near your starter airports. Check back shortly.</p>
      )}

      <ul className="flight-list">
        {flights?.map((flight) => (
          <li key={flight.id} className="flight-card">
            <div>
              <strong>{flight.callsign ?? flight.icao24}</strong>
              <span className="flight-status">
                {STATUS_LABELS[flight.status] ?? flight.status}
              </span>
            </div>
            <div className="flight-meta">
              First seen airborne: {new Date(flight.first_seen_at).toLocaleTimeString()}
            </div>
            {flight.bets_open ? (
              <Link className="button" to={`/flights/${flight.id}/bet`}>
                Place bet
              </Link>
            ) : (
              <span className="muted">Betting closed</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
