import { Link } from "react-router-dom";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeToggle } from "../components/ThemeToggle";
import { useLanguage } from "../i18n";

export function NotFoundPage() {
  const { t } = useLanguage();
  return (
    <div className="page">
      <div className="corner-controls">
        <LanguageSwitcher />
        <ThemeToggle />
      </div>
      <h1>{t("notFound.title")}</h1>
      <p>
        {t("notFound.bodyPre")}
        <Link to="/">{t("notFound.backToDashboard")}</Link>
      </p>
    </div>
  );
}
