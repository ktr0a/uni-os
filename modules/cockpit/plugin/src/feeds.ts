// Live calendar: fetches private iCal addresses (kept in Obsidian's secret storage, never in the vault), expands
// them for a window around today, and caches the result on this device so the cockpit still has the last good
// copy offline. Read-only towards the calendar provider.

import { App, requestUrl } from "obsidian";
import { occurrences } from "./ical";
import { addDays, dayKey, mondayOf, zdate } from "./model";
import type { LiveCalendar, RawEvent } from "./parse";
import type { CockpitSettings, FeedConfig } from "./settings";

interface FeedState {
  events: RawEvent[];
  fetchedAt: number;
  error: string | null;
  /** Diagnostics for the settings page. */
  ms?: number;
  windowStart?: string;
}

const CACHE_KEY = "uni-os-cockpit-feed-cache";
const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;

export function scrub(s: string): string {
  return s.replace(EMAIL, "[email removed]");
}

/** Monday of last week to five weeks ahead: enough for Today, Agenda and paging in Week. */
export function feedWindow(now: Date): { from: Date; to: Date; range: { start: string; end: string } } {
  const mon = mondayOf(dayKey(now));
  const start = addDays(mon, -7);
  const end = addDays(mon, 34);
  const [y1, m1, d1] = start.split("-").map(Number);
  const [y2, m2, d2] = addDays(end, 1).split("-").map(Number);
  return { from: zdate(y1, m1, d1), to: zdate(y2, m2, d2), range: { start, end } };
}

