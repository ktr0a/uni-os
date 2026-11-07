// Courses & bonus: one compact tile per course, then the detail panels. Every course comes from the registry.

import { MarkdownRenderer } from "obsidian";
import { bonusFigure } from "../bonus";
import { num, plain } from "../md";
import { relative } from "../model";
import { CourseInfo, courses, moduleEnabled } from "../registry";
import { courseVars, dot, meter, noteLink } from "../ui";
import { Ctx } from "./ctx";

export function renderCourses(ctx: Ctx, main: HTMLElement): void {
  main.addClass("uc-layout-courses");
  const list = courses();
  if (!list.length) {
    main.createDiv({ cls: "uc-muted uc-empty-line", text: "No courses yet: add them to _agent/uni-os.toml and run `python tools/uni_os.py render`." });
    return;
  }
  const strip = main.createDiv({ cls: "uc-tiles" });
  for (const c of list) {
    const b = ctx.model.bonus[c.id];
    const t = strip.createDiv({ cls: `uc-tile is-${b?.tone ?? "unknown"}` });
    courseVars(t, c.id);
    const name = t.createDiv({ cls: "uc-tile-name" });
    dot(name, c.id);
    name.appendText(c.short);
    const big = t.createDiv({ cls: "uc-tile-big" });
    big.createSpan({ text: b?.big ?? "—" });
    if (b?.of) big.createSpan({ cls: "uc-tile-of", text: ` ${b.of}` });
    if (b?.meter) meter(t, b.meter);
    else t.createDiv({ cls: "uc-meter is-empty" });
    const max = `${num(c.bonus.maxBonus)}${c.bonus.maxIsPercent ? " %" : ""}`;
    const foot = c.bonus.scheme === "none" ? "no bonus scheme" : b?.bonusNow === null || !b ? plain(b?.banked ?? "") || "not computable yet" : `${bonusFigure(b.bonusNow, c.bonus)} of ${max} banked`;
    t.createDiv({ cls: "uc-tile-foot", text: foot });
    t.addEventListener("click", () => main.querySelector(`[data-course="${c.id}"]`)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }
  const grid = main.createDiv({ cls: "uc-course-grid" });
  for (const c of list) coursePanel(ctx, grid, c);
}

function coursePanel(ctx: Ctx, parent: HTMLElement, course: CourseInfo): void {
  const id = course.id;
  const b = ctx.model.bonus[id];
  const p = parent.createDiv({ cls: "uc-course", attr: { "data-course": id } });
  courseVars(p, id);
  const head = p.createDiv({ cls: "uc-course-head" });
  dot(head, id);
  head.createSpan({ cls: "uc-course-short", text: course.short });
  head.createSpan({ cls: "uc-course-name", text: course.name });
  const rating = ctx.model.selfRating[id];
  if (rating) head.createSpan({ cls: "uc-pill", text: `self-rated ${rating}` });

  if (b) {
    p.createDiv({ cls: "uc-course-headline", text: b.headline });
    if (b.detail) p.createDiv({ cls: "uc-muted uc-small", text: b.detail });
    if (course.bonus.scheme !== "none") {
      const facts = p.createDiv({ cls: "uc-facts" });
      const fact = (k: string, v: string) => {
        const r = facts.createDiv({ cls: "uc-fact" });
        r.createDiv({ cls: "uc-fact-k", text: k });
        r.createDiv({ cls: "uc-fact-v", text: v });
      };
      fact("Banked", plain(b.banked) || "?");
      fact("Full bonus at", plain(b.target) || "?");
      fact("Next", plain(b.next) || "?");
      fact("Rule", b.rule);
    }
  }

  const ex = ctx.model.exercises[id];
  if (ex && ctx.model.statusPath) {
    const det = p.createEl("details", { cls: "uc-course-more" });
    det.createEl("summary", { text: "Done vs. to do" });
    const md = det.createDiv({ cls: "uc-md" });
    void MarkdownRenderer.render(ctx.app, ex, md, ctx.model.statusPath, ctx.scope);
    md.addEventListener("click", (ev) => {
      const a = (ev.target as HTMLElement).closest("a.internal-link") as HTMLAnchorElement | null;
      if (!a) return;
      ev.preventDefault();
      void ctx.app.workspace.openLinkText(a.dataset.href ?? a.getAttr("href") ?? "", ctx.model.statusPath ?? "", ev.ctrlKey || ev.metaKey);
    });
  }

  const notes = p.createEl("details", { cls: "uc-course-more" });
  notes.createEl("summary", { text: "Notes and study pages" });
  const l = notes.createDiv({ cls: "uc-linklist" });
  if (ctx.model.coursePaths[id]) noteLink(ctx.app, l, "Course card", ctx.model.coursePaths[id], "", ctx.hover);
  // Error logs are the error-logs module's notes: no links to them while it is off.
  if (moduleEnabled("error-logs")) for (const log of course.errorLogs) noteLink(ctx.app, l, log.label, log.path, "", ctx.hover);
  for (const n of ctx.model.studyPages[id] ?? []) {
    const r = notes.createDiv({ cls: "uc-recent" });
    noteLink(ctx.app, r, n.title, n.path, "", ctx.hover);
    r.createSpan({ cls: "uc-muted uc-small", text: relative(ctx.model.now, new Date(n.mtime)) });
  }
}
