// The parsers against the synthetic week-6 fixture vault (test/fixtures/oct26). `npm test`
import assert from "node:assert/strict";
import { dayKey, hm, parseDayTime, relative, semesterWeek, zdate } from "../src/model";
import { buildModel, eventsOn, nowAndNext, sideBySide, studyHours, weekKeys, weekPageParts } from "../src/parse";
import { courses } from "../src/registry";
import { check, courseCards, finish, readFixture, useFixtureRegistry } from "./helpers";

useFixtureRegistry();

// Time helpers
check("zdate/dayKey round trip across the 25 Oct DST change", () => {
  assert.equal(dayKey(zdate(2026, 10, 25, 1, 30)), "2026-10-25");
  assert.equal(hm(zdate(2026, 10, 26, 9, 15)), "09:15");
  assert.equal(hm(zdate(2026, 10, 20, 9, 15)), "09:15");
});
check("term week from term.week0_monday", () => {
  assert.equal(semesterWeek(zdate(2026, 9, 14, 8)), 0);
  assert.equal(semesterWeek(zdate(2026, 10, 26, 21)), 6);
  assert.equal(semesterWeek(zdate(2026, 11, 1, 23)), 6);
  assert.equal(semesterWeek(zdate(2026, 11, 2, 0, 1)), 7);
});
check("parseDayTime, with the year inferred around the reference date", () => {
  const ref = zdate(2026, 10, 26, 12);
  const a = parseDayTime("Wed 28 Oct 14:15-14:35", ref);
  assert.ok(a && hm(a.date) === "14:15" && a.key === "2026-10-28" && !a.dateOnly);
  const b = parseDayTime("tutorial Tue 3 Nov", ref);
  assert.ok(b && b.dateOnly && b.key === "2026-11-03");
  assert.equal(parseDayTime("no date here", ref), null);
  assert.equal(relative(zdate(2026, 10, 26, 13, 28), zdate(2026, 10, 26, 14, 15)), "in 47 min");
  // Around New Year: January dates read in December belong to the next year, and the other way round.
  assert.equal(parseDayTime("Tue 5 Jan 23:59", zdate(2026, 12, 20, 9))!.key, "2027-01-05");
  assert.equal(parseDayTime("Mon 28 Dec", zdate(2027, 1, 10, 9))!.key, "2026-12-28");
  // A wrong weekday in a note does not flip the year.
  assert.equal(parseDayTime("Sun 26 Oct", ref)!.key, "2026-10-26");
  // A spring term works the same way (no fixed month-to-year table).
  assert.equal(parseDayTime("Fri 19 Mar 23:59", zdate(2027, 3, 1, 9))!.key, "2027-03-19");
});

// The fixture vault
const V = "oct26";
const now = zdate(2026, 10, 26, 21, 45);
const model = buildModel({
  now,
  status: { path: "progress/current-status.md", text: readFixture(`${V}/progress/current-status.md`) },
  week: { path: "progress/weeks/week-06.md", text: readFixture(`${V}/progress/weeks/week-06.md`) },
  weekPlanPath: "semester/plans/week-06-plan.md",
  courses: courseCards(V),
  snapshot: { path: "_agent/cockpit/calendar-snapshot.json", text: readFixture(`${V}/_agent/cockpit/calendar-snapshot.json`) },
  recent: [],
  studyPages: {},
});

