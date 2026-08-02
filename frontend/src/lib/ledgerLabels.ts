import { useLanguage } from "../i18n";

const KNOWN_REASONS = new Set([
  "signup_bonus",
  "rental_fee",
  "settlement",
  "license_purchase",
  "item_type_purchase",
  "crew_hire",
  "admin_adjustment",
]);

export function useReasonLabel() {
  const { t } = useLanguage();
  return (reason: string) => (KNOWN_REASONS.has(reason) ? t(`ledgerReasons.${reason}`) : reason);
}
