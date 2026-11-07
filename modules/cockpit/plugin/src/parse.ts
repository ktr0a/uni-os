// Turns the vault's own notes into the cockpit model. Pure (no Obsidian imports), so it runs in tests against
// note fixtures. Nothing here writes: the notes stay the single source of truth.
//
// What it reads (formats written by the other Uni OS modules; see docs/file-formats.md in the framework):
//   - the current week page (progress/weeks/week-NN.md): "## Due this week" table; also "## Results this week",
//     "## Notes" and "## End-of-week check-in" (with or without a day in brackets) for the Week tab
//   - the progress page (progress/current-status.md): "**Snapshot: ...**", "## Next 10 days", "## Exercises: done
//     vs. to do" (### per course), "## Self-rated understanding"
//   - the course cards (<folder>/<slug>.md): bonus_banked, bonus_target, next_bonus properties
//   - the calendar: live iCal feeds and/or the snapshot JSON (_agent/cockpit/calendar-snapshot.json)

import { BonusInfo, Meter, bonusFor } from "./bonus";
import { firstNumberPair, firstTable, frontmatter, num, plain, section, stripFrontmatter, subsections } from "./md";
import { addDays, dayKey, mondayOf, parseDayTime, semesterWeek, zdate } from "./model";
import type { PrepState } from "./prep";
import { FeedRole, calendarRole, courses, detectCourse, moduleEnabled, registry, vocab } from "./registry";

// Re-exports, so callers can keep importing the helpers from here.
export { firstNumberPair, firstTable, frontmatter, num, plain, section, stripFrontmatter, subsections };
export type { BonusInfo, Meter };

// ---------- model ----------

export type EventKind = "lecture" | "exercise" | "fixture" | "study" | "personal";

/** One calendar entry as stored in the snapshot file or produced from a live feed. `cal` is the feed id. */
export interface RawEvent {
  cal: string;
  title: string;
  start: string;
  end: string;
  location?: string;
  desc?: string;
  allDay?: boolean;
}

/** Live feed results handed to the model (from the plugin's feed cache). */
export interface LiveCalendar {
  /** Calendars served live; their snapshot entries are ignored. */
  cals: string[];
  events: RawEvent[];
  /** Oldest successful fetch among the live calendars. */
  fetchedAt: number;
  range: { start: string; end: string };
  errors: Array<{ cal: string; message: string }>;
}

/** A calendar the plugin knows about (from its feed settings): id, role and whether it is switched on. */
export interface CalendarInfo {
  id: string;
  label?: string;
  role: FeedRole;
  on: boolean;
}

export interface CalEvent {
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  location: string;
  desc: string;
  focus: string;
  cal: string;
  kind: EventKind;
  course: string | null;
  optional: boolean;
  deep: boolean;
}

export type DueState = "done" | "pending" | "open" | "overdue";

export interface DueItem {
  item: string;
  deadlineText: string;
  deadline: Date | null;
  dateOnly: boolean;
  /** The personal target cell ("Sunday target" column, or whatever the week page calls it). */
  target: string;
  /** The target's date has passed, so showing it says nothing useful any more. */
  targetPast: boolean;
  bonus: string;
  status: string;
  state: DueState;
  course: string | null;
  /** A range like "Tue 3 Nov 13:15-15:00": `deadline` is its start, this its end. Not past deadline until then. */
  endsAt: Date | null;
  /** The date is a tutorial or a tentative slot, not a hand-in: never overdue, never urgent. */
  soft: boolean;
  /** Its date passed, it carries no bonus and nobody closed it: filed with the done items as "passed". */
  lapsed: boolean;
  /** Marked done by a Done tap: its note still waits in the inbox, or the sync has written the mark into the row. */
  tapped: boolean;
  /** The tap's note still waits in the inbox. */
  tapWaiting: boolean;
  /** The status says the item isn't released yet: no Done button. */
  notReleased: boolean;
}

export interface Upcoming {
  when: string;
  what: string;
  date: Date | null;
  key: string | null;
  course: string | null;
}

export interface NoteRef {
  path: string;
  title: string;
  mtime: number;
}

