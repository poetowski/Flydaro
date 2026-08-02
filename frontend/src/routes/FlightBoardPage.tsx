import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAircraftFamilies } from "../api/aircraftFamilies";
import { listAircraftTypes } from "../api/aircraftTypes";
import { listAirports } from "../api/airports";
import { getCrewOverview } from "../api/crew";
import { getFlightBoard } from "../api/flights";
import { useLanguage, dateLocale } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";
import { familyBadgeLabel } from "../lib/familyLabel";

// Discovery for airports due a fresh check now runs in the background
// after GET /flights/board returns (see backend/app/routers/flights.py),
// so this request's own response reflects whatever was already known --
// a flight the background pass just found wouldn't show up until the
// *next* fetch. One extra refetch a few seconds later -- generous for a
// couple of adsb.fi calls under its ~1 req/sec pacing -- picks it up
// without the user needing to press Refresh twice.
const FOLLOW_UP_REFETCH_DELAY_MS = 4000;

export function FlightBoardPage() {
  const queryClient = useQueryClient();
  const { t, language } = useLanguage();
  const [airportId, setAirportId] = useState<number | "all">("all");
  const [aircraftFamilyId, setAircraftFamilyId] = useState<number | "all">("all");
  const [showOnlyIdleCrew, setShowOnlyIdleCrew] = useState(true);

  const {
    data: airports,
    isError: airportsIsError,
    error: airportsError,
  } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const {
    data: aircraftFamilies,
    isError: aircraftFamiliesIsError,
    error: aircraftFamiliesError,
  } = useQuery({
    queryKey: ["aircraft-families"],
    queryFn: listAircraftFamilies,
  });
  // Separate from the family filter control -- still needed to resolve each
  // flight card's specific real model name (e.g. "Airbus A321neo"), since a
  // flight's actual aircraft is always an individual type, only the filter
  // itself is family-scoped.
  const { data: aircraftTypes } = useQuery({
    queryKey: ["aircraft-types"],
    queryFn: listAircraftTypes,
  });
  // Same query key TheCrewPage uses -- shares the cache across both pages.
  const { data: crewOverview } = useQuery({ queryKey: ["crew"], queryFn: getCrewOverview });
  const boardQueryKey = ["flights", "board", airportId, aircraftFamilyId];
  const {
    data: flights,
    isLoading,
    isFetching,
    isError: flightsIsError,
    error: flightsError,
  } = useQuery({
    queryKey: boardQueryKey,
    queryFn: () =>
      getFlightBoard(
        airportId === "all" ? undefined : airportId,
        aircraftFamilyId === "all" ? undefined : aircraftFamilyId,
      ),
    // No auto-refetch interval: the flight-data API is only called ad hoc,
    // when this request is actually made -- loading the page, changing a
    // filter, or pressing Refresh below, not on a timer from every open tab.
  });

  function scheduleFollowUpRefetch(): ReturnType<typeof setTimeout> {
    return setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: boardQueryKey });
    }, FOLLOW_UP_REFETCH_DELAY_MS);
  }

  useEffect(() => {
    const timeoutId = scheduleFollowUpRefetch();
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [airportId, aircraftFamilyId]);

  const unlockedAirports = airports?.filter((airport) => airport.unlocked) ?? [];
  const unlockedAircraftFamilies = aircraftFamilies?.filter((family) => family.unlocked) ?? [];
  const aircraftTypeById = new Map((aircraftTypes ?? []).map((type) => [type.id, type]));
  const airportById = new Map((airports ?? []).map((airport) => [airport.id, airport]));
  const familyCodeByTypeId = new Map(
    (aircraftFamilies ?? []).flatMap((family) =>
      family.member_types.map((type) => [type.id, family.code] as const),
    ),
  );
  const freeCountByAirportId = new Map(
    (crewOverview ?? []).map((entry) => [entry.airport_id, entry.free_count]),
  );
  const visibleFlights = (flights ?? []).filter(
    (flight) => !showOnlyIdleCrew || (freeCountByAirportId.get(flight.origin_airport_id) ?? 0) > 0,
  );

  return (
    <div className="page">
      <h1>{t("flightBoard.title")}</h1>

      {airportsIsError && (
        <p className="form-error">
          {t("flightBoard.couldNotLoadAirports", { error: translateApiError(airportsError, t) })}
        </p>
      )}
      {aircraftFamiliesIsError && (
        <p className="form-error">
          {t("flightBoard.couldNotLoadAircraftFamilies", {
            error: translateApiError(aircraftFamiliesError, t),
          })}
        </p>
      )}

      <div className="board-filters">
        <label className="airport-filter">
          {t("flightBoard.airportLabel")}
          <select
            value={airportId}
            onChange={(e) =>
              setAirportId(e.target.value === "all" ? "all" : Number(e.target.value))
            }
          >
            <option value="all">{t("flightBoard.allUnlockedAirports")}</option>
            {unlockedAirports.map((airport) => (
              <option key={airport.id} value={airport.id}>
                {airport.name} ({airport.icao4})
              </option>
            ))}
          </select>
        </label>

        <label className="airport-filter">
          {t("flightBoard.aircraftFamilyLabel")}
          <select
            value={aircraftFamilyId}
            onChange={(e) =>
              setAircraftFamilyId(e.target.value === "all" ? "all" : Number(e.target.value))
            }
          >
            <option value="all">{t("flightBoard.allUnlockedFamilies")}</option>
            {unlockedAircraftFamilies.map((family) => (
              <option key={family.id} value={family.id}>
                {family.name}
              </option>
            ))}
          </select>
        </label>

        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={showOnlyIdleCrew}
            onChange={(e) => setShowOnlyIdleCrew(e.target.checked)}
          />
          <span className="toggle-switch-track" />
          {t("flightBoard.showOnlyIdleCrew")}
        </label>

        <button
          className="button"
          disabled={isFetching}
          onClick={() => {
            queryClient.invalidateQueries({ queryKey: boardQueryKey });
            scheduleFollowUpRefetch();
          }}
        >
          {isFetching ? t("flightBoard.refreshing") : t("flightBoard.refresh")}
        </button>
      </div>

      <p className="muted">
        {t("flightBoard.wantMorePrefix")}
        <Link to="/licenses">{t("nav.licenses")}</Link>
        {t("flightBoard.wantMoreSuffix")}
      </p>
      <p className="muted">
        {t("flightBoard.liveDataPrefix")}
        <a href="https://adsb.fi" target="_blank" rel="noreferrer">
          adsb.fi
        </a>
        {t("flightBoard.liveDataSuffix")}
      </p>

      {flightsIsError && (
        <p className="form-error">
          {t("flightBoard.couldNotLoadBoard", { error: translateApiError(flightsError, t) })}
        </p>
      )}
      {isLoading && <p>{t("flightBoard.loadingFlights")}</p>}
      {!isLoading && !flightsIsError && visibleFlights.length === 0 && (
        <p>{t("flightBoard.noFlights")}</p>
      )}

      <ul className="flight-list">
        {visibleFlights.map((flight) => {
          const aircraftType = flight.aircraft_type_id
            ? aircraftTypeById.get(flight.aircraft_type_id)
            : undefined;
          const airport = airportById.get(flight.origin_airport_id);
          const familyCode = flight.aircraft_type_id
            ? familyCodeByTypeId.get(flight.aircraft_type_id)
            : undefined;
          const canRent = flight.capacity_open;
          return (
            <li key={flight.id} className="flight-card">
              <div>
                <strong>{flight.callsign ?? flight.icao24}</strong>
                <span className="flight-status">{t(`flightStatus.${flight.status}`)}</span>
              </div>
              <div>
                {airport && <span className="badge badge-airport">{airport.icao4}</span>}
                {familyCode && (
                  <span className="badge badge-family" style={{ marginLeft: 6 }}>
                    {familyBadgeLabel(familyCode)}
                  </span>
                )}
              </div>
              <div className="flight-meta">
                {aircraftType ? aircraftType.name : t("flightBoard.unknownAircraftType")}
              </div>
              <div className="flight-meta">
                {t("flightBoard.firstSeenAirborne", {
                  time: new Date(flight.first_seen_at).toLocaleTimeString(dateLocale(language)),
                })}
              </div>
              {canRent ? (
                <Link className="button" to={`/flights/${flight.id}/rent`}>
                  {t("flightBoard.rentCapacityLink")}
                </Link>
              ) : (
                <span className="muted">{t("flightBoard.capacityClosed")}</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
