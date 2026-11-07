// A compact Markdown "context pack" of where things stand right now: pasted into any AI chat beside Obsidian
// (free), or used as the volatile part of the assistant panel's prompt. Pure.

import { appliedWhen, syncWhen } from "./done";
import { plain } from "./md";
import { addDays, dayKey, hm, shortDay, zparts } from "./model";
import { CockpitModel, DueItem, eventsOn } from "./parse";
import { courses, registry } from "./registry";

/** A due row as the cockpit shows it: "passed" and "tapped" instead of the status cell, which is old or only a mark by then. */
function dueLine(model: CockpitModel, d: DueItem): string {
  const target = plain(d.target) && !d.targetPast ? ` / ${model.targetLabel || "target"} ${plain(d.target)}` : "";
  const status = plain(d.status) || "open";
  let shown = status;
  if (d.lapsed) shown = "passed (no bonus, its date is over)";
  else if (d.tapped) shown = d.tapWaiting ? `tapped done (the week page updates ${syncWhen(model.now)})` : "tapped done";
  else if (d.state === "overdue") shown = `past deadline, ${status}`;
  else if (d.state === "pending" && d.deadline && d.deadline.getTime() < model.now.getTime()) shown = `deadline passed, result not logged yet (${status})`;
  return `- ${plain(d.item)}: ${plain(d.deadlineText)}${target} / ${shown}`;
}

export function scheduleLines(model: CockpitModel, key: string): string[] {
  return eventsOn(model, key)
    .filter((e) => e.kind !== "personal")
    .map((e) => `- ${hm(e.start)}-${hm(e.end)} ${e.title}${e.location ? ` (${e.location})` : ""}`);
}

export function contextPack(model: CockpitModel): string {
  const reg = registry();
  const lines: string[] = [];
  const p = (s = "") => lines.push(s);
  p(`# Study status, ${shortDay(model.now)} ${zparts(model.now).y} ${hm(model.now)} (term week ${model.week})`);
  p(`From my Obsidian vault (${model.statusPath ?? reg.paths.status}${model.statusSnapshot ? `, snapshot "${model.statusSnapshot}"` : ""}).`);
  p();
  p("## Today");
  const today = scheduleLines(model, model.today);
  lines.push(...(today.length ? today : ["- nothing in the calendar"]));
  const tomorrow = addDays(model.today, 1);
  p();
  p(`## Tomorrow (${shortDay(tomorrow)})`);
  const tm = scheduleLines(model, tomorrow);
  lines.push(...(tm.length ? tm : ["- nothing in the calendar"]));
  const withBonus = courses().filter((c) => c.bonus.scheme !== "none");
  if (withBonus.length) {
    p();
    p("## Bonus standing");
    for (const c of withBonus) {
      const b = model.bonus[c.id];
      if (!b) continue;
      p(`- ${c.short}: ${plain(b.banked) || "?"} (full at ${plain(b.target) || "?"}). ${b.headline}. Next: ${plain(b.next) || "?"}`);
    }
  }
  p();
  p(`## ${reg.headings.due} (official deadline${model.targetLabel ? ` / ${model.targetLabel} while it is ahead` : ""} / status as the cockpit shows it)`);
  for (const d of model.due) p(dueLine(model, d));
  if (!model.due.length) p("- no due table on the current week page");
  if (model.inboxWaiting) p(`(${model.inboxWaiting} update${model.inboxWaiting > 1 ? "s" : ""} waiting in the inbox, ${appliedWhen(model.now)}; the week page doesn't show them yet.)`);
  if (model.upcoming.length) {
    p();
    p(`## ${reg.headings.next}`);
    for (const u of model.upcoming) p(`- ${plain(u.when)}: ${plain(u.what)}`);
  }
  p();
  const cal = model.liveCals.length && model.liveAt ? `live feeds, fetched ${shortDay(new Date(model.liveAt))} ${hm(new Date(model.liveAt))}` : `the snapshot of ${model.snapshotGenerated ? dayKey(new Date(model.snapshotGenerated)) : "?"}`;
  p(`(Calendar from ${cal}; re-check the live calendar before moving blocks.)`);
  return lines.join("\n");
}
