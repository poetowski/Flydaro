import { useQuery } from "@tanstack/react-query";
import { ApiError } from "../api/client";
import { getWalletLedger } from "../api/wallet";
import { REASON_LABELS } from "../lib/ledgerLabels";

export function WalletLedgerPage() {
  const {
    data: entries,
    isLoading,
    isError,
    error,
  } = useQuery({ queryKey: ["wallet", "ledger"], queryFn: getWalletLedger });

  return (
    <div className="page">
      <h1>Wallet Ledger</h1>
      <p className="muted">Every credit movement on your account, newest first.</p>

      {isError && (
        <p className="form-error">
          Could not load your ledger: {error instanceof ApiError ? error.message : "unknown error"}
        </p>
      )}
      {isLoading && <p>Loading ledger...</p>}
      {!isLoading && !isError && entries?.length === 0 && <p>No credit movements yet.</p>}

      <ul className="ledger-list">
        {entries?.map((entry) => (
          <li key={entry.id} className="ledger-entry">
            <div>
              <strong>{REASON_LABELS[entry.reason] ?? entry.reason}</strong>
              {entry.related_rental_code && (
                <span className="flight-meta"> -- {entry.related_rental_code}</span>
              )}
            </div>
            <div className="flight-meta">{new Date(entry.created_at).toLocaleString()}</div>
            <div className={entry.delta_credits >= 0 ? "ledger-amount-positive" : "ledger-amount-negative"}>
              {entry.delta_credits >= 0 ? "+" : ""}
              {entry.delta_credits} credits
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
