// Week 7 of the synthetic fixture vault (Mon 2 to Sun 8 Nov 2026), as the notes stand on Mon 2 Nov in the evening,
// played hour by hour: the due rules, Done taps and undos, the calendar and the prep card on a full week page
// instead of single invented rows. `npm test`
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import { contextPack } from "../src/context";
import { doneNote, markedRow, otherUpdates, rowLine, undoNote } from "../src/done";
import { dayKey, hm, relative, semesterWeek, shortDay, zdate } from "../src/model";
import { CockpitModel, DueItem, buildModel, nowAndNext, plain, tapKey } from "../src/parse";
import { PrepNote, parsePrep, prepState } from "../src/prep";
import { courses } from "../src/registry";
import { isUrgent, sortedDue } from "../src/render/ctx";
import { DEFAULT_SETTINGS } from "../src/settings";
import { FIXTURES, check, courseCards, finish, readFixture, useFixtureRegistry } from "./helpers";

useFixtureRegistry();

const V = "nov02";
const WEEK_PATH = "progress/weeks/week-07.md";
const WEEK = readFixture(`${V}/${WEEK_PATH}`);
const STATUS = readFixture(`${V}/progress/current-status.md`);
const SNAPSHOT = readFixture(`${V}/_agent/cockpit/calendar-snapshot.json`);
const CARDS = courseCards(V);
const PREP: PrepNote[] = fs
  .readdirSync(path.join(FIXTURES, V, "semester/prep"))
  .filter((f) => /^prep-.*\.md$/.test(f))
  .map((f) => parsePrep(`semester/prep/${f}`, readFixture(`${V}/semester/prep/${f}`))!);
const [WARN_H, WARN_M] = DEFAULT_SETTINGS.prepWarnAfter.split(":").map(Number);

interface Variant {
  week?: string;
  taps?: string[];
  undos?: string[];
  inboxWaiting?: number;
}

/** The cockpit model as it would be built at `now`, with the settings' defaults. */
function modelAt(now: Date, v: Variant = {}): CockpitModel {
  return buildModel({
    now,
    prep: prepState(PREP, dayKey(now), now, DEFAULT_SETTINGS.prepSwitchHour, WARN_H * 60 + WARN_M),
    status: { path: "progress/current-status.md", text: STATUS },
    week: { path: WEEK_PATH, text: v.week ?? WEEK },
    weekPlanPath: null,
    courses: CARDS,
    snapshot: { path: "_agent/cockpit/calendar-snapshot.json", text: SNAPSHOT },
    recent: [],
    studyPages: {},
    taps: v.taps,
    undos: v.undos,
    inboxWaiting: v.inboxWaiting,
    staleDays: DEFAULT_SETTINGS.staleDays,
  });
}

const ctxOf = (model: CockpitModel) => ({ model, s: DEFAULT_SETTINGS });
const urgent = (model: CockpitModel, d: DueItem) => isUrgent(ctxOf(model), d);
const at = (day: number, h: number, m = 0) => zdate(2026, 11, day, h, m);
const label = (now: Date) => `${shortDay(now)} ${hm(now)}`;
const find = (model: CockpitModel, name: RegExp) => {
  const d = model.due.find((x) => name.test(x.item));
  assert.ok(d, `no row matches ${name}`);
  return d;
};

// Every hour from Mon 2 Nov 00:00 to Mon 9 Nov 00:00 (no clock change in this stretch).
const HOURS: Date[] = [];
for (let day = 2; day <= 9; day++) for (let h = 0; h < 24 && (day < 9 || h === 0); h++) HOURS.push(at(day, h));
const MODELS = HOURS.map((now) => modelAt(now));

function sweep(name: string, fn: (now: Date, model: CockpitModel, i: number) => void): void {
  check(name, () => {
    const bad: string[] = [];
    HOURS.forEach((now, i) => {
      try {
        fn(now, MODELS[i], i);
      } catch (err) {
        bad.push(`${label(now)}: ${(err as Error).message.split("\n")[0]}`);
      }
    });
    assert.equal(bad.length, 0, `${bad.length} of ${HOURS.length} hours failed:\n  ${bad.slice(0, 5).join("\n  ")}`);
  });
}

// ---------- the sweep ----------

const ROWS = WEEK.split(/\r?\n/).filter((l) => /^\|/.test(l)).length - 2;

check("the week page has the 15 rows the sweep expects", () => {
  assert.equal(ROWS, 15);
  assert.equal(HOURS.length, 7 * 24 + 1);
});

