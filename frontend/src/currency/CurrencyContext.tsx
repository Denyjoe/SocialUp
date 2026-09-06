import { useQuery } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { apiClient } from "../api/client";

export interface ExchangeRates {
  base: string;
  rates: Record<string, string>;
  supported: string[];
  fetched_at: string | null;
  stale: boolean;
}

const STORAGE_KEY = "displayCurrency";

/** Symbols for the currencies we offer. Anything else falls back to the
 * code itself, which is still perfectly readable. */
const SYMBOLS: Record<string, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  KES: "KSh",
  UGX: "USh",
  RWF: "FRw",
  ZAR: "R",
  NGN: "₦",
  INR: "₹",
};

interface CurrencyValue {
  /** Currency the customer wants to read prices in. */
  currency: string;
  setCurrency: (code: string) => void;
  /** The currency everything is actually charged in. */
  base: string;
  supported: string[];
  rates: Record<string, string>;
  fetchedAt: string | null;
  /** True when we are showing anything other than the base currency, so
   * the UI can say the figure is approximate. */
  isConverted: boolean;
  /** Formats an amount that is denominated in the base currency. */
  format: (amount: string | number) => string;
}

const CurrencyContext = createContext<CurrencyValue | undefined>(undefined);

function readStored(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [chosen, setChosen] = useState<string>(readStored);

  const { data } = useQuery({
    queryKey: ["exchange-rates"],
    queryFn: async () => {
      const { data } = await apiClient.get<ExchangeRates>("/public/exchange-rates/");
      return data;
    },
    // Rates are refreshed hourly on the server, so this is plenty.
    staleTime: 30 * 60 * 1000,
  });

  const base = data?.base ?? "TZS";
  const rates = data?.rates ?? {};
  const supported = data?.supported ?? [base];

  // Fall back to the base currency if the stored choice is not offered any
  // more, so a withdrawn currency cannot leave prices unreadable.
  const currency = chosen && supported.includes(chosen) ? chosen : base;

  const setCurrency = useCallback((code: string) => {
    setChosen(code);
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch {
      // A blocked storage API should not stop the switch taking effect.
    }
  }, []);

  const format = useCallback(
    (amount: string | number) => {
      const value = typeof amount === "string" ? Number(amount) : amount;
      if (!Number.isFinite(value)) return `0 ${currency}`;

      if (currency === base) {
        return `${value.toLocaleString(undefined, {
          minimumFractionDigits: 0,
          maximumFractionDigits: 2,
        })} ${base}`;
      }

      const rate = Number(rates[currency]);
      if (!rate || rate <= 0) {
        // No usable rate: show the real figure rather than a guess.
        return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${base}`;
      }

      const converted = value * rate;
      const symbol = SYMBOLS[currency] ?? "";
      const shown = converted.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      return symbol ? `${symbol}${shown}` : `${shown} ${currency}`;
    },
    [currency, base, rates]
  );

  const value = useMemo<CurrencyValue>(
    () => ({
      currency,
      setCurrency,
      base,
      supported,
      rates,
      fetchedAt: data?.fetched_at ?? null,
      isConverted: currency !== base,
      format,
    }),
    [currency, setCurrency, base, supported, rates, data?.fetched_at, format]
  );

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useCurrency(): CurrencyValue {
  const ctx = useContext(CurrencyContext);
  if (!ctx) throw new Error("useCurrency must be used within a CurrencyProvider");
  return ctx;
}

/** Formats an amount denominated in the base currency into whatever the
 * customer chose to read prices in. */
export function useMoney() {
  return useCurrency().format;
}
