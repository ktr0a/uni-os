// Prep notes: parsing the fixture notes and picking which one to show. `npm test`
import assert from "node:assert/strict";
import { zdate } from "../src/model";
import { gapCount, parsePrep, prepRunsText, prepState } from "../src/prep";
import { buildRegistry, setRegistry } from "../src/registry";
import { check, finish, fixtureJson, readFixture, useFixtureRegistry } from "./helpers";

useFixtureRegistry();

const V = "oct26/semester/prep";
const r1 = parsePrep("semester/prep/prep-2026-10-28.md", readFixture(`${V}/prep-2026-10-28.md`))!;
const r2 = parsePrep("semester/prep/prep-2026-10-28-r2.md", readFixture(`${V}/prep-2026-10-28-r2.md`))!;
const WARN = 19 * 60 + 30;

check("properties and revision", () => {
  assert.equal(r1.date, "2026-10-28");
  assert.equal(r1.status, "ready-with-gaps");
  assert.equal(r2.status, "ready");
  assert.equal(r2.revision, 2);
  assert.equal(r1.revision, 1);
  assert.equal(r2.generated!.toISOString(), "2026-10-27T17:42:00.000Z");
  assert.equal(r2.run, "17:30");
});
check("blocks with times, course and items; wrapped item lines join the item", () => {
  assert.equal(r2.blocks.length, 5);
  const ad = r2.blocks[0];
  assert.equal(ad.start, "12:10");
  assert.equal(ad.end, "13:50");
  assert.equal(ad.course, "algo");
  assert.match(ad.title, /^AD_ theory sheet 6/);
  assert.equal(ad.items.length, 5);
  assert.match(ad.items[1], /task 6\.1 only .* don't read it before your solo attempt$/);
  assert.deepEqual(r2.blocks.map((b) => b.course), ["algo", "la", "dm", "dm", "prog"]);
});
check("callout types by slug work too (`> [!ad]`)", () => {
  assert.deepEqual(r1.blocks.map((b) => b.course), ["algo", "dm", "la", "prog"]);
});
check("gaps", () => {
  assert.equal(r1.gaps.length, 2);
  assert.equal(gapCount(r2), 2);
});
check("today's before the switch hour, tomorrow's after; newest revision wins", () => {
  const notes = [r1, r2];
  const morning = prepState(notes, "2026-10-28", zdate(2026, 10, 28, 9, 0), 18, WARN);
  assert.equal(morning.which, "today");
  assert.equal(morning.note!.revision, 2);
  const evening = prepState(notes, "2026-10-27", zdate(2026, 10, 27, 18, 30), 18, WARN);
  assert.equal(evening.which, "tomorrow");
  assert.equal(evening.target, "2026-10-28");
  assert.equal(evening.note!.path, "semester/prep/prep-2026-10-28-r2.md");
  assert.deepEqual(evening.alerts, []);
});
check("alerts: tomorrow missing after the warn time; today missing once the routine has run before", () => {
  const notes = [r1, r2];
  const lateWed = prepState(notes, "2026-10-28", zdate(2026, 10, 28, 19, 45), 18, WARN);
  assert.equal(lateWed.note, null);
  assert.equal(lateWed.alerts.length, 1);
  assert.match(lateWed.alerts[0], /Tomorrow's study prep is still missing \(it runs 17:30, change check 19:30, morning check 07:30\)/);
  const earlyWed = prepState(notes, "2026-10-28", zdate(2026, 10, 28, 19, 0), 18, WARN);
  assert.equal(earlyWed.alerts.length, 0);
  const thursday = prepState(notes, "2026-10-29", zdate(2026, 10, 29, 8, 0), 18, WARN);
  assert.match(thursday.alerts[0], /No study prep for today: the 07:30 morning check didn't/);
  // The morning check may still write it: a softer text until 15 minutes after it.
  const thursdayEarly = prepState(notes, "2026-10-29", zdate(2026, 10, 29, 7, 40), 18, WARN);
  assert.match(thursdayEarly.alerts[0], /07:30 morning check will try again/);
  const thursday745 = prepState(notes, "2026-10-29", zdate(2026, 10, 29, 7, 45), 18, WARN);
  assert.match(thursday745.alerts[0], /didn't produce one/);
  const firstDay = prepState(notes, "2026-10-27", zdate(2026, 10, 27, 10, 0), 18, WARN);
  assert.deepEqual(firstDay.alerts, []);
});

check("a free day and an empty gap list", () => {
  const free = parsePrep(
    "semester/prep/prep-2026-11-01.md",
    "---\ntype: prep\ndate: 2026-11-01\ngenerated: 2026-10-31T17:17:05+01:00\nrun: 17:17\nstatus: ready\n---\n# Prep for Sun 1 Nov 2026\n\nNo study blocks tomorrow.\n\n## Gaps\n- none\n",
  )!;
  assert.equal(free.blocks.length, 0);
  assert.equal(gapCount(free), 0);
  assert.equal(free.generated!.toISOString(), "2026-10-31T16:17:05.000Z");
  const state = prepState([free], "2026-10-31", zdate(2026, 10, 31, 20, 0), 18, WARN);
  assert.equal(state.note!.date, "2026-11-01");
  assert.deepEqual(state.alerts, []);
});

check("other run times come from the config (schedule.daily_prep, schedule.prep_check)", () => {
  const j = fixtureJson() as Record<string, any>;
  j.schedule = { daily_prep: ["16:00"], prep_check: "06:45" };
  setRegistry(buildRegistry(j));
  assert.equal(prepRunsText(), "runs 16:00, morning check 06:45");
  const early = prepState([r1, r2], "2026-10-29", zdate(2026, 10, 29, 6, 55), 18, WARN);
  assert.match(early.alerts[0], /06:45 morning check will try again/);
  const later = prepState([r1, r2], "2026-10-29", zdate(2026, 10, 29, 7, 0), 18, WARN);
  assert.match(later.alerts[0], /06:45 morning check didn't produce one/);
  useFixtureRegistry();
});

check("a note of another type, or without a date, is not a prep note", () => {
  assert.equal(parsePrep("semester/prep/notes.md", "---\ntype: plan\n---\n# x"), null);
  assert.equal(parsePrep("semester/prep/prep-2026-11-01.md", "---\ntype: plan\n---\n# x"), null);
});

finish();
