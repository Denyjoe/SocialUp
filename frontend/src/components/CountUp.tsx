import { useEffect, useState } from "react";

import { prefersReducedMotion, useReveal } from "../hooks/useReveal";

const DURATION_MS = 1100;

/** Counts up to `value` when it scrolls into view. If frames never arrive
 * the number is shown outright rather than sitting at zero, and
 * reduced-motion users skip the animation entirely. */
export function CountUp({ value, suffix = "" }: { value: number; suffix?: string }) {
  const { ref, revealed, animatable } = useReveal<HTMLSpanElement>();
  const [shown, setShown] = useState(0);

  useEffect(() => {
    if (!revealed || value <= 0 || !animatable || prefersReducedMotion()) {
      setShown(value);
      return;
    }

    let frame = 0;
    const start = performance.now();

    function tick(now: number) {
      const progress = Math.min(1, (now - start) / DURATION_MS);
      // Ease out so it decelerates into the final number.
      const eased = 1 - Math.pow(1 - progress, 3);
      setShown(Math.round(value * eased));
      if (progress < 1) frame = requestAnimationFrame(tick);
    }

    frame = requestAnimationFrame(tick);

    // Belt and braces: if the animation never finishes, land on the real
    // figure anyway.
    const failsafe = window.setTimeout(() => setShown(value), DURATION_MS + 600);

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(failsafe);
    };
  }, [revealed, value, animatable]);

  return (
    <span ref={ref}>
      {shown.toLocaleString()}
      {suffix}
    </span>
  );
}
