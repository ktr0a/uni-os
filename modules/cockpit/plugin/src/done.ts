// The Done tap and its undo: one small update note each in the inbox, which the inbox sync (module inbox-sync)
// applies to the week page. Until then the notes themselves say the item's state, on every device. Pure.
//
// File name: <inbox>/<YYYY-MM-DD>_<HHMM>_cockpit-<done|undo>-<slug>-update.md. Keep the "_cockpit-(done|undo)-"
// part: the sync job's filter matches it, so a tap alone does not trigger a sync run and gets a longer grace
// period before a "stuck note" alert. The notes are rule-based (no quoted row), so a row edited since the tap
// can't park them.

import { plain } from "./md";
import { dayKey, hm, minuteOfDay, shortDay, tz, zparts } from "./model";
import { tapKey } from "./parse";
import { moduleEnabled, registry, studentName } from "./registry";

/** Who wrote the note: "cockpit" here; another UI (a phone page, a wrapper) may use its own source name. */
export type TapSource = "cockpit" | string;

const FROM: Record<string, string> = { cockpit: "Uni OS cockpit in Obsidian" };

/**
 * Whether the inbox-sync module is enabled (modules.enabled). Without it no job applies the notes: the Done button
 * still files them, and you or an agent apply them (each note says exactly what to change).
 */
export function syncOn(): boolean {
  return moduleEnabled("inbox-sync");
}

/** When the inbox sync runs (schedule.inbox_sync; none while the inbox-sync module is off). */
export function syncTimes(): string[] {
  return syncOn() ? registry().schedule.syncTimes : [];
}

/** "13:15", or "tomorrow 07:15" after the day's last run ("" when no sync times are configured). */
export function nextSync(now: Date): string {
  const times = syncTimes();
  if (!times.length) return "";
  const minute = minuteOfDay(now);
  for (const t of times) {
    const [h, m] = t.split(":").map(Number);
    if (h * 60 + m > minute) return t;
  }
  return `tomorrow ${times[0]}`;
}

/**
 * When a waiting note reaches the week page: "at 13:15", "tomorrow at 07:15", "at the next inbox sync" when no
 * times are configured, or who applies it while the inbox-sync module is off. Reads after "the week page updates".
 */
export function syncWhen(now: Date): string {
  if (!syncOn()) return "once you or your agent apply the inbox note, since the inbox-sync module is off";
  const next = nextSync(now);
  if (!next) return "at the next inbox sync";
  return next.startsWith("tomorrow ") ? `tomorrow at ${next.slice(9)}` : `at ${next}`;
}

/** "applied at 13:15" (after "N updates waiting in the inbox, "), or who applies them while inbox-sync is off. */
export function appliedWhen(now: Date): string {
  return syncOn() ? `applied ${syncWhen(now)}` : "for you or your agent to apply, since the inbox-sync module is off";
}

/** The week page's raw table row for an item, exactly as it stands. */
export function rowLine(weekText: string, item: string): string | null {
  const wanted = plain(item);
  for (const line of weekText.split(/\r?\n/)) {
    if (!/^\s*\|/.test(line)) continue;
    if (plain(line.replace(/^\s*\|/, "").split("|")[0]) === wanted) return line;
  }
  return null;
}

function slug(item: string): string {
  return plain(item)
    .toLowerCase()
    .replace(/&/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 32)
    .replace(/-+$/, "");
}

function noteTitle(now: Date, source: TapSource, kind: "done" | "undo", item: string): string {
  const p = zparts(now);
  return `${dayKey(now)}_${String(p.hh).padStart(2, "0")}${String(p.mm).padStart(2, "0")}_${source}-${kind}-${slug(item) || "item"}-update.md`;
}

function noteHead(now: Date, from: string, property: string, item: string): string[] {
  return [
    "---",
    "type: inbox-update",
    `from: ${from}`,
    `created: ${dayKey(now)} ${hm(now)} (${tz()})`,
    `tapped_at: ${now.toISOString()}`,
    `${property}: ${JSON.stringify(plain(item))}`,
    "---",
  ];
}

/** The status a Done tap leaves in a row: the mark first, what it said before behind it. */
export function tappedStatus(old: string, now: Date): string {
  const before = plain(old);
  return `done (${shortDay(now)} ${hm(now)}, tapped)${before ? `. Before: ${before}` : ""}`;
}