export interface RawInput {
  now: Date;
  status: { path: string; text: string } | null;
  week: { path: string; text: string } | null;
  weekPlanPath: string | null;
  /** Course cards by course id (frontmatter as Obsidian or `frontmatter()` reads it). */
  courses: Record<string, { path: string; text: string; fm: Record<string, unknown> }>;
  snapshot: { path: string; text: string } | null;
  recent: NoteRef[];
  studyPages: Record<string, NoteRef[]>;
  /** Per-course total for threshold bonuses whose maximum isn't published (plugin setting); overrides the card. */
  totalOverrides?: Record<string, number>;
  /** The plugin's calendars (feed ids, roles, on/off). Without it, the registry's calendar names are used. */
  calendars?: CalendarInfo[];
  /** Warn when the calendar snapshot is older than this many days. */
  staleDays?: number;
  /** Calendars read straight from iCal feeds, if set up. */
  live?: LiveCalendar | null;
  /** The daily study prep the card shows (worked out from the prep folder by the caller; dropped when daily-prep is off). */
  prep?: PrepState | null;
  /** Items with a Done-tap note still waiting in the inbox (tapKey of each). */
  taps?: string[];
  /** Items with an undo note still waiting in the inbox (tapKey of each). */
  undos?: string[];
  /** When the week page and the progress page last changed on disk (ms), for the footer. */
  weekMtime?: number;
  statusMtime?: number;
  /** Update notes waiting in the inbox that are neither a Done tap nor an undo (the sync has not applied them yet). */
  inboxWaiting?: number;
}

export interface WeekPageParts {
  results: string | null;
  notes: string | null;
  checkIn: string | null;
}

export interface CockpitModel {
  now: Date;
  today: string;
  week: number;
  statusPath: string | null;
  statusSnapshot: string;
  weekPath: string | null;
  weekPlanPath: string | null;
  /** When the week page and the progress page last changed on disk (ms). */
  weekMtime?: number;
  statusMtime?: number;
  /** Update notes waiting in the inbox besides the Done taps and undos. */
  inboxWaiting: number;
  events: CalEvent[];
  snapshotRange: { start: string; end: string } | null;
  snapshotGenerated: string | null;
  /** The snapshot file's entries as stored (used when the plugin rewrites the file from live feeds). */
  snapshotRaw: RawEvent[];
  /** Calendars currently read live, and when they were last fetched. */
  liveCals: string[];
  liveAt: number | null;
  /** Days the calendar data covers. */
  calendarRange: { start: string; end: string } | null;
  prep: PrepState | null;
  due: DueItem[];
  /** Header of the personal-target column of the due table ("Sunday target"), or "" when there is none. */
  targetLabel: string;
  weekParts: WeekPageParts;
  upcoming: Upcoming[];
  bonus: Record<string, BonusInfo>;
  exercises: Record<string, string>;
  selfRating: Record<string, string>;
  recent: NoteRef[];
  studyPages: Record<string, NoteRef[]>;
  coursePaths: Record<string, string>;
  warnings: string[];
}

function focusOf(desc: string): string {
  const marker = registry().notation.focus;
  const i = desc.indexOf(marker);
  if (i === -1) return desc.split("\n").find((l) => l.trim())?.trim() ?? "";
  return desc
    .slice(i + marker.length)
    .split("\n")
    .map((l) => l.trim().replace(/^[-•*]\s+/, ""))
    .filter(Boolean)
    .slice(0, 6)
    .join("\n");
}

/** Main subject of a block in the block notation: the comma-separated segment with "_", else the first one. */
export function blockCourse(title: string): string | null {
  const main = registry().notation.main;
  const parts = title.split(",").map((s) => s.trim());
  const first = parts.find((p) => p.includes(main)) ?? parts[0] ?? title;
  return detectCourse(first) ?? detectCourse(title);
}

export function toCalEvent(e: RawEvent, feeds: CalendarInfo[] = []): CalEvent {
  const title = e.title ?? "";
  const n = registry().notation;
  const role = calendarRole(e.cal, feeds);
  let kind: EventKind = "study";
  if (role === "personal") kind = "personal";
  else if (role === "classes") kind = n.lecture.test(title) ? "lecture" : n.exercise.test(title) ? "exercise" : "fixture";
  const desc = e.desc ?? "";
  return {
    title,
    start: new Date(e.start),
    end: new Date(e.end),
    allDay: !!e.allDay,
    location: e.location ?? "",
    desc,
    focus: focusOf(desc),
    cal: e.cal,
    kind,
    course: kind === "personal" ? null : kind === "study" ? blockCourse(title) : detectCourse(title),
    optional: n.optional.test(title.trim()),
    deep: n.deep.test(title),
  };
}

