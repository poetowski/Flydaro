import type { Language } from "../i18n/types";

const LANGUAGE_KEY = "flydaro_language";

export function getLanguage(): Language {
  return localStorage.getItem(LANGUAGE_KEY) === "sk" ? "sk" : "en";
}

export function setLanguage(language: Language): void {
  localStorage.setItem(LANGUAGE_KEY, language);
}
