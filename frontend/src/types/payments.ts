export type DepositGateway = "nowpayments";

/** Mirrors apps.payments.models.Transaction.Status on the backend. */
export type DepositStatus =
  | "waiting"
  | "confirming"
  | "confirmed"
  | "sending"
  | "partially_paid"
  | "finished"
  | "failed"
  | "expired";

/** A statuses a deposit can still move on from. Anything else is final. */
export const PENDING_DEPOSIT_STATUSES: DepositStatus[] = [
  "waiting",
  "confirming",
  "confirmed",
  "sending",
];

export interface Transaction {
  id: string;
  gateway: DepositGateway;
  gateway_label: string;
  internal_reference: string;
  amount_local: string;
  amount_quote: string;
  quote_currency: string;
  pay_currency: string;
  status: DepositStatus;
  status_label: string;
  checkout_url: string;
  created_at: string;
  updated_at: string;
}
