import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createRental } from "../api/rentals";
import { listItemTypes } from "../api/itemTypes";
import { ApiError } from "../api/client";
import { getFlight } from "../api/flights";
import { Modal } from "../components/Modal";
import { useToast } from "../lib/ToastContext";

const RENTAL_FEE_MARKS = [100, 250, 500, 1000];

export function RentalPlacementPage() {
  const { flightId } = useParams<{ flightId: string }>();
  const numericFlightId = Number(flightId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const {
    data: flight,
    isLoading: flightIsLoading,
    isError: flightIsError,
    error: flightError,
  } = useQuery({
    queryKey: ["flights", numericFlightId],
    queryFn: () => getFlight(numericFlightId),
  });
  const { data: itemTypes } = useQuery({ queryKey: ["item-types"], queryFn: listItemTypes });

  const [itemTypeId, setItemTypeId] = useState<number | null>(null);
  const [rentalFeeIndex, setRentalFeeIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const selectedItem = itemTypes?.find((item) => item.id === itemTypeId);
  const rentalFee = RENTAL_FEE_MARKS[rentalFeeIndex];
  const minFeeIndex = selectedItem
    ? RENTAL_FEE_MARKS.findIndex((mark) => mark >= selectedItem.base_cost_credits)
    : 0;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (itemTypeId === null) {
      setError("Pick an item type first");
      return;
    }
    if (selectedItem && rentalFee < selectedItem.base_cost_credits) {
      setError(`This item requires a minimum rental fee of ${selectedItem.base_cost_credits} credits`);
      return;
    }
    setError(null);
    setConfirming(true);
  }

  async function confirmAndSubmit() {
    if (itemTypeId === null) return;
    setSubmitting(true);
    try {
      await createRental(numericFlightId, itemTypeId, rentalFee);
      await queryClient.invalidateQueries({ queryKey: ["wallet"] });
      await queryClient.invalidateQueries({ queryKey: ["rentals", "mine"] });
      showToast("Capacity rented!");
      navigate("/rentals");
    } catch (err) {
      setConfirming(false);
      setError(err instanceof ApiError ? err.message : "Could not rent capacity");
    } finally {
      setSubmitting(false);
    }
  }

  if (flightIsError) {
    return (
      <div className="page">
        <h1>Could not load this flight</h1>
        <p className="form-error">
          {flightError instanceof ApiError ? flightError.message : "unknown error"}
        </p>
      </div>
    );
  }

  if (flightIsLoading || !flight) return <p className="page">Loading flight...</p>;

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
                onChange={() => {
                  setItemTypeId(item.id);
                  const requiredIndex = RENTAL_FEE_MARKS.findIndex(
                    (mark) => mark >= item.base_cost_credits,
                  );
                  setRentalFeeIndex((prev) => Math.max(prev, requiredIndex));
                }}
              />
              <span>
                <strong>{item.name}</strong> ({item.category}, {item.settlement_multiplier}x) --{" "}
                {item.base_cost_credits > 0 ? `min ${item.base_cost_credits} credits` : "no minimum"} --{" "}
                {item.flavor_text}
              </span>
            </label>
          ))}
        </fieldset>

        <label>
          Rental fee: <strong>{rentalFee} credits</strong>
          <input
            type="range"
            min={minFeeIndex}
            max={RENTAL_FEE_MARKS.length - 1}
            step={1}
            value={rentalFeeIndex}
            onChange={(e) => setRentalFeeIndex(Number(e.target.value))}
          />
          <span className="rental-fee-marks">
            {RENTAL_FEE_MARKS.map((mark) => (
              <span key={mark}>{mark}</span>
            ))}
          </span>
        </label>

        <button type="submit" disabled={submitting}>
          {submitting ? "Renting capacity..." : "Rent capacity"}
        </button>
      </form>

      {confirming && selectedItem && (
        <Modal title="Confirm rental" onClose={() => setConfirming(false)}>
          <p>
            Rent capacity on <strong>{flight.callsign ?? flight.icao24}</strong> for{" "}
            <strong>{selectedItem.name}</strong> at a fee of{" "}
            <strong>{rentalFee} credits</strong>?
          </p>
          <div className="modal-row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button onClick={() => setConfirming(false)}>Cancel</button>
            <button className="button" disabled={submitting} onClick={confirmAndSubmit}>
              {submitting ? "Renting..." : "Confirm"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
