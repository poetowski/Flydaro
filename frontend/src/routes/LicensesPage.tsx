import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAircraftFamilies, type AircraftFamily } from "../api/aircraftFamilies";
import { listAirports, type Airport } from "../api/airports";
import { ApiError } from "../api/client";
import { unlockAircraftFamily, unlockAirport } from "../api/licenses";
import { Modal } from "../components/Modal";
import { useLanguage } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";
import { PAGE_ICONS } from "../lib/pageIcons";
import { useToast } from "../lib/ToastContext";

export function LicensesPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { t } = useLanguage();
  const [error, setError] = useState<string | null>(null);
  const [confirmingAirport, setConfirmingAirport] = useState<Airport | null>(null);
  const [confirmingFamily, setConfirmingFamily] = useState<AircraftFamily | null>(null);

  const {
    data: airports,
    isLoading: airportsIsLoading,
    isError: airportsIsError,
    error: airportsError,
  } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const {
    data: aircraftFamilies,
    isLoading: aircraftFamiliesIsLoading,
    isError: aircraftFamiliesIsError,
    error: aircraftFamiliesError,
  } = useQuery({
    queryKey: ["aircraft-families"],
    queryFn: listAircraftFamilies,
  });

  // Unlocked first, then locked -- stable sort so a freshly-unlocked item
  // just moves into the unlocked group instead of the whole list reordering.
  const sortedAirports = [...(airports ?? [])].sort(
    (a, b) => Number(b.unlocked) - Number(a.unlocked),
  );
  const sortedAircraftFamilies = [...(aircraftFamilies ?? [])].sort(
    (a, b) => Number(b.unlocked) - Number(a.unlocked),
  );

  const unlockAirportMutation = useMutation({
    mutationFn: unlockAirport,
    onSuccess: (airport) => {
      setError(null);
      setConfirmingAirport(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["airports"] });
      showToast(t("licenses.toastUnlockedAirport", { name: airport.name }));
    },
    onError: (err) =>
      setError(err instanceof ApiError ? translateApiError(err, t) : t("licenses.couldNotUnlockAirport")),
  });

  const unlockAircraftFamilyMutation = useMutation({
    mutationFn: unlockAircraftFamily,
    onSuccess: (family) => {
      setError(null);
      setConfirmingFamily(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["aircraft-families"] });
      showToast(t("licenses.toastUnlockedFamily", { name: family.name }));
    },
    onError: (err) =>
      setError(err instanceof ApiError ? translateApiError(err, t) : t("licenses.couldNotUnlockFamily")),
  });

  return (
    <div className="page">
      <h1>
        {PAGE_ICONS["/licenses"]} {t("licenses.title")}
      </h1>
      {error && <p className="form-error">{error}</p>}

      <section className="card">
        <h2>{t("licenses.airportLicensesHeading")}</h2>
        {airportsIsLoading && <p>{t("licenses.loadingAirports")}</p>}
        {airportsIsError && (
          <p className="form-error">
            {t("licenses.couldNotLoadAirports", { error: translateApiError(airportsError, t) })}
          </p>
        )}
        <ul className="license-list">
          {sortedAirports.map((airport: Airport) => (
            <li key={airport.id} className="license-card">
              <div>
                <strong>{airport.name}</strong> ({airport.icao4}) -- {airport.city},{" "}
                {airport.country}
              </div>
              {airport.unlocked ? (
                <span className="badge badge-unlocked">{t("licenses.unlockedBadge")}</span>
              ) : (
                <button
                  onClick={() => setConfirmingAirport(airport)}
                  disabled={unlockAirportMutation.isPending}
                >
                  {t("licenses.unlockButton", { amount: airport.unlock_cost_credits })}
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>{t("licenses.pilotLicensesHeading")}</h2>
        {aircraftFamiliesIsLoading && <p>{t("licenses.loadingAircraftLicenses")}</p>}
        {aircraftFamiliesIsError && (
          <p className="form-error">
            {t("licenses.couldNotLoadAircraftLicenses", {
              error: translateApiError(aircraftFamiliesError, t),
            })}
          </p>
        )}
        <ul className="license-list">
          {sortedAircraftFamilies.map((family: AircraftFamily) => (
            <li key={family.id} className="license-card">
              <div>
                <strong>{family.name}</strong>
                <div className="flight-meta">
                  {t("licenses.coversPrefix")}
                  {family.member_types.map((memberType) => memberType.name).join(", ")}
                </div>
              </div>
              {family.unlocked ? (
                <span className="badge badge-unlocked">{t("licenses.unlockedBadge")}</span>
              ) : (
                <button
                  onClick={() => setConfirmingFamily(family)}
                  disabled={unlockAircraftFamilyMutation.isPending}
                >
                  {t("licenses.unlockButton", { amount: family.unlock_cost_credits })}
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>

      {confirmingAirport && (
        <Modal title={t("licenses.confirmAirportTitle")} onClose={() => setConfirmingAirport(null)}>
          <p>
            {t("licenses.confirmAirportBody", {
              name: confirmingAirport.name,
              icao4: confirmingAirport.icao4,
              amount: confirmingAirport.unlock_cost_credits,
            })}
          </p>
          <div className="modal-row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button onClick={() => setConfirmingAirport(null)}>{t("common.cancel")}</button>
            <button
              className="button"
              disabled={unlockAirportMutation.isPending}
              onClick={() => unlockAirportMutation.mutate(confirmingAirport.id)}
            >
              {unlockAirportMutation.isPending ? t("licenses.unlockingButton") : t("common.confirm")}
            </button>
          </div>
        </Modal>
      )}

      {confirmingFamily && (
        <Modal title={t("licenses.confirmFamilyTitle")} onClose={() => setConfirmingFamily(null)}>
          <p>
            {t("licenses.confirmFamilyBody", {
              name: confirmingFamily.name,
              amount: confirmingFamily.unlock_cost_credits,
            })}
          </p>
          <div className="modal-row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button onClick={() => setConfirmingFamily(null)}>{t("common.cancel")}</button>
            <button
              className="button"
              disabled={unlockAircraftFamilyMutation.isPending}
              onClick={() => unlockAircraftFamilyMutation.mutate(confirmingFamily.id)}
            >
              {unlockAircraftFamilyMutation.isPending ? t("licenses.unlockingButton") : t("common.confirm")}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
