import { apiClient } from "../client";
import type { Wallet } from "../../types/api";

export async function fetchWallet(): Promise<Wallet> {
  const { data } = await apiClient.get<Wallet>("/wallet/");
  return data;
}
