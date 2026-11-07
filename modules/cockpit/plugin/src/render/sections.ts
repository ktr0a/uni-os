// Building blocks shared by the three home layouts.

import { setIcon, setTooltip } from "obsidian";
import { bonusFigure as figureOf } from "../bonus";
import { syncOn, syncWhen } from "../done";
import { PrepBlock, PrepNote, gapCount, prepRunsText } from "../prep";
import { MONTH_LONG, WEEKDAY_LONG, addDays, dayKey, hm, minuteOfDay, minutesOf, mondayOf, relative, shortDay, zdate, zparts } from "../model";
import { CalEvent, DueItem, eventsOn, nowAndNext, plain, studyHours, weekKeys } from "../parse";
import { courseById, courses } from "../registry";
import { courseVars, dot, iconButton, inline, meter, noteLink, section } from "../ui";
import { Ctx, countdown, eventTitle, isSelected, isUrgent, pastLabel, sortedDue, whenLabel } from "./ctx";

/** Events of a day as the settings want them; all-day entries only where asked for (the agenda). */
export function visibleEvents(ctx: Ctx, key: string, withAllDay = false): CalEvent[] {
  return eventsOn(ctx.model, key).filter((e) => (withAllDay || !e.allDay) && (ctx.s.showPersonal || e.kind !== "personal") && (ctx.s.showOptional || !e.optional));
}

export function longDate(ctx: Ctx): string {
  const p = zparts(ctx.model.now);
  return `${WEEKDAY_LONG[p.wd]} ${p.d} ${MONTH_LONG[p.m - 1]} · week ${ctx.model.week}`;
}

// ---------- headline ----------

export function headline(ctx: Ctx, parent: HTMLElement): void {
  const el = parent.createDiv({ cls: "uc-headline" });
  const { current, next } = nowAndNext(ctx.model);
  const cur = current.find((e) => e.kind === "study") ?? current[0];
  const main = el.createDiv({ cls: "uc-headline-main" });
  const sub = el.createDiv({ cls: "uc-headline-sub" });
  if (cur) {
    courseVars(main, cur.course);
    main.createSpan({ cls: "uc-headline-kicker", text: `Now until ${hm(cur.end)}` });
    main.createSpan({ text: cur.title });
    const focus = cur.focus.split("\n")[0];
    sub.setText([cur.location, focus].filter(Boolean).join(" · "));
  } else if (next[0]) {
    const n = next[0];
    courseVars(main, n.course);
    const today = dayKey(n.start) === ctx.model.today;
    main.createSpan({ cls: "uc-headline-kicker", text: today ? `Next at ${hm(n.start)}` : `Done for today · next ${whenLabel(ctx, n.start)}` });
    main.createSpan({ text: n.title });
    sub.setText([relative(ctx.model.now, n.start), n.location].filter(Boolean).join(" · "));
  } else {
    main.setText("Nothing planned in the calendar.");
  }
  sub.addEventListener("click", () => {
    const e = cur ?? next[0];
    if (!e) return;
    ctx.state.selected = isSelected(ctx, e) ? null : e;
    ctx.rerender();
  });

  for (const d of sortedDue(ctx).filter((x) => isUrgent(ctx, x))) {
    const u = el.createDiv({ cls: "uc-urgent" });
    const ic = u.createSpan({ cls: "uc-urgent-icon" });
    const past = d.deadline!.getTime() < ctx.model.now.getTime();
    setIcon(ic, d.state === "overdue" ? "alert-triangle" : past && !d.endsAt ? "hourglass" : "alarm-clock");
    inline(ctx.app, u.createSpan({ cls: "uc-urgent-text" }), d.item, ctx.model.weekPath ?? "", ctx.hover);
    u.createSpan({ cls: "uc-urgent-when", text: past ? pastLabel(d) : countdown(ctx, d.deadline!, d.dateOnly) });
    doneButton(ctx, u, d);
  }
}

// ---------- timeline ----------

function dayRange(ctx: Ctx, events: CalEvent[]): { from: number; to: number } {
  let from = ctx.s.dayStart * 60;
  let to = ctx.s.dayEnd * 60;
  if (ctx.s.fitDay && events.length) {
    from = Math.min(from, ...events.map((e) => Math.floor(minuteOfDay(e.start) / 60) * 60));
    to = Math.max(to, ...events.map((e) => Math.ceil((minuteOfDay(e.end) || 24 * 60) / 60) * 60));
  }
  return { from, to: Math.max(to, from + 60) };
}

