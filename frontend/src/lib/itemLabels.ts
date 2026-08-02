import type { Language } from "../i18n/types";

export interface ItemLabel {
  name: string;
  flavorText: string;
}

const ITEM_LABELS_EN: Record<string, ItemLabel> = {
  FRUIT_AND_VEGETABLES: {
    name: "Fruit and Vegetables",
    flavorText: "Fresh produce -- steady demand, modest margins.",
  },
  ELECTRONICS: {
    name: "Electronics",
    flavorText: "Consumer electronics and components -- higher value, handle with care.",
  },
  MEDICAL: {
    name: "Medical Supplies",
    flavorText: "Pharmaceuticals and medical equipment -- time-critical and high-value.",
  },
  ECONOMY_PASSENGER: {
    name: "Economy Passenger",
    flavorText: "Budget travelers -- reliable, low-margin business.",
  },
  BUSINESS_PASSENGER: {
    name: "Business Passenger",
    flavorText: "Comfort seekers paying a premium for space and service.",
  },
  VIP_PASSENGER: {
    name: "VIP Passenger",
    flavorText: "High-value, high-stakes. Big payouts, less forgiving of hiccups.",
  },
};

const ITEM_LABELS_SK: Record<string, ItemLabel> = {
  FRUIT_AND_VEGETABLES: {
    name: "Ovocie a zelenina",
    flavorText: "Čerstvé produkty -- stály dopyt, skromné marže.",
  },
  ELECTRONICS: {
    name: "Elektronika",
    flavorText: "Spotrebná elektronika a súčiastky -- vyššia hodnota, treba zaobchádzať opatrne.",
  },
  MEDICAL: {
    name: "Zdravotnícky materiál",
    flavorText: "Lieky a zdravotnícke vybavenie -- časovo kritické a vysoko hodnotné.",
  },
  ECONOMY_PASSENGER: {
    name: "Cestujúci v ekonomickej triede",
    flavorText: "Rozpočtoví cestujúci -- spoľahlivý biznis s nízkou maržou.",
  },
  BUSINESS_PASSENGER: {
    name: "Cestujúci v biznis triede",
    flavorText: "Cestujúci hľadajúci pohodlie, ochotní priplatiť si za priestor a servis.",
  },
  VIP_PASSENGER: {
    name: "VIP cestujúci",
    flavorText: "Vysoká hodnota, vysoké riziko. Veľké výnosy, menej odpúšťa zaváhania.",
  },
};

const ITEM_LABELS: Record<Language, Record<string, ItemLabel>> = {
  en: ITEM_LABELS_EN,
  sk: ITEM_LABELS_SK,
};

/** Falls back to the raw backend `name`/`flavor_text` for any future item
 * code added server-side before its translation lands here. */
export function itemLabel(code: string, language: Language, fallback: ItemLabel): ItemLabel {
  return ITEM_LABELS[language][code] ?? fallback;
}
