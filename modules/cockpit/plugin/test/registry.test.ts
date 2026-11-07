// The course registry from _agent/uni-os.json: courses, detection, colours, paths, defaults. `npm test`
import assert from "node:assert/strict";
import { buildRegistry, calendarRole, calloutCourse, courseById, courses, detectCourse, lighten, moduleEnabled, paletteOf, registry, setRegistry, termPattern, vocab } from "../src/registry";
import { check, finish, fixtureJson, useFixtureRegistry } from "./helpers";

useFixtureRegistry();

check("courses come from the config, in order, with derived paths", () => {
  assert.deepEqual(courses().map((c) => c.id), ["algo", "dm", "la", "prog"]);
  const ad = courseById("algo")!;
  assert.equal(ad.short, "AD");
  assert.equal(ad.card, "AD/ad.md");
  assert.deepEqual(ad.errorLogs, [
    { path: "AD/ad-error-log-theory.md", label: "Error log: theory" },
    { path: "AD/ad-error-log-programming.md", label: "Error log: programming" },
  ]);
  assert.deepEqual(courseById("dm")!.errorLogs, [{ path: "DM/dm-error-log.md", label: "Error log" }]);
  assert.deepEqual(ad.studyFolders, ["AD/notes/", "AD/quiz-prep/"]);
  assert.deepEqual(registry().problems, []);
});

check("term, schedule, calendars and paths", () => {
  const r = registry();
  assert.equal(r.term.timezone, "Europe/Zurich");
  assert.equal(r.term.week0, "2026-09-14");
  assert.deepEqual(r.schedule.syncTimes, ["07:15", "13:15", "18:15"]);
  assert.deepEqual(r.schedule.prepRuns, ["17:30", "19:30"]);
  assert.equal(r.schedule.studyCutoff, "19:00");
  assert.deepEqual(r.calendars.map((c) => `${c.id}:${c.role}:${c.label}`), ["courses:classes:Courses", "study_blocks:study:Study blocks", "events:personal:Events", "busy:personal:Busy"]);
  assert.equal(r.paths.rules, "_agent/rules.md");
  assert.equal(r.paths.snapshot, "_agent/cockpit/calendar-snapshot.json");
  assert.equal(r.paths.inbox, "inbox");
  assert.equal(r.student.name, "Alex Example");
});

check("detectCourse: the course mentioned first, short codes case-sensitive, block notation", () => {
  assert.equal(detectCourse("PROG timed bonus 1 · E7 due 23:59 · LA hand-in 6 due 23:59"), "prog");
  assert.equal(detectCourse("**AD** quiz"), "algo");
  assert.equal(detectCourse("[DM], (PROG reading)"), "dm");
  assert.equal(detectCourse("LA_ mock A"), "la");
  assert.equal(detectCourse("la la land"), null, "lower-case 'la' is not Linear Algebra");
  assert.equal(detectCourse("Linear algebra recap"), "la", "full names match in any case");
  assert.equal(detectCourse("CodeLab task 3"), "algo", "aliases");
  assert.equal(detectCourse("E12 is out"), "prog", "a raw detect regex");
  assert.equal(detectCourse("BADGE"), null, "whole words only");
  assert.equal(detectCourse("Study-plan review"), null);
});

check("termPattern keeps & and spaces literal and allows the '_' of the block notation", () => {
  assert.ok(termPattern("A&D").test("A&D_ sheet 6"));
  assert.ok(!termPattern("A&D").test("XA&DY"));
  assert.ok(termPattern("Code Expert").test("code expert task"));
});

check("callout types: id, slug or short name", () => {
  assert.equal(calloutCourse("algo"), "algo");
  assert.equal(calloutCourse("ad"), "algo");
  assert.equal(calloutCourse("PROG"), "prog");
  assert.equal(calloutCourse("tip"), null);
});

check("colours: from the config, light colour derived when missing, overrides on top", () => {
  assert.equal(courseById("la")!.colourLight, "#b48ef5");
  assert.equal(courseById("algo")!.colourLight, lighten("#1e66f5"));
  assert.equal(lighten("#000000", 0.5), "#808080");
  const p = paletteOf(registry(), { dm: { main: "#123456" } });
  assert.equal(p.dm.main, "#123456");
  assert.equal(p.dm.light, courseById("dm")!.colourLight);
  assert.equal(p.algo.main, "#1e66f5");
});