/** "strip": a thin bar of coloured segments (Focus); "full": labelled blocks in lanes (Dashboard). */
export function timeline(ctx: Ctx, parent: HTMLElement, key: string, variant: "strip" | "full"): void {
  const events = visibleEvents(ctx, key);
  const { from, to } = dayRange(ctx, events);
  const span = to - from;
  const wrap = parent.createDiv({ cls: `uc-timeline is-${variant}` });
  const track = wrap.createDiv({ cls: "uc-track" });
  const laneEnds: number[] = [];
  const laneH = variant === "strip" ? 10 : 50;
  for (const e of events) {
    const s = Math.max(from, minuteOfDay(e.start));
    const en = Math.min(to, minuteOfDay(e.end) || 24 * 60);
    if (en <= s) continue;
    let lane = laneEnds.findIndex((end) => end <= s);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(en);
    } else laneEnds[lane] = en;
    const b = track.createDiv({ cls: `uc-ev uc-ev-${e.kind}${e.optional ? " is-optional" : ""}${isSelected(ctx, e) ? " is-selected" : ""}` });
    courseVars(b, e.course);
    b.style.left = `${((s - from) / span) * 100}%`;
    b.style.width = `calc(${((en - s) / span) * 100}% - 2px)`;
    b.style.top = `${lane * (laneH + (variant === "strip" ? 3 : 6))}px`;
    b.style.height = `${laneH}px`;
    b.setAttr("aria-label", `${hm(e.start)}-${hm(e.end)} ${eventTitle(ctx, e)}${e.location ? " · " + e.location : ""}`);
    if (variant === "full") {
      b.createDiv({ cls: "uc-ev-title", text: eventTitle(ctx, e) });
      b.createDiv({ cls: "uc-ev-meta", text: `${hm(e.start)}${e.location ? " · " + e.location : ""}` });
    }
    b.addEventListener("click", () => {
      ctx.state.selected = isSelected(ctx, e) ? null : e;
      ctx.rerender();
    });
  }
  const lanes = Math.max(1, laneEnds.length);
  track.style.height = `${lanes * (laneH + (variant === "strip" ? 3 : 6))}px`;
  if (key === ctx.model.today) {
    const nm = minuteOfDay(ctx.model.now);
    if (nm >= from && nm <= to) track.createDiv({ cls: "uc-now" }).style.left = `${((nm - from) / span) * 100}%`;
  }
  const axis = wrap.createDiv({ cls: "uc-axis" });
  const step = span > 10 * 60 ? 180 : 120;
  for (let m = Math.ceil(from / step) * step; m <= to; m += step) axis.createSpan({ text: `${String(m / 60).padStart(2, "0")}:00` }).style.left = `${((m - from) / span) * 100}%`;
  if (!events.length) wrap.createDiv({ cls: "uc-muted uc-empty-line", text: "Nothing in the calendar for this day." });

  const sel = ctx.state.selected && dayKey(ctx.state.selected.start) === key ? ctx.state.selected : null;
  if (sel) eventDetail(ctx, parent, sel);
}

export function eventDetail(ctx: Ctx, parent: HTMLElement, e: CalEvent): void {
  const d = parent.createDiv({ cls: "uc-detail" });
  courseVars(d, e.course);
  const head = d.createDiv({ cls: "uc-detail-head" });
  const cal = ctx.s.feeds.find((f) => f.id === e.cal)?.label ?? e.cal;
  head.createSpan({ cls: "uc-detail-title", text: e.kind === "personal" ? `${eventTitle(ctx, e)} (${cal} calendar)` : e.title });
  head.createSpan({ cls: "uc-muted", text: `${shortDay(e.start)} ${hm(e.start)}-${hm(e.end)}${e.location ? " · " + e.location : ""}` });
  const close = head.createSpan({ cls: "uc-detail-close", attr: { "aria-label": "Close" } });
  setIcon(close, "x");
  close.addEventListener("click", () => {
    ctx.state.selected = null;
    ctx.rerender();
  });
  if (e.desc) d.createEl("pre", { cls: "uc-detail-desc", text: e.desc });
  else if ((e.kind === "lecture" || e.kind === "exercise") && e.course && ctx.model.coursePaths[e.course]) {
    const p = d.createDiv({ cls: "uc-muted" });
    noteLink(ctx.app, p, `${courseById(e.course)?.short ?? e.course} course card`, ctx.model.coursePaths[e.course], "", ctx.hover);
  }
}

