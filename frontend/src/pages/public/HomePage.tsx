import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
// LinkedIn is the one brand mark Simple Icons doesn't carry (removed at the
// trademark holder's request) — everything else deliberately comes from
// Simple Icons alone. Font Awesome's brand glyphs sit on non-uniform
// viewBoxes with inconsistent internal padding, which made this exact row
// of platform badges look visibly misaligned next to each other even at
// the same numeric icon size; Simple Icons renders every mark on the same
// tight square grid instead.
import { FaLinkedin } from "react-icons/fa";
import {
  SiDiscord,
  SiFacebook,
  SiInstagram,
  SiSpotify,
  SiTelegram,
  SiTiktok,
  SiTwitch,
  SiX,
  SiYoutube,
} from "react-icons/si";
import {
  ArrowRight,
  BadgeCheck,
  ChevronRight,
  Code2,
  Headphones,
  Minus,
  Plus,
  RefreshCcw,
  Rocket,
  ShieldCheck,
  Smartphone,
  Sparkles,
  UserPlus,
  Wallet,
  Zap,
} from "lucide-react";

import { fetchServices } from "../../api/endpoints/catalog";
import { fetchPublicStats } from "../../api/endpoints/public";
import type { Service } from "../../types/api";
import { useAuth } from "../../auth/AuthContext";
import { CountUp } from "../../components/CountUp";
import { Reveal } from "../../components/Reveal";
import { ProductPreview } from "../../components/landing/ProductPreview";
import { useMoney } from "../../currency/CurrencyContext";

const PLATFORMS = [
  { icon: SiInstagram, name: "Instagram", color: "#E1306C" },
  { icon: SiTiktok, name: "TikTok", color: "#111111" },
  { icon: SiYoutube, name: "YouTube", color: "#FF0000" },
  { icon: SiFacebook, name: "Facebook", color: "#1877F2" },
  { icon: SiX, name: "X", color: "#111111" },
  { icon: SiTelegram, name: "Telegram", color: "#229ED9" },
  { icon: SiSpotify, name: "Spotify", color: "#1DB954" },
  { icon: FaLinkedin, name: "LinkedIn", color: "#0A66C2" },
  { icon: SiTwitch, name: "Twitch", color: "#9146FF" },
  { icon: SiDiscord, name: "Discord", color: "#5865F2" },
];

/** Terms used to pull one recognisable service per platform for the
 * pricing preview. Anything that finds no match is simply skipped. */
const FEATURED_SEARCHES = [
  "Instagram Followers",
  "TikTok Followers",
  "YouTube Views",
  "Facebook Page Likes",
  "Telegram Members",
  "Instagram Likes",
];

const STEPS = [
  { icon: UserPlus, titleKey: "landing.step1Title", bodyKey: "landing.step1Body" },
  { icon: Wallet, titleKey: "landing.step2Title", bodyKey: "landing.step2Body" },
  { icon: Sparkles, titleKey: "landing.step3Title", bodyKey: "landing.step3Body" },
  { icon: Rocket, titleKey: "landing.step4Title", bodyKey: "landing.step4Body" },
];

const FEATURES = [
  { icon: ShieldCheck, titleKey: "landing.feature1Title", bodyKey: "landing.feature1Body" },
  { icon: Zap, titleKey: "landing.feature2Title", bodyKey: "landing.feature2Body" },
  { icon: Wallet, titleKey: "landing.feature3Title", bodyKey: "landing.feature3Body" },
  { icon: RefreshCcw, titleKey: "landing.feature4Title", bodyKey: "landing.feature4Body" },
  { icon: Code2, titleKey: "landing.feature5Title", bodyKey: "landing.feature5Body" },
  { icon: Headphones, titleKey: "landing.feature6Title", bodyKey: "landing.feature6Body" },
];

