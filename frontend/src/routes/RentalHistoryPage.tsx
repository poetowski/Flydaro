import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAircraftTypes } from "../api/aircraftTypes";
import { listAirports } from "../api/airports";
import { ApiError } from "../api/client";
import { getFlight, getFlightSamples } from "../api/flights";
import { listItemTypes } from "../api/itemTypes";
import { claimRental, listMyRentals, type Rental } from "../api/rentals";
import { FlightTraceChart, type FlightTracePoint } from "../components/FlightTraceChart";
import { Modal } from "../components/Modal";
import { useLanguage, dateLocale } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";
import { familyBadgeLabel } from "../lib/familyLabel";
import { itemLabel } from "../lib/itemLabels";
import { PAGE_ICONS } from "../lib/pageIcons";
import { RENTAL_STATUS_ICONS } from "../lib/statusIcons";
import { useToast } from "../lib/ToastContext";

function RentalDetailModal({ rental, onClose }: { rental: Rental; onClose: () => void }) {
  const { t, language } = useLanguage();
  const { data: flight } = useQuery({
    queryKey: ["flights", rental.tracked_flight_id],
    queryFn: () => getFlight(rental.tracked_flight_id),
  });
  const { data: itemTypes } = useQuery({ queryKey: ["item-types"], queryFn: listItemTypes });
  const { data: airports } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const { data: aircraftTypes } = useQuery({
    queryKey: ["aircraft-types"],
    queryFn: listAircraftTypes,
  });
  const { data: samples } = useQuery({
    queryKey: ["flights", rental.tracked_flight_id, "samples"],
    queryFn: () => getFlightSamples(rental.tracked_flight_id),
  });

  const itemType = itemTypes?.find((t) => t.id === rental.item_type_id);
  const itemDisplayName = itemType
    ? itemLabel(itemType.code, language, { name: itemType.name, flavorText: itemType.flavor_text }).name
    : `#${rental.item_type_id}`;
  const airport = flight ? airports?.find((a) => a.id === flight.origin_airport_id) : undefined;
  const aircraftType = flight?.aircraft_type_id
    ? aircraftTypes?.find((t) => t.id === flight.aircraft_type_id)
    : undefined;
  const tracePoints: FlightTracePoint[] = (samples ?? [])
    .filter((s): s is typeof s & { baro_altitude: number } => s.baro_altitude !== null)
    .map((s) => ({ date: new Date(s.observed_at), altitude: s.baro_altitude }));

  const locale = dateLocale(language);

  return (
    <Modal title={rental.display_code} onClose={onClose}>
      <div className="modal-row">
        <span className="modal-row-label">{t("rentalHistory.statusLabel")}</span>
        <span>
          {RENTAL_STATUS_ICONS[rental.status]} {t(`rentalStatus.${rental.status}`)}
        </span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">{t("rentalHistory.itemLabel")}</span>
        <span>{itemDisplayName}</span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">{t("rentalHistory.rentalFeeLabel")}</span>
        <span>{t("common.creditsAmount", { amount: rental.rental_fee_credits })}</span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">{t("rentalHistory.rentedAtLabel")}</span>
        <span>{new Date(rental.rented_at).toLocaleString(locale)}</span>
      </div>

      {rental.resolved_at && (
        <>
          <div className="modal-row">
            <span className="modal-row-label">{t("rentalHistory.resolvedAtLabel")}</span>
            <span>{new Date(rental.resolved_at).toLocaleString(locale)}</span>
          </div>
          <div className="modal-row">
            <span className="modal-row-label">{t("rentalHistory.resolutionLabel")}</span>
            <span>
              {rental.resolution_reason
                ? t(`resolutionReason.${rental.resolution_reason}`)
                : t("rentalHistory.noneDash")}
            </span>
          </div>
          <div className="modal-row">
            <span className="modal-row-label">{t("rentalHistory.settlementLabel")}</span>
            <span>{t("common.creditsAmount", { amount: rental.settlement_credits ?? 0 })}</span>
          </div>
        </>
      )}
      {rental.claimed_at && (
        <div className="modal-row">
          <span className="modal-row-label">{t("rentalHistory.claimedAtLabel")}</span>
          <span>{new Date(rental.claimed_at).toLocaleString(locale)}</span>
        </div>
      )}

      <div className="modal-row">
        <span className="modal-row-label">{t("rentalHistory.flightLabel")}</span>
        <span>{flight?.callsign ?? flight?.icao24 ?? t("rentalHistory.loadingEllipsis")}</span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">{t("rentalHistory.aircraftLabel")}</span>
        <span>{aircraftType ? aircraftType.name : t("rentalHistory.unknownAircraft")}</span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">{t("rentalHistory.originAirportLabel")}</span>
        <span>
          {airport ? `${airport.name} (${airport.icao4})` : t("rentalHistory.loadingEllipsis")}
        </span>
      </div>
      {flight && (
        <>
          <div className="modal-row">
            <span className="modal-row-label">{t("rentalHistory.firstSeenLabel")}</span>
            <span>{new Date(flight.first_seen_at).toLocaleString(locale)}</span>
          </div>
          <div className="modal-row">
            <span className="modal-row-label">{t("rentalHistory.lastSeenLabel")}</span>
            <span>{new Date(flight.last_seen_at).toLocaleString(locale)}</span>
          </div>
        </>
      )}

      <h3>{t("rentalHistory.flightTraceHeading")}</h3>
      <FlightTraceChart
        points={tracePoints}
        language={language}
        emptyLabel={t("charts.flightTraceEmpty")}
        ariaLabel={t("charts.flightTraceLabel")}
      />
    </Modal>
  );
}