/** What the sync makes of a table row when it applies a Done note (Status is the last column). */
export function markedRow(row: string, now: Date): string {
  return row.replace(/\|([^|]*)\|\s*$/, (_m, old: string) => `| ${tappedStatus(old, now)} |`);
}

/** Rule-based, with no quoted row: a row edited since the tap must not park the note, because nobody would re-send it. */
export function doneNote(args: { weekPath: string; weekText: string; item: string; now: Date; source: TapSource }): { title: string; text: string } | null {
  const { weekPath, weekText, item, now, source } = args;
  const row = rowLine(weekText, item);
  if (!row) return null;
  const who = studentName();
  const stamp = `${shortDay(now)} ${hm(now)}`;
  const heading = registry().headings.due;
  const text = [
    ...noteHead(now, `${FROM[source] ?? source} (Done tap by ${who})`, "done_item", item),
    `# Done tap: ${plain(item)}`,
    "",
    `${who} tapped Done on this item on ${stamp}. Apply this before any later undo note for the same item.`,
    "",
    `## ${weekPath}`,
    `Section "${heading}", the row whose Item cell is \`${plain(item)}\`: change only its Status cell. Put \`done (${stamp}, tapped). Before: \` in front of what the cell says now (if it is empty, write just \`done (${stamp}, tapped)\`). If the Status cell already starts with \`done\`, change nothing. Change nothing else. The tap says the item is finished, not how it went, so add no score or result.`,
    "",
  ].join("\n");
  return { title: noteTitle(now, source, "done", item), text };
}

export function undoNote(args: { weekPath: string; item: string; now: Date; source: TapSource }): { title: string; text: string } {
  const { weekPath, item, now, source } = args;
  const who = studentName();
  const heading = registry().headings.due;
  const text = [
    ...noteHead(now, `${FROM[source] ?? source} (undo of a Done tap by ${who})`, "undo_item", item),
    `# Undo of a Done tap: ${plain(item)}`,
    "",
    `${who} undid the Done tap on this item on ${shortDay(now)} ${hm(now)}. Apply this after any earlier Done-tap note for the same item.`,
    "",
    `## ${weekPath}`,
    `Section "${heading}", the row whose Item cell is \`${plain(item)}\`: if its Status cell starts with \`done (\` and contains \`tapped)\`, put back what follows \`Before: \` (if nothing follows, write \`open\`). If the Status cell has no \`tapped)\` mark, change nothing. Change nothing else.`,
    "",
  ].join("\n");
  return { title: noteTitle(now, source, "undo", item), text };
}

function property(text: string, name: string): string | null {
  const head = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  const m = head && new RegExp(`^${name}:\\s*(.+)$`, "m").exec(head[1]);
  if (!m) return null;
  const raw = m[1].trim();
  try {
    return raw.startsWith('"') ? (JSON.parse(raw) as string) : raw;
  } catch {
    return raw.replace(/^"|"$/g, "");
  }
}

/** The item a Done-tap note is about, or null for any other note. */
export function tapFromNote(text: string): string | null {
  return property(text, "done_item");
}

/** What the waiting notes in the inbox add up to: per item the latest tap wins (tapKey of each). Other notes are ignored. */
export function tapsFromNotes(notes: string[]): { taps: string[]; undos: string[] } {
  const seen = notes
    .map((text) => ({ done: property(text, "done_item"), undo: property(text, "undo_item"), at: Date.parse(property(text, "tapped_at") ?? "") || 0 }))
    .filter((n) => n.done || n.undo)
    .sort((a, b) => a.at - b.at);
  const taps = new Set<string>();
  const undos = new Set<string>();
  for (const n of seen) {
    const key = tapKey((n.done ?? n.undo)!);
    if (n.done) {
      taps.add(key);
      undos.delete(key);
    } else {
      taps.delete(key);
      undos.add(key);
    }
  }
  return { taps: [...taps], undos: [...undos] };
}

/** Waiting notes that are neither a Done tap nor an undo (from agent sessions, mostly): they wait for the sync like the taps do. */
export function otherUpdates(notes: string[]): number {
  return notes.filter((text) => !property(text, "done_item") && !property(text, "undo_item")).length;
}