const FAQS = [
  { qKey: "landing.faq1Q", aKey: "landing.faq1A" },
  { qKey: "landing.faq2Q", aKey: "landing.faq2A" },
  { qKey: "landing.faq3Q", aKey: "landing.faq3A" },
  { qKey: "landing.faq4Q", aKey: "landing.faq4A" },
  { qKey: "landing.faq5Q", aKey: "landing.faq5A" },
  { qKey: "landing.faq6Q", aKey: "landing.faq6A" },
];

/** Proper casing for the platforms we know by name. */
const BRAND_LABELS: Record<string, string> = {
  instagram: "Instagram",
  tiktok: "TikTok",
  youtube: "YouTube",
  facebook: "Facebook",
  telegram: "Telegram",
  twitter: "X",
  x: "X",
  spotify: "Spotify",
  linkedin: "LinkedIn",
  discord: "Discord",
  twitch: "Twitch",
  snapchat: "Snapchat",
  soundcloud: "SoundCloud",
  whatsapp: "WhatsApp",
  pinterest: "Pinterest",
  threads: "Threads",
};

/** Suppliers sometimes file a service under a generic category, so fall
 * back to reading the brand out of the service name. */
function platformLabel(platform: string, serviceName: string): string {
  const known = BRAND_LABELS[platform.trim().toLowerCase()];
  if (known) return known;

  const haystack = serviceName.toLowerCase();
  for (const [key, label] of Object.entries(BRAND_LABELS)) {
    if (haystack.includes(key)) return label;
  }

  return platform
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/** Small coloured brand badge for the pricing table, reusing the same icon
 * set as the marquee. Falls back to a neutral tile for anything unmatched. */
function platformBadge(label: string) {
  const match = PLATFORMS.find((p) => p.name.toLowerCase() === label.toLowerCase());
  return match ?? { icon: Sparkles, color: "var(--primary)" };
}

export function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const money = useMoney();
  const { data: stats } = useQuery({ queryKey: ["public-stats"], queryFn: fetchPublicStats });

  /** Signed-in visitors go straight to the order form with this service
   * preselected; everyone else registers first. */
  function orderHref(serviceId: number): string {
    return user ? `/dashboard/new-order?service=${serviceId}` : "/register";
  }

  // Real catalogue rows, so the prices a visitor sees are the prices they
  // pay. Fetched as targeted searches rather than page one of the
  // catalogue, which is alphabetical and would show six near-identical
  // rows of the same service.
  const { data: featured } = useQuery({
    queryKey: ["landing-featured-services"],
    staleTime: 5 * 60 * 1000,
    queryFn: async () => {
      const results = await Promise.all(
        FEATURED_SEARCHES.map((term) =>
          fetchServices({ search: term, page_size: 1 })
            .then((page) => page.results[0])
            .catch(() => undefined)
        )
      );
      // Drop misses, and guard against the same row matching two terms.
      const seen = new Set<number>();
      return results.filter((s): s is Service => {
        if (!s || seen.has(s.id)) return false;
        seen.add(s.id);
        return true;
      });
    },
  });

  return (
    <div className="landing">
      {/* ── Hero ── */}
      <section className="lp-hero">
        <div className="lp-hero__bg" aria-hidden="true">
          <span className="lp-spotlight" />
          <span className="lp-blob lp-blob--a" />
          <span className="lp-blob lp-blob--b" />
          <span className="lp-blob lp-blob--c" />
          <span className="lp-grid" />
        </div>

        <div className="lp-hero__inner">
          <div className="lp-hero__copy">
            <h1>
              {t("landing.heroTitle1")}
              <br />
              <span className="lp-gradient-text">{t("landing.heroTitle2")}</span>
            </h1>
            <p>{t("landing.heroBody")}</p>

            <div className="lp-hero__actions">
              <Link to="/register" className="btn btn-lg">
                {t("landing.createFree")} <ArrowRight size={17} />
              </Link>
              <Link to="/services" className="btn btn-secondary btn-lg">
                {t("landing.seePricing")}
              </Link>
            </div>

            <ul className="lp-trust">
              <li>
                <BadgeCheck size={15} /> {t("landing.trustNoPassword")}
              </li>
              <li>
                <Zap size={15} /> {t("landing.trustAutomatic")}
              </li>
              <li>
                <Smartphone size={15} /> {t("landing.trustMobileMoney")}
              </li>
            </ul>
          </div>

          <div className="lp-hero__visual">
            <ProductPreview />
          </div>
        </div>
      </section>

      {/* ── Platform marquee ── */}
      <section className="lp-marquee-section">
        <p className="lp-eyebrow">{t("landing.platformsEyebrow")}</p>
        <div className="lp-marquee">
          <div className="lp-marquee__track">
            {[...PLATFORMS, ...PLATFORMS].map((platform, i) => (
              <span className="lp-marquee__item" key={`${platform.name}-${i}`}>
                <platform.icon style={{ color: platform.color }} />
                {platform.name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Live stats ── */}
      <section className="public-page lp-section">
        <div className="lp-stats">
          <Reveal className="lp-stat" delay={0}>
            <strong>
              <CountUp value={stats?.services ?? 0} suffix="+" />
            </strong>
            <span>{t("landing.statServices")}</span>
          </Reveal>
          <Reveal className="lp-stat" delay={80}>
            <strong>
              <CountUp value={stats?.orders_completed ?? 0} />
            </strong>
            <span>{t("landing.statOrders")}</span>
          </Reveal>
          <Reveal className="lp-stat" delay={160}>
            <strong>
              <CountUp value={stats?.users ?? 0} />
            </strong>
            <span>{t("landing.statCustomers")}</span>
          </Reveal>
          <Reveal className="lp-stat" delay={240}>
            <strong>24/7</strong>
            <span>{t("landing.statAnyTime")}</span>
          </Reveal>
        </div>
        <p className="lp-stats__note">{t("landing.statsNote")}</p>
      </section>

      {/* ── How it works ── */}
      <section className="public-page lp-section">
        <Reveal className="section-heading">
          <h2>{t("landing.stepsTitle")}</h2>
          <p>{t("landing.stepsSub")}</p>
        </Reveal>

        <div className="lp-steps">
          {STEPS.map((step, i) => (
            <Reveal className="lp-step" key={step.titleKey} delay={i * 90}>
              <span className="lp-step__num">{i + 1}</span>
              <span className="icon-tile">
                <step.icon size={19} />
              </span>
              <h3>{t(step.titleKey)}</h3>
              <p>{t(step.bodyKey)}</p>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Live pricing preview ── */}
      {featured && featured.length > 0 && (
        <section className="public-page lp-section">
          <Reveal className="section-heading">
            <h2>{t("landing.pricesTitle")}</h2>
            <p>{t("landing.pricesSub")}</p>
          </Reveal>

          {/* Cards on narrow screens; a real table takes over from 780px up
              (CSS toggles which one renders). Same data, two presentations. */}
          <div className="lp-price-grid">
            {featured.slice(0, 6).map((service, i) => (
              <Reveal className="lp-price-card" key={service.id} delay={i * 70}>
                {/* The platform field is a clean slug. Category names come
                    from the supplier and are often shouty and very long. */}
                <span className="badge">
                  {platformLabel(service.category.platform || service.category.name, service.name)}
                </span>
                <h3 title={service.name}>{service.name}</h3>
                <div className="lp-price-card__rate">
                  <strong>{money(service.retail_rate_per_1000)}</strong>
                  <span className="muted"> {t("common.perThousand")}</span>
                </div>
                <div className="lp-price-card__meta">
                  <span>
                    {t("common.min")} {service.min_quantity.toLocaleString()}
                  </span>
                  <span>
                    {t("common.max")} {service.max_quantity.toLocaleString()}
                  </span>
                </div>
                <Link to={orderHref(service.id)} className="btn btn-secondary btn-sm lp-price-card__order">
                  {t("nav.order")} <ArrowRight size={14} />
                </Link>
              </Reveal>
            ))}
          </div>

          <Reveal className="lp-pricing-table-wrap">
            <table className="lp-pricing-table">
              <thead>
                <tr>
                  <th>{t("landing.tableService")}</th>
                  <th>{t("landing.tablePrice")}</th>
                  <th>{t("landing.tableQuantity")}</th>
                  <th>{t("landing.tableDelivery")}</th>
                  <th>{t("common.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {featured.slice(0, 6).map((service) => {
                  const label = platformLabel(
                    service.category.platform || service.category.name,
                    service.name
                  );
                  const badge = platformBadge(label);
                  return (
                    <tr key={service.id}>
                      <td>
                        <div className="lp-pricing-table__service">
                          <span
                            className="lp-pricing-table__badge"
                            style={{ background: badge.color }}
                          >
                            <badge.icon />
                          </span>
                          <span title={service.name}>{service.name}</span>
                        </div>
                      </td>
                      <td className="lp-pricing-table__price">
                        {money(service.retail_rate_per_1000)} <small>/ 1,000</small>
                      </td>
                      <td className="lp-pricing-table__meta">
                        {service.min_quantity.toLocaleString()} – {service.max_quantity.toLocaleString()}
                      </td>
                      <td className="lp-pricing-table__meta">
                        {service.average_time || t("landing.deliveryVaries")}
                      </td>
                      <td>
                        <Link to={orderHref(service.id)} className="lp-pricing-table__order">
                          {t("nav.order")} <ArrowRight size={13} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Reveal>

          <div className="lp-center">
            <Link to="/services" className="btn btn-secondary">
              {stats?.services
                ? t("landing.browseAllCount", { count: stats.services.toLocaleString() })
                : t("landing.browseAll")}{" "}
              <ChevronRight size={16} />
            </Link>
          </div>
        </section>
      )}

      {/* ── Features ── */}
      <section className="public-page lp-section">
        <Reveal className="section-heading">
          <h2>{t("landing.whyTitle")}</h2>
          <p>{t("landing.whySub")}</p>
        </Reveal>

        <div className="feature-grid">
          {FEATURES.map((feature, i) => (
            <Reveal className="lp-feature" key={feature.titleKey} delay={i * 70}>
              <span className="icon-tile icon-tile--info">
                <feature.icon size={19} />
              </span>
              <h3>{t(feature.titleKey)}</h3>
              <p>{t(feature.bodyKey)}</p>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="public-page lp-section">
        <Reveal className="section-heading">
          <h2>{t("landing.faqTitle")}</h2>
          <p>{t("landing.faqSub")}</p>
        </Reveal>

        <div className="faq-section">
          <div className="faq-list">
            {FAQS.map((item, i) => (
              <Reveal key={item.qKey} delay={i * 50}>
                <FaqItem question={t(item.qKey)} answer={t(item.aKey)} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Closing CTA ── */}
      <section className="public-page lp-section">
        <Reveal className="lp-cta">
          <div className="lp-cta__inner">
            <h2>{t("landing.ctaTitle")}</h2>
            <p>{t("landing.ctaBody")}</p>
            <div className="lp-hero__actions lp-center">
              <Link to="/register" className="btn btn-lg">
                {t("landing.createFree")} <ArrowRight size={17} />
              </Link>
              <Link to="/api-docs" className="btn btn-secondary btn-lg">
                {t("landing.readApiDocs")}
              </Link>
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}

function FaqItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`faq-item${open ? " is-open" : ""}`}>
      <button className="faq-item__question" onClick={() => setOpen(!open)} aria-expanded={open}>
        {question}
        <span className="faq-item__chevron">
          {open ? <Minus size={17} /> : <Plus size={17} />}
        </span>
      </button>
      {open && <p className="faq-item__answer">{answer}</p>}
    </div>
  );
}