sweep("every hour: the model builds, the due list has every row with a date, the week number follows the clock", (now, m) => {
  assert.equal(m.due.length, ROWS);
  for (const d of m.due) {
    assert.ok(plain(d.item), "a row without an item");
    assert.ok(d.deadline, `no date read from "${d.deadlineText}"`);
  }
  assert.equal(m.week, semesterWeek(now));
  assert.equal(m.week, now.getTime() >= at(9, 0).getTime() ? 8 : 7);
  assert.equal(courses().filter((c) => m.bonus[c.id]).length, 4);
  for (const w of m.warnings) assert.equal(typeof w, "string");
});

sweep("every hour: the context pack lists every row and prints no junk", (_now, m) => {
  const pack = contextPack(m);
  for (const d of m.due) assert.ok(pack.includes(plain(d.item)), `missing ${plain(d.item)}`);
  assert.doesNotMatch(pack, /undefined|NaN|\[object/);
});

sweep("every hour: nothing is both tapped and lapsed", (_now, m) => {
  for (const d of m.due) assert.ok(!(d.tapped && d.lapsed), plain(d.item));
});

sweep("every hour: a done or soft item is never urgent", (_now, m) => {
  for (const d of m.due) if (d.state === "done" || d.soft) assert.equal(urgent(m, d), false, plain(d.item));
});

sweep("every hour: a lapsed row is done and over, an overdue row is not soft and over", (now, m) => {
  for (const d of m.due) {
    if (d.lapsed) {
      assert.equal(d.state, "done", plain(d.item));
      assert.ok(d.deadline!.getTime() < now.getTime(), plain(d.item));
    }
    if (d.state === "overdue") {
      assert.ok(!d.soft && !d.lapsed, plain(d.item));
      assert.ok(d.deadline!.getTime() < now.getTime(), plain(d.item));
    }
  }
});

check("a deadline that has passed stays passed from hour to hour", () => {
  const over = new Set<number>();
  HOURS.forEach((now, i) => {
    MODELS[i].due.forEach((d, row) => {
      const isOver = d.state === "overdue" || d.lapsed;
      if (over.has(row)) assert.ok(isOver, `${plain(d.item)} came back at ${label(now)}`);
      if (isOver) over.add(row);
    });
  });
  assert.ok(over.size > 5, "the sweep should see several rows pass");
});

sweep("every hour: now and next don't throw, and every next event is ahead", (now, m) => {
  const { current, next } = nowAndNext(m);
  assert.ok(next.length <= 6);
  for (const e of next) assert.ok(e.start.getTime() > now.getTime(), `${e.title} at ${label(e.start)}`);
  for (const e of current) assert.ok(e.start.getTime() <= now.getTime() && now.getTime() < e.end.getTime(), e.title);
  for (let k = 1; k < next.length; k++) assert.ok(next[k - 1].start.getTime() <= next[k].start.getTime());
});

sweep("every hour: the prep card picks today's note until the switch hour, tomorrow's after, and only warns when a note is really missing", (now, m) => {
  const p = m.prep!;
  assert.equal(p.which, Number(hm(now).slice(0, 2)) >= DEFAULT_SETTINGS.prepSwitchHour ? "tomorrow" : "today");
  if (p.note) assert.equal(p.note.date, p.target);
  if (p.target <= "2026-11-03") assert.ok(p.note, `a note exists for ${p.target}`);
  for (const a of p.alerts) assert.ok(/prep/i.test(a), a);
});

// Done taps, their notes and undos on every open row, hour by hour.
let tapRows = 0;
let markRows = 0;
sweep("every hour: a waiting tap marks an open row done, tapped and quiet", (now, m) => {
  const open = m.due.filter((d) => d.state !== "done");
  const tapped = modelAt(now, { taps: open.map((d) => tapKey(d.item)) });
  for (const d of tapped.due) {
    const before = m.due.find((x) => x.item === d.item)!;
    if (before.state === "done") continue;
    tapRows++;
    assert.equal(d.state, "done", plain(d.item));
    assert.ok(d.tapped && d.tapWaiting && !d.lapsed, plain(d.item));
    assert.equal(urgent(tapped, d), false, plain(d.item));
  }
});

sweep("every hour: the row the sync marked reads as tapped, and an undo reopens it with its old status", (now, m) => {
  for (const before of m.due) {
    if (before.state === "done") continue;
    const note = doneNote({ weekPath: WEEK_PATH, weekText: WEEK, item: before.item, now, source: "cockpit" });
    assert.ok(note, `no note for ${plain(before.item)}`);
    markRows++;
    const week = WEEK.replace(rowLine(WEEK, before.item)!, markedRow(rowLine(WEEK, before.item)!, now));
    const marked = modelAt(now, { week });
    const d = marked.due.find((x) => x.item === before.item)!;
    assert.ok(d.tapped && !d.tapWaiting && !d.lapsed, plain(d.item));
    assert.equal(d.state, "done", plain(d.item));
    assert.equal(urgent(marked, d), false, plain(d.item));
    const undone = modelAt(now, { week, undos: [tapKey(before.item)] }).due.find((x) => x.item === before.item)!;
    assert.ok(!undone.tapped, plain(before.item));
    assert.equal(undone.state, before.state, plain(before.item));
    assert.equal(plain(undone.status), plain(before.status), plain(before.item));
    assert.equal(undone.lapsed, before.lapsed, plain(before.item));
  }
});

check("the tap sweeps really covered rows (open rows only, many hours)", () => {
  assert.ok(tapRows > 1000 && markRows > 1000, `${tapRows} / ${markRows}`);
});

// ---------- known moments ----------

check("Mon 2 Nov 20:00: programming sheet 2 is open, DM sheet 7 has passed, the AD quiz is done", () => {
  const m = modelAt(at(2, 20));
  const ps = find(m, /programming sheet 2/);
  assert.equal(ps.state, "open");
  assert.equal(urgent(m, ps), false);
  const dm = find(m, /DM sheet 7/);
  assert.ok(dm.soft && dm.lapsed, "a tentative tutorial slot with no bonus drops off once it is over");
  assert.equal(dm.state, "done");
  const quiz = find(m, /quiz "Week 8"/);
  assert.equal(quiz.state, "done");
  assert.ok(!quiz.lapsed && !quiz.tapped);
  // The peer grading is due tomorrow at noon and open: urgent, not yet overdue.
  const pg = find(m, /peer grading sheet 6/);
  assert.equal(pg.state, "open");
  assert.ok(urgent(m, pg));
  // Items not released yet get no Done button.
  assert.ok(find(m, /DM sheet 8/).notReleased);
});

check("Tue 3 Nov 12:45: the timed bonus is within 24 h, 30 min away, and the urgent rows come soonest first", () => {
  const now = at(3, 12, 45);
  const m = modelAt(now);
  const timed = find(m, /timed bonus task 1/);
  assert.equal(timed.state, "open");
  assert.ok(urgent(m, timed));
  assert.equal(relative(now, timed.deadline!), "in 30 min");
  assert.equal(hm(timed.deadline!), "13:15");
  const names = sortedDue(ctxOf(m))
    .filter((d) => urgent(m, d))
    .map((d) => plain(d.item).split(/ \(| "/)[0]);
  assert.deepEqual(names, ["AD peer grading sheet 6", "PROG timed bonus task 1", "LA hand-in 6", "PROG exercise 7"]);
  // Not urgent yet: the quiz on Thursday and everything due on Friday or later.
  assert.equal(urgent(m, find(m, /LA bonus quiz 4/)), false);
  assert.equal(urgent(m, find(m, /programming sheet 2/)), false);
  // The calendar agrees: the warm-up runs now, the timed task starts at 13:15.
  const { current, next } = nowAndNext(m);
  assert.match(current[0].title, /warm-up/);
  assert.equal(hm(next[0].start), "13:15");
  assert.match(next[0].title, /timed bonus/);
  assert.equal(next[0].kind, "fixture");
});

check("Wed 4 Nov 00:10: LA hand-in 6 and PROG exercise 7 have passed, peer grading 6 is overdue (it has a bonus)", () => {
  const m = modelAt(at(4, 0, 10));
  for (const re of [/LA hand-in 6/, /PROG exercise 7/]) {
    const d = find(m, re);
    assert.ok(d.lapsed, plain(d.item));
    assert.equal(d.state, "done");
    assert.equal(urgent(m, d), false);
  }
  const pg = find(m, /peer grading sheet 6/);
  assert.equal(pg.state, "overdue");
  assert.ok(!pg.lapsed);
  assert.ok(urgent(m, pg));
  // The timed bonus has a bonus too, so it stays red until someone closes it.
  assert.equal(find(m, /timed bonus task 1/).state, "overdue");
});

check("Sat 7 Nov 00:05: programming sheet 2 is overdue; the study-plan review was open on its day and passed the day after", () => {
  const m = modelAt(at(7, 0, 5));
  const ps = find(m, /programming sheet 2/);
  assert.equal(ps.state, "overdue");
  assert.ok(!ps.lapsed);
  assert.ok(urgent(m, ps));
  assert.equal(find(modelAt(at(6, 0, 5)), /Study-plan review/).state, "open");
  const review = find(m, /Study-plan review/);
  assert.ok(review.lapsed, "no bonus: it drops off once its day is over");
  assert.equal(review.state, "done");
});

check("bonus maths on the fixture cards: AD 40 / 50 of ~120, LA 2 / 7, DM 4 / 12, PROG 8 of ~40", () => {
  const close = (a: number | null, b: number) => assert.ok(a !== null && Math.abs(a - b) < 1e-9, `${a} vs ${b}`);
  const b = modelAt(at(2, 20)).bonus;
  // AD: full +0.25 at 80 % of the estimated 120, so 96 points; 40 of the 50 graded so far.
  assert.equal(b.algo.big, "40");
  assert.equal(b.algo.of, "/ 50 graded");
  close(b.algo.bonusNow, (0.25 * 40) / 96);
  assert.deepEqual(b.algo.meter, { value: 40, max: 120, marker: 96, ghost: 50 });
  assert.match(b.algo.headline, /^80 % of graded points/);
  assert.match(b.algo.detail, /About 56 more of the ~70 points still to come \(80 %\)/);
  assert.equal(b.algo.tone, "good");
  // LA: 5 of 7 quiz points give the full +0.25, 0.05 per point; four quizzes left after Mon 2 Nov.
  assert.equal(b.la.big, "2");
  assert.equal(b.la.of, "/ 7 quiz points");
  close(b.la.bonusNow, 0.1);
  assert.equal(b.la.headline, "3 more from the 4 quizzes left");
  assert.deepEqual(b.la.meter, { value: 2, max: 7, marker: 5 });
  assert.match(modelAt(at(5, 17)).bonus.la.headline, /from the 3 quizzes left/, "quiz 4 is over on Thursday evening");
  // DM: linear, 0.25 x B / 12; one oral left (Thu 26 Nov).
  assert.equal(b.dm.big, "4");
  close(b.dm.bonusNow, 0.25 * 4 / 12);
  assert.match(b.dm.headline, /^1 oral left/);
  assert.deepEqual(b.dm.meter, { value: 4, max: 12, marker: 12 });
  // PROG: 8 of 8 graded, out of an estimated 40; full at 32.
  assert.equal(b.prog.big, "8");
  close(b.prog.bonusNow, (0.25 * 8) / 32);
  assert.deepEqual(b.prog.meter, { value: 8, max: 40, marker: 32, ghost: 8 });
  assert.match(b.prog.detail, /About 24 more of the ~32 points still to come \(75 %\)/);
});

check("context pack: a passed or tapped row says what the cockpit shows, not the raw status or a past target", () => {
  const pack = contextPack(modelAt(at(4, 0, 10)));
  assert.match(pack, /^# Study status, Wed 4 Nov 2026 00:10 \(term week 7\)$/m);
  assert.match(pack, /^- LA hand-in 6 \(A6, out Wed 28 Oct\): Tue 3 Nov 23:59 \/ passed \(no bonus, its date is over\)$/m);
  // DM sheet 7: its Sunday target ("Sun 1 Nov (rolls over)") is long past.
  assert.match(pack, /^- DM sheet 7 \(out Thu 29 Oct\): [^/]* \/ passed \(no bonus/m);
  assert.doesNotMatch(pack, /rolls over|7\.1 and 7\.2|in progress/);
  // A row still open keeps its status; a target that is still ahead stays.
  assert.match(pack, /^- AD theory sheet 7 \(group; out Mon 2 Nov\): Sun 8 Nov 23:59 \/ Sunday target Thu 5 Nov \/ open$/m);
  assert.match(pack, /^- AD peer grading sheet 6: Tue 3 Nov 12:00 \/ past deadline, open$/m);
  // A tap whose note still waits, and a row the sync has already marked.
  const item = "LA hand-in 6 (A6, out Wed 28 Oct)";
  const now = at(2, 20);
  const waiting = contextPack(modelAt(now, { taps: [tapKey(item)] }));
  assert.match(waiting, /^- LA hand-in 6 \(A6, out Wed 28 Oct\): Tue 3 Nov 23:59 \/ tapped done \(the week page updates tomorrow at 07:15\)$/m);
  const marked = contextPack(modelAt(now, { week: WEEK.replace(rowLine(WEEK, item)!, markedRow(rowLine(WEEK, item)!, now)) }));
  assert.match(marked, /^- LA hand-in 6 \(A6, out Wed 28 Oct\): Tue 3 Nov 23:59 \/ tapped done$/m);
  assert.doesNotMatch(marked, /Before:/);
});

check("the inbox: only notes that are not a Done tap or an undo count, and the pack says so", () => {
  const item = "LA hand-in 6 (A6, out Wed 28 Oct)";
  const now = at(2, 20);
  const done = doneNote({ weekPath: WEEK_PATH, weekText: WEEK, item, now, source: "cockpit" })!.text;
  const undo = undoNote({ weekPath: WEEK_PATH, item, now, source: "cockpit" }).text;
  const session = "---\ntype: inbox-update\nfrom: LA exercise help\n---\n# LA update\n";
  assert.equal(otherUpdates([done, undo]), 0);
  assert.equal(otherUpdates([done, session, undo, "no properties at all"]), 2);
  assert.equal(modelAt(now).inboxWaiting, 0);
  assert.doesNotMatch(contextPack(modelAt(now)), /waiting in the inbox/);
  assert.match(contextPack(modelAt(now, { inboxWaiting: 2 })), /\(2 updates waiting in the inbox, applied tomorrow at 07:15; the week page doesn't show them yet\.\)/);
  assert.match(contextPack(modelAt(at(2, 9), { inboxWaiting: 1 })), /\(1 update waiting in the inbox, applied at 13:15;/);
});

check("prep: today's newest revision until 18:00, tomorrow's from 18:00, a missing note only warns when it should", () => {
  const noon = modelAt(at(2, 12)).prep!;
  assert.equal(noon.which, "today");
  assert.equal(noon.note!.revision, 3);
  assert.equal(noon.note!.blocks.length, 6);
  assert.deepEqual(noon.alerts, []);
  const evening = modelAt(at(2, 18)).prep!;
  assert.equal(evening.which, "tomorrow");
  assert.equal(evening.note!.path, "semester/prep/prep-2026-11-03-r2.md");
  assert.deepEqual(evening.alerts, []);
  // Wednesday's note does not exist in the fixtures: that is a warning after 19:30 on Tuesday, not before.
  assert.equal(modelAt(at(3, 19)).prep!.alerts.length, 0);
  assert.match(modelAt(at(3, 19, 30)).prep!.alerts[0], /Tomorrow's study prep is still missing/);
});

check("daily-prep off (modules.enabled): no prep in the model, no prep warnings, whatever notes and schedule.daily_prep say", () => {
  // Wednesday 19:30: tomorrow's note is missing, which warns while daily-prep is on.
  const now = at(3, 19, 30);
  assert.ok(modelAt(now).warnings.some((w) => /study prep/i.test(w)));
  useFixtureRegistry((j) => (j.modules.enabled = j.modules.enabled.filter((m: string) => m !== "daily-prep")));
  try {
    for (const t of [now, at(2, 12), at(2, 18)]) {
      const m = modelAt(t);
      assert.equal(m.prep, null, label(t));
      assert.ok(!m.warnings.some((w) => /prep/i.test(w)), `${label(t)}: ${m.warnings.join(" | ")}`);
    }
  } finally {
    useFixtureRegistry();
  }
  assert.ok(modelAt(at(2, 12)).prep!.note, "back on: the card returns");
});

check("inbox-sync off (modules.enabled): taps still count, but no texts promise a sync time", () => {
  const item = "LA hand-in 6 (A6, out Wed 28 Oct)";
  const now = at(2, 20);
  useFixtureRegistry((j) => (j.modules.enabled = j.modules.enabled.filter((m: string) => m !== "inbox-sync")));
  try {
    const m = modelAt(now, { taps: [tapKey(item)], inboxWaiting: 2 });
    assert.equal(m.due.find((d) => d.item === item)!.state, "done");
    const pack = contextPack(m);
    assert.match(pack, /^- LA hand-in 6 \(A6, out Wed 28 Oct\): Tue 3 Nov 23:59 \/ tapped done \(the week page updates once you or your agent apply the inbox note, since the inbox-sync module is off\)$/m);
    assert.match(pack, /\(2 updates waiting in the inbox, for you or your agent to apply, since the inbox-sync module is off; the week page doesn't show them yet\.\)/);
    assert.doesNotMatch(pack, /updates (tomorrow )?at |applied (tomorrow )?at |next inbox sync/);
  } finally {
    useFixtureRegistry();
  }
});

finish();
