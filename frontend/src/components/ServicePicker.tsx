import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Clock, Search, Tag, X } from "lucide-react";

import { fetchServices } from "../api/endpoints/catalog";
import { useMoney } from "../currency/CurrencyContext";
import type { Service } from "../types/api";
import { useTranslation } from "react-i18next";

/** Server-backed search instead of a native select holding every service.
 * The catalog runs to ~2,000 entries, which is unusable as a dropdown on a
 * phone and made the page fetch the whole catalog on every visit. */
export function ServicePicker({
  value,
  onChange,
}: {
  value: Service | null;
  onChange: (service: Service | null) => void;
}) {
  const { t } = useTranslation();
  const money = useMoney();
  const [term, setTerm] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(term.trim()), 250);
    return () => clearTimeout(timer);
  }, [term]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  const { data, isFetching } = useQuery({
    queryKey: ["service-search", debounced],
    queryFn: () => fetchServices({ search: debounced, page_size: 25 }),
    enabled: open && debounced.length >= 2,
    staleTime: 60 * 1000,
  });

  const results = data?.results ?? [];

  if (value) {
    return (
      <div className="service-picker__selected">
        <span className="icon-tile">
          <Tag size={16} />
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <strong>{value.name}</strong>
          <div className="service-picker__meta">
            <span>{value.category.name}</span>
            <span>{money(value.retail_rate_per_1000)} per 1000</span>
            <span>
              {t("common.min")} {value.min_quantity.toLocaleString()} - {value.max_quantity.toLocaleString()}
            </span>
            {value.average_time && (
              <span className="row" style={{ gap: "0.25rem" }}>
                <Clock size={12} /> {value.average_time}
              </span>
            )}
          </div>
        </div>
        <button
          type="button"
          className="btn-ghost btn-icon"
          onClick={() => {
            onChange(null);
            setTerm("");
          }}
          aria-label={t("newOrder.chooseDifferent")}
        >
          <X size={16} />
        </button>
      </div>
    );
  }

  return (
    <div className="service-picker" ref={boxRef}>
      <div className="service-picker__input-wrap">
        <Search size={16} />
        <input
          type="text"
          placeholder={t("newOrder.searchServices")}
          value={term}
          onChange={(e) => {
            setTerm(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
        />
      </div>

      {open && term.trim().length >= 2 && (
        <div className="service-picker__results">
          {isFetching && <div className="service-group">{t("newOrder.searching")}</div>}
          {!isFetching && results.length === 0 && (
            <div className="service-group">{t("newOrder.noServiceMatch")}</div>
          )}
          {results.map((service) => (
            <button
              key={service.id}
              type="button"
              className="service-picker__option"
              onClick={() => {
                onChange(service);
                setOpen(false);
              }}
            >
              <strong>{service.name}</strong>
              <span>
                {service.category.name} · {money(service.retail_rate_per_1000)} per 1000 ·
                min {service.min_quantity.toLocaleString()}
              </span>
            </button>
          ))}
        </div>
      )}

      {term.trim().length > 0 && term.trim().length < 2 && (
        <span className="field-hint">{t("newOrder.typeTwoChars")}</span>
      )}
    </div>
  );
}
