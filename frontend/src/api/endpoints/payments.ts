import { apiClient } from "../client";
import type { Paginated } from "../../types/api";
import type { DepositGateway, Transaction } from "../../types/payments";

export interface CreateDepositPayload {
  amount: number;
  gateway?: DepositGateway;
}

export async function createDeposit(payload: CreateDepositPayload): Promise<Transaction> {
  const { data } = await apiClient.post<Transaction>("/payments/deposits/", payload);
  return data;
}

export async function fetchDeposits(): Promise<Transaction[]> {
  const { data } = await apiClient.get<Paginated<Transaction>>("/payments/deposits/", {
    params: { page_size: 50 },
  });
  return data.results;
}

export async function fetchDepositStatus(reference: string): Promise<Transaction> {
  const { data } = await apiClient.get<Transaction>(`/payments/deposits/${reference}/`);
  return data;
}
