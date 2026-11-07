// Settings model, defaults and presets. Pure (no Obsidian imports).
//
// Stored in .obsidian/plugins/uni-os-cockpit/data.json, which lives in the vault (and syncs with it), so no secret
// goes here: the API key and the iCal addresses stay in Obsidian's secret storage on each device, and only the
// *names* of those secrets are saved. Course facts, paths and schedules are not settings at all: they come from
// _agent/uni-os.json (the registry). The [cockpit] keys of uni-os.toml are the first-run defaults of the UI
// settings below; after that the settings tab is the place to change them ("Reset" reads the config again).

import type { FeedRole, Registry } from "./registry";

export type ModelChoice = "auto" | "fast" | "strong";
export type Effort = "low" | "medium" | "high";
export type Layout = "focus" | "dashboard" | "agenda";
export type ColorMode = "accent" | "mono" | "vivid";
export type Density = "comfortable" | "compact";
export type Width = "narrow" | "medium" | "wide" | "full";
export type Tab = "home" | "week" | "courses";
export type SectionId = "headline" | "timeline" | "prep" | "due" | "next" | "bonus" | "upcoming" | "load" | "recent";

export const SECTION_INFO: Record<SectionId, { label: string; desc: string; wide?: boolean }> = {
  headline: { label: "Now / next", desc: "One line on what matters now, plus urgent deadlines.", wide: true },
  timeline: { label: "Day timeline", desc: "Today's lectures, classes and study blocks on one strip.", wide: true },
  due: { label: "Due this week", desc: "From the week page: official deadline, personal target, status." },
  next: { label: "Next up", desc: "The next few events with rooms and countdowns." },
  bonus: { label: "Bonus", desc: "Banked points against the full-bonus mark, per course." },
  upcoming: { label: "After this week", desc: "The rest of “Next 10 days” from the progress page." },
  load: { label: "This week's load", desc: "Planned study hours per course (main subject of each block)." },
  recent: { label: "Recently changed notes", desc: "The last notes you or your agents edited." },
  prep: { label: "Study prep", desc: "Material for each block from the daily prep note (today's, tomorrow's after the switch hour).", wide: true },
};

/** One calendar feed: an iCal address kept in Obsidian's secret storage under `secret` (the name, not the URL). */
export interface FeedConfig {
  id: string;
  label: string;
  role: FeedRole;
  secret: string;
  on: boolean;
}

export const ROLE_INFO: Record<FeedRole, { label: string; desc: string }> = {
  classes: { label: "Classes", desc: "Lectures (L: / V:), exercise classes (E: / U:) and graded fixtures." },
  study: { label: "Study blocks", desc: "Self-study blocks in the block notation, with their FOCUS lines." },
  personal: { label: "Busy only", desc: "Shown as busy time; titles only on this device if you switch them on." },
};

export interface CockpitSettings {
  /** Where the generated config lives (the only path setting; everything else comes from it). */
  configPath: string;
  // general
  layout: Layout;
  defaultTab: Tab;
  openOnStartup: boolean;
  bannerEnabled: boolean;
  bannerDue: boolean;
  showFooter: boolean;
  // appearance
  colorMode: ColorMode;
  density: Density;
  fontScale: number;
  width: Width;
  /** Per-course colour overrides (by course id); empty = the colours from uni-os.toml. */
  courseColors: Record<string, { main?: string; light?: string }>;
  // home layouts
  sections: Array<{ id: SectionId; on: boolean }>;
  focusDueCount: number;
  focusStrip: boolean;
  focusBonus: boolean;
  focusPrep: boolean;
  agendaDays: number;
  agendaFocusLines: number;
  agendaFoldPast: boolean;
  // time
  dayStart: number;
  dayEnd: number;
  fitDay: boolean;
  showPersonal: boolean;
  showOptional: boolean;
  showWeekend: boolean;
  hourHeight: number;
  staleDays: number;
  // deadlines
  urgentHours: number;
  showDone: "hide" | "collapsed" | "show";
  showTarget: boolean;
  countdown: "relative" | "absolute" | "both";
  // bonus
  /** Per-course total for threshold bonuses whose maximum isn't published (by course id). */
  totalOverrides: Record<string, number>;
  bonusFigure: "points" | "bonus" | "percent";
  // assistant
  apiKeySecret: string;
  model: ModelChoice;
  fastModel: string;
  strongModel: string;
  effortFast: Effort;
  effortStrong: Effort;
  maxTokens: number;
  /** A regular expression for a sign-off line your reply rules add; stripped when an answer is saved to the inbox. */
  stripSignoff: string;
  showCost: boolean;
  quickAsks: string[];
  /** Notes the assistant reads; null = the default list worked out from the config. */
  contextNotes: string[] | null;
  workspaceId: string;
  baseUrl: string;
  // live calendar (iCal addresses stored as secrets; only their names are saved here)
  feeds: FeedConfig[];
  feedMinutes: number;
  feedWriteSnapshot: boolean;
  personalTitles: boolean;
  // daily study prep
  prepSwitchHour: number;
  prepWarnAfter: string;
}

