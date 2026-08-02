const SEEN_ACHIEVEMENTS_KEY = "flydaro_seen_achievements";

export function getSeenAchievements(): Set<string> {
  const stored = localStorage.getItem(SEEN_ACHIEVEMENTS_KEY);
  if (!stored) return new Set();
  try {
    return new Set(JSON.parse(stored) as string[]);
  } catch {
    return new Set();
  }
}

export function markSeen(ids: string[]): void {
  if (ids.length === 0) return;
  const seen = getSeenAchievements();
  ids.forEach((id) => seen.add(id));
  localStorage.setItem(SEEN_ACHIEVEMENTS_KEY, JSON.stringify([...seen]));
}
