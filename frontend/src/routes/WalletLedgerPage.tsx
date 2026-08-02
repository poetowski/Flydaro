import { useQuery } from "@tanstack/react-query";
import { getWalletLedger } from "../api/wallet";
import { useLanguage, dateLocale } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";
import { useReasonLabel } from "../lib/ledgerLabels";

export function WalletLedgerPage() {
  const { t, language } = useLanguage();
  const reasonLabel = useReasonLabel();
  const {
    data: entries,
    isLoading,
    isError,
    error,
  } = useQuery({ queryKey: ["wallet", "ledger"], queryFn: getWalletLedger });

  return (
    <div className="page">
      <h1>{t("walletLedger.title")}</h1>
      <p className="muted">{t("walletLedger.subtitle")}</p>

      {isError && (
        <p className="form-error">
          {t("walletLedger.couldNotLoadLedger", { error: translateApiError(error, t) })}
        </p>
      )}
      {isLoading && <p>{t("walletLedger.loadingLedger")}</p>}
      {!isLoading && !isError && entries?.length === 0 && <p>{t("walletLedger.noMovements")}</p>}

      <ul className="ledger-list">
        {entries?.map((entry) => (
          <li key={entry.id} className="ledger-entry">
            <div>
              <strong>{reasonLabel(entry.reason)}</strong>
              {entry.related_rental_code && (
                <span className="flight-meta"> -- {entry.related_rental_code}</span>
              )}
            </div>
            <div className="flight-meta">
              {new Date(entry.created_at).toLocaleString(dateLocale(language))}
            </div>
            <div className={entry.delta_credits >= 0 ? "ledger-amount-positive" : "ledger-amount-negative"}>
              {entry.delta_credits >= 0 ? "+" : ""}
              {t("common.creditsAmount", { amount: entry.delta_credits })}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