// ---------- due ----------

/**
 * The quiet Done button at the end of a due row or urgent line. Every row gets the slot, so the labels line up
 * whether or not the button applies (done rows and items not released yet have none).
 */
function doneButton(ctx: Ctx, parent: HTMLElement, d: DueItem): void {
  const slot = parent.createSpan({ cls: "uc-due-act" });
  if (d.tapped) {
    iconButton(slot, "undo-2", "Undo Done", () => ctx.markUndone(d), "uc-quiet uc-icon-only uc-done-btn is-undo");
    return;
  }
  if (d.state === "done" || d.notReleased) return;
  iconButton(slot, "check", "Mark done", () => ctx.markDone(d), "uc-quiet uc-icon-only uc-done-btn");
}

export function dueRow(ctx: Ctx, parent: HTMLElement, d: DueItem, compact: boolean): void {
  const row = parent.createDiv({ cls: `uc-due is-${d.state}${isUrgent(ctx, d) ? " is-urgent" : ""}${compact ? " is-compact" : ""}` });
  dot(row, d.course);
  const main = row.createDiv({ cls: "uc-due-main" });
  inline(ctx.app, main.createSpan({ cls: "uc-due-item" }), d.item, ctx.model.weekPath ?? "", ctx.hover);
  const meta = main.createDiv({ cls: "uc-due-meta" });
  if (!compact) meta.createSpan({ text: plain(d.deadlineText) });
  if (ctx.s.showTarget && plain(d.target) && !d.targetPast) meta.createSpan({ cls: "uc-due-target", text: `${ctx.model.targetLabel || "target"} ${plain(d.target)}` });
  if (!compact && plain(d.status)) inline(ctx.app, meta.createSpan({ cls: "uc-due-status" }), d.status, ctx.model.weekPath ?? "", ctx.hover);
  const right = row.createDiv({ cls: "uc-due-right" });
  // A tutorial or tentative slot is not a hand-in: say so next to its countdown.
  const lead = d.soft ? "no hand-in · " : "";
  if (d.lapsed) right.createSpan({ text: "passed" });
  else if (d.tapped) {
    const i = right.createSpan({ cls: "uc-state-icon" });
    setIcon(i, "check");
    right.createSpan({ text: !d.tapWaiting ? "tapped" : syncOn() ? `tapped · week page ${syncWhen(ctx.model.now)}` : "tapped · note in the inbox" });
  } else if (d.state === "done") {
    const i = right.createSpan({ cls: "uc-state-icon" });
    setIcon(i, "check");
    right.createSpan({ text: plain(d.status).split(" ")[0] || "done" });
  } else if (d.state === "pending") {
    const i = right.createSpan({ cls: "uc-state-icon" });
    setIcon(i, "hourglass");
    const past = d.deadline && d.deadline.getTime() < ctx.model.now.getTime();
    right.createSpan({ text: !d.deadline ? "waiting" : past ? "result not logged yet" : lead + countdown(ctx, d.deadline, d.dateOnly) });
  } else if (d.state === "overdue") right.createSpan({ text: pastLabel(d) });
  else if (d.endsAt && d.deadline && d.deadline.getTime() < ctx.model.now.getTime()) right.createSpan({ text: pastLabel(d) });
  else right.createSpan({ text: d.deadline ? lead + countdown(ctx, d.deadline, d.dateOnly) : plain(d.deadlineText) });
  doneButton(ctx, row, d);
}

