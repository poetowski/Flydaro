import { apiRequest } from "./client";

export interface Wallet {
  balance_credits: number;
}

export const getWallet = (): Promise<Wallet> => apiRequest<Wallet>("/wallet/me");
