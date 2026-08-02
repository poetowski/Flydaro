import type { Language, PluralKey } from "./types";

// Slovak (CLDR rules): n=1 -> one; n=2..4 -> few; everything else (incl. 0) -> other.
// English: n=1 -> one; everything else -> other ("few" is carried in the dict
// shape for symmetry with Slovak, but English never selects it).
export function pluralKeyFor(language: Language, count: number): PluralKey {
  const n = Math.abs(count);
  if (language === "sk") {
    if (n === 1) return "one";
    if (n >= 2 && n <= 4) return "few";
    return "other";
  }
  return n === 1 ? "one" : "other";
}
