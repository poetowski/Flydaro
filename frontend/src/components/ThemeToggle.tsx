import { useLanguage } from "../i18n";
import { useTheme } from "../lib/ThemeContext";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const { t } = useLanguage();
  const next = theme === "light" ? "dark" : "light";
  const icon = theme === "light" ? "🌙" : "☀️";
  const label = theme === "light" ? t("theme.switchToDark") : t("theme.switchToLight");

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={() => setTheme(next)}
      aria-label={label}
      title={label}
    >
      {icon}
    </button>
  );
}