check("no warnings on the fixture vault", () => assert.deepEqual(model.warnings, []));
check("week 6", () => assert.equal(model.week, 6));
check("status snapshot line", () => assert.match(model.statusSnapshot, /Mon 26 Oct 2026/));
check("due table: 10 rows, quiz done, LA hand-in open, pending and date-only rows", () => {
  assert.equal(model.due.length, 10);
  const quiz = model.due.find((d) => /quiz "Week 7"/.test(d.item))!;
  assert.equal(quiz.state, "done");
  assert.equal(quiz.course, "algo");
  const la = model.due.find((d) => /LA hand-in 5/.test(d.item))!;
  assert.equal(la.state, "open");
  assert.equal(dayKey(la.deadline!), "2026-10-27");
  const reg = model.due.find((d) => /registration/.test(d.item))!;
  assert.equal(reg.state, "pending");
  const dm = model.due.find((d) => /DM sheet 7/.test(d.item))!;
  assert.equal(dm.course, "dm");
  assert.ok(dm.dateOnly);
  assert.ok(dm.targetPast, "Sun 25 Oct is behind Mon 26 Oct");
  assert.ok(model.due.find((d) => /reading for lecture 12/.test(d.item))!.soft);
  assert.equal(model.due.find((d) => /programming sheet 1/.test(d.item))!.state, "open", "'done' later in the cell is not done");
  assert.equal(model.targetLabel, "Sunday target");
});
check("the other parts of the week page; '(Sat)' after the check-in heading is fine", () => {
  assert.match(model.weekParts.results!, /3 \/ 4/);
  assert.match(model.weekParts.notes!, /room 205/);
  assert.match(model.weekParts.checkIn!, /Focused hours/);
  const plainHeading = weekPageParts("# W\n## End-of-week check-in\n- Done: all\n");
  assert.match(plainHeading.checkIn!, /Done: all/);
  assert.equal(plainHeading.results, null);
});
check("next 10 days", () => {
  assert.ok(model.upcoming.length >= 8, `got ${model.upcoming.length}`);
  assert.equal(model.upcoming[0].key, "2026-10-26");
  assert.equal(model.upcoming.find((u) => /timed bonus/.test(u.what))!.course, "prog");
});
check("bonus standing per course", () => {
  assert.equal(model.bonus.la.bonusNow, 0.1);
  assert.match(model.bonus.la.headline, /^3 more from the 4 quizzes left$/);
  assert.equal(model.bonus.la.tone, "good", "0.75 per quiz is still on track");
  assert.ok(Math.abs(model.bonus.dm.bonusNow! - 0.25 * 4 / 12) < 1e-9);
  assert.equal(model.bonus.algo.tone, "good");
  assert.match(model.bonus.algo.headline, /^81 % of graded points/);
  assert.equal(model.bonus.algo.meter!.max, 120);
  assert.equal(model.bonus.prog.meter!.max, 45);
  assert.equal(model.bonus.prog.meter!.marker, 36);
});
check("exercises per course", () => {
  for (const c of courses()) assert.ok(model.exercises[c.id], `missing ${c.id}`);
  assert.match(model.exercises.la, /A5 hand-in/);
});
check("self ratings", () => {
  assert.equal(model.selfRating.prog, "~90 %");
  assert.equal(model.selfRating.algo, "~70 %");
  assert.equal(model.selfRating.la, "80-85 %");
});
check("calendar: Monday 26 Oct, and the AD exercise class on Wednesday", () => {
  const mon = eventsOn(model, "2026-10-26");
  assert.ok(mon.some((e) => e.title === "V: DM" && e.kind === "lecture" && e.course === "dm" && hm(e.start) === "08:15"));
  assert.ok(mon.some((e) => e.title === "V: LA" && e.kind === "lecture" && e.course === "la"));
  const wed = eventsOn(model, "2026-10-28");
  assert.ok(wed.some((e) => e.title === "U: AD" && e.kind === "exercise" && e.course === "algo" && hm(e.start) === "14:15"));
  const toolkit = mon.find((e) => /maths toolkit/.test(e.title))!;
  assert.equal(toolkit.course, "algo");
  assert.equal(toolkit.kind, "study");
  assert.equal(toolkit.focus, "sums and logarithms cheat sheet\ntwo warm-up recurrences");
  const multi = model.events.find((e) => e.title.startsWith("DM_ sheet 7 deep"))!;
  assert.equal(multi.course, "dm", "the segment with '_' is the main subject");
  assert.ok(multi.deep);
  const gym = model.events.find((e) => e.title === "OP Gym")!;
  assert.ok(gym.optional);
  assert.equal(model.events.find((e) => e.cal === "events")!.kind, "personal");
});
check("now and next at Mon 26 Oct 21:45", () => {
  const nn = nowAndNext(model);
  assert.equal(nn.current.length, 0);
  assert.equal(nn.next[0].title, "AD_ sheet 6");
});
check("study hours week 6", () => {
  const h = studyHours(model, weekKeys("2026-10-28"));
  assert.ok((h.algo ?? 0) > 8, JSON.stringify(h));
  assert.ok((h.dm ?? 0) > 3, JSON.stringify(h));
  assert.equal(h.prog, 2);
});

check("sideBySide only splits overlapping clusters", () => {
  const out = sideBySide([
    { s: 495, en: 600 }, // V: DM 08:15-10:00
    { s: 720, en: 780 }, // busy 12:00-13:00
    { s: 740, en: 780 }, // study block 12:20-13:00
    { s: 795, en: 900 }, // V: LA 13:15-15:00
  ]);
  const by = (s: number) => out.find((o) => o.s === s)!;
  assert.equal(by(495).lanes, 1);
  assert.equal(by(720).lanes, 2);
  assert.equal(by(740).lane, 1);
  assert.equal(by(795).lanes, 1);
});

check("live feeds replace their calendar's snapshot entries; the snapshot stays needed while a study feed is missing", () => {
  const live = {
    cals: ["courses"],
    events: [{ cal: "courses", title: "V: LA (moved)", start: "2026-10-27T08:30:00+01:00", end: "2026-10-27T10:00:00+01:00" }],
    fetchedAt: now.getTime(),
    range: { start: "2026-10-19", end: "2026-11-30" },
    errors: [],
  };
  const m = buildModel({
    now,
    status: null,
    week: null,
    weekPlanPath: null,
    courses: courseCards(V),
    snapshot: { path: "s.json", text: readFixture(`${V}/_agent/cockpit/calendar-snapshot.json`) },
    recent: [],
    studyPages: {},
    live,
  });
  assert.ok(!m.events.some((e) => e.title === "U: AD"), "snapshot entries of a live calendar are dropped");
  assert.ok(m.events.some((e) => e.title === "V: LA (moved)" && e.kind === "lecture"));
  assert.ok(m.events.some((e) => e.title === "AD_ sheet 6"), "study blocks still come from the snapshot");
  assert.deepEqual(m.calendarRange, { start: "2026-10-26", end: "2026-11-08" }, "the snapshot's range, since it is still needed");
  assert.ok(m.warnings.some((w) => /current-status/.test(w)));
});

finish();
