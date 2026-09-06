export function formatMoney(amount: string | number, currency = "TZS"): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  return `${value.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 })} ${currency}`;
}
