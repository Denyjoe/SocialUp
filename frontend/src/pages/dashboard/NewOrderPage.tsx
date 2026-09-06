import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, HelpCircle, Link2, ShoppingCart, Ticket } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { fetchService } from "../../api/endpoints/catalog";
import { createOrder } from "../../api/endpoints/orders";
import { ServicePicker } from "../../components/ServicePicker";
import type { Order, Service } from "../../types/api";
import { extractErrorMessage } from "../../utils/errors";
import { useMoney } from "../../currency/CurrencyContext";
import { useTranslation } from "react-i18next";

export function NewOrderPage() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  const money = useMoney();
  const [params] = useSearchParams();
  const preselectedId = params.get("service");

  const [service, setService] = useState<Service | null>(null);

  // Arriving from the Services page with ?service=<id>: load that service
  // and drop it straight into the picker so the customer does not have to
  // search for what they already chose.
  const { data: preselected } = useQuery({
    queryKey: ["service", preselectedId],
    queryFn: () => fetchService(preselectedId!),
    enabled: !!preselectedId,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (preselected) setService(preselected);
  }, [preselected]);
  const [link, setLink] = useState("");
  const [quantity, setQuantity] = useState("");
  const [couponCode, setCouponCode] = useState("");
  const [showCoupon, setShowCoupon] = useState(false);
  const [placedOrder, setPlacedOrder] = useState<Order | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);

  const qty = Number(quantity);
  const estimatedCharge = useMemo(() => {
    if (!service || !qty || qty <= 0) return null;
    return (Number(service.retail_rate_per_1000) * qty) / 1000;
  }, [service, qty]);

  const mutation = useMutation({
    mutationFn: createOrder,
    onSuccess: (order) => {
      setPlacedOrder(order);
      setServerError(null);
      setLink("");
      setQuantity("");
      setCouponCode("");
      setService(null);
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (err) => setServerError(extractErrorMessage(err, t("newOrder.couldNotPlace"))),
  });

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setPlacedOrder(null);
    setFieldError(null);

    if (!service) return setFieldError(t("newOrder.chooseServiceFirst"));
    if (!link.trim()) return setFieldError(t("newOrder.enterLink"));
    if (!qty || qty <= 0) return setFieldError(t("newOrder.enterQuantity"));
    if (qty < service.min_quantity || qty > service.max_quantity) {
      return setFieldError(
        t("newOrder.quantityBetween", {
          min: service.min_quantity.toLocaleString(),
          max: service.max_quantity.toLocaleString(),
        })
      );
    }

    mutation.mutate({
      service: service.id,
      link: link.trim(),
      quantity: qty,
      coupon_code: couponCode.trim() || undefined,
    });
  }

  return (
    <>
      <div className="page-header-row">
        <h1>{t("newOrder.title")}</h1>
      </div>
      <p className="page-subtitle">{t("newOrder.subtitle")}</p>

      <div className="dashboard-columns">
        <section className="panel">
          <div className="panel-header">
            <span className="icon-tile">
              <ShoppingCart size={18} />
            </span>
            <h2>{t("newOrder.placeYourOrder")}</h2>
          </div>

          {serverError && <p className="form-error">{serverError}</p>}
          {fieldError && <p className="form-error">{fieldError}</p>}
          {placedOrder && (
            <p className="form-success">
              <CheckCircle2 size={15} style={{ verticalAlign: "-2px" }} />{" "}
              {t("newOrder.placedSuccess", {
                status: t(`orders.status.${placedOrder.status}`, placedOrder.status),
                amount: money(placedOrder.charge_amount),
              })}{" "}
              <Link to="/dashboard/orders">{t("newOrder.viewHistory")}</Link>
            </p>
          )}

          <form onSubmit={onSubmit} noValidate className="new-order-form">
            <label>
              {t("newOrder.service")}
              <ServicePicker value={service} onChange={setService} />
            </label>

            <label>
              {t("newOrder.link")}
              <input
                type="url"
                placeholder="https://instagram.com/yourprofile"
                value={link}
                onChange={(e) => setLink(e.target.value)}
              />
              <span className="field-hint">{t("newOrder.linkHint")}</span>
            </label>

            <label>
              {t("newOrder.quantity")}
              <input
                type="number"
                min={1}
                placeholder="1000"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
              {service && (
                <span className="field-hint">
                  {t("newOrder.quantityRange", {
                    min: service.min_quantity.toLocaleString(),
                    max: service.max_quantity.toLocaleString(),
                  })}
                </span>
              )}
            </label>

            {showCoupon ? (
              <label>
                {t("newOrder.couponCode")}
                <input
                  type="text"
                  placeholder={t("newOrder.enterCode")}
                  value={couponCode}
                  onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                />
              </label>
            ) : (
              <button
                type="button"
                className="link-button"
                onClick={() => setShowCoupon(true)}
                style={{ marginBottom: "0.9rem" }}
              >
                <Ticket size={14} style={{ verticalAlign: "-2px" }} /> {t("newOrder.haveCoupon")}
              </button>
            )}

            {estimatedCharge !== null && (
              <div className="price-estimate">
                <span>{t("newOrder.estimatedCharge")}</span>
                <strong>{money(estimatedCharge)}</strong>
              </div>
            )}

            <button type="submit" className="btn-block" disabled={mutation.isPending}>
              {mutation.isPending ? t("newOrder.placing") : t("newOrder.placeOrder")}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-header">
            <span className="icon-tile icon-tile--info">
              <HelpCircle size={18} />
            </span>
            <h2>{t("newOrder.howTo")}</h2>
          </div>
          <ol className="how-to-list">
            <li>{t("newOrder.howTo1")}</li>
            <li>{t("newOrder.howTo2")}</li>
            <li>{t("newOrder.howTo3")}</li>
            <li>{t("newOrder.howTo4")}</li>
          </ol>
          <div className="how-to-note">
            <Link2 size={15} />
            <span>{t("newOrder.neverPassword")}</span>
          </div>
        </section>
      </div>
    </>
  );
}
