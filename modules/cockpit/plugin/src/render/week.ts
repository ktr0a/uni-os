// Week grid: read-only view of the calendar, plus the rest of the current week page (results, notes, check-in).

import { MarkdownRenderer } from "obsidian";
import { addDays, dayKey, hm, minuteOfDay, mondayOf, shortDay } from "../model";
import { sideBySide, weekKeys } from "../parse";
import { registry } from "../registry";
import { courseVars, iconButton, noteLink } from "../ui";
import { Ctx, eventTitle, isSelected } from "./ctx";
import { eventDetail, visibleEvents } from "./sections";

export function renderWeek(ctx: Ctx, main: HTMLElement): void {
  main.addClass("uc-layout-week");
  const monday = addDays(mondayOf(ctx.model.today), ctx.state.weekOffset * 7);
  const keys = weekKeys(monday).slice(0, ctx.s.showWeekend ? 7 : 5);

  const bar = main.createDiv({ cls: "uc-weekbar" });
  iconButton(bar, "chevron-left", "Previous week", () => ((ctx.state.weekOffset -= 1), ctx.rerender()), "uc-quiet uc-icon-only");
  bar.createSpan({ cls: "uc-weekbar-label", text: `Week ${ctx.model.week + ctx.state.weekOffset}` });
  bar.createSpan({ cls: "uc-muted", text: `${shortDay(keys[0])} – ${shortDay(keys[keys.length - 1])}` });
  iconButton(bar, "chevron-right", "Next week", () => ((ctx.state.weekOffset += 1), ctx.rerender()), "uc-quiet uc-icon-only");
  if (ctx.state.weekOffset !== 0) iconButton(bar, "undo-2", "This week", () => ((ctx.state.weekOffset = 0), ctx.rerender()), "uc-quiet");

  const all = keys.flatMap((k) => visibleEvents(ctx, k));
  let from = ctx.s.dayStart * 60;
  let to = ctx.s.dayEnd * 60;
  if (ctx.s.fitDay && all.length) {
    from = Math.min(from, ...all.map((e) => Math.floor(minuteOfDay(e.start) / 60) * 60));
    to = Math.max(to, ...all.map((e) => Math.ceil((minuteOfDay(e.end) || 24 * 60) / 60) * 60));
  }
  const pxPerMin = ctx.s.hourHeight / 60;

  const grid = main.createDiv({ cls: "uc-wgrid" });
  grid.style.gridTemplateColumns = `44px repeat(${keys.length}, minmax(0, 1fr))`;
  const hoursCol = grid.createDiv({ cls: "uc-wcol uc-whours" });
  hoursCol.createDiv({ cls: "uc-wday-head" });
  const hoursBody = hoursCol.createDiv({ cls: "uc-wbody" });
  hoursBody.style.height = `${(to - from) * pxPerMin}px`;
  for (let m = from; m < to; m += 60) hoursBody.createDiv({ cls: "uc-whour", text: `${String(m / 60).padStart(2, "0")}` }).style.top = `${(m - from) * pxPerMin}px`;

  for (const key of keys) {
    const col = grid.createDiv({ cls: `uc-wcol${key === ctx.model.today ? " is-today" : ""}${key < ctx.model.today ? " is-past" : ""}` });
    const head = col.createDiv({ cls: "uc-wday-head" });
    head.createSpan({ cls: "uc-wday-name", text: shortDay(key).split(" ")[0] });
    head.createSpan({ cls: "uc-wday-date", text: shortDay(key).split(" ")[1] });
    const body = col.createDiv({ cls: "uc-wbody" });
    body.style.height = `${(to - from) * pxPerMin}px`;
    for (let m = from; m < to; m += 60) body.createDiv({ cls: "uc-wline" }).style.top = `${(m - from) * pxPerMin}px`;

    const evs = visibleEvents(ctx, key).map((e) => ({ e, s: Math.max(from, minuteOfDay(e.start)), en: Math.min(to, minuteOfDay(e.end) || 24 * 60) }));
    for (const { e, s, en, lane, lanes } of sideBySide(evs)) {
      if (en <= from || s >= to) continue;
      const b = body.createDiv({ cls: `uc-ev uc-wev uc-ev-${e.kind}${e.optional ? " is-optional" : ""}${isSelected(ctx, e) ? " is-selected" : ""}` });
      courseVars(b, e.course);
      b.style.top = `${(s - from) * pxPerMin}px`;
      b.style.height = `${Math.max(14, (en - s) * pxPerMin - 2)}px`;
      b.style.left = `${(lane / lanes) * 100}%`;
      b.style.width = `calc(${100 / lanes}% - 2px)`;
      b.createDiv({ cls: "uc-ev-title", text: eventTitle(ctx, e) });
      if ((en - s) * pxPerMin > 30) b.createDiv({ cls: "uc-ev-meta", text: `${hm(e.start)}–${hm(e.end)}` });
      b.setAttr("aria-label", `${hm(e.start)}–${hm(e.end)} ${eventTitle(ctx, e)}${e.location ? " · " + e.location : ""}`);
      b.addEventListener("click", () => {
        ctx.state.selected = isSelected(ctx, e) ? null : e;
        ctx.rerender();
      });
    }
    if (key === ctx.model.today) {
      const nm = minuteOfDay(ctx.model.now);
      if (nm > from && nm < to) body.createDiv({ cls: "uc-wnow" }).style.top = `${(nm - from) * pxPerMin}px`;
    }
  }
  if (ctx.state.selected && keys.includes(dayKey(ctx.state.selected.start))) eventDetail(ctx, main, ctx.state.selected);

  const range = ctx.model.calendarRange;
  if (range && (keys[keys.length - 1] < range.start || keys[0] > range.end)) {
    main.createDiv({ cls: "uc-note", text: `The calendar data covers ${shortDay(range.start)} to ${shortDay(range.end)} only.` });
  }

  // The rest of this week's page, folded: what the agents wrote under the other fixed headings.
  if (ctx.state.weekOffset === 0 && ctx.model.weekPath) {
    const h = registry().headings;
    const parts: Array<[string, string | null]> = [
      [h.results, ctx.model.weekParts.results],
      [h.notes, ctx.model.weekParts.notes],
      [h.checkIn, ctx.model.weekParts.checkIn],
    ];
    const wrap = main.createDiv({ cls: "uc-weekpage" });
    const title = wrap.createDiv({ cls: "uc-weekpage-title" });
    noteLink(ctx.app, title, `Week page ${ctx.model.week}`, ctx.model.weekPath, "", ctx.hover);
    if (ctx.model.weekPlanPath) {
      title.appendText(" · ");
      noteLink(ctx.app, title, "plan", ctx.model.weekPlanPath, "", ctx.hover);
    }
    for (const [heading, md] of parts) {
      if (!md) continue;
      const det = wrap.createEl("details", { cls: "uc-course-more" });
      det.createEl("summary", { text: heading });
      const box = det.createDiv({ cls: "uc-md" });
      void MarkdownRenderer.render(ctx.app, md, box, ctx.model.weekPath, ctx.scope);
    }
  }
}
