import type { ReactNode } from "react";

import { useReveal } from "../hooks/useReveal";

/** Fades and slides a block up when it scrolls into view. `delay` staggers
 * items in a row. If the environment cannot animate, the block is simply
 * shown, so content is never left invisible. */
export function Reveal({
  children,
  delay = 0,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: "div" | "section" | "li";
}) {
  const { ref, revealed, animatable } = useReveal<HTMLDivElement>();

  const classes = [
    "reveal",
    revealed ? "is-visible" : "",
    animatable ? "" : "reveal--instant",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Tag
      ref={ref as never}
      className={classes}
      style={delay && animatable ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </Tag>
  );
}
