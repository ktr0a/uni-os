// The three home layouts. Same data, different amounts of it:
//   Focus     one screen, only what matters now (inverted pyramid: now > due next > bonus)
//   Dashboard every section you switch on, in the order you choose
//   Agenda    today and the next days as one list, deadlines slotted in between

import { setIcon } from "obsidian";
import { addDays, dayKey, hm, minuteOfDay, minutesOf, mondayOf, shortDay } from "../model";
import { CalEvent, DueItem, Upcoming, plain } from "../parse";
import { registry } from "../registry";
import type { SectionId } from "../settings";
import { SECTION_INFO } from "../settings";
import { courseVars, dot, inline, section } from "../ui";
import { Ctx, eventTitle, isSelected, isUrgent } from "./ctx";
import { bonusList, dueList, eventDetail, headline, loadBars, longDate, nextList, prepCard, prepFor, prepPresence, recentList, timeline, upcomingList, visibleEvents } from "./sections";

export function renderFocus(ctx: Ctx, main: HTMLElement): void {
  main.addClass("uc-layout-focus");
  main.createDiv({ cls: "uc-date", text: longDate(ctx) });
  headline(ctx, main);
  if (ctx.s.focusStrip) timeline(ctx, main, ctx.model.today, "strip");
  if (ctx.s.focusPrep) prepCard(ctx, main, "focus");
  const due = section(main, "Due next", { quiet: true });
  dueList(ctx, due.body, { limit: ctx.s.focusDueCount, compact: true, skipUrgent: true });
  if (ctx.s.focusBonus) {
    const b = section(main, "Bonus", { quiet: true, aside: "bar = banked · tick = full bonus" });
    bonusList(ctx, b.body, true);
    if (!b.body.querySelector(".uc-bonus")) b.el.remove();
  }
}

const DASH: Record<SectionId, (ctx: Ctx, parent: HTMLElement) => void> = {
  headline: (ctx, p) => headline(ctx, p),
  timeline: (ctx, p) => timeline(ctx, p, ctx.model.today, "full"),
  prep: (ctx, p) => prepCard(ctx, p, "full"),
  due: (ctx, p) => {
    const s = section(p, "Due this week", { aside: ctx.model.targetLabel ? `deadline · ${ctx.model.targetLabel.toLowerCase()}` : "deadline" });
    dueList(ctx, s.body);
  },
  next: (ctx, p) => nextList(ctx, section(p, "Next up").body),
  bonus: (ctx, p) => {
    const s = section(p, "Bonus", { aside: "bar = banked · tick = full bonus" });
    bonusList(ctx, s.body, false);
    if (!s.body.querySelector(".uc-bonus")) s.el.remove();
  },
  upcoming: (ctx, p) => {
    const s = section(p, "After this week");
    if (!upcomingList(ctx, s.body)) s.el.remove();
  },
  load: (ctx, p) => loadBars(ctx, section(p, "This week's load", { aside: "planned study hours" }).body),
  recent: (ctx, p) => recentList(ctx, section(p, "Recently changed").body),
};

export function renderDashboard(ctx: Ctx, main: HTMLElement): void {
  main.addClass("uc-layout-dashboard");
  main.createDiv({ cls: "uc-date", text: longDate(ctx) });
  // Wide sections span the page; runs of the others flow into balanced columns, in the chosen order.
  let flow: HTMLElement | null = null;
  for (const { id, on } of ctx.s.sections) {
    if (!on) continue;
    if (SECTION_INFO[id].wide) {
      flow = null;
      DASH[id](ctx, main);
    } else {
      flow ??= main.createDiv({ cls: "uc-flow" });
      DASH[id](ctx, flow);
    }
  }
}

type AgendaItem = { kind: "event"; at: number; e: CalEvent } | { kind: "due"; at: number; d: DueItem } | { kind: "upcoming"; at: number; u: Upcoming };

function agendaItems(ctx: Ctx, key: string): AgendaItem[] {
  const items: AgendaItem[] = visibleEvents(ctx, key, true).map((e) => ({ kind: "event", at: e.start.getTime() - (e.allDay ? 1 : 0), e }));
  for (const d of ctx.model.due) {
    if (d.deadline && dayKey(d.deadline) === key && d.state !== "done") items.push({ kind: "due", at: d.deadline.getTime() + (d.dateOnly ? 1 : 0), d });
  }
  const sunday = addDays(mondayOf(ctx.model.today), 6);
  if (key > sunday) for (const u of ctx.model.upcoming) if (u.key === key && u.date) items.push({ kind: "upcoming", at: u.date.getTime(), u });
  return items.sort((a, b) => a.at - b.at);
}

