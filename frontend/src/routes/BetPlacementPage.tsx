import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { placeBet } from "../api/bets";
import { listCargoTypes } from "../api/cargo";
import { ApiError } from "../api/client";
import { getFlight } from "../api/flights";

export function BetPlacementPage() {
  const { flightId } = useParams<{ flightId: string }>();
  const numericFlightId = Number(flightId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: flight } = useQuery({
    queryKey: ["flights", numericFlightId],
    queryFn: () => getFlight(numericFlightId),
  });
  const { data: cargoTypes } = useQuery({ queryKey: ["cargo-types"], queryFn: listCargoTypes });

  const [cargoTypeId, setCargoTypeId] = useState<number | null>(null);
  const [stake, setStake] = useState(100);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (cargoTypeId === null) {
      setError("Pick a cargo type first");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await placeBet(numericFlightId, cargoTypeId, stake);
      await queryClient.invalidateQueries({ queryKey: ["wallet"] });
      await queryClient.invalidateQueries({ queryKey: ["bets", "mine"] });
      navigate("/bets");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not place bet");
    } finally {
      setSubmitting(false);
    }
  }

  if (!flight) return <p className="page">Loading flight...</p>;

  if (!flight.bets_open) {
    return (
      <div className="page">
        <h1>Betting closed</h1>
        <p>Betting for {flight.callsign ?? flight.icao24} has already closed.</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Bet on {flight.callsign ?? flight.icao24}</h1>
      <form className="bet-form" onSubmit={handleSubmit}>
        {error && <p className="form-error">{error}</p>}

        <fieldset>
          <legend>Cargo type</legend>
          {cargoTypes?.map((cargo) => (
            <label key={cargo.id} className="cargo-option">
              <input
                type="radio"
                name="cargoType"
                value={cargo.id}
                checked={cargoTypeId === cargo.id}
                onChange={() => setCargoTypeId(cargo.id)}
              />
              <span>
                <strong>{cargo.name}</strong> ({cargo.payout_multiplier}x) -- {cargo.flavor_text}
              </span>
            </label>
          ))}
        </fieldset>

        <label>
          Stake (credits)
          <input
            type="number"
            min={1}
            value={stake}
            onChange={(e) => setStake(Number(e.target.value))}
          />
        </label>

        <button type="submit" disabled={submitting}>
          {submitting ? "Placing bet..." : "Place bet"}
        </button>
      </form>
    </div>
  );
}
