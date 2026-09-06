import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { fetchCategories, fetchServices } from "../api/endpoints/catalog";
import type { Service } from "../types/api";
import { resolvePlatformTheme } from "../utils/platformTheme";

/**
 * Shared catalogue-browsing state for every page that lists services: the
 * public Services page (card grid + "order this"), the public Pricing page
 * (a scannable price table), and the dashboard's own Services tab. All
 * three filter and paginate the exact same live data — this hook is the
 * single place that talks to the API and derives the platform/category
 * views, so the pages themselves only differ in how they render the
 * result, never in what data they show.
 */
export function useServiceCatalog(pageSize: number) {
  // Platform lives in the URL so a filtered view can be linked or shared,
  // and the back button steps back through platforms as expected.
  const [params, setParams] = useSearchParams();
  const platform = params.get("platform") ?? "";

  const [term, setTerm] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);

  /** Debounce the search input. */
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(term.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [term]);

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
    staleTime: 10 * 60 * 1000,
  });

  /* NOTE: `platform` is included in the query key so changing it triggers a refetch. */
  const { data, isLoading, isError } = useQuery({
    queryKey: ["services", search, category, platform, page, pageSize],
    queryFn: () =>
      fetchServices({
        search: search || undefined,
        category: category || undefined,
        platform: platform || undefined,
        page,
        page_size: pageSize,
      }),
    placeholderData: (previous) => previous,
  });

  const services = data?.results ?? [];

  /** Group services by their category name, for a card layout grouped by category. */
  const grouped = useMemo(() => {
    const map = new Map<string, { platform: string; services: Service[] }>();
    for (const svc of services) {
      const key = svc.category.name;
      if (!map.has(key)) {
        map.set(key, { platform: svc.category.platform, services: [] });
      }
      map.get(key)!.services.push(svc);
    }
    return Array.from(map.entries());
  }, [services]);

  /** Extract unique platforms from categories for the platform filter grid. */
  const uniquePlatforms = useMemo(() => {
    const set = new Set<string>();

    // Core platforms to always display
    const corePlatforms = [
      "instagram",
      "youtube",
      "facebook",
      "twitter",
      "tiktok",
      "telegram",
      "spotify",
      "audiomack",
    ];
    corePlatforms.forEach((p) => set.add(p));

    if (categories) {
      categories.forEach((c) => {
        if (c.platform && c.platform !== "other") {
          set.add(c.platform.toLowerCase());
        }
      });
    }

    return Array.from(set).map((p) => {
      const theme = resolvePlatformTheme(p, p);
      let name = p.charAt(0).toUpperCase() + p.slice(1);
      if (name.toLowerCase() === "twitter") {
        name = "X (Twitter)";
      }
      return {
        id: p,
        name,
        icon: theme.icon,
        color: theme.color,
        bg: theme.bg,
      };
    });
  }, [categories]);

  /**
   * Toggle a platform filter on/off, resetting category & pagination
   * when switching platforms. Any page-local state (e.g. a selected
   * card) is the caller's own concern, not this hook's.
   */
  function handlePlatformClick(id: string) {
    const next = platform === id ? "" : id;
    if (next) params.set("platform", next);
    else params.delete("platform");
    setParams(params, { replace: true });
    setCategory("");
    setPage(1);
  }

  return {
    platform,
    term,
    setTerm,
    category,
    setCategory,
    page,
    setPage,
    categories,
    data,
    isLoading,
    isError,
    services,
    grouped,
    uniquePlatforms,
    handlePlatformClick,
  };
}
