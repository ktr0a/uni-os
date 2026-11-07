// Due states and the Done tap, on rows of a synthetic week-7 page (Mon 2 to Sun 8 Nov 2026). `npm test`
import assert from "node:assert/strict";
import { appliedWhen, doneNote, markedRow, nextSync, rowLine, syncOn, syncTimes, syncWhen, tapFromNote, tapsFromNotes, undoNote } from "../src/done";
import { zdate } from "../src/model";
import { parseDue, tapKey } from "../src/parse";
import { buildRegistry, setRegistry } from "../src/registry";
import { check, finish, fixtureJson, useFixtureRegistry } from "./helpers";

useFixtureRegistry();

const WEEK = `---
type: week
week: 7
status: current
---
# Week 07

## Due this week
| Item | Official deadline | Sunday target | Bonus | Status |
|---|---|---|---|---|
| AD quiz "Week 8" | Mon 2 Nov 12:00 (online, 20 min) | | 4 pts | done 2.5 / 4 (Sun 1 Nov) |
| AD peer grading sheet 6 | Tue 3 Nov 12:00 | | 1 pt | open |
| AD programming sheet 2 | Fri 6 Nov 23:59 | | 2 pts left (task B) | task A done 2/2; task B open |
| DM sheet 7 (out Thu 29 Oct) | tutorial: Q&A hour Mon 2 Nov 15:15 (tentative), else Tue 3 Nov 16:15 | Sun 1 Nov (rolls over) | none | Sun 1 Nov: 7.1 and 7.2 only |
| LA hand-in 6 (A6, out Wed 28 Oct) | Tue 3 Nov 23:59 | Sun 1 Nov | feedback only | in progress (see Notes) |
| PROG exercise 7 (out Tue 27 Oct) | Tue 3 Nov 23:59 | Sun 1 Nov (rolls over) | none ("without bonus") | tasks 2 and 3 done; tasks 1 and 4 dropped |
| DM oral 2 slot booking | Fri 6 Nov 12:00 | | none | not reported |

## Results this week
`;

const MON_MORNING = zdate(2026, 11, 2, 10, 0);
const MON_EVENING = zdate(2026, 11, 2, 20, 0);
const TUE_MORNING = zdate(2026, 11, 3, 8, 0);
const WED_MORNING = zdate(2026, 11, 4, 8, 0);
const find = (now: Date, name: RegExp, taps: string[] = []) => parseDue(WEEK, now, taps).find((d) => name.test(d.item))!;
const LA = "LA hand-in 6 (A6, out Wed 28 Oct)";

