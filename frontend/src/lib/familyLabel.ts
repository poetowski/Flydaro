/** Short badge-friendly label from an aircraft family code, e.g.
 * "A320_FAMILY" -> "A320", "EMBRAER_EJET_FAMILY" -> "EMBRAER EJET". */
export function familyBadgeLabel(code: string): string {
  return code.replace(/_FAMILY$/, "").replace(/_/g, " ");
}
