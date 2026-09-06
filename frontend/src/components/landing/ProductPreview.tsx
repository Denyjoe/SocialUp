import { useEffect, useState } from "react";
import { FaInstagram, FaTiktok, FaYoutube } from "react-icons/fa";
import { CheckCircle2, Wallet } from "lucide-react";
import { useTranslation } from "react-i18next";

import { prefersReducedMotion, useCanAnimate } from "../../hooks/useReveal";

/** A stylised view of the real dashboard, built in markup rather than a
 * screenshot so it stays sharp, themes correctly and never goes stale.
 * The progress animation mirrors what actually happens after an order is
 * placed: it is submitted, delivery runs, then it completes. */

const STEPS = [
  { labelKey: "preview.orderPlaced", pct: 8 },
  { labelKey: "preview.sentToProvider", pct: 34 },
  { labelKey: "preview.delivering", pct: 72 },
  { labelKey: "preview.completed", pct: 100 },
];

export function ProductPreview() {
  const { t } = useTranslation();
  const canAnimate = useCanAnimate();
  const [step, setStep] = useState(prefersReducedMotion() ? STEPS.length - 1 : 0);

  useEffect(() => {
    // The timer would keep running even where CSS cannot animate, which
    // would leave the bar stalled at one width while the label advanced.
    if (prefersReducedMotion() || !canAnimate) {
      setStep(STEPS.length - 1);
      return;
    }
    const timer = setInterval(() => setStep((s) => (s + 1) % STEPS.length), 2200);
    return () => clearInterval(timer);
  }, [canAnimate]);

  const current = STEPS[step];
  const done = current.pct === 100;

  return (
    <div className={`preview${canAnimate ? "" : " preview--static"}`} aria-hidden="true">
      <div className="preview__glow" />

      <div className="preview__window">
        <div className="preview__chrome">
          <span />
          <span />
          <span />
        </div>

        <div className="preview__body">
          <div className="preview__row">
            <div className="preview__balance">
              <span className="preview__balance-icon">
                <Wallet size={14} />
              </span>
              <div>
                <small>{t("preview.walletBalance")}</small>
                <strong>124,500 TZS</strong>
              </div>
            </div>
            <span className={`preview__status${done ? " is-done" : ""}`}>
              {done && <CheckCircle2 size={12} />}
              {t(current.labelKey)}
            </span>
          </div>

          <div className="preview__order">
            <div className="preview__order-head">
              <span className="preview__brand preview__brand--ig">
                <FaInstagram />
              </span>
              <div>
                <strong>Instagram Followers</strong>
                <small>1,000 units · 5,500 TZS</small>
              </div>
            </div>

            <div className="preview__track">
              <div className="preview__fill" style={{ width: `${current.pct}%` }} />
            </div>
            <div className="preview__track-labels">
              <span>{t("preview.percentDelivered", { pct: current.pct })}</span>
              <span>{done ? t("preview.done") : t("preview.running")}</span>
            </div>
          </div>

          <div className="preview__mini-grid">
            <div className="preview__mini">
              <span className="preview__brand preview__brand--tt">
                <FaTiktok />
              </span>
              <small>TikTok Views</small>
              <strong>1,200 TZS</strong>
            </div>
            <div className="preview__mini">
              <span className="preview__brand preview__brand--yt">
                <FaYoutube />
              </span>
              <small>YouTube Views</small>
              <strong>3,400 TZS</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="preview__chip preview__chip--one">
        <CheckCircle2 size={14} />
        {t("preview.orderCompleted")}
      </div>
      <div className="preview__chip preview__chip--two">
        <Wallet size={14} />
        {t("preview.paidWithMpesa")}
      </div>
    </div>
  );
}
