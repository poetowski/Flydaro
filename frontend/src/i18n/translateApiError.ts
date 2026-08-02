import { ApiError } from "../api/client";

type TFunction = (key: string, params?: Record<string, string | number>) => string;

export function translateApiError(err: unknown, t: TFunction, fallbackKey = "errors.UNKNOWN"): string {
  if (err instanceof ApiError && err.code) {
    return t(`errors.${err.code}`, err.params);
  }
  return t(fallbackKey);
}
