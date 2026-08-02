import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createRental } from "../api/rentals";
import { listItemTypes } from "../api/itemTypes";
import { ApiError } from "../api/client";
import { getFlight } from "../api/flights";
import { Modal } from "../components/Modal";
import { useLanguage } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";
import { itemLabel } from "../lib/itemLabels";
import { useToast } from "../lib/ToastContext";

const RENTAL_FEE_MARKS = [100, 250, 500, 1000];

export function RentalPlacementPage() {
  const { flightId } = useParams<{ flightId: string }>();
  const numericFlightId = Number(flightId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { t, language } = useLanguage();

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
      setError(t("rentalPlacement.pickItemFirst"));
      return;
    }
    if (selectedItem && rentalFee < selectedItem.base_cost_credits) {
      setError(t("rentalPlacement.minFeeError", { amount: selectedItem.base_cost_credits }));
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
      showToast(t("rentalPlacement.toastRented"));
      navigate("/rentals");
    } catch (err) {
      setConfirming(false);
      setError(err instanceof ApiError ? translateApiError(err, t) : t("rentalPlacement.couldNotRent"));
    } finally {
      setSubmitting(false);
    }
  }

  if (flightIsError) {
    return (
      <div className="page">
        <h1>{t("rentalPlacement.couldNotLoadFlightTitle")}</h1>
        <p className="form-error">{translateApiError(flightError, t)}</p>
      </div>
    );
  }

  if (flightIsLoading || !flight) return <p className="page">{t("rentalPlacement.loadingFlight")}</p>;

  if (!flight.capacity_open) {
    return (
      <div className="page">
        <h1>{t("rentalPlacement.capacityClosedTitle")}</h1>
        <p>
          {t("rentalPlacement.capacityClosedBody", { callsign: flight.callsign ?? flight.icao24 })}
        </p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>{t("rentalPlacement.rentCapacityOnTitle", { callsign: flight.callsign ?? flight.icao24 })}</h1>
      <form className="rental-form" onSubmit={handleSubmit}>
        {error && <p className="form-error">{error}</p>}

        <fieldset>
          <legend>{t("rentalPlacement.itemTypeLegend")}</legend>
          {itemTypes?.map((item) => {
            const label = itemLabel(item.code, language, { name: item.name, flavorText: item.flavor_text });
            return (
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
                  <strong>{label.name}</strong> ({t(`itemCategory.${item.category}`)},{" "}
                  {item.settlement_multiplier}x) --{" "}
                  {item.base_cost_credits > 0
                    ? t("rentalPlacement.minFee", { amount: item.base_cost_credits })
                    : t("rentalPlacement.noMinimum")}{" "}
                  -- {label.flavorText}
                </span>
              </label>
            );
          })}
        </fieldset>

        <label>
          {t("rentalPlacement.rentalFeeLabel")} <strong>{t("common.creditsAmount", { amount: rentalFee })}</strong>
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
          {submitting ? t("rentalPlacement.rentingButton") : t("rentalPlacement.rentButton")}
        </button>
      </form>

      {confirming && selectedItem && (
        <Modal title={t("rentalPlacement.confirmTitle")} onClose={() => setConfirming(false)}>
          <p>
            {t("rentalPlacement.confirmBody", {
              callsign: flight.callsign ?? flight.icao24,
              item: itemLabel(selectedItem.code, language, {
                name: selectedItem.name,
                flavorText: selectedItem.flavor_text,
              }).name,
              amount: rentalFee,
            })}
          </p>
          <div className="modal-row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button onClick={() => setConfirming(false)}>{t("common.cancel")}</button>
            <button className="button" disabled={submitting} onClick={confirmAndSubmit}>
              {submitting ? t("rentalPlacement.confirmingButton") : t("common.confirm")}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
