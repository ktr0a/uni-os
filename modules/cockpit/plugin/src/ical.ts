// A small iCalendar (RFC 5545) reader for private calendar feeds (Google Calendar's "secret address in iCal
// format", Outlook's published ICS link, iCloud's public calendar link, ...). Pure: no Obsidian imports, so it
// runs in tests. Handles what Google produces (and the others mostly share): folded lines,
// TZID / UTC / all-day dates, DURATION, RRULE (DAILY, WEEKLY, MONTHLY, YEARLY with INTERVAL, COUNT,
// UNTIL, BYDAY incl. ordinals, BYMONTHDAY, BYMONTH), RDATE, EXDATE, moved or cancelled single instances
// (RECURRENCE-ID) and cancelled series.

import { tz } from "./model";

export interface Occurrence {
  uid: string;
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  location: string;
  desc: string;
}

interface Prop {
  name: string;
  params: Record<string, string>;
  value: string;
}

interface Stamp {
  /** UTC milliseconds of the instant. */
  ms: number;
  allDay: boolean;
  /** Wall clock in `tz` (or UTC), used to step through recurrences without DST drift. */
  wall: { y: number; m: number; d: number; hh: number; mm: number; ss: number };
  tz: string | null;
}

interface VEvent {
  uid: string;
  summary: string;
  description: string;
  location: string;
  status: string;
  start: Stamp;
  end: Stamp | null;
  duration: number | null;
  rrule: string | null;
  rdates: number[];
  exdates: number[];
  recurrenceId: number | null;
}

/** The reader's time zone: the term's (term.timezone in uni-os.toml). */
const readerTz = (): string => tz();

// ---------- lines and properties ----------

function unfold(text: string): string[] {
  return text.replace(/\r\n?/g, "\n").replace(/\n[ \t]/g, "").split("\n");
}

function parseLine(line: string): Prop | null {
  // The value starts at the first ":" outside double quotes.
  let inQuote = false;
  let colon = -1;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') inQuote = !inQuote;
    else if (c === ":" && !inQuote) {
      colon = i;
      break;
    }
  }
  if (colon === -1) return null;
  const [name, ...rawParams] = line.slice(0, colon).split(";");
  const params: Record<string, string> = {};
  for (const p of rawParams) {
    const eq = p.indexOf("=");
    if (eq > 0) params[p.slice(0, eq).toUpperCase()] = p.slice(eq + 1).replace(/^"|"$/g, "");
  }
  return { name: name.toUpperCase(), params, value: line.slice(colon + 1) };
}

export function unescapeText(v: string): string {
  return v.replace(/\\([\\;,nN])/g, (_m, c: string) => (c === "n" || c === "N" ? "\n" : c));
}

// ---------- time ----------

const formatters = new Map<string, Intl.DateTimeFormat | null>();
function formatter(tz: string): Intl.DateTimeFormat | null {
  if (!formatters.has(tz)) {
    try {
      formatters.set(
        tz,
        new Intl.DateTimeFormat("en-GB", { timeZone: tz, year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric", second: "numeric", hourCycle: "h23" }),
      );
    } catch {
      formatters.set(tz, null);
    }
  }
  return formatters.get(tz)!;
}

/** Wall-clock time in an IANA zone as UTC milliseconds (DST-safe). Unknown zones fall back to the term's zone. */
export function wallToMs(y: number, m: number, d: number, hh: number, mm: number, ss: number, zone: string): number {
  const fmt = formatter(zone) ?? formatter(readerTz()) ?? formatter("UTC")!;
  const want = Date.UTC(y, m - 1, d, hh, mm, ss);
  let guess = want;
  for (let i = 0; i < 3; i++) {
    const p: Record<string, string> = {};
    for (const part of fmt.formatToParts(new Date(guess))) p[part.type] = part.value;
    const shown = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute, +p.second);
    guess += want - shown;
  }
  return guess;
}

function parseStamp(prop: Prop, fallbackTz: string): Stamp | null {
  const v = prop.value.trim();
  const date = /^(\d{4})(\d{2})(\d{2})$/.exec(v);
  if (date || prop.params.VALUE === "DATE") {
    // All-day dates float: they mean that day where the reader is (the term's zone), whatever the feed's zone.
    const m = date ?? /^(\d{4})(\d{2})(\d{2})/.exec(v);
    if (!m) return null;
    const wall = { y: +m[1], m: +m[2], d: +m[3], hh: 0, mm: 0, ss: 0 };
    const zone = readerTz();
    return { ms: wallToMs(wall.y, wall.m, wall.d, 0, 0, 0, zone), allDay: true, wall, tz: zone };
  }
  const dt = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})(Z?)$/.exec(v);
  if (!dt) return null;
  const wall = { y: +dt[1], m: +dt[2], d: +dt[3], hh: +dt[4], mm: +dt[5], ss: +dt[6] };
  if (dt[7] === "Z") return { ms: Date.UTC(wall.y, wall.m - 1, wall.d, wall.hh, wall.mm, wall.ss), allDay: false, wall, tz: null };
  const zone = prop.params.TZID || fallbackTz;
  return { ms: wallToMs(wall.y, wall.m, wall.d, wall.hh, wall.mm, wall.ss, zone), allDay: false, wall, tz: zone };
}

