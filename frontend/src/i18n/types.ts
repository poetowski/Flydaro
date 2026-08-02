export type Language = "en" | "sk";

export type PluralKey = "one" | "few" | "other";

export interface PluralEntry {
  one: string;
  few: string;
  other: string;
}
