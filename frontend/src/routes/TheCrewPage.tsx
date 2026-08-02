import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listAirports, type Airport } from "../api/airports";
import { ApiError } from "../api/client";
import { getCrewOverview, hireCrew } from "../api/crew";
import { Modal } from "../components/Modal";
import { useLanguage } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";
import { useToast } from "../lib/ToastContext";

export function TheCrewPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { t } = useLanguage();
  const [error, setError] = useState<string | null>(null);
  const [confirmingAirport, setConfirmingAirport] = useState<Airport | null>(null);

  const {
    data: airports,
    isLoading: airportsIsLoading,
    isError: airportsIsError,
    error: airportsError,
  } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const {
    data: crewOverview,
    isLoading: crewIsLoading,
    isError: crewIsError,
    error: crewError,
  } = useQuery({ queryKey: ["crew"], queryFn: getCrewOverview });

  const crewByAirportId = new Map((crewOverview ?? []).map((entry) => [entry.airport_id, entry]));

  const totalCrew = (crewOverview ?? []).reduce((sum, c) => sum + c.crew_count, 0);
  const busyCrew = (crewOverview ?? []).reduce((sum, c) => sum + c.busy_count, 0);
  const idleCrew = totalCrew - busyCrew;

  // Unlocked-with-crew-data first, then locked -- same stable-sort convention as LicensesPage.
  const sortedAirports = [...(airports ?? [])].sort(
    (a, b) => Number(b.unlocked) - Number(a.unlocked),
  );

  const hireCrewMutation = useMutation({
    mutationFn: hireCrew,
    onSuccess: (crew) => {
      setError(null);
      setConfirmingAirport(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["crew"] });
      showToast(t("crew.toastHired", { icao4: crew.icao4, free: crew.free_count }));
    },
    onError: (err) =>
      setError(err instanceof ApiError ? translateApiError(err, t) : t("crew.couldNotHireCrew")),
  });

  return (
    <div className="page">
      <h1>{t("crew.title")}</h1>
      <p>{t("crew.intro")}</p>
      {error && <p className="form-error">{error}</p>}
      {(airportsIsLoading || crewIsLoading) && <p>{t("crew.loadingCrew")}</p>}
      {airportsIsError && (
        <p className="form-error">
          {t("crew.couldNotLoadAirports", { error: translateApiError(airportsError, t) })}
        </p>
      )}
      {crewIsError && (
        <p className="form-error">
          {t("crew.couldNotLoadCrew", { error: translateApiError(crewError, t) })}
        </p>
      )}

      <section className="card stat-row">
        <div className="stat-card">
          <p className="stat-value">{idleCrew}</p>
          <p className="stat-label">{t("crew.idleCrewMembersLabel")}</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{busyCrew}</p>
          <p className="stat-label">{t("crew.busyCrewMembersLabel")}</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{totalCrew}</p>
          <p className="stat-label">{t("crew.totalCrewMembersLabel")}</p>
        </div>
      </section>

      <section className="card">
        <ul className="license-list">
          {sortedAirports.map((airport: Airport) => {
            const crew = crewByAirportId.get(airport.id);
            return (
              <li key={airport.id} className="license-card">
                <div>
                  <strong>{airport.name}</strong> ({airport.icao4}) -- {airport.city},{" "}
                  {airport.country}
                  {airport.unlocked && crew && (
                    <div className="flight-meta">
                      {t("crew.crewDetailLine", {
                        total: crew.crew_count,
                        free: crew.free_count,
                        busy: crew.busy_count,
                      })}
                    </div>
                  )}
                </div>
                {!airport.unlocked ? (
                  <span className="badge">{t("crew.unlockAirportFirst")}</span>
                ) : (
                  <button
                    onClick={() => setConfirmingAirport(airport)}
                    disabled={hireCrewMutation.isPending}
                  >
                    {t("crew.hireCrewButton", { amount: crew?.next_hire_cost ?? "..." })}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      {confirmingAirport && (
        <Modal title={t("crew.confirmTitle")} onClose={() => setConfirmingAirport(null)}>
          <p>
            {t("crew.confirmBody", {
              name: confirmingAirport.name,
              icao4: confirmingAirport.icao4,
              amount: crewByAirportId.get(confirmingAirport.id)?.next_hire_cost ?? "...",
            })}
          </p>
          <div className="modal-row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button onClick={() => setConfirmingAirport(null)}>{t("common.cancel")}</button>
            <button
              className="button"
              disabled={hireCrewMutation.isPending}
              onClick={() => hireCrewMutation.mutate(confirmingAirport.id)}
            >
              {hireCrewMutation.isPending ? t("crew.hiringButton") : t("common.confirm")}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
