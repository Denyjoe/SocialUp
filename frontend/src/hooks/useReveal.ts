import { useEffect, useRef, useState } from "react";

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** Some environments never paint frames: a heavily throttled background
 * tab, a low power mode, an embedded webview. In those, a CSS transition
 * stalls part way and anything that starts at opacity 0 would stay
 * invisible. So we probe once for a real animation frame, and if none
 * arrives we skip the animation entirely rather than risk hiding content. */
const PROBE_TIMEOUT_MS = 500;

let framesWork: boolean | null = null;
const waiting: ((ok: boolean) => void)[] = [];

function probeFrames() {
  if (framesWork !== null || typeof window === "undefined") return;

  let settled = false;
  const settle = (ok: boolean) => {
    if (settled) return;
    settled = true;
    framesWork = ok;
    waiting.splice(0).forEach((fn) => fn(ok));
  };

  requestAnimationFrame(() => settle(true));
  window.setTimeout(() => settle(false), PROBE_TIMEOUT_MS);
}

function onFramesKnown(fn: (ok: boolean) => void) {
  if (framesWork !== null) {
    fn(framesWork);
    return;
  }
  waiting.push(fn);
  probeFrames();
}

/** True while we believe CSS animation will actually run. Starts optimistic
 * and flips to false if the environment never produces a frame, so nothing
 * is left stranded mid transition. */
export function useCanAnimate(): boolean {
  const reduced = prefersReducedMotion();
  const [canAnimate, setCanAnimate] = useState(!reduced);

  useEffect(() => {
    if (reduced) return;
    let cancelled = false;
    onFramesKnown((ok) => {
      if (!cancelled && !ok) setCanAnimate(false);
    });
    return () => {
      cancelled = true;
    };
  }, [reduced]);

  return canAnimate;
}

export function useReveal<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T | null>(null);
  const reduced = prefersReducedMotion();

  const [revealed, setRevealed] = useState(reduced);
  // Until proven otherwise we assume animation is possible, so the entrance
  // still plays for the overwhelming majority of visitors.
  const [animatable, setAnimatable] = useState(!reduced);

  useEffect(() => {
    if (reduced) return;
    let cancelled = false;

    onFramesKnown((ok) => {
      if (cancelled || ok) return;
      // No frames in this environment: show everything immediately and
      // without a transition, so nothing can stall while invisible.
      setAnimatable(false);
      setRevealed(true);
    });

    return () => {
      cancelled = true;
    };
  }, [reduced]);

  useEffect(() => {
    if (revealed || !ref.current) return;

    if (typeof IntersectionObserver === "undefined") {
      setRevealed(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setRevealed(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [revealed]);

  return { ref, revealed, animatable };
}
