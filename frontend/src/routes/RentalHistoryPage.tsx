import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAircraftTypes } from "../api/aircraftTypes";
import { listAirports } from "../api/airports";
import { ApiError } from "../api/client";
import { getFlight } from "../api/flights";
import { listItemTypes } from "../api/itemTypes";
import { claimRental, listMyRentals, type Rental } from "../api/rentals";
import { Modal } from "../components/Modal";
import { familyBadgeLabel } from "../lib/familyLabel";

const STATUS_LABELS: Record<string, string> = {
  PENDING: "Pending departure",
  IN_PROGRESS: "In flight",
  RESOLVING: "Landing...",
  RESOLVED: "Resolved",
  CLAIMED: "Claimed",
};

function RentalDetailModal({ rental, onClose }: { rental: Rental; onClose: () => void }) {
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

  const itemType = itemTypes?.find((t) => t.id === rental.item_type_id);
  const airport = flight ? airports?.find((a) => a.id === flight.origin_airport_id) : undefined;
  const aircraftType = flight?.aircraft_type_id
    ? aircraftTypes?.find((t) => t.id === flight.aircraft_type_id)
    : undefined;

  return (
    <Modal title={rental.display_code} onClose={onClose}>
      <div className="modal-row">
        <span className="modal-row-label">Status</span>
        <span>{STATUS_LABELS[rental.status] ?? rental.status}</span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">Item</span>
        <span>{itemType ? itemType.name : `#${rental.item_type_id}`}</span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">Rental fee</span>
        <span>{rental.rental_fee_credits} credits</span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">Rented at</span>
        <span>{new Date(rental.rented_at).toLocaleString()}</span>
      </div>

      {rental.resolved_at && (
        <>
          <div className="modal-row">
            <span className="modal-row-label">Resolved at</span>
            <span>{new Date(rental.resolved_at).toLocaleString()}</span>
          </div>
          <div className="modal-row">
            <span className="modal-row-label">Resolution</span>
            <span>{rental.resolution_reason ?? "--"}</span>
          </div>
          <div className="modal-row">
            <span className="modal-row-label">Settlement</span>
            <span>{rental.settlement_credits} credits</span>
          </div>
        </>
      )}
      {rental.claimed_at && (
        <div className="modal-row">
          <span className="modal-row-label">Claimed at</span>
          <span>{new Date(rental.claimed_at).toLocaleString()}</span>
        </div>
      )}

      <div className="modal-row">
        <span className="modal-row-label">Flight</span>
        <span>{flight?.callsign ?? flight?.icao24 ?? "Loading..."}</span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">Aircraft</span>
        <span>{aircraftType ? aircraftType.name : "Unknown"}</span>
      </div>
      <div className="modal-row">
        <span className="modal-row-label">Origin airport</span>
        <span>{airport ? `${airport.name} (${airport.icao4})` : "Loading..."}</span>
      </div>
      {flight && (
        <>
          <div className="modal-row">
            <span className="modal-row-label">First seen airborne</span>
            <span>{new Date(flight.first_seen_at).toLocaleString()}</span>
          </div>
          <div className="modal-row">
            <span className="modal-row-label">Last seen</span>
            <span>{new Date(flight.last_seen_at).toLocaleString()}</span>
          </div>
        </>
      )}
    </Modal>
  );
}

export function RentalHistoryPage() {
  const queryClient = useQueryClient();
  const [selectedRental, setSelectedRental] = useState<Rental | null>(null);
  const { data: rentals, isLoading } = useQuery({
    queryKey: ["rentals", "mine"],
    queryFn: () => listMyRentals(),
  });
  const claimMutation = useMutation({
    mutationFn: claimRental,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rentals", "mine"] }),
  });

  return (
    <div className="page">
      <h1>Rental History</h1>
      {isLoading && <p>Loading rentals...</p>}
      {!isLoading && rentals?.length === 0 && <p>No capacity rented yet.</p>}

      <ul className="rental-list">
        {rentals?.map((rental) => (
          <li
            key={rental.id}
            className="rental-card"
            onClick={() => setSelectedRental(rental)}
            style={{ cursor: "pointer" }}
          >
            <div>
              <strong>{rental.display_code}</strong>
              <span className={`rental-status rental-status-${rental.status.toLowerCase()}`}>
                {rental.status}
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
            <div>Rental fee: {rental.rental_fee_credits} credits</div>
            {rental.status === "RESOLVED" && (
              <div>
                Settlement: {rental.settlement_credits} credits
                {rental.resolution_reason && ` (${rental.resolution_reason})`}
                <button
                  className="button"
                  disabled={claimMutation.isPending}
                  onClick={(e) => {
                    e.stopPropagation();
                    claimMutation.mutate(rental.id);
                  }}
                >
                  Claim {rental.settlement_credits} credits
                </button>
              </div>
            )}
            {rental.status === "CLAIMED" && (
              <div>
                Claimed: {rental.settlement_credits} credits
                {rental.resolution_reason && ` (${rental.resolution_reason})`}
              </div>
            )}
          </li>
        ))}
      </ul>

      {claimMutation.isError && (
        <p className="form-error">
          {claimMutation.error instanceof ApiError
            ? claimMutation.error.message
            : "Could not claim reward"}
        </p>
      )}

      {selectedRental && (
        <RentalDetailModal rental={selectedRental} onClose={() => setSelectedRental(null)} />
      )}
    </div>
  );
}