check("calendar roles: plugin feeds first, then the registry, then the default names", () => {
  assert.equal(calendarRole("courses"), "classes");
  assert.equal(calendarRole("study_blocks"), "study");
  assert.equal(calendarRole("events"), "personal");
  assert.equal(calendarRole("my-gym"), "study");
  assert.equal(calendarRole("my-gym", [{ id: "my-gym", role: "personal" }]), "personal");
});

check("vocabulary: done only at the start of the cell, pending anywhere, soft dates", () => {
  const v = vocab();
  assert.ok(v.doneStart.test("done 2.5 / 4"));
  assert.ok(v.doneStart.test("3/4"));
  assert.ok(v.doneStart.test("✓ Mon"));
  assert.ok(!v.doneStart.test("task A done 2/2; task B open"));
  assert.ok(!v.doneStart.test("doneish"));
  assert.ok(v.pending.test("submitted, result not recorded"));
  assert.ok(v.soft.test("tutorial Tue 3 Nov"));
  assert.ok(v.soft.test("Mon 2 Nov 15:15 (tentative)"));
  assert.ok(!v.soft.test("Tue 3 Nov 23:59"));
  assert.ok(v.noBonus.test(""));
  assert.ok(v.noBonus.test("none (not an oral week)"));
  assert.ok(v.noBonus.test("feedback only"));
  assert.ok(!v.noBonus.test("4 pts"));
  assert.ok(!v.noBonus.test("nominal"));
});

check("custom vocabulary from cockpit.* keys", () => {
  const j = fixtureJson() as Record<string, any>;
  j.cockpit = { done_words: ["erledigt"], soft_prefixes: [], soft_markers: ["(maybe)"] };
  setRegistry(buildRegistry(j));
  const v = vocab();
  assert.ok(v.doneStart.test("erledigt Mo"));
  assert.ok(!v.doneStart.test("done"));
  assert.ok(v.doneStart.test("2/3"), "a score always counts");
  assert.ok(!v.soft.test("tutorial Tue 3 Nov"));
  assert.ok(v.soft.test("Tue 3 Nov (maybe)"));
  useFixtureRegistry();
});

check("class titles: the default patterns and the planning module's prefixes (calendar.lecture_prefix)", () => {
  const n = registry().notation;
  assert.ok(n.lecture.test("V: LA") && n.lecture.test("L: LA"));
  assert.ok(n.exercise.test("U: AD") && n.exercise.test("E: AD"));
  assert.ok(!n.lecture.test("PROG timed bonus task 1"));
  const r = buildRegistry({ term: { week0_monday: "2026-09-14" }, calendar: { lecture_prefix: "Lec ", exercise_prefix: "Tut " }, cockpit: { lecture_pattern: "^Vorlesung", exercise_pattern: "^Übung" } });
  assert.ok(r.notation.lecture.test("Lec LA") && r.notation.lecture.test("Vorlesung LA"));
  assert.ok(r.notation.exercise.test("Tut AD") && r.notation.exercise.test("Übung AD"));
  assert.ok(!r.notation.lecture.test("V: LA"), "a custom pattern replaces the default one");
});

check("a missing config: no courses, one clear problem, sane defaults", () => {
  const r = buildRegistry(null, "_agent/uni-os.json");
  assert.equal(r.courses.length, 0);
  assert.equal(r.loaded, false);
  assert.match(r.problems[0], /No _agent\/uni-os.json found.*uni_os.py render/);
  assert.equal(r.paths.status, "progress/current-status.md");
  assert.deepEqual(r.schedule.syncTimes, ["07:15", "13:15", "18:15"]);
});