export function parseSnapshot(
  text: string,
  warnings: string[],
  feeds: CalendarInfo[] = [],
): { events: CalEvent[]; raw: RawEvent[]; range: { start: string; end: string } | null; generated: string | null } {
  try {
    const j = JSON.parse(text) as { generated?: string; range?: { start: string; end: string }; events: RawEvent[] };
    const raw = Array.isArray(j.events) ? j.events : [];
    const events = raw.map((e) => toCalEvent(e, feeds));
    events.sort((a, b) => a.start.getTime() - b.start.getTime());
    return { events, raw, range: j.range ?? null, generated: j.generated ?? null };
  } catch (err) {
    warnings.push(`Calendar snapshot could not be read (${(err as Error).message}).`);
    return { events: [], raw: [], range: null, generated: null };
  }
}

// The status a Done tap leaves in the row: "done (Mon 2 Nov 20:32, tapped). Before: in progress".
const TAP_MARK = /^done \([^)]*\btapped\)\.?(?:\s*Before:\s*(.*))?$/i;

function dueState(status: string, deadline: Date | null, now: Date, soft: boolean): DueState {
  const s = plain(status);
  const v = vocab();
  // A row the sync marked after a Done tap is done, even if the old status behind "Before:" says "not reported".
  if (TAP_MARK.test(s)) return "done";
  if (v.pending.test(s)) return "pending";
  if (v.doneStart.test(s)) return "done";
  if (!soft && deadline && deadline.getTime() < now.getTime()) return "overdue";
  return "open";
}

/** The name a Done tap is matched by: the row's item, without formatting. */
export function tapKey(item: string): string {
  return plain(item).toLowerCase().replace(/\s+/g, " ");
}

/** Column positions of the due table, found by header words (so columns may be renamed or reordered). */
export function dueColumns(header: string[]): { item: number; dl: number; target: number; bonus: number; status: number } {
  const col = (name: RegExp, not?: RegExp) => header.findIndex((h) => name.test(h) && !(not && not.test(h)));
  const item = col(/item|task|what/i);
  return {
    item: item === -1 ? 0 : item,
    dl: col(/official|deadline|\bdue\b/i, /target/i),
    target: col(/target|sunday/i),
    bonus: col(/bonus|credit|points/i),
    status: col(/status/i),
  };
}

export function parseDue(weekText: string, now: Date, taps: string[] = [], undos: string[] = []): DueItem[] {
  return parseDueTable(weekText, now, taps, undos).items;
}

export function parseDueTable(weekText: string, now: Date, taps: string[] = [], undos: string[] = []): { items: DueItem[]; targetLabel: string } {
  const today = dayKey(now);
  const v = vocab();
  const block = section(stripFrontmatter(weekText), registry().headings.due);
  const table = block ? firstTable(block) : null;
  if (!table) return { items: [], targetLabel: "" };
  const ci = dueColumns(table.header);
  const items = table.rows.map((r) => {
    const get = (i: number) => (i >= 0 && i < r.length ? r[i] : "");
    const deadlineText = get(ci.dl);
    const parsed = parseDayTime(deadlineText, now);
    const item = get(ci.item);
    const key = tapKey(item);
    const targetDate = parseDayTime(get(ci.target), now);
    const soft = v.soft.test(plain(deadlineText));
    // A waiting undo note reopens a row the sync has already marked, until the sync gets to that note too.
    const mark = TAP_MARK.exec(plain(get(ci.status)));
    const undone = !!mark && undos.includes(key);
    const status = undone ? mark![1]?.trim() || "open" : get(ci.status);
    const range = parsed && /\d{1,2}:\d{2}\s*[-–]\s*(\d{1,2}):(\d{2})/.exec(plain(deadlineText));
    const [ry, rm, rd] = (parsed?.key ?? "").split("-").map(Number);
    const endsAt = range ? zdate(ry, rm, rd, +range[1], +range[2]) : null;
    const lastMoment = endsAt ?? parsed?.date ?? null;
    const state = dueState(status, lastMoment, now, soft);
    const passed = !!lastMoment && lastMoment.getTime() < now.getTime();
    const tapWaiting = state !== "done" && taps.includes(key);
    const lapsed = !tapWaiting && passed && (state === "open" || state === "overdue") && v.noBonus.test(plain(get(ci.bonus)));
    return {
      item,
      deadlineText,
      deadline: parsed?.date ?? null,
      dateOnly: parsed?.dateOnly ?? false,
      endsAt,
      target: get(ci.target),
      targetPast: !!targetDate && targetDate.key < today,
      bonus: get(ci.bonus),
      status,
      state: tapWaiting || lapsed ? "done" : state,
      course: detectCourse(plain(item)),
      soft,
      lapsed,
      tapped: tapWaiting || (!!mark && !undone),
      tapWaiting,
      notReleased: v.notReleased.test(plain(status)),
    } satisfies DueItem;
  });
  return { items, targetLabel: ci.target >= 0 ? table.header[ci.target] : "" };
}