export function normaliseFeedUrl(raw: string): string {
  const u = raw.trim().replace(/^webcal:\/\//i, "https://");
  // Plain http only for a feed on this machine (testing).
  if (!/^https:\/\//i.test(u) && !/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//i.test(u)) throw new Error("the address should start with https:// (or webcal://)");
  return u;
}

export class FeedCache {
  private state = new Map<string, FeedState>();
  private inflight: Promise<boolean> | null = null;

  constructor(
    private app: App,
    private settings: () => CockpitSettings,
  ) {
    try {
      const saved = this.app.loadLocalStorage(CACHE_KEY) as Record<string, FeedState> | null;
      for (const [id, st] of Object.entries(saved ?? {})) this.state.set(id, { ...st, error: null });
    } catch {
      // A broken cache only means the first refresh starts from nothing.
    }
  }

  private feed(id: string): FeedConfig | undefined {
    return this.settings().feeds.find((f) => f.id === id);
  }

  private url(id: string): string | null {
    const f = this.feed(id);
    if (!f?.on || !f.secret) return null;
    return this.app.secretStorage.getSecret(f.secret) || null;
  }

  configured(): string[] {
    return this.settings()
      .feeds.map((f) => f.id)
      .filter((id) => this.url(id));
  }

  status(id: string): FeedState | undefined {
    return this.state.get(id);
  }

  isDue(now = new Date()): boolean {
    const minutes = this.settings().feedMinutes;
    const win = feedWindow(now).range.start;
    return this.configured().some((id) => {
      const st = this.state.get(id);
      return !st || st.windowStart !== win || now.getTime() - st.fetchedAt > minutes * 60000;
    });
  }

  private toRaw(id: string, o: ReturnType<typeof occurrences>[number]): RawEvent {
    const personal = this.feed(id)?.role === "personal";
    const showTitles = this.settings().personalTitles;
    return {
      cal: id,
      title: personal && !showTitles ? "Personal" : o.title,
      start: o.start.toISOString(),
      end: o.end.toISOString(),
      location: personal && !showTitles ? "" : o.location,
      desc: personal && !showTitles ? "" : scrub(o.desc),
      allDay: o.allDay || undefined,
    };
  }

  /** Fetches the feeds that are due (or all, with force). Resolves true when any calendar changed. */
  refresh(force = false): Promise<boolean> {
    this.inflight ??= this.doRefresh(force).finally(() => (this.inflight = null));
    return this.inflight;
  }

  private async doRefresh(force: boolean): Promise<boolean> {
    const now = new Date();
    const { from, to, range } = feedWindow(now);
    const minutes = this.settings().feedMinutes;
    let changed = false;
    for (const id of this.configured()) {
      const prev = this.state.get(id);
      if (!force && prev && prev.windowStart === range.start && now.getTime() - prev.fetchedAt <= minutes * 60000) continue;
      const started = Date.now();
      try {
        const res = await requestUrl({ url: normaliseFeedUrl(this.url(id)!), method: "GET", throw: false });
        if (res.status !== 200) throw new Error(res.status === 404 ? "address not found (404): was it reset at the calendar provider?" : `HTTP ${res.status}`);
        const text = res.text;
        if (!text.includes("BEGIN:VCALENDAR")) throw new Error("the address did not return an iCal file");
        const events = occurrences(text, from, to).map((o) => this.toRaw(id, o));
        if (!prev || JSON.stringify(prev.events) !== JSON.stringify(events)) changed = true;
        this.state.set(id, { events, fetchedAt: Date.now(), error: null, ms: Date.now() - started, windowStart: range.start });
      } catch (err) {
        const message = (err as Error).message || String(err);
        if (!prev?.error) changed = true;
        this.state.set(id, { ...(prev ?? { events: [], fetchedAt: 0 }), error: message, ms: Date.now() - started });
      }
    }
    // Drop calendars that were unlinked or switched off.
    for (const id of [...this.state.keys()]) {
      if (!this.configured().includes(id)) {
        this.state.delete(id);
        changed = true;
      }
    }
    this.save();
    return changed;
  }

  private save(): void {
    const out: Record<string, FeedState> = {};
    for (const [id, st] of this.state) if (st.fetchedAt) out[id] = { events: st.events, fetchedAt: st.fetchedAt, error: null, windowStart: st.windowStart };
    this.app.saveLocalStorage(CACHE_KEY, out);
  }

  live(): LiveCalendar | null {
    const ids = this.configured();
    const ok = ids.filter((id) => (this.state.get(id)?.fetchedAt ?? 0) > 0);
    const errors = ids.flatMap((id) => {
      const e = this.state.get(id)?.error;
      return e ? [{ cal: this.feed(id)?.label ?? id, message: e }] : [];
    });
    if (!ok.length && !errors.length) return null;
    return {
      cals: ok,
      events: ok.flatMap((id) => this.state.get(id)!.events),
      fetchedAt: ok.length ? Math.min(...ok.map((id) => this.state.get(id)!.fetchedAt)) : 0,
      range: feedWindow(new Date()).range,
      errors,
    };
  }
}

// ---------- the snapshot file, kept fresh for agents that read the vault ----------

export interface SnapshotFile {
  generated: string;
  source: string;
  range: { start: string; end: string };
  events: RawEvent[];
}

/**
 * The snapshot the vault keeps for agents: this week and next, from the live feeds where there are some and the
 * old snapshot otherwise. Busy-only calendars stay busy time only, whatever the cockpit shows on this device,
 * because the file syncs.
 */
export function snapshotFromLive(live: LiveCalendar, previous: RawEvent[], now: Date, feeds: Array<Pick<FeedConfig, "id" | "role">>): SnapshotFile {
  const mon = mondayOf(dayKey(now));
  const range = { start: mon, end: addDays(mon, 13) };
  const inRange = (e: RawEvent) => {
    const k = dayKey(new Date(e.start));
    return k >= range.start && k <= range.end;
  };
  const busyOnly = new Set(feeds.filter((f) => f.role === "personal").map((f) => f.id));
  const fromLive = live.events
    .filter(inRange)
    .map((e) => (busyOnly.has(e.cal) ? { cal: e.cal, title: "Personal", start: e.start, end: e.end, ...(e.allDay ? { allDay: true } : {}) } : { ...e, desc: scrub(e.desc ?? "").slice(0, 900) }));
  const kept = previous.filter((e) => !live.cals.includes(e.cal) && inRange(e));
  const events = [...fromLive, ...kept].sort((a, b) => a.start.localeCompare(b.start) || a.title.localeCompare(b.title));
  return {
    generated: now.toISOString(),
    source: `Live iCal feeds via the Uni OS cockpit plugin (${live.cals.join(", ")})${kept.length ? "; other calendars from the previous snapshot" : ""}. Busy-only calendars: time only, no titles.`,
    range,
    events,
  };
}

/** True when two snapshot files would show the same calendar (ignores when they were made). */
export function sameSnapshot(a: { range?: unknown; events?: unknown } | null, b: SnapshotFile): boolean {
  return !!a && JSON.stringify(a.range) === JSON.stringify(b.range) && JSON.stringify(a.events) === JSON.stringify(b.events);
}
