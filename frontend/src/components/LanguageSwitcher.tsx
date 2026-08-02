import { useLanguage } from "../i18n";

export function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage();
  const next = language === "en" ? "sk" : "en";
  const flag = language === "en" ? "🇬🇧" : "🇸🇰";
  const label = language === "en" ? "Switch to Slovak" : "Switch to English";

  return (
    <button
      type="button"
      className="language-switcher"
      onClick={() => setLanguage(next)}
      aria-label={label}
      title={label}
    >
      {flag}
    </button>
  );
}
