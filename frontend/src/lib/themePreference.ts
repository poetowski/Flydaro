export type Theme = "light" | "dark";

const THEME_KEY = "flydaro_theme";

export function getTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return "light";
}

export function setTheme(theme: Theme): void {
  localStorage.setItem(THEME_KEY, theme);
}