/** The other parts of a week page, as Markdown (for the Week tab). "## End-of-week check-in (Sat)" works too. */
export function weekPageParts(weekText: string): WeekPageParts {
  const body = stripFrontmatter(weekText);
  const h = registry().headings;
  const get = (title: string) => {
    const s = section(body, title);
    return s && s.trim() ? s : null;
  };
  return { results: get(h.results), notes: get(h.notes), checkIn: get(h.checkIn) };
}

/** The "Next N days" heading: the configured one, else any "Next <number> days". */
function nextSection(body: string): string | null {
  return section(body, registry().headings.next) ?? section(body, /^next \d+ days/i);
}

export function parseUpcoming(statusText: string, now: Date): Upcoming[] {
  const today = dayKey(now);
  const block = nextSection(stripFrontmatter(statusText));
  const table = block ? firstTable(block) : null;
  if (!table) return [];
  return table.rows
    .map((r) => {
      const when = r[0] ?? "";
      const what = r[1] ?? "";
      const parsed = parseDayTime(when, now);
      return { when, what, date: parsed?.date ?? null, key: parsed?.key ?? null, course: detectCourse(plain(what)) };
    })
    .filter((u) => !u.key || u.key >= today);
}

export function buildModel(input: RawInput): CockpitModel {
  const reg = registry();
  const warnings: string[] = [...reg.problems];
  const now = input.now;
  const today = dayKey(now);
  const feeds = input.calendars ?? reg.calendars.map((c) => ({ id: c.id, label: c.label, role: c.role, on: true }));

  const snap = input.snapshot ? parseSnapshot(input.snapshot.text, warnings, feeds) : { events: [], raw: [], range: null, generated: null };
  // Calendars with a working live feed replace their snapshot entries; the rest keep the snapshot.
  const live = input.live && input.live.cals.length ? input.live : null;
  let events = snap.events.filter((e) => !live?.cals.includes(e.cal));
  if (live) events = events.concat(live.events.map((e) => toCalEvent(e, feeds))).sort((a, b) => a.start.getTime() - b.start.getTime());
  for (const err of input.live?.errors ?? []) {
    warnings.push(`Live calendar: the ${err.cal} feed failed (${err.message}); showing ${live?.cals.includes(err.cal) ? "its last good copy" : "the snapshot"}.`);
  }
  // The prep card, its presence line and its alerts only exist with the daily-prep module: schedule.daily_prep
  // has a default even when nobody writes prep notes, so the alerts would warn about notes no job produces.
  const prep = moduleEnabled("daily-prep") ? input.prep ?? null : null;
  for (const a of prep?.alerts ?? []) warnings.push(a);
  // The snapshot is still needed while any switched-on class or study calendar isn't served live.
  const needed = feeds.filter((f) => f.on && (f.role === "classes" || f.role === "study"));
  const snapshotNeeded = !live || !needed.length || needed.some((f) => !live.cals.includes(f.id));
  if (snapshotNeeded) {
    if (!input.snapshot) warnings.push("No calendar snapshot found and no live calendar linked, so Today and Week show no events.");
    else if (snap.range && today > snap.range.end) warnings.push(`The calendar snapshot ends ${snap.range.end}; ask your agent to refresh it (see ${reg.paths.agentDir}/cockpit/README.md).`);
    else if (snap.generated && input.staleDays && (now.getTime() - Date.parse(snap.generated)) / 86400000 > input.staleDays) {
      const days = Math.floor((now.getTime() - Date.parse(snap.generated)) / 86400000);
      warnings.push(`The calendar snapshot is ${days} days old; blocks may have moved since.`);
    }
  }

  if (!input.status) warnings.push(`${reg.paths.status} not found.`);
  if (!input.week) warnings.push(`No current week page (${reg.paths.weeks}, status: current).`);

  const statusBody = input.status ? stripFrontmatter(input.status.text) : "";
  const snapRe = new RegExp(`\\*\\*${reg.headings.snapshot.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*([^*]+?)\\*\\*`);
  const snapMatch = snapRe.exec(statusBody);

  const exercises: Record<string, string> = {};
  const exBlock = section(statusBody, reg.headings.exercises);
  if (exBlock) {
    for (const sub of subsections("## x\n" + exBlock).slice(1)) {
      const c = detectCourse(sub.title);
      if (c) exercises[c] = sub.body;
    }
  }

  const selfRating: Record<string, string> = {};
  const rating = section(statusBody, reg.headings.selfRating);
  if (rating) {
    const firstLine = rating.split("\n")[0].replace(/\(.*$/, "");
    for (const part of firstLine.split("·")) {
      const c = detectCourse(part);
      const v = /[~\d][\d\s\-–~%]*%/.exec(part);
      if (c && v) selfRating[c] = v[0].replace(/\s+/g, " ").trim();
    }
  }

  const bonus: Record<string, BonusInfo> = {};
  const coursePaths: Record<string, string> = {};
  for (const c of courses()) {
    const card = input.courses[c.id];
    if (card) coursePaths[c.id] = card.path;
    else warnings.push(`Course card ${c.card} not found.`);
    bonus[c.id] = bonusFor(c, card?.fm, now, input.totalOverrides?.[c.id]);
  }

  const due = input.week ? parseDueTable(input.week.text, now, input.taps ?? [], input.undos ?? []) : { items: [], targetLabel: "" };

  return {
    now,
    today,
    week: semesterWeek(now),
    statusPath: input.status?.path ?? null,
    statusSnapshot: snapMatch ? snapMatch[1].trim() : "",
    weekPath: input.week?.path ?? null,
    weekPlanPath: input.weekPlanPath,
    weekMtime: input.weekMtime,
    statusMtime: input.statusMtime,
    inboxWaiting: input.inboxWaiting ?? 0,
    events,
    snapshotRange: snap.range,
    snapshotGenerated: snap.generated,
    snapshotRaw: snap.raw,
    liveCals: live?.cals ?? [],
    liveAt: live?.fetchedAt ?? null,
    calendarRange: live && !snapshotNeeded ? live.range : snap.range,
    prep,
    due: due.items,
    targetLabel: due.targetLabel,
    weekParts: input.week ? weekPageParts(input.week.text) : { results: null, notes: null, checkIn: null },
    upcoming: input.status ? parseUpcoming(input.status.text, now) : [],
    bonus,
    exercises,
    selfRating,
    recent: input.recent,
    studyPages: input.studyPages,
    coursePaths,
    warnings,
  };
}

// ---------- selectors used by the views ----------

export function eventsOn(model: CockpitModel, key: string): CalEvent[] {
  return model.events.filter((e) => dayKey(e.start) === key);
}

export function weekKeys(anyKey: string): string[] {
  const mon = mondayOf(anyKey);
  return Array.from({ length: 7 }, (_, i) => addDays(mon, i));
}

/** What is happening now and what comes next (personal blocks are skipped). */
export function nowAndNext(model: CockpitModel): { current: CalEvent[]; next: CalEvent[] } {
  const t = model.now.getTime();
  const timed = model.events.filter((e) => !e.allDay && e.kind !== "personal");
  const current = timed.filter((e) => e.start.getTime() <= t && t < e.end.getTime());
  const next = timed.filter((e) => e.start.getTime() > t).slice(0, 6);
  return { current, next };
}

/**
 * Side-by-side layout for one day column: overlapping events share the width of their own overlap cluster
 * only, so one clash doesn't squeeze the whole day.
 */
export function sideBySide<T extends { s: number; en: number }>(items: T[]): Array<T & { lane: number; lanes: number }> {
  const sorted = [...items].sort((a, b) => a.s - b.s || b.en - a.en);
  const out: Array<T & { lane: number; lanes: number }> = [];
  let cluster: Array<T & { lane: number; lanes: number }> = [];
  let laneEnds: number[] = [];
  let clusterEnd = -1;
  const close = () => {
    for (const x of cluster) x.lanes = Math.max(1, laneEnds.length);
    out.push(...cluster);
    cluster = [];
    laneEnds = [];
  };
  for (const it of sorted) {
    if (cluster.length && it.s >= clusterEnd) close();
    let lane = laneEnds.findIndex((end) => end <= it.s);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(it.en);
    } else laneEnds[lane] = it.en;
    clusterEnd = cluster.length ? Math.max(clusterEnd, it.en) : it.en;
    cluster.push({ ...it, lane, lanes: 1 });
  }
  if (cluster.length) close();
  return out;
}

/** Planned study hours per course in a set of days, from the main subject of each block. */
export function studyHours(model: CockpitModel, keys: string[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const e of model.events) {
    if (e.kind !== "study" || !e.course || e.optional) continue;
    if (!keys.includes(dayKey(e.start))) continue;
    out[e.course] = (out[e.course] ?? 0) + (e.end.getTime() - e.start.getTime()) / 3600000;
  }
  return out;
}
