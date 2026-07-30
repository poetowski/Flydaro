import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { claimRental, listMyRentals } from "../api/rentals";

export function RentalHistoryPage() {
  const queryClient = useQueryClient();
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
          <li key={rental.id} className="rental-card">
            <div>
              <strong>Rental #{rental.id}</strong>
              <span className={`rental-status rental-status-${rental.status.toLowerCase()}`}>
                {rental.status}
              </span>
            </div>
            <div>Rental fee: {rental.rental_fee_credits} credits</div>
            {rental.status === "RESOLVED" && (
              <div>
                Settlement: {rental.settlement_credits} credits
                {rental.resolution_reason && ` (${rental.resolution_reason})`}
                <button
                  className="button"
                  disabled={claimMutation.isPending}
                  onClick={() => claimMutation.mutate(rental.id)}
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
    </div>
  );
}
