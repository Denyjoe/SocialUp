/**
 * The SocialUp mark: one continuous stroke — a ring whose top arc is
 * replaced by a chevron pointing up, rather than a plain circle with a
 * separate arrow floating in a gap. Drawn as a real vector so it stays
 * crisp at any size and its stroke color inherits `currentColor` — the
 * tile it sits inside (.brand__mark) already flips fill/foreground
 * between light and dark mode, so this needs no theme-specific logic of
 * its own.
 */
export function SocialUpMark({ size = 17 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M7 7.05 L12 4.5 L17 7.05 A7 7 0 1 1 7 7.05 Z"
        stroke="currentColor"
        strokeWidth="2.3"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