check("a score or done at the start of the cell is done", () => assert.equal(find(MON_MORNING, /quiz/).state, "done"));
check("a word or a score later in the cell is not done", () => {
  assert.equal(find(MON_MORNING, /programming sheet 2/).state, "open");
  assert.equal(find(MON_MORNING, /DM sheet 7/).state, "open");
  assert.equal(find(MON_MORNING, /PROG exercise 7/).state, "open");
});
check("a bonus item past its deadline stays overdue until someone closes it", () => {
  assert.equal(find(TUE_MORNING, /peer grading/).state, "open");
  const pg = find(WED_MORNING, /peer grading/);
  assert.equal(pg.state, "overdue");
  assert.equal(pg.lapsed, false);
});
check("a tutorial date is soft: before it open, after it passed", () => {
  const before = find(MON_MORNING, /DM sheet 7/);
  assert.ok(before.soft);
  assert.equal(before.state, "open");
  const after = find(MON_EVENING, /DM sheet 7/);
  assert.equal(after.state, "done");
  assert.ok(after.lapsed);
});
check("a no-bonus item drops off once its deadline has passed", () => {
  assert.equal(find(MON_EVENING, /LA hand-in/).state, "open");
  const la = find(WED_MORNING, /LA hand-in/);
  assert.equal(la.state, "done");
  assert.ok(la.lapsed);
});
check("'not reported' is pending, never overdue", () => {
  assert.equal(find(MON_MORNING, /slot booking/).state, "pending");
  assert.equal(find(zdate(2026, 11, 7, 9), /slot booking/).state, "pending");
});
check("a range runs until its end: the timed bonus is not past deadline while it is on", () => {
  const row = "| PROG timed bonus task 1 | Tue 3 Nov 13:15-15:00 (hand-in by 15:00) | | 5 pts | rehearsal Tue 3 Nov 08:30-10:00 |";
  const withBonus = WEEK.replace("| PROG exercise 7", row + "\n| PROG exercise 7");
  const at = (now: Date) => parseDue(withBonus, now).find((d) => /timed bonus/.test(d.item))!;
  assert.equal(at(zdate(2026, 11, 3, 12, 45)).state, "open");
  assert.equal(at(zdate(2026, 11, 3, 12, 45)).deadline!.getTime(), zdate(2026, 11, 3, 13, 15).getTime());
  assert.equal(at(zdate(2026, 11, 3, 13, 45)).state, "open");
  assert.equal(at(zdate(2026, 11, 3, 13, 45)).endsAt!.getTime(), zdate(2026, 11, 3, 15, 0).getTime());
  assert.equal(at(zdate(2026, 11, 3, 15, 30)).state, "overdue");
});
check("a past target is flagged", () => {
  assert.ok(find(MON_MORNING, /LA hand-in/).targetPast);
  assert.equal(find(zdate(2026, 11, 1, 10, 0), /LA hand-in/).targetPast, false);
});
check("a waiting tap note marks the row done", () => {
  const key = tapKey(LA);
  const la = find(MON_EVENING, /LA hand-in/, [key]);
  assert.equal(la.state, "done");
  assert.ok(la.tapped);
  assert.equal(find(MON_EVENING, /peer grading/, [key]).tapped, false);
});
check("rowLine finds the exact row", () => {
  assert.match(rowLine(WEEK, 'AD quiz "Week 8"')!, /^\| AD quiz "Week 8" \| Mon 2 Nov/);
  assert.equal(rowLine(WEEK, "no such item"), null);
});
check("the note has an update-note name, no quoted row, the student's name, and leaves a status the parser reads as done", () => {
  const note = doneNote({ weekPath: "progress/weeks/week-07.md", weekText: WEEK, item: LA, now: MON_EVENING, source: "cockpit" })!;
  assert.equal(note.title, "2026-11-02_2000_cockpit-done-la-hand-in-6-a6-out-wed-28-oct-update.md");
  assert.ok(!note.text.includes(rowLine(WEEK, LA)!));
  assert.match(note.text, /change only its Status cell/);
  assert.match(note.text, /^from: Uni OS cockpit in Obsidian \(Done tap by Alex Example\)$/m);
  assert.match(note.text, /^created: 2026-11-02 20:00 \(Europe\/Zurich\)$/m);
  assert.match(note.text, /Alex Example tapped Done on this item on Mon 2 Nov 20:00/);
  assert.match(note.text, /Section "Due this week"/);
  const replaced = WEEK.replace(rowLine(WEEK, LA)!, markedRow(rowLine(WEEK, LA)!, MON_EVENING));
  const la = parseDue(replaced, MON_EVENING).find((d) => /LA hand-in/.test(d.item))!;
  assert.equal(la.state, "done");
  assert.match(la.status, /^done \(Mon 2 Nov 20:00, tapped\)\. Before: in progress/);
});
check("a marked row whose old status was 'not reported' is done, not pending", () => {
  const item = "DM oral 2 slot booking";
  const week = WEEK.replace(rowLine(WEEK, item)!, markedRow(rowLine(WEEK, item)!, MON_EVENING));
  const d = parseDue(week, MON_EVENING).find((x) => x.item === item)!;
  assert.equal(d.state, "done");
  assert.ok(d.tapped);
});
check("the note reads back to its item, quotes included", () => {
  const note = doneNote({ weekPath: "w.md", weekText: WEEK, item: 'AD quiz "Week 8"', now: MON_EVENING, source: "cockpit" })!;
  assert.equal(tapFromNote(note.text), 'AD quiz "Week 8"');
  assert.equal(tapKey(tapFromNote(note.text)!), tapKey('AD quiz "Week 8"'));
  assert.equal(tapFromNote("---\ntype: inbox-update\n---\nbody"), null);
});
check("undo: the latest note per item wins, other notes are ignored", () => {
  const key = tapKey(LA);
  const args = { weekPath: "progress/weeks/week-07.md", weekText: WEEK, item: LA, source: "cockpit" as const };
  const done1 = doneNote({ ...args, now: MON_EVENING })!.text;
  const undo = undoNote({ weekPath: args.weekPath, item: LA, now: zdate(2026, 11, 2, 20, 5), source: "cockpit" }).text;
  const done2 = doneNote({ ...args, now: zdate(2026, 11, 2, 20, 9) })!.text;
  assert.deepEqual(tapsFromNotes([done1]), { taps: [key], undos: [] });
  assert.deepEqual(tapsFromNotes([undo, done1]), { taps: [], undos: [key] });
  assert.deepEqual(tapsFromNotes([done2, undo, done1, "---\ntype: inbox-update\n---\nbody"]), { taps: [key], undos: [] });
  assert.equal(tapsFromNotes(["no properties at all"]).taps.length, 0);
});
check("undo note has an update-note name and no quoted row", () => {
  const n = undoNote({ weekPath: "progress/weeks/week-07.md", item: "PROG exercise 7 (out Tue 27 Oct)", now: MON_EVENING, source: "cockpit" });
  assert.match(n.title, /^2026-11-02_2000_cockpit-undo-prog-exercise-7-out-tue-27-oct-update\.md$/);
  assert.match(n.text, /undo_item: "PROG exercise 7 \(out Tue 27 Oct\)"/);
  assert.match(n.text, /put back what follows/);
});
check("a row the sync has marked: tapped, and a waiting undo reopens it with its old status", () => {
  const row = rowLine(WEEK, LA)!;
  const marked = WEEK.replace(row, markedRow(row, MON_EVENING));
  const la = parseDue(marked, TUE_MORNING).find((d) => /LA hand-in/.test(d.item))!;
  assert.equal(la.state, "done");
  assert.ok(la.tapped);
  assert.equal(la.tapWaiting, false);
  const back = parseDue(marked, TUE_MORNING, [], [tapKey(LA)]).find((d) => /LA hand-in/.test(d.item))!;
  assert.equal(back.state, "open");
  assert.equal(back.tapped, false);
  assert.match(back.status, /^in progress/);
  // An undo for a row with no mark changes nothing.
  assert.equal(parseDue(WEEK, MON_MORNING, [], [tapKey('AD quiz "Week 8"')]).find((d) => /quiz/.test(d.item))!.state, "done");
});
check("next sync from schedule.inbox_sync", () => {
  assert.equal(nextSync(zdate(2026, 11, 2, 6, 0)), "07:15");
  assert.equal(nextSync(zdate(2026, 11, 2, 13, 15)), "18:15");
  assert.equal(nextSync(MON_EVENING), "tomorrow 07:15");
  assert.equal(syncWhen(MON_EVENING), "tomorrow at 07:15");
  assert.equal(syncWhen(MON_MORNING), "at 13:15");
});
check("other sync times, none, and another student name", () => {
  const j = fixtureJson() as Record<string, any>;
  j.schedule = { inbox_sync: ["12:00"] };
  j.student = { name: "", handle: "sam" };
  setRegistry(buildRegistry(j));
  assert.equal(syncWhen(MON_MORNING), "at 12:00");
  assert.equal(syncWhen(MON_EVENING), "tomorrow at 12:00");
  assert.match(doneNote({ weekPath: "w.md", weekText: WEEK, item: LA, now: MON_EVENING, source: "cockpit" })!.text, /sam tapped Done/);
  j.schedule = { inbox_sync: [] };
  setRegistry(buildRegistry(j));
  assert.equal(syncWhen(MON_MORNING), "at the next inbox sync");
  useFixtureRegistry();
});

check("inbox-sync off: no sync times, and the texts say who applies the notes instead", () => {
  assert.ok(syncOn());
  assert.equal(appliedWhen(MON_MORNING), "applied at 13:15");
  const j = fixtureJson() as Record<string, any>;
  j.modules = { enabled: ["core", "courses", "progress", "cockpit"] };
  setRegistry(buildRegistry(j));
  assert.ok(!syncOn());
  assert.deepEqual(syncTimes(), [], "schedule.inbox_sync still has its default, but nothing runs it");
  assert.equal(nextSync(MON_MORNING), "");
  assert.equal(syncWhen(MON_MORNING), "once you or your agent apply the inbox note, since the inbox-sync module is off");
  assert.equal(appliedWhen(MON_EVENING), "for you or your agent to apply, since the inbox-sync module is off");
  // The notes themselves don't change: something else (an agent, or you) can still apply them.
  assert.match(doneNote({ weekPath: "w.md", weekText: WEEK, item: LA, now: MON_EVENING, source: "cockpit" })!.text, /change only its Status cell/);
  useFixtureRegistry();
});

finish();
