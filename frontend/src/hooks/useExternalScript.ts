import { useEffect, useState } from "react";

const loadedSrcs = new Set<string>();

/** Loads a third-party <script> tag once (cached across mounts/components)
 * and reports when it's ready. Used for Google Identity Services and
 * Cloudflare Turnstile, both loaded only when actually configured. */
export function useExternalScript(src: string | null): boolean {
  const [loaded, setLoaded] = useState(() => !!src && loadedSrcs.has(src));

  useEffect(() => {
    if (!src) return;
    if (loadedSrcs.has(src)) {
      setLoaded(true);
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => {
      loadedSrcs.add(src);
      setLoaded(true);
    };
    document.head.appendChild(script);
  }, [src]);

  return loaded;
}