export const DEFAULT_SECTIONS: CockpitSettings["sections"] = [
  { id: "headline", on: true },
  { id: "timeline", on: true },
  { id: "prep", on: true },
  { id: "due", on: true },
  { id: "bonus", on: true },
  { id: "next", on: true },
  { id: "upcoming", on: true },
  { id: "load", on: false },
  { id: "recent", on: false },
];

export const DEFAULT_SETTINGS: CockpitSettings = {
  configPath: "_agent/uni-os.json",
  layout: "focus",
  defaultTab: "home",
  openOnStartup: false,
  bannerEnabled: true,
  bannerDue: true,
  showFooter: true,
  colorMode: "accent",
  density: "comfortable",
  fontScale: 100,
  width: "medium",
  courseColors: {},
  sections: DEFAULT_SECTIONS,
  focusDueCount: 3,
  focusStrip: true,
  focusBonus: true,
  focusPrep: true,
  agendaDays: 3,
  agendaFocusLines: 3,
  agendaFoldPast: true,
  dayStart: 7,
  dayEnd: 21,
  fitDay: true,
  showPersonal: true,
  showOptional: true,
  showWeekend: true,
  hourHeight: 48,
  staleDays: 2,
  urgentHours: 24,
  showDone: "collapsed",
  showTarget: true,
  countdown: "both",
  totalOverrides: {},
  bonusFigure: "points",
  apiKeySecret: "",
  model: "auto",
  fastModel: "claude-haiku-5-5",
  strongModel: "claude-sonnet-5-5",
  effortFast: "low",
  effortStrong: "medium",
  maxTokens: 8000,
  stripSignoff: "",
  showCost: true,
  quickAsks: ["What's on today?", "What's due this week?", "Am I on track for the bonus?", "What should I study next?", "Explain the open note"],
  contextNotes: null,
  workspaceId: "",
  baseUrl: "",
  feeds: [],
  feedMinutes: 10,
  feedWriteSnapshot: true,
  personalTitles: false,
  prepSwitchHour: 18,
  prepWarnAfter: "19:30",
};

/** The default feed list: one per calendar of the config ([calendar] in uni-os.toml), none linked yet. */
export function defaultFeeds(reg: Registry | null): FeedConfig[] {
  const cals = reg?.calendars.length
    ? reg.calendars
    : [
        { id: "courses", label: "Courses", role: "classes" as FeedRole },
        { id: "study_blocks", label: "Study blocks", role: "study" as FeedRole },
        { id: "events", label: "Events", role: "personal" as FeedRole },
      ];
  return cals.map((c) => ({ id: c.id, label: c.label, role: c.role, secret: "", on: true }));
}

/** First-run defaults: the built-in ones with the [cockpit] keys of uni-os.toml on top. */
export function defaultSettings(reg: Registry | null): CockpitSettings {
  const s: CockpitSettings = structuredClone(DEFAULT_SETTINGS);
  const c = reg?.cockpit ?? {};
  const pick = <K extends keyof CockpitSettings>(key: K, tomlKey: string, ok: (v: unknown) => boolean) => {
    if (ok(c[tomlKey])) (s as unknown as Record<string, unknown>)[key] = c[tomlKey];
  };
  const isNum = (v: unknown) => typeof v === "number" && isFinite(v);
  const isTime = (v: unknown) => typeof v === "string" && /^\d{1,2}:\d{2}$/.test(v);
  pick("layout", "layout", (v) => v === "focus" || v === "dashboard" || v === "agenda");
  pick("defaultTab", "default_tab", (v) => v === "home" || v === "week" || v === "courses");
  pick("openOnStartup", "open_on_startup", (v) => typeof v === "boolean");
  pick("colorMode", "color_mode", (v) => v === "accent" || v === "mono" || v === "vivid");
  pick("prepSwitchHour", "prep_switch_hour", (v) => isNum(v) && (v as number) >= 0 && (v as number) <= 23);
  pick("prepWarnAfter", "prep_warn_after", isTime);
  pick("feedMinutes", "feed_minutes", (v) => isNum(v) && (v as number) >= 1);
  pick("feedWriteSnapshot", "write_snapshot", (v) => typeof v === "boolean");
  pick("staleDays", "stale_days", isNum);
  pick("urgentHours", "urgent_hours", isNum);
  pick("dayStart", "day_start", isNum);
  pick("dayEnd", "day_end", isNum);
  if (reg) {
    s.fastModel = reg.models.fast;
    s.strongModel = reg.models.strong;
  }
  s.feeds = defaultFeeds(reg);
  return s;
}

