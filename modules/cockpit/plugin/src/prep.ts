// Daily study prep notes (semester/prep/prep-YYYY-MM-DD[-rN].md, written by the daily-prep jobs): which one to
// show, and its blocks and links. Pure, so it runs in tests.
//
// Format (the daily-prep module's contract):
//   ---
//   type: prep
//   date: YYYY-MM-DD            the day being prepared
//   generated: YYYY-MM-DDTHH:MM+01:00
//   run: 17:30                  which run wrote it (or "manual")
//   status: ready | ready-with-gaps
//   ---
//   # Prep for <Ddd D Mon YYYY> (week N)
//   > [!<course slug>] HH:MM-HH:MM <block title as in the calendar>   (the id or short name work too)
//   > - <item>
//   ## Gaps
//   - none
// Per date the highest -rN wins, then the latest `generated`. Old notes are never deleted.

import { firstNumberPair, frontmatter, section, stripFrontmatter } from "./md";
import { addDays, clockOf, minuteOfDay, minutesOf } from "./model";
import { calloutCourse, registry } from "./registry";

export { frontmatter };

/** When the prep jobs run (schedule.daily_prep and schedule.prep_check), for the texts and the morning warning. */
export function prepRuns(): { prep: string; changeCheck: string; morningCheck: string } {
  const s = registry().schedule;
  return { prep: s.prepRuns[0] ?? "", changeCheck: s.prepRuns[1] ?? "", morningCheck: s.prepCheck };
}

/** Today's missing note is only an alarm from here on: the morning check plus 15 min to write and sync. */
export function morningWarnMinute(): number | null {
  const m = minutesOf(prepRuns().morningCheck);
  return m === null ? null : m + 15;
}

export function morningWarnText(): string {
  const m = morningWarnMinute();
  return m === null ? "" : clockOf(m);
}

/** "runs 17:30, change check 19:30, morning check 07:30" (parts without a time are left out; "" if none). */
export function prepRunsText(): string {
  const r = prepRuns();
  return [r.prep && `runs ${r.prep}`, r.changeCheck && `change check ${r.changeCheck}`, r.morningCheck && `morning check ${r.morningCheck}`].filter(Boolean).join(", ");
}

export interface PrepBlock {
  /** "12:10" */
  start: string;
  end: string;
  title: string;
  course: string | null;
  /** One Markdown line per item (without the leading "- "). */
  items: string[];
}

export interface PrepNote {
  path: string;
  date: string;
  generated: Date | null;
  run: string;
  status: string;
  revision: number;
  blocks: PrepBlock[];
  gaps: string[];
}

export interface PrepState {
  /** The day the card is about. */
  target: string;
  which: "today" | "tomorrow";
  note: PrepNote | null;
  /** Newest notes for today and tomorrow, by date (for the agenda). */
  byDate: Record<string, PrepNote>;
  /** Alerts (missing notes) for the warnings line. */
  alerts: string[];
}

export function parsePrep(path: string, text: string): PrepNote | null {
  const fm = frontmatter(text);
  const nameDate = /prep-(\d{4}-\d{2}-\d{2})(?:-r(\d+))?\.md$/.exec(path);
  const date = fm.date || nameDate?.[1];
  if (!date || (fm.type && fm.type !== "prep")) return null;
  const body = stripFrontmatter(text);
  const blocks: PrepBlock[] = [];
  let cur: PrepBlock | null = null;
  for (const line of body.split(/\r?\n/)) {
    const head = /^>\s*\[!([\w-]+)\][-+]?\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s*(.*)$/.exec(line);
    if (head) {
      cur = { start: head[2].padStart(5, "0"), end: head[3].padStart(5, "0"), title: head[4].trim(), course: calloutCourse(head[1]), items: [] };
      blocks.push(cur);
      continue;
    }
    if (cur && /^>/.test(line)) {
      const item = /^>\s*[-*]\s+(.*)$/.exec(line);
      if (item) cur.items.push(item[1].trim());
      else if (line.replace(/^>\s*/, "").trim() && cur.items.length) cur.items[cur.items.length - 1] += " " + line.replace(/^>\s*/, "").trim();
      continue;
    }
    cur = null;
  }
  const gapsBlock = section(body, "Gaps");
  // "- none" (or "None.", "no gaps", "-") means the routine found nothing missing.
  const gaps = gapsBlock
    ? gapsBlock
        .split(/\r?\n/)
        .map((l) => /^\s*[-*]\s+(.*)$/.exec(l)?.[1]?.trim())
        .filter((x): x is string => !!x && !/^(none|no gaps?|nothing|[-–—])\.?$/i.test(x))
    : [];
  const generated = fm.generated ? new Date(fm.generated.replace(/T(\d{2}:\d{2})([+-])/, "T$1:00$2")) : null;
  return {
    path,
    date,
    generated: generated && !isNaN(generated.getTime()) ? generated : null,
    run: fm.run ?? "",
    status: fm.status ?? "",
    revision: nameDate?.[2] ? +nameDate[2] : 1,
    blocks,
    gaps,
  };
}

/** Newest note per date: highest revision, then latest `generated`. */
export function newestByDate(notes: PrepNote[]): Map<string, PrepNote> {
  const out = new Map<string, PrepNote>();
  for (const n of notes) {
    const prev = out.get(n.date);
    const newer = !prev || n.revision > prev.revision || (n.revision === prev.revision && (n.generated?.getTime() ?? 0) > (prev.generated?.getTime() ?? 0));
    if (newer) out.set(n.date, n);
  }
  return out;
}

/**
 * Which prep the card shows: today's until `switchHour`, tomorrow's after. Alerts when tomorrow's is still
 * missing after `warnAfterMin` (minutes after midnight), or when today's is missing although the routine was
 * already running before today.
 */
export function prepState(notes: PrepNote[], today: string, now: Date, switchHour: number, warnAfterMin: number): PrepState {
  const byDate = newestByDate(notes);
  const minute = minuteOfDay(now);
  const tomorrow = addDays(today, 1);
  const which = minute >= switchHour * 60 ? "tomorrow" : "today";
  const target = which === "today" ? today : tomorrow;
  const alerts: string[] = [];
  const startedBefore = notes.some((n) => n.date < today);
  const morning = prepRuns().morningCheck;
  const warnAt = morningWarnMinute();
  if (!byDate.has(today) && startedBefore) {
    if (!morning) alerts.push("No study prep for today.");
    else
      alerts.push(
        warnAt !== null && minute < warnAt
          ? `No study prep for today yet: the ${morning} morning check will try again.`
          : `No study prep for today: the ${morning} morning check didn't produce one either.`,
      );
  }
  if (!byDate.has(tomorrow) && minute >= warnAfterMin) {
    const runs = prepRunsText();
    alerts.push(`Tomorrow's study prep is still missing (${runs ? `it ${runs}` : "check the daily-prep job"}).`);
  }
  const near: Record<string, PrepNote> = {};
  for (const d of [today, tomorrow]) if (byDate.has(d)) near[d] = byDate.get(d)!;
  return { target, which, note: byDate.get(target) ?? null, byDate: near, alerts };
}

/** Number of gaps, from the list or (for older notes) the status. */
export function gapCount(n: PrepNote): number {
  if (n.gaps.length) return n.gaps.length;
  const m = firstNumberPair(n.status);
  return m ? m.a : /gap/i.test(n.status) ? 1 : 0;
}