export function dueList(ctx: Ctx, parent: HTMLElement, opts: { limit?: number; compact?: boolean; skipUrgent?: boolean } = {}): void {
  if (!ctx.model.due.length) {
    parent.createDiv({ cls: "uc-muted uc-empty-line", text: "No “Due this week” table on the current week page." });
    return;
  }
  // When the headline already lists the urgent ones, don't repeat them right below it.
  const items = sortedDue(ctx).filter((d) => !opts.skipUrgent || !isUrgent(ctx, d));
  const open = items.filter((d) => d.state !== "done");
  const done = items.filter((d) => d.state === "done");
  const limit = opts.limit && !ctx.state.dueExpanded ? opts.limit : open.length;
  const list = parent.createDiv({ cls: "uc-due-list" });
  for (const d of open.slice(0, limit)) dueRow(ctx, list, d, !!opts.compact);
  if (open.length > limit) {
    const more = parent.createDiv({ cls: "uc-more", text: `${open.length - limit} more due this week` });
    more.addEventListener("click", () => {
      ctx.state.dueExpanded = true;
      ctx.rerender();
    });
  } else if (opts.limit && ctx.state.dueExpanded && open.length > opts.limit) {
    const less = parent.createDiv({ cls: "uc-more", text: "Show fewer" });
    less.addEventListener("click", () => {
      ctx.state.dueExpanded = false;
      ctx.rerender();
    });
  }
  if (done.length && ctx.s.showDone !== "hide" && (!opts.limit || ctx.state.dueExpanded)) {
    const det = parent.createEl("details", { cls: "uc-done" });
    det.open = ctx.s.showDone === "show" || ctx.state.doneOpen;
    det.addEventListener("toggle", () => (ctx.state.doneOpen = det.open));
    det.createEl("summary", { text: `${done.length} done or passed this week` });
    for (const d of done) dueRow(ctx, det, d, !!opts.compact);
  } else if (opts.limit) {
    // Focus folds what is done, but a tap must stay easy to undo.
    const tapped = done.filter((d) => d.tapped);
    if (tapped.length) {
      const det = parent.createEl("details", { cls: "uc-done" });
      det.open = ctx.state.doneOpen;
      det.addEventListener("toggle", () => (ctx.state.doneOpen = det.open));
      det.createEl("summary", { text: `${tapped.length} tapped done, open to undo` });
      for (const d of tapped) dueRow(ctx, det, d, !!opts.compact);
    }
  }
}

// ---------- next up ----------

export function nextList(ctx: Ctx, parent: HTMLElement, limit = 6): void {
  const { current, next } = nowAndNext(ctx.model);
  const list = [...current.map((e) => ({ e, now: true })), ...next.map((e) => ({ e, now: false }))].filter(({ e }) => ctx.s.showOptional || !e.optional).slice(0, limit);
  if (!list.length) parent.createDiv({ cls: "uc-muted uc-empty-line", text: "Nothing ahead in the calendar." });
  for (const { e, now } of list) {
    const r = parent.createDiv({ cls: `uc-next is-${e.kind}${now ? " is-now" : ""}` });
    r.createDiv({ cls: "uc-next-time", text: hm(e.start) });
    dot(r, e.course);
    const mid = r.createDiv({ cls: "uc-next-mid" });
    mid.createDiv({ cls: "uc-next-title", text: e.title });
    const day = dayKey(e.start) === ctx.model.today ? "" : dayKey(e.start) === addDays(ctx.model.today, 1) ? "tomorrow" : shortDay(e.start);
    mid.createDiv({ cls: "uc-muted uc-small", text: [day, e.location].filter(Boolean).join(" · ") });
    r.createDiv({ cls: "uc-next-rel", text: now ? "now" : relative(ctx.model.now, e.start) });
    r.addEventListener("click", () => {
      ctx.state.selected = e;
      if (dayKey(e.start) !== ctx.model.today) {
        ctx.state.weekOffset = Math.round((Date.parse(mondayOf(dayKey(e.start))) - Date.parse(mondayOf(ctx.model.today))) / (7 * 86400000));
        ctx.go("week");
      } else ctx.rerender();
    });
  }
}

// ---------- bonus ----------

function bonusFigure(ctx: Ctx, id: string): string {
  const b = ctx.model.bonus[id];
  const c = courseById(id);
  if (!b || !c || !b.meter) return "—";
  if (ctx.s.bonusFigure === "bonus") return b.bonusNow === null ? "?" : figureOf(b.bonusNow, c.bonus);
  if (ctx.s.bonusFigure === "percent") return b.bonusNow === null || !c.bonus.maxBonus ? "?" : `${Math.round((b.bonusNow / c.bonus.maxBonus) * 100)} %`;
  return b.ofShort ? `${b.big} ${b.ofShort}` : b.big;
}

