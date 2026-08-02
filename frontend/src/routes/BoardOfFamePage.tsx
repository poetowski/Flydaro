import { useQuery } from "@tanstack/react-query";
import { getLeaderboard } from "../api/leaderboard";
import { useLanguage } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";
import { PAGE_ICONS } from "../lib/pageIcons";

const MEDALS: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };
const RANK_MODIFIER: Record<number, string> = {
  1: "leaderboard-entry-gold",
  2: "leaderboard-entry-silver",
  3: "leaderboard-entry-bronze",
};

export function BoardOfFamePage() {
  const { t } = useLanguage();
  const {
    data: entries,
    isLoading,
    isError,
    error,
  } = useQuery({ queryKey: ["leaderboard"], queryFn: getLeaderboard });

  return (
    <div className="page">
      <h1>
        {PAGE_ICONS["/board-of-fame"]} {t("boardOfFame.title")}
      </h1>
      <p className="muted">{t("boardOfFame.subtitle")}</p>

      {isError && (
        <p className="form-error">
          {t("boardOfFame.couldNotLoad", { error: translateApiError(error, t) })}
        </p>
      )}
      {isLoading && <p>{t("boardOfFame.loadingLeaderboard")}</p>}
      {!isLoading && !isError && entries?.length === 0 && <p>{t("boardOfFame.noPlayers")}</p>}

      <ul className="leaderboard-list">
        {entries?.map((entry) => (
          <li
            key={entry.rank}
            className={`leaderboard-entry ${RANK_MODIFIER[entry.rank] ?? ""}`}
          >
            <span className="leaderboard-rank">
              {MEDALS[entry.rank] ? `${MEDALS[entry.rank]} #${entry.rank}` : `#${entry.rank}`}
            </span>
            <span className="leaderboard-name">{entry.display_name}</span>
            <span className="badge badge-airport">{entry.credit_bracket}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
