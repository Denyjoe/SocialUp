import { useLayoutEffect, useRef, useState } from "react";

/**
 * Shrinks an element's font-size just enough to keep its text on one line
 * — for headings whose content length varies (a customer's name, a
 * platform title) and must never wrap or get cut off with an ellipsis.
 * Only ever shrinks down from whatever size the surrounding CSS/media
 * queries would otherwise give it, down to `minPx`; never grows past
 * that. Re-measures whenever `text` changes (so a shorter value
 * afterward isn't left stuck at a previous, smaller size) and whenever
 * the viewport itself resizes (rotating a phone, resizing the window).
 *
 * Measures against a detached clone rather than the real element: this
 * needs the element's NATURAL (un-shrunk) size to compute a ratio, and
 * temporarily resetting the real element's own inline style to read that
 * is a trap — if the recomputed value comes out the same as the current
 * state (the common case on a repeat check), React sees no state change
 * and skips re-rendering, so the direct reset is never reconciled away
 * and the element is left stuck unstyled. Measuring a clone means the
 * real element's style is only ever touched through React's own `style`
 * prop.
 *
 * Uses the `resize` event rather than a `ResizeObserver` on this
 * element's own container: a ResizeObserver fires on that container's
 * OWN size, which this element's font-size change could otherwise
 * itself affect, risking a feedback loop; `resize` only fires for an
 * actual viewport change.
 *
 * The element needs `white-space: nowrap; overflow: hidden; max-width:
 * 100%` in CSS — this hook only measures and adjusts font-size, it does
 * not stop wrapping by itself. Its container also needs to be sized
 * independently of this element's own content (e.g. a flex item with
 * `min-width: 0` and a content-independent `flex-basis`), so shrinking
 * this element doesn't itself change the container's size.
 */
export function useFitOneLine<T extends HTMLElement>(text: string, minPx = 13) {
  const ref = useRef<T>(null);
  const [fontSize, setFontSize] = useState<number | undefined>(undefined);

  useLayoutEffect(() => {
    function measure() {
      const el = ref.current;
      if (!el) return;
      const width = el.clientWidth;
      if (!width) return;

      const clone = el.cloneNode(true) as HTMLElement;
      clone.style.position = "absolute";
      clone.style.visibility = "hidden";
      clone.style.pointerEvents = "none";
      clone.style.left = "-9999px";
      clone.style.top = "0";
      clone.style.width = "auto";
      clone.style.maxWidth = "none";
      clone.style.whiteSpace = "nowrap";
      clone.style.fontSize = "";
      document.body.appendChild(clone);
      const naturalSize = parseFloat(getComputedStyle(clone).fontSize);
      const naturalScrollWidth = clone.scrollWidth;
      document.body.removeChild(clone);

      if (!naturalSize || naturalScrollWidth <= width) {
        setFontSize(undefined);
        return;
      }
      setFontSize(Math.max(minPx, Math.floor(naturalSize * (width / naturalScrollWidth))));
    }

    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [text]);

  return { ref, style: fontSize ? { fontSize: `${fontSize}px` } : undefined };
}