function parseDuration(v: string): number | null {
  const m = /^([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$/.exec(v.trim());
  if (!m) return null;
  const ms = ((+(m[2] ?? 0) * 7 + +(m[3] ?? 0)) * 86400 + +(m[4] ?? 0) * 3600 + +(m[5] ?? 0) * 60 + +(m[6] ?? 0)) * 1000;
  return m[1] === "-" ? -ms : ms;
}

// ---------- parsing ----------

export function parseIcs(text: string): { events: VEvent[]; tz: string } {
  const lines = unfold(text);
  let calTz = readerTz();
  for (const l of lines) {
    const p = l.startsWith("X-WR-TIMEZONE") ? parseLine(l) : null;
    if (p?.value) calTz = p.value.trim();
  }
  const events: VEvent[] = [];
  let cur: Prop[] | null = null;
  let depth = 0; // nested components (VALARM) inside a VEVENT
  for (const line of lines) {
    if (line === "BEGIN:VEVENT") {
      cur = [];
      depth = 0;
      continue;
    }
    if (!cur) continue;
    if (line.startsWith("BEGIN:")) {
      depth++;
      continue;
    }
    if (line.startsWith("END:") && depth > 0) {
      depth--;
      continue;
    }
    if (line === "END:VEVENT") {
      const ev = toEvent(cur, calTz);
      if (ev) events.push(ev);
      cur = null;
      continue;
    }
    if (depth === 0) {
      const p = parseLine(line);
      if (p) cur.push(p);
    }
  }
  return { events, tz: calTz };
}

function toEvent(props: Prop[], calTz: string): VEvent | null {
  const get = (n: string) => props.find((p) => p.name === n);
  const startProp = get("DTSTART");
  const start = startProp ? parseStamp(startProp, calTz) : null;
  if (!start) return null;
  const endProp = get("DTEND");
  const durProp = get("DURATION");
  const stamps = (name: string): number[] => {
    const out: number[] = [];
    for (const p of props.filter((x) => x.name === name)) {
      if (p.params.VALUE === "PERIOD") continue;
      for (const v of p.value.split(",")) {
        const s = parseStamp({ ...p, value: v }, calTz);
        if (s) out.push(s.ms);
      }
    }
    return out;
  };
  const exdates = stamps("EXDATE");
  const rdates = stamps("RDATE");
  const rid = get("RECURRENCE-ID");
  return {
    uid: get("UID")?.value ?? "",
    summary: unescapeText(get("SUMMARY")?.value ?? ""),
    description: unescapeText(get("DESCRIPTION")?.value ?? ""),
    location: unescapeText(get("LOCATION")?.value ?? ""),
    status: (get("STATUS")?.value ?? "CONFIRMED").toUpperCase(),
    start,
    end: endProp ? parseStamp(endProp, calTz) : null,
    duration: durProp ? parseDuration(durProp.value) : null,
    rrule: get("RRULE")?.value ?? null,
    rdates,
    exdates,
    recurrenceId: rid ? parseStamp(rid, calTz)?.ms ?? null : null,
  };
}

// ---------- recurrence ----------

const WEEKDAYS = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"];

function weekday(y: number, m: number, d: number): number {
  return new Date(Date.UTC(y, m - 1, d)).getUTCDay();
}
function daysInMonth(y: number, m: number): number {
  return new Date(Date.UTC(y, m, 0)).getUTCDate();
}
function addDaysWall(w: { y: number; m: number; d: number }, n: number): { y: number; m: number; d: number } {
  const t = new Date(Date.UTC(w.y, w.m - 1, w.d + n));
  return { y: t.getUTCFullYear(), m: t.getUTCMonth() + 1, d: t.getUTCDate() };
}

/** Days of month for BYDAY entries like "MO", "1MO", "-1FR" within one month. */
function byDayInMonth(y: number, m: number, entries: string[]): number[] {
  const out: number[] = [];
  const dim = daysInMonth(y, m);
  for (const e of entries) {
    const mm = /^([+-]?\d+)?(SU|MO|TU|WE|TH|FR|SA)$/.exec(e);
    if (!mm) continue;
    const wd = WEEKDAYS.indexOf(mm[2]);
    const days: number[] = [];
    for (let d = 1; d <= dim; d++) if (weekday(y, m, d) === wd) days.push(d);
    if (!mm[1]) out.push(...days);
    else {
      const n = +mm[1];
      const pick = n > 0 ? days[n - 1] : days[days.length + n];
      if (pick) out.push(pick);
    }
  }
  return [...new Set(out)].sort((a, b) => a - b);
}

/**
 * Start times (UTC ms) of a series, in order, up to `untilMs` (the end of the window we care about).
 * Steps in the series' own wall clock, so a 10:15 lecture stays at 10:15 across the DST change.
 */
export function expandRule(start: Stamp, rrule: string, windowEndMs: number, maxInstances = 2000): number[] {
  const r: Record<string, string> = {};
  for (const part of rrule.split(";")) {
    const [k, v] = part.split("=");
    if (k && v !== undefined) r[k.toUpperCase()] = v;
  }
  const freq = r.FREQ;
  const interval = Math.max(1, +(r.INTERVAL ?? 1));
  const count = r.COUNT ? +r.COUNT : Infinity;
  let until = Infinity;
  if (r.UNTIL) {
    const u = parseStamp({ name: "UNTIL", params: {}, value: r.UNTIL }, start.tz ?? readerTz());
    if (u) until = u.allDay ? u.ms + 86400000 - 1 : u.ms;
  }
  const byDay = r.BYDAY ? r.BYDAY.split(",") : null;
  const byMonthDay = r.BYMONTHDAY ? r.BYMONTHDAY.split(",").map(Number) : null;
  const byMonth = r.BYMONTH ? r.BYMONTH.split(",").map(Number) : null;
  const zone = start.tz;
  const { hh, mm, ss } = start.wall;
  const toMs = (w: { y: number; m: number; d: number }) =>
    start.allDay ? wallToMs(w.y, w.m, w.d, 0, 0, 0, zone ?? readerTz()) : zone ? wallToMs(w.y, w.m, w.d, hh, mm, ss, zone) : Date.UTC(w.y, w.m - 1, w.d, hh, mm, ss);

  const out: number[] = [];
  let n = 0;
  const limit = Math.min(windowEndMs, until);
  const emit = (w: { y: number; m: number; d: number }): boolean => {
    const ms = toMs(w);
    if (ms < start.ms) return true; // before the first instance: neither counted nor emitted
    if (ms > limit || n >= count) return false;
    n++;
    out.push(ms);
    return out.length < maxInstances;
  };

  const base = { y: start.wall.y, m: start.wall.m, d: start.wall.d };
  if (freq === "DAILY") {
    for (let i = 0; ; i += interval) {
      const w = addDaysWall(base, i);
      if (byDay && !byDay.some((e) => WEEKDAYS.indexOf(e.slice(-2)) === weekday(w.y, w.m, w.d))) {
        if (toMs(w) > limit) break;
        continue;
      }
      if (byMonth && !byMonth.includes(w.m)) {
        if (toMs(w) > limit) break;
        continue;
      }
      if (!emit(w)) break;
    }
  } else if (freq === "WEEKLY") {
    const wkst = WEEKDAYS.indexOf(r.WKST ?? "MO");
    const days = (byDay ?? [WEEKDAYS[weekday(base.y, base.m, base.d)]]).map((e) => WEEKDAYS.indexOf(e.slice(-2))).filter((x) => x >= 0);
    // Order the weekdays from the week start, so instances come out in time order.
    const order = [...new Set(days)].sort((a, b) => ((a - wkst + 7) % 7) - ((b - wkst + 7) % 7));
    const weekStart = addDaysWall(base, -((weekday(base.y, base.m, base.d) - wkst + 7) % 7));
    outer: for (let wk = 0; ; wk += interval) {
      const ws = addDaysWall(weekStart, wk * 7);
      if (toMs(ws) > limit + 7 * 86400000) break;
      for (const wd of order) {
        const w = addDaysWall(ws, (wd - wkst + 7) % 7);
        if (byMonth && !byMonth.includes(w.m)) continue;
        if (!emit(w)) break outer;
      }
    }
  } else if (freq === "MONTHLY") {
    outer: for (let k = 0; ; k += interval) {
      const y = base.y + Math.floor((base.m - 1 + k) / 12);
      const m = ((base.m - 1 + k) % 12) + 1;
      if (toMs({ y, m, d: 1 }) > limit) break;
      if (byMonth && !byMonth.includes(m)) continue;
      let days: number[];
      if (byMonthDay) days = byMonthDay.map((d) => (d < 0 ? daysInMonth(y, m) + d + 1 : d)).filter((d) => d >= 1 && d <= daysInMonth(y, m));
      else if (byDay) days = byDayInMonth(y, m, byDay);
      else days = base.d <= daysInMonth(y, m) ? [base.d] : [];
      for (const d of days.sort((a, b) => a - b)) if (!emit({ y, m, d })) break outer;
    }
  } else if (freq === "YEARLY") {
    outer: for (let k = 0; ; k += interval) {
      const y = base.y + k;
      if (toMs({ y, m: 1, d: 1 }) > limit) break;
      const months = byMonth ?? [base.m];
      for (const m of months) {
        const days = byDay ? byDayInMonth(y, m, byDay) : byMonthDay ?? [base.d];
        for (const d of days) if (d <= daysInMonth(y, m) && !emit({ y, m, d })) break outer;
      }
    }
  } else {
    if (start.ms <= limit) out.push(start.ms);
  }
  return out;
}

// ---------- expansion into a window ----------

/** Every occurrence overlapping [from, to), with moved and cancelled instances applied. */
export function occurrences(text: string, from: Date, to: Date): Occurrence[] {
  const { events } = parseIcs(text);
  const fromMs = from.getTime();
  const toMs = to.getTime();
  const overrides = new Map<string, VEvent>();
  for (const e of events) if (e.recurrenceId !== null) overrides.set(`${e.uid}|${e.recurrenceId}`, e);

  const out: Occurrence[] = [];
  const push = (e: VEvent, startMs: number) => {
    const length = e.end ? e.end.ms - e.start.ms : e.duration ?? (e.start.allDay ? 86400000 : 0);
    const endMs = startMs + length;
    if (endMs <= fromMs && !(length === 0 && startMs >= fromMs)) return;
    if (startMs >= toMs) return;
    out.push({ uid: e.uid, title: e.summary, start: new Date(startMs), end: new Date(endMs), allDay: e.start.allDay, location: e.location, desc: e.description });
  };

  for (const e of events) {
    if (e.recurrenceId !== null) continue; // handled below
    if (e.status === "CANCELLED") continue;
    if (!e.rrule && !e.rdates.length) {
      push(e, e.start.ms);
      continue;
    }
    // Instances = the rule's dates (or just DTSTART) plus any extra RDATEs, minus EXDATEs and overrides.
    const starts = new Set(e.rrule ? expandRule(e.start, e.rrule, toMs) : [e.start.ms]);
    for (const r of e.rdates) if (r <= toMs) starts.add(r);
    const ex = new Set(e.exdates);
    for (const ms of [...starts].sort((a, b) => a - b)) {
      if (ex.has(ms) || overrides.has(`${e.uid}|${ms}`)) continue;
      push(e, ms);
    }
  }
  for (const o of overrides.values()) if (o.status !== "CANCELLED") push(o, o.start.ms);
  return out.sort((a, b) => a.start.getTime() - b.start.getTime() || a.title.localeCompare(b.title));
}