/** compact: one row of small bullet graphs (Focus). Otherwise a row per course with its headline. Courses without a bonus are left out. */
export function bonusList(ctx: Ctx, parent: HTMLElement, compact: boolean): void {
  const wrap = parent.createDiv({ cls: compact ? "uc-bonus-grid" : "uc-bonus-list" });
  for (const c of courses()) {
    const b = ctx.model.bonus[c.id];
    if (!b || c.bonus.scheme === "none") continue;
    const r = wrap.createDiv({ cls: `uc-bonus is-${b.tone}` });
    courseVars(r, c.id);
    const top = r.createDiv({ cls: "uc-bonus-top" });
    dot(top, c.id);
    top.createSpan({ cls: "uc-bonus-name", text: c.short });
    top.createSpan({ cls: "uc-bonus-fig", text: bonusFigure(ctx, c.id) });
    if (b.meter) meter(r, b.meter);
    else r.createDiv({ cls: "uc-meter is-empty" });
    r.createDiv({ cls: "uc-bonus-head", text: b.headline });
    r.setAttr("aria-label", `${c.short}: ${b.headline}. ${b.detail}`);
    r.addEventListener("click", () => ctx.go("courses"));
  }
}

// ---------- daily study prep ----------

/** "Prep for Wed 28 Oct: ready, 2 gaps · 18:16" (the presence line). */
export function prepPresence(ctx: Ctx, el: HTMLElement): void {
  const p = ctx.model.prep;
  if (!p) return;
  const line = el.createDiv({ cls: "uc-prep-presence" });
  const n = p.note;
  if (!n) {
    const warnMin = minutesOf(ctx.s.prepWarnAfter) ?? 19 * 60 + 30;
    const missing = p.alerts.length > 0 && (p.which === "today" || minuteOfDay(ctx.model.now) >= warnMin);
    if (missing) line.addClass("is-alert");
    setIcon(line.createSpan({ cls: "uc-prep-icon" }), missing ? "alert-triangle" : "hourglass");
    const runs = prepRunsText();
    line.createSpan({ text: `Prep for ${shortDay(p.target)}: not there yet${runs ? ` · ${runs}` : ""}` });
    return;
  }
  const gaps = gapCount(n);
  setIcon(line.createSpan({ cls: "uc-prep-icon" }), gaps ? "circle-dot" : "check");
  const when = n.generated ? (dayKey(n.generated) === ctx.model.today ? hm(n.generated) : `${shortDay(n.generated)} ${hm(n.generated)}`) : "?";
  line.createSpan({ text: `Prep for ${shortDay(p.target)}: ${gaps ? `ready, ${gaps} gap${gaps > 1 ? "s" : ""}` : "ready"} · ${when}` });
  if (n.run) setTooltip(line, `Run: ${n.run}`);
  line.appendText(" · ");
  noteLink(ctx.app, line, "open note", n.path, "", ctx.hover);
}

/**
 * The prep card. "focus": only blocks still ahead, the next one open and the rest folded (one click opens
 * them). "full": every block open.
 */
