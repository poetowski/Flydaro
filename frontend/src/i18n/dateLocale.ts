import type { Language } from "./types";

export function dateLocale(language: Language): string {
  return language === "sk" ? "sk-SK" : "en-US";
}
