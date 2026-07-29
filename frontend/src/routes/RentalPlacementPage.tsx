import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createRental } from "../api/rentals";
import { listItemTypes } from "../api/itemTypes";
import { ApiError } from "../api/client";
import { getFlight } from "../api/flights";

export function RentalPlacementPage() {
  const { flightId } = useParams<{ flightId: string }>();
  const numericFlightId = Number(flightId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: flight } = useQuery({
    queryKey: ["flights", numericFlightId],
    queryFn: () => getFlight(numericFlightId),
  });
  const { data: itemTypes } = useQuery({ queryKey: ["item-types"], queryFn: listItemTypes });

  const [itemTypeId, setItemTypeId] = useState<number | null>(null);
  const [rentalFee, setRentalFee] = useState(100);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (itemTypeId === null) {
      setError("Pick an item type first");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await createRental(numericFlightId, itemTypeId, rentalFee);
      await queryClient.invalidateQueries({ queryKey: ["wallet"] });
      await queryClient.invalidateQueries({ queryKey: ["rentals", "mine"] });
      navigate("/rentals");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not rent capacity");
    } finally {
      setSubmitting(false);
    }
  }

  if (!flight) return <p className="page">Loading flight...</p>;

  if (!flight.capacity_open) {
    return (
      <div className="page">
        <h1>Capacity closed</h1>
        <p>Capacity on {flight.callsign ?? flight.icao24} is no longer available to rent.</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Rent capacity on {flight.callsign ?? flight.icao24}</h1>
      <form className="rental-form" onSubmit={handleSubmit}>
        {error && <p className="form-error">{error}</p>}

        <fieldset>
          <legend>Item type</legend>
          {itemTypes?.map((item) => (
            <label key={item.id} className="item-option">
              <input
                type="radio"
                name="itemType"
                value={item.id}
                checked={itemTypeId === item.id}
                onChange={() => setItemTypeId(item.id)}
              />
              <span>
                <strong>{item.name}</strong> ({item.category}, {item.settlement_multiplier}x) -- {item.flavor_text}
              </span>
            </label>
          ))}
        </fieldset>

        <label>
          Rental fee (credits)
          <input
            type="number"
            min={1}
            value={rentalFee}
            onChange={(e) => setRentalFee(Number(e.target.value))}
          />
        </label>

        <button type="submit" disabled={submitting}>
          {submitting ? "Renting capacity..." : "Rent capacity"}
        </button>
      </form>
    </div>
  );
}