export function prepCard(ctx: Ctx, parent: HTMLElement, variant: "focus" | "full"): void {
  const p = ctx.model.prep;
  if (!p) return;
  const s = section(parent, p.which === "today" ? "Prep for today" : "Prep for tomorrow", { quiet: variant === "focus", cls: "uc-prep" });
  prepPresence(ctx, s.body);
  const n = p.note;
  if (!n) return;
  const now = ctx.model.now.getTime();
  const endOf = (b: PrepBlock) => {
    const [h, m] = b.end.split(":").map(Number);
    const [y, mo, d] = n.date.split("-").map(Number);
    return zdate(y, mo, d, h, m).getTime();
  };
  const blocks = n.blocks.filter((b) => p.which === "tomorrow" || endOf(b) > now);
  const done = n.blocks.length - blocks.length;
  if (!blocks.length) s.body.createDiv({ cls: "uc-muted uc-empty-line", text: done ? "All of today's prepped blocks are over." : "No study blocks that day." });
  blocks.forEach((b, i) => {
    const key = `${n.date}|${b.start}`;
    const open = variant === "full" ? ctx.state.prepOpen[key] !== false : ctx.state.prepOpen[key] ?? i === 0;
    const el = s.body.createDiv({ cls: `uc-prep-block${open ? " is-open" : ""}` });
    const head = el.createDiv({ cls: "uc-prep-head" });
    head.createSpan({ cls: "uc-prep-time", text: b.start });
    dot(head, b.course);
    inline(ctx.app, head.createSpan({ cls: "uc-prep-title" }), b.title, n.path, ctx.hover);
    head.createSpan({ cls: "uc-prep-count", text: open ? "" : `${b.items.length} item${b.items.length === 1 ? "" : "s"}` });
    head.addEventListener("click", (ev: MouseEvent) => {
      if ((ev.target as HTMLElement).closest("a")) return;
      ctx.state.prepOpen[key] = !open;
      ctx.rerender();
    });
    if (!open) return;
    const ul = el.createEl("ul", { cls: "uc-prep-items" });
    for (const item of b.items) inline(ctx.app, ul.createEl("li"), item, n.path, ctx.hover);
  });
  if (done && variant === "focus") s.body.createDiv({ cls: "uc-muted uc-small uc-prep-done", text: `${done} earlier block${done > 1 ? "s" : ""} today` });
  if (n.gaps.length) {
    const g = s.body.createDiv({ cls: "uc-prep-gaps" });
    setIcon(g.createSpan({ cls: "uc-prep-icon" }), "circle-dot");
    const list = g.createDiv();
    for (const gap of n.gaps) inline(ctx.app, list.createDiv(), gap, n.path, ctx.hover);
  }
}

/** The prep items for one calendar event (agenda): the block with the same day and start time. */
export function prepFor(ctx: Ctx, e: CalEvent): { note: PrepNote; block: PrepBlock } | null {
  const n = ctx.model.prep?.byDate[dayKey(e.start)];
  const block = n?.blocks.find((b) => b.start === hm(e.start));
  return n && block ? { note: n, block } : null;
}

// ---------- the rest ----------

export function upcomingList(ctx: Ctx, parent: HTMLElement): boolean {
  const sunday = addDays(mondayOf(ctx.model.today), 6);
  const later = ctx.model.upcoming.filter((u) => u.key && u.key > sunday);
  if (!later.length) return false;
  for (const u of later) {
    const r = parent.createDiv({ cls: "uc-row" });
    dot(r, u.course);
    r.createDiv({ cls: "uc-row-when", text: plain(u.when) });
    inline(ctx.app, r.createDiv({ cls: "uc-row-what" }), u.what, ctx.model.statusPath ?? "", ctx.hover);
  }
  return true;
}

export function loadBars(ctx: Ctx, parent: HTMLElement): void {
  const hours = studyHours(ctx.model, weekKeys(ctx.model.today));
  const list = courses();
  const max = Math.max(1, ...list.map((c) => hours[c.id] ?? 0));
  if (!list.length) parent.createDiv({ cls: "uc-muted uc-empty-line", text: "No courses in the config." });
  for (const c of list) {
    const r = parent.createDiv({ cls: "uc-load" });
    courseVars(r, c.id);
    r.createDiv({ cls: "uc-load-name", text: c.short });
    const bar = r.createDiv({ cls: "uc-load-bar" });
    bar.createDiv({ cls: "uc-load-fill" }).style.width = `${((hours[c.id] ?? 0) / max) * 100}%`;
    r.createDiv({ cls: "uc-load-h", text: `${(hours[c.id] ?? 0).toFixed(1)} h` });
  }
}

export function recentList(ctx: Ctx, parent: HTMLElement, limit = 6): void {
  for (const n of ctx.model.recent.slice(0, limit)) {
    const r = parent.createDiv({ cls: "uc-recent" });
    noteLink(ctx.app, r, n.title, n.path, "", ctx.hover);
    r.createSpan({ cls: "uc-muted uc-small", text: relative(ctx.model.now, new Date(n.mtime)) });
  }
}
