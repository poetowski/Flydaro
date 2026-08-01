import { apiRequest } from "./client";

export interface Wallet {
  balance_credits: number;
}

export interface WalletLedgerEntry {
  id: number;
  delta_credits: number;
  reason: string;
  related_rental_id: number | null;
  related_rental_code: string | null;
  created_at: string;
}

export const getWallet = (): Promise<Wallet> => apiRequest<Wallet>("/wallet/me");

export const getWalletLedger = (): Promise<WalletLedgerEntry[]> =>
  apiRequest<WalletLedgerEntry[]>("/wallet/ledger");