export function RentalHistoryPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { t } = useLanguage();
  const [selectedRental, setSelectedRental] = useState<Rental | null>(null);
  const { data: rentals, isLoading } = useQuery({
    queryKey: ["rentals", "mine"],
    queryFn: () => listMyRentals(),
  });
  const claimMutation = useMutation({
    mutationFn: claimRental,
    onSuccess: (rental) => {
      queryClient.invalidateQueries({ queryKey: ["rentals", "mine"] });
      showToast(t("rentalHistory.toastClaimed", { amount: rental.settlement_credits ?? 0 }));
    },
  });

  return (
    <div className="page">
      <h1>
        {PAGE_ICONS["/rentals"]} {t("rentalHistory.title")}
      </h1>
      {isLoading && <p>{t("rentalHistory.loadingRentals")}</p>}
      {!isLoading && rentals?.length === 0 && <p>{t("rentalHistory.noRentals")}</p>}

      <ul className="rental-list">
        {rentals?.map((rental) => (
          <li
            key={rental.id}
            className="rental-card rental-card-clickable"
            onClick={() => setSelectedRental(rental)}
          >
            <div>
              <strong>{rental.display_code}</strong>
              <span className={`rental-status rental-status-${rental.status.toLowerCase()}`}>
                {RENTAL_STATUS_ICONS[rental.status]} {t(`rentalStatusBadge.${rental.status}`)}
              </span>
            </div>
            <div>
              {rental.origin_airport_code && (
                <span className="badge badge-airport">{rental.origin_airport_code}</span>
              )}
              {rental.aircraft_family_code && (
                <span className="badge badge-family" style={{ marginLeft: 6 }}>
                  {familyBadgeLabel(rental.aircraft_family_code)}
                </span>
              )}
            </div>
            <div>{t("rentalHistory.rentalFeeLine", { amount: rental.rental_fee_credits })}</div>
            {rental.status === "RESOLVED" && (
              <div>
                {t("rentalHistory.settlementLine", { amount: rental.settlement_credits ?? 0 })}
                {rental.resolution_reason && ` (${t(`resolutionReason.${rental.resolution_reason}`)})`}
                <button
                  className="button"
                  disabled={claimMutation.isPending}
                  onClick={(e) => {
                    e.stopPropagation();
                    claimMutation.mutate(rental.id);
                  }}
                >
                  {t("rentalHistory.claimButton", { amount: rental.settlement_credits ?? 0 })}
                </button>
              </div>
            )}
            {rental.status === "CLAIMED" && (
              <div>
                {t("rentalHistory.claimedLine", { amount: rental.settlement_credits ?? 0 })}
                {rental.resolution_reason && ` (${t(`resolutionReason.${rental.resolution_reason}`)})`}
              </div>
            )}
          </li>
        ))}
      </ul>

      {claimMutation.isError && (
        <p className="form-error">
          {claimMutation.error instanceof ApiError
            ? translateApiError(claimMutation.error, t)
            : t("rentalHistory.couldNotClaim")}
        </p>
      )}

      {selectedRental && (
        <RentalDetailModal rental={selectedRental} onClose={() => setSelectedRental(null)} />
      )}
    </div>
  );
}