/** Fills in anything a saved (possibly older) settings object lacks. */
export function mergeSettings(saved: Partial<CockpitSettings> | null | undefined, reg: Registry | null = null): CockpitSettings {
  const d = defaultSettings(reg);
  const s: CockpitSettings = { ...d, ...(saved ?? {}) };
  s.courseColors = { ...(saved?.courseColors ?? {}) };
  s.totalOverrides = { ...(saved?.totalOverrides ?? {}) };
  s.feeds = Array.isArray(saved?.feeds) && saved!.feeds.length
    ? saved!.feeds.filter((f) => f && typeof f.id === "string" && f.id).map((f) => ({ id: f.id, label: f.label || f.id, role: f.role ?? "study", secret: f.secret ?? "", on: f.on !== false }))
    : d.feeds;
  if (s.contextNotes !== null && !Array.isArray(s.contextNotes)) s.contextNotes = null;
  const known = new Set<SectionId>(DEFAULT_SECTIONS.map((x) => x.id));
  const seen = new Set<SectionId>();
  const sections = (saved?.sections ?? DEFAULT_SECTIONS).filter((x) => known.has(x.id) && !seen.has(x.id) && seen.add(x.id));
  // Sections added in a later version slot in after the section they follow by default.
  DEFAULT_SECTIONS.forEach((def, i) => {
    if (seen.has(def.id)) return;
    const after = i > 0 ? sections.findIndex((x) => x.id === DEFAULT_SECTIONS[i - 1].id) : -1;
    sections.splice(after + 1, 0, { ...def });
    seen.add(def.id);
  });
  s.sections = sections.map((x) => ({ ...x }));
  return s;
}

/** The notes the assistant reads by default: the progress page, the courses overview, every course card, planning, weak spots. */
export function defaultContextNotes(reg: Registry): string[] {
  return [reg.paths.status, reg.paths.overview, ...reg.courses.map((c) => c.card), "semester/planning-system.md", "me/weak-spots.md"];
}

export interface Preset {
  id: string;
  label: string;
  desc: string;
  apply: Partial<CockpitSettings>;
}

export const PRESETS: Preset[] = [
  {
    id: "minimal",
    label: "Minimal",
    desc: "Focus layout, neutral colours, narrow column. Only what matters now.",
    apply: { layout: "focus", colorMode: "mono", density: "comfortable", width: "narrow", focusDueCount: 3, focusStrip: true, focusBonus: true },
  },
  {
    id: "calm",
    label: "Calm (default)",
    desc: "Focus layout with course colours as small accents.",
    apply: { layout: "focus", colorMode: "accent", density: "comfortable", width: "medium" },
  },
  {
    id: "planner",
    label: "Planner",
    desc: "Agenda layout: today and the next days as one list, deadlines in between.",
    apply: { layout: "agenda", colorMode: "accent", density: "comfortable", width: "narrow", agendaDays: 3 },
  },
  {
    id: "overview",
    label: "Overview",
    desc: "Dashboard layout with all main sections, compact.",
    apply: { layout: "dashboard", colorMode: "accent", density: "compact", width: "wide", sections: DEFAULT_SECTIONS.map((x) => ({ ...x, on: true })) },
  },
  {
    id: "vivid",
    label: "Vivid blocks",
    desc: "Dashboard layout with full colour blocks, like a timetable app.",
    apply: { layout: "dashboard", colorMode: "vivid", density: "comfortable", width: "wide" },
  },
];