check("a sloppy config: bad time zone, duplicate and id-less courses, folders with spaces and &", () => {
  const r = buildRegistry({
    term: { timezone: "Mars/Olympus", week0_monday: "2026-09-14" },
    courses: [{ id: "x", short: "X", folder: "A&D stuff/", slug: "ad" }, { id: "x" }, { short: "no id" }],
    schedule: { inbox_sync: [], study_cutoff: "" },
  });
  assert.equal(r.courses.length, 1);
  assert.equal(r.courses[0].card, "A&D stuff/ad.md");
  assert.equal(r.problems.length, 3, r.problems.join(" | "));
  assert.notEqual(r.term.timezone, "Mars/Olympus");
  assert.deepEqual(r.schedule.syncTimes, [], "an explicitly empty list stays empty");
  assert.equal(r.schedule.studyCutoff, "");
});

check("bonus rule fields: percent max, threshold given in percent, unknown scheme becomes custom", () => {
  const r = buildRegistry({
    term: { week0_monday: "2026-09-14" },
    courses: [
      { id: "a", bonus: { scheme: "threshold", max_bonus: "10%", threshold: 75 } },
      { id: "b", bonus: { scheme: "magic" } },
      { id: "c" },
    ],
  });
  assert.equal(r.courses[0].bonus.maxBonus, 10);
  assert.ok(r.courses[0].bonus.maxIsPercent);
  assert.equal(r.courses[0].bonus.threshold, 0.75);
  assert.equal(r.courses[1].bonus.scheme, "custom");
  assert.equal(r.courses[2].bonus.scheme, "none");
  assert.equal(r.courses[2].bonus.maxBonus, 0, "no max_bonus = size not known, as in the config's defaults");
});

check("empty strings from module.toml defaults: paths fall back to the derived ones, empty patterns never match", () => {
  const r = buildRegistry({
    term: { week0_monday: "2026-09-14" },
    paths: { agent_dir: "_sys", inbox: "" },
    calendar: { lecture_prefix: "L:" },
    cockpit: { snapshot_path: "", rules_path: "", prompt_note: "", status_path: "", weeks_folder: "", lecture_pattern: "", deep_pattern: "" },
    courses: [{ id: "x", short: "X", name: "Xylology", detect: "" }],
  });
  assert.equal(r.paths.snapshot, "_sys/cockpit/calendar-snapshot.json");
  assert.equal(r.paths.rules, "_sys/rules.md");
  assert.equal(r.paths.prompt, "_sys/cockpit/assistant-prompt.md");
  assert.equal(r.paths.status, "progress/current-status.md");
  assert.equal(r.paths.weeks, "progress/weeks");
  assert.equal(r.paths.inbox, "inbox");
  assert.ok(!r.notation.lecture.test("V: LA"), "an empty lecture pattern is off ...");
  assert.ok(r.notation.lecture.test("L: LA"), "... but the planning prefix still counts");
  assert.ok(!r.notation.deep.test("AD_ sheet deep"));
  assert.equal(r.courses[0].detect.length, 2, "short name and name; an empty detect adds no pattern");
  assert.deepEqual(r.problems, []);
});

check("modules.enabled: listed modules are on, others off; a file without the list (or an empty one) shows everything", () => {
  const r = registry();
  assert.deepEqual(r.modules, ["core", "courses", "progress", "planning", "check-in", "daily-prep", "inbox-sync", "cockpit"]);
  assert.ok(moduleEnabled("daily-prep"));
  assert.ok(!moduleEnabled("heartbeat"));
  const off = buildRegistry({ term: { week0_monday: "2026-09-14" }, modules: { enabled: ["core", "courses", "progress", "cockpit"] } });
  assert.ok(!moduleEnabled("daily-prep", off));
  assert.ok(!moduleEnabled("inbox-sync", off));
  assert.ok(moduleEnabled("progress", off));
  // schedule.daily_prep keeps its value (it has a framework default); the module list decides what is shown.
  assert.deepEqual(off.schedule.prepRuns, ["17:30", "19:30"]);
  for (const json of [{ term: { week0_monday: "2026-09-14" } }, { modules: {} }, { modules: { enabled: [] } }, null]) {
    const r2 = buildRegistry(json);
    assert.equal(r2.modules, null, JSON.stringify(json));
    assert.ok(moduleEnabled("daily-prep", r2) && moduleEnabled("inbox-sync", r2));
  }
});

finish();
