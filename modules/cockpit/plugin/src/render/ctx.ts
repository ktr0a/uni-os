import type { App, Component } from "obsidian";
import type { CalEvent, CockpitModel, DueItem } from "../parse";
import type { CockpitSettings, Tab } from "../settings";
import { addDays, dayKey, daysBetween, hm, relative, shortDay } from "../model";

/** Per-view state that survives re-renders (every minute and on every note change). */
export interface ViewState {
  selected: CalEvent | null;
  weekOffset: number;
  doneOpen: boolean;
  dueExpanded: boolean;
  pastOpen: boolean;
  /** Prep blocks the reader opened or closed, by "date|start". */
  prepOpen: Record<string, boolean>;
}

/** Everything a renderer needs. */
export interface Ctx {
  app: App;
  model: CockpitModel;
  s: CockpitSettings;
  /** Hover-preview parent for links. */
  hover: Component;
  /** Owner of rendered Markdown; unloaded on every re-render. */
  scope: Component;
  state: ViewState;
  rerender(): void;
  go(tab: Tab): void;
  /** The Done button: moves the row to the done list now and files the update note after an undo window. */
  markDone(d: DueItem): void;
  /** The Undo on a tapped row: reopens it now and files an undo note if the Done note was already written. */
  markUndone(d: DueItem): void;
}

/** Busy-only (personal) calendar entries read "Busy" unless their titles are switched on. */
export function eventTitle(ctx: Ctx, e: CalEvent): string {
  if (e.kind !== "personal") return e.title;
  return ctx.s.personalTitles && e.title && e.title !== "Personal" ? e.title : "Busy";
}

export function isSelected(ctx: Ctx, e: CalEvent): boolean {
  const s = ctx.state.selected;
  return !!s && s.start.getTime() === e.start.getTime() && s.title === e.title;
}

/** "today 23:59", "tomorrow 08:20", "Thu 5 Nov 16:15" */
export function whenLabel(ctx: Ctx, d: Date, dateOnly = false): string {
  const k = dayKey(d);
  const day = k === ctx.model.today ? "today" : k === addDays(ctx.model.today, 1) ? "tomorrow" : shortDay(d);
  return dateOnly ? day : `${day} ${hm(d)}`;
}

/** Countdown text in the style chosen in the settings. Date-only deadlines ("tutorial Tue 3 Nov") get no clock time. */
export function countdown(ctx: Ctx, d: Date, dateOnly = false): string {
  const rel = dateOnly ? relativeDays(ctx, d) : relative(ctx.model.now, d);
  if (ctx.s.countdown === "relative") return rel;
  if (ctx.s.countdown === "absolute") return whenLabel(ctx, d, dateOnly);
  return `${whenLabel(ctx, d, dateOnly)} · ${rel}`;
}

function relativeDays(ctx: Ctx, d: Date): string {
  const n = daysBetween(ctx.model.today, dayKey(d));
  return n === 0 ? "today" : n > 0 ? `in ${n} d` : `${-n} d ago`;
}

/** Text for a deadline in the past: a missing result reads differently from missed work. */
export function pastLabel(d: DueItem): string {
  if (d.state === "open" && d.endsAt) return `running until ${hm(d.endsAt)}`;
  return d.state === "pending" ? "deadline passed · result not logged yet" : "past deadline";
}

export function isUrgent(ctx: Pick<Ctx, "model" | "s">, d: DueItem): boolean {
  // A tutorial or tentative slot is not a hand-in, so it never alarms.
  if (d.state === "done" || d.soft || !d.deadline) return false;
  const hours = (d.deadline.getTime() - ctx.model.now.getTime()) / 3600000;
  return d.state === "overdue" || hours <= ctx.s.urgentHours;
}

const ORDER = { overdue: 0, pending: 1, open: 2, done: 3 } as const;

/** Open work first, soonest deadline first; done last. */
export function sortedDue(ctx: Pick<Ctx, "model">): DueItem[] {
  return [...ctx.model.due].sort((a, b) => ORDER[a.state] - ORDER[b.state] || (a.deadline?.getTime() ?? Infinity) - (b.deadline?.getTime() ?? Infinity));
}