export function renderAgenda(ctx: Ctx, main: HTMLElement): void {
  main.addClass("uc-layout-agenda");
  main.createDiv({ cls: "uc-date", text: longDate(ctx) });
  const now = ctx.model.now.getTime();
  const cutoff = registry().schedule.studyCutoff;
  const cutoffMin = cutoff ? minutesOf(cutoff) : null;
  for (let i = 0; i < ctx.s.agendaDays; i++) {
    const key = addDays(ctx.model.today, i);
    const items = agendaItems(ctx, key);
    const day = main.createDiv({ cls: "uc-day" });
    const head = day.createDiv({ cls: "uc-day-head" });
    head.createSpan({ cls: "uc-day-name", text: i === 0 ? "Today" : i === 1 ? "Tomorrow" : shortDay(key).split(" ")[0] });
    head.createSpan({ cls: "uc-day-date", text: shortDay(key).split(" ").slice(1).join(" ") });
    const classes = items.filter((x) => x.kind === "event" && (x.e.kind === "lecture" || x.e.kind === "exercise")).length;
    const studyMin = items.reduce((acc, x) => acc + (x.kind === "event" && x.e.kind === "study" && !x.e.optional ? (x.e.end.getTime() - x.e.start.getTime()) / 60000 : 0), 0);
    const due = items.filter((x) => x.kind !== "event").length;
    head.createSpan({
      cls: "uc-day-sum",
      text: [classes && `${classes} class${classes > 1 ? "es" : ""}`, studyMin && `${(studyMin / 60).toFixed(1)} h study`, due && `${due} due`].filter(Boolean).join(" · "),
    });
    if (ctx.model.prep?.target === key) prepPresence(ctx, day);
    if (!items.length) {
      day.createDiv({ cls: "uc-muted uc-empty-line", text: "Nothing planned." });
      continue;
    }
    const isPast = (x: AgendaItem) => (x.kind === "event" ? x.e.end.getTime() <= now : x.at < now);
    const pastCount = i === 0 ? items.filter(isPast).length : 0;
    // What's over today folds into one line, unless the reader opened it.
    if (pastCount && ctx.s.agendaFoldPast) {
      const fold = day.createDiv({ cls: "uc-more uc-agenda-fold", text: ctx.state.pastOpen ? "Hide what's over" : `${pastCount} earlier today` });
      fold.addEventListener("click", () => {
        ctx.state.pastOpen = !ctx.state.pastOpen;
        ctx.rerender();
      });
    }
    for (const it of items) {
      const past = isPast(it);
      if (past && i === 0 && ctx.s.agendaFoldPast && !ctx.state.pastOpen) continue;
      const row = day.createDiv({ cls: `uc-agenda-row${past ? " is-past" : ""}` });
      if (it.kind === "event") {
        const e = it.e;
        const current = e.start.getTime() <= now && now < e.end.getTime();
        if (current) row.addClass("is-now");
        if (isSelected(ctx, e)) row.addClass("is-selected");
        row.addClass(`is-${e.kind}`);
        row.createDiv({ cls: "uc-agenda-time", text: e.allDay ? "all day" : hm(e.start) });
        dot(row, e.course, e.kind === "study" ? "is-hollow" : "");
        const body = row.createDiv({ cls: "uc-agenda-body" });
        body.createDiv({ cls: "uc-agenda-title", text: eventTitle(ctx, e) });
        const meta = [e.allDay ? "" : `until ${hm(e.end)}`, e.location].filter(Boolean).join(" · ");
        body.createDiv({ cls: "uc-agenda-meta", text: meta });
        if (current && e.focus && ctx.s.agendaFocusLines > 0) {
          body.createEl("pre", { cls: "uc-agenda-focus", text: e.focus.split("\n").slice(0, ctx.s.agendaFocusLines).join("\n") });
        }
        // The material the daily prep listed for this block.
        const prep = !past ? prepFor(ctx, e) : null;
        if (prep && prep.block.items.length) {
          const ul = body.createEl("ul", { cls: "uc-prep-items is-compact" });
          for (const item of prep.block.items) inline(ctx.app, ul.createEl("li"), item, prep.note.path, ctx.hover);
        }
        row.addEventListener("click", () => {
          ctx.state.selected = isSelected(ctx, e) ? null : e;
          ctx.rerender();
        });
        if (isSelected(ctx, e) && !current) eventDetail(ctx, day, e);
      } else if (it.kind === "due") {
        const d = it.d;
        row.addClass("is-deadline");
        if (isUrgent(ctx, d)) row.addClass("is-urgent");
        row.createDiv({ cls: "uc-agenda-time", text: d.dateOnly ? "" : hm(d.deadline!) });
        const mark = row.createSpan({ cls: "uc-deadline-mark" });
        courseVars(mark, d.course);
        setIcon(mark, "flag");
        const body = row.createDiv({ cls: "uc-agenda-body" });
        inline(ctx.app, body.createDiv({ cls: "uc-agenda-title" }), `Due: ${d.item}`, ctx.model.weekPath ?? "", ctx.hover);
        body.createDiv({
          cls: "uc-agenda-meta",
          text: [plain(d.status), ctx.s.showTarget && plain(d.target) && !d.targetPast ? `${ctx.model.targetLabel || "target"} ${plain(d.target)}` : ""].filter(Boolean).join(" · "),
        });
      } else {
        const u = it.u;
        row.addClass("is-deadline");
        row.createDiv({ cls: "uc-agenda-time", text: u.date && plain(u.when).match(/\d{1,2}:\d{2}/) ? hm(u.date) : "" });
        const mark = row.createSpan({ cls: "uc-deadline-mark" });
        courseVars(mark, u.course);
        setIcon(mark, "flag");
        inline(ctx.app, row.createDiv({ cls: "uc-agenda-body uc-agenda-title" }), u.what, ctx.model.statusPath ?? "", ctx.hover);
      }
    }
    if (i === 0 && items.every((x) => (x.kind === "event" ? x.e.end.getTime() <= now : x.at < now))) {
      const late = cutoffMin !== null && minuteOfDay(ctx.model.now) >= cutoffMin;
      day.createDiv({ cls: "uc-agenda-done", text: late ? `Done for today. No study after ${cutoff}.` : "Nothing left today." });
    }
  }
}
