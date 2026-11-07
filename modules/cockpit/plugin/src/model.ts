// Time helpers in the term's time zone (DST-safe) and the term week. Pure: no Obsidian or DOM imports.
// The time zone and week 0 come from the registry (term.timezone, term.week0_monday in uni-os.toml).
// Dates in the notes are English ("Mon 26 Oct 23:59"): that is part of the Uni OS file-format contract.

import { registry } from "./registry";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const WEEKDAY_LONG = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
export const MONTH_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** The term's IANA time zone. */
export function tz(): string {
  return registry().term.timezone;
}

export interface ZParts {
  y: number;
  m: number; // 1-12
  d: number;
  hh: number;
  mm: number;
  wd: number; // 0 = Sunday
}

const formatters = new Map<string, Intl.DateTimeFormat>();
function fmt(zone: string): Intl.DateTimeFormat {
  let f = formatters.get(zone);
  if (!f) {
    f = new Intl.DateTimeFormat("en-GB", {
      timeZone: zone,
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
      hourCycle: "h23",
      weekday: "short",
    });
    formatters.set(zone, f);
  }
  return f;
}

export function zparts(date: Date): ZParts {
  const p: Record<string, string> = {};
  for (const part of fmt(tz()).formatToParts(date)) p[part.type] = part.value;
  return {
    y: +p.year,
    m: +p.month,
    d: +p.day,
    hh: +p.hour % 24,
    mm: +p.minute,
    wd: WEEKDAYS.indexOf(p.weekday),
  };
}

/** A wall-clock time in the term's time zone as a Date. */
export function zdate(y: number, m: number, d: number, hh = 0, mm = 0): Date {
  const wall = Date.UTC(y, m - 1, d, hh, mm);
  let guess = wall;
  for (let i = 0; i < 3; i++) {
    const p = zparts(new Date(guess));
    const shown = Date.UTC(p.y, p.m - 1, p.d, p.hh, p.mm);
    guess += wall - shown;
  }
  return new Date(guess);
}

export function dayKey(date: Date): string {
  const p = zparts(date);
  return `${p.y}-${String(p.m).padStart(2, "0")}-${String(p.d).padStart(2, "0")}`;
}

function dayNumber(key: string): number {
  const [y, m, d] = key.split("-").map(Number);
  return Math.round(Date.UTC(y, m - 1, d) / 86400000);
}

export function addDays(key: string, n: number): string {
  const dt = new Date((dayNumber(key) + n) * 86400000);
  return dt.toISOString().slice(0, 10);
}

export function daysBetween(fromKey: string, toKey: string): number {
  return dayNumber(toKey) - dayNumber(fromKey);
}

/** Term week: week 0 starts on term.week0_monday. Without it, 0. */
export function semesterWeek(date: Date): number {
  const w0 = registry().term.week0;
  if (!w0) return 0;
  return Math.floor(daysBetween(w0, dayKey(date)) / 7);
}

/** Monday (day key) of the week containing the date. */
export function mondayOf(key: string): string {
  const wd = new Date(dayNumber(key) * 86400000).getUTCDay();
  return addDays(key, -((wd + 6) % 7));
}

export function weekdayOf(key: string): number {
  return new Date(dayNumber(key) * 86400000).getUTCDay();
}

export function hm(date: Date): string {
  const p = zparts(date);
  return `${String(p.hh).padStart(2, "0")}:${String(p.mm).padStart(2, "0")}`;
}

/** "Mon 26 Oct" */
export function shortDay(dateOrKey: Date | string): string {
  const key = typeof dateOrKey === "string" ? dateOrKey : dayKey(dateOrKey);
  const [, m, d] = key.split("-").map(Number);
  return `${WEEKDAYS[weekdayOf(key)]} ${d} ${MONTHS[m - 1]}`;
}

/** Minutes since local midnight. */
export function minuteOfDay(date: Date): number {
  const p = zparts(date);
  return p.hh * 60 + p.mm;
}

/** "17:30" -> 1050; anything else -> null. */
export function minutesOf(t: string): number | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(t.trim());
  return m ? +m[1] * 60 + +m[2] : null;
}

/** 1050 -> "17:30" (wraps past midnight). */
export function clockOf(minutes: number): string {
  const m = ((minutes % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

/** "in 47 min", "in 2 h 5 min", "in 3 d", "2 d ago" */
export function relative(from: Date, to: Date): string {
  const mins = Math.round((to.getTime() - from.getTime()) / 60000);
  const abs = Math.abs(mins);
  const past = mins < 0;
  let s: string;
  if (abs < 60) s = `${abs} min`;
  else if (abs < 60 * 24) s = `${Math.floor(abs / 60)} h${abs % 60 ? ` ${abs % 60} min` : ""}`;
  else {
    const days = daysBetween(dayKey(from), dayKey(to));
    s = `${Math.abs(days)} d`;
  }
  return past ? `${s} ago` : `in ${s}`;
}

/**
 * The year of a day written without one ("Mon 26 Oct"): the candidate (last, this or next year) closest to
 * `ref`, preferring one whose weekday matches the written weekday. A wrong weekday in a note costs 60 days of
 * distance, so a typo can't flip the year, but around New Year "Tue 5 Jan" read on 20 Dec lands in January.
 */
export function inferYear(month: number, day: number, weekday: number | null, ref: Date): number {
  const refKey = dayKey(ref);
  const y = +refKey.slice(0, 4);
  let best = { year: y, score: Infinity };
  for (const year of [y - 1, y, y + 1]) {
    const key = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const score = Math.abs(daysBetween(refKey, key)) + (weekday !== null && weekdayOf(key) !== weekday ? 60 : 0);
    if (score < best.score) best = { year, score };
  }
  return best.year;
}

/**
 * Parse a date like "Mon 26 Oct 23:59", "Tue 3 Nov 13:15-15:00", "Sun 1 Nov" (the year is inferred around
 * `ref`, by default now). Returns the first date found in the text. A date without a time means 23:59 that day.
 */
export function parseDayTime(text: string, ref: Date = new Date()): { date: Date; dateOnly: boolean; key: string } | null {
  const re = /\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\s+(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*(?:\s+(\d{1,2}):(\d{2}))?/;
  const m = re.exec(text.replace(/\*\*/g, ""));
  if (!m) return null;
  const month = MONTHS.indexOf(m[3]) + 1;
  const day = +m[2];
  const year = inferYear(month, day, WEEKDAYS.indexOf(m[1]), ref);
  const dateOnly = m[4] === undefined;
  const date = dateOnly ? zdate(year, month, day, 23, 59) : zdate(year, month, day, +m[4], +m[5]);
  const key = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  return { date, dateOnly, key };
}

/** "2026-11-05" or "2026-11-05 16:15" (or with a "T") as a Date in the term's zone; date-only means 23:59. */
export function parseStamp(s: string): { date: Date; dateOnly: boolean } | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{1,2}):(\d{2}))?/.exec(s.trim());
  if (!m) return null;
  const dateOnly = m[4] === undefined;
  return { date: dateOnly ? zdate(+m[1], +m[2], +m[3], 23, 59) : zdate(+m[1], +m[2], +m[3], +m[4], +m[5]), dateOnly };
}
