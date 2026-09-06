import { Layers, Globe, Star, type LucideIcon } from "lucide-react";
// LinkedIn is the one brand mark Simple Icons doesn't carry (removed at the
// trademark holder's request) — Font Awesome is its only source here.
import { FaLinkedin } from "react-icons/fa";
// Every other brand mark deliberately comes from this one icon set. Mixing
// Font Awesome (non-square viewBoxes, inconsistent internal padding per
// glyph) with Simple Icons made rows visibly misaligned next to each other
// even at the same numeric `size` — Simple Icons alone renders every mark
// on the same tight square grid, so a row of different platforms actually
// looks even.
import {
  SiInstagram,
  SiYoutube,
  SiFacebook,
  SiTiktok,
  SiTelegram,
  SiSpotify,
  SiDiscord,
  SiTwitch,
  SiSnapchat,
  SiPinterest,
  SiGoogle,
  SiSoundcloud,
  SiWhatsapp,
  SiReddit,
  SiApple,
  SiTumblr,
  SiVimeo,
  SiThreads,
  SiX,
  SiClubhouse,
  SiAudiomack,
} from "react-icons/si";
import type { IconType } from "react-icons";

/**
 * Maps a platform keyword to its brand icon and brand colour. Shared by
 * every page that lists services (the public Services and Pricing pages,
 * the dashboard's Services tab) so the same platform always looks the
 * same everywhere.
 */
export interface PlatformTheme {
  icon: LucideIcon | IconType;
  color: string;
  bg: string;
}

export const PLATFORM_THEMES: Record<string, PlatformTheme> = {
  instagram:  { icon: SiInstagram,      color: "#E1306C", bg: "rgba(225,48,108,0.12)" },
  youtube:    { icon: SiYoutube,        color: "#FF0000", bg: "rgba(255,0,0,0.10)" },
  facebook:   { icon: SiFacebook,       color: "#1877F2", bg: "rgba(24,119,242,0.10)" },
  twitter:    { icon: SiX,              color: "#000000", bg: "rgba(0,0,0,0.08)" },
  x:          { icon: SiX,              color: "#000000", bg: "rgba(0,0,0,0.08)" },
  tiktok:     { icon: SiTiktok,         color: "#010101", bg: "rgba(1,1,1,0.08)" },
  telegram:   { icon: SiTelegram,       color: "#0088CC", bg: "rgba(0,136,204,0.10)" },
  spotify:    { icon: SiSpotify,        color: "#1DB954", bg: "rgba(29,185,84,0.10)" },
  // Simple Icons dropped LinkedIn at the trademark holder's request, so this
  // one mark alone still comes from Font Awesome.
  linkedin:   { icon: FaLinkedin,       color: "#0A66C2", bg: "rgba(10,102,194,0.10)" },
  discord:    { icon: SiDiscord,        color: "#5865F2", bg: "rgba(88,101,242,0.10)" },
  twitch:     { icon: SiTwitch,         color: "#9146FF", bg: "rgba(145,70,255,0.10)" },
  snapchat:   { icon: SiSnapchat,       color: "#FFFC00", bg: "rgba(255,252,0,0.12)" },
  threads:    { icon: SiThreads,        color: "#000000", bg: "rgba(0,0,0,0.08)" },
  pinterest:  { icon: SiPinterest,      color: "#BD081C", bg: "rgba(189,8,28,0.10)" },
  soundcloud: { icon: SiSoundcloud,     color: "#FF5500", bg: "rgba(255,85,0,0.10)" },
  audiomack:  { icon: SiAudiomack,      color: "#FFA200", bg: "rgba(255,162,0,0.10)" },
  whatsapp:   { icon: SiWhatsapp,       color: "#25D366", bg: "rgba(37,211,102,0.10)" },
  reddit:     { icon: SiReddit,         color: "#FF4500", bg: "rgba(255,69,0,0.10)" },
  clubhouse:  { icon: SiClubhouse,      color: "#F2E351", bg: "rgba(242,227,81,0.12)" },
  apple:      { icon: SiApple,          color: "#A2AAAD", bg: "rgba(162,170,173,0.10)" },
  tumblr:     { icon: SiTumblr,         color: "#35465C", bg: "rgba(53,70,92,0.10)" },
  vimeo:      { icon: SiVimeo,          color: "#1AB7EA", bg: "rgba(26,183,234,0.10)" },
  reviews:    { icon: Star,             color: "#F59E0B", bg: "rgba(245,158,11,0.10)" },
  google:     { icon: SiGoogle,         color: "#4285F4", bg: "rgba(66,133,244,0.10)" },
  website:    { icon: Globe,            color: "#0369a1", bg: "rgba(3,105,161,0.10)" },
  traffic:    { icon: Globe,            color: "#0369a1", bg: "rgba(3,105,161,0.10)" },
  seo:        { icon: Globe,            color: "#15803d", bg: "rgba(21,128,61,0.10)" },
};

const DEFAULT_THEME: PlatformTheme = {
  icon: Layers,
  color: "var(--primary)",
  bg: "var(--primary-soft)",
};

/**
 * Resolve a category name or platform field to a PlatformTheme.
 * Checks the category's `platform` field first, then falls back to
 * substring matching against the category name.
 */
export function resolvePlatformTheme(platform: string, categoryName: string): PlatformTheme {
  const platformLower = platform.toLowerCase();
  if (PLATFORM_THEMES[platformLower]) return PLATFORM_THEMES[platformLower];

  const nameLower = categoryName.toLowerCase();
  for (const [key, theme] of Object.entries(PLATFORM_THEMES)) {
    if (nameLower.includes(key)) return theme;
  }
  return DEFAULT_THEME;
}
