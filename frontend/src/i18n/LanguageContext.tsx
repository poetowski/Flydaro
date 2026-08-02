import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { en, type Dict } from "./en";
import { sk } from "./sk";
import type { Language, PluralEntry } from "./types";
import { interpolate } from "./interpolate";
import { pluralKeyFor } from "./pluralize";
import { getLanguage, setLanguage as persistLanguage } from "../lib/languagePreference";

const DICTS: Record<Language, Dict> = { en, sk };

function resolve(dict: Dict, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, part) => {
    if (acc && typeof acc === "object" && part in acc) {
      return (acc as Record<string, unknown>)[part];
    }
    return undefined;
  }, dict);
}

interface LanguageContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  tPlural: (key: string, count: number, params?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<LanguageContextValue | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(getLanguage);

  const value = useMemo<LanguageContextValue>(() => {
    const dict = DICTS[language];

    const t = (key: string, params?: Record<string, string | number>) => {
      const resolved = resolve(dict, key);
      if (typeof resolved !== "string") return key;
      return interpolate(resolved, params);
    };

    const tPlural = (key: string, count: number, params?: Record<string, string | number>) => {
      const resolved = resolve(dict, key) as PluralEntry | undefined;
      if (!resolved || typeof resolved !== "object") return key;
      const form = pluralKeyFor(language, count);
      return interpolate(resolved[form], { count, ...params });
    };

    return {
      language,
      setLanguage: (next: Language) => {
        setLanguageState(next);
        persistLanguage(next);
      },
      t,
      tPlural,
    };
  }, [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
