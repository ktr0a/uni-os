// The bonus rule engine: every scheme, on invented numbers. `npm test`
import assert from "node:assert/strict";
import { bonusFigure, bonusFor, bonusText, ruleText, sittings } from "../src/bonus";
import { zdate } from "../src/model";
import { buildRegistry, courseById, setRegistry } from "../src/registry";
import { check, finish, useFixtureRegistry } from "./helpers";

useFixtureRegistry();
const MON = zdate(2026, 11, 2, 20, 0);
const close = (a: number | null, b: number) => assert.ok(a !== null && Math.abs(a - b) < 1e-9, `${a} vs ${b}`);

check("threshold with the card's estimate: 80 % of ~120, proportional below", () => {
  const b = bonusFor(courseById("algo")!, { bonus_banked: "40 / 50 graded (80 %)", bonus_target: "80 % of ~120 pts (est.)" }, MON);
  assert.equal(b.big, "40");
  assert.equal(b.of, "/ 50 graded");
  assert.equal(b.ofShort, "/ 50");
  close(b.bonusNow, (0.25 * 40) / 96);
  assert.deepEqual(b.meter, { value: 40, max: 120, marker: 96, ghost: 50 });
  assert.equal(b.headline, "80 % of graded points (full bonus needs 80 %)");
  assert.match(b.detail, /^About 56 more of the ~70 points still to come \(80 %\) for the full \+0\.25\. The total ~120 is an estimate, not official\.$/);
  assert.equal(b.tone, "good");
});
check("threshold: a plugin override beats the card; the config total is the last resort; without any total the share of what's graded", () => {
  const c = courseById("algo")!;
  assert.equal(bonusFor(c, { bonus_banked: "40 / 50", bonus_target: "80 % of ~120 pts" }, MON, 100).meter!.max, 100);
  const noTotal = bonusFor(c, { bonus_banked: "30 / 50", bonus_target: "80 % of all points" }, MON);
  assert.deepEqual(noTotal.meter, { value: 30, max: 50, marker: 40 });
  assert.equal(noTotal.bonusNow, null);
  assert.equal(noTotal.tone, "warn");
  assert.match(noTotal.detail, /Total not published/);
});
check("threshold, all or nothing, with a published total", () => {
  setRegistry(buildRegistry({ term: { week0_monday: "2026-09-14" }, courses: [{ id: "x", bonus: { scheme: "threshold", threshold: 0.6, total: 100, proportional: false, max_bonus: "5%" } }] }));
  const c = courseById("x")!;
  const below = bonusFor(c, { bonus_banked: "50 / 70" }, MON);
  assert.equal(below.bonusNow, 0);
  assert.match(below.detail, /Total: 100 points\./);
  const above = bonusFor(c, { bonus_banked: "65 / 70" }, MON);
  assert.equal(above.bonusNow, 5);
  assert.equal(bonusText(5, c.bonus), "+5 %");
  assert.equal(bonusFigure(2.5, c.bonus), "+2.5 %");
  assert.match(above.detail, /^Enough for the full \+5 %/);
  useFixtureRegistry();
});
check("points with slack: 5 of 7 quiz points, quizzes left from the dates (timed: over once started)", () => {
  const c = courseById("la")!;
  const b = bonusFor(c, { bonus_banked: "2 / 7" }, MON);
  assert.equal(b.of, "/ 7 quiz points");
  close(b.bonusNow, 0.1);
  assert.equal(b.headline, "3 more from the 4 quizzes left");
  assert.equal(b.detail, "That is 0.75 per quiz on average. 5 of 7 quiz points give the full +0.25.");
  assert.equal(b.tone, "good");
  assert.deepEqual(b.meter, { value: 2, max: 7, marker: 5 });
  assert.equal(sittings(c, zdate(2026, 11, 5, 16, 14)).left, 4);
  assert.equal(sittings(c, zdate(2026, 11, 5, 16, 15)).left, 3);
  assert.equal(bonusFor(c, { bonus_banked: "1 / 7" }, MON).tone, "warn", "4 from 4 quizzes is 1 per quiz: too tight");
  const full = bonusFor(c, { bonus_banked: "5.5 / 7" }, MON);
  assert.equal(full.headline, "Full bonus reached");
  assert.equal(full.bonusNow, 0.25);
});
check("points without slack: linear 0.25 x B / 12, sittings left, solo note from the assessment", () => {
  const c = courseById("dm")!;
  const b = bonusFor(c, { bonus_banked: "4 / 12" }, MON);
  close(b.bonusNow, 0.25 * 4 / 12);
  assert.equal(b.headline, "1 oral left, no slack: every point counts");
  assert.equal(b.detail, "Linear: bonus = 0.25 × points / 12, no threshold. Solo work, no AI help: Oral bonus.");
  assert.deepEqual(b.meter, { value: 4, max: 12, marker: 12 });
  assert.equal(b.tone, "warn");
  // A date-only sitting counts as left for the whole day.
  assert.equal(sittings(c, zdate(2026, 11, 26, 18, 0)).left, 1);
  assert.equal(sittings(c, zdate(2026, 11, 27, 0, 1)).left, 0);
  assert.equal(bonusFor(c, { bonus_banked: "7 / 12" }, zdate(2026, 11, 27, 9)).headline, "All orals done");
});
check("best-n: 8 of 10 sheets must pass, admission style", () => {
  setRegistry(
    buildRegistry({
      term: { week0_monday: "2026-09-14" },
      courses: [{ id: "s", assessments: [{ name: "Sheets", kind: "sheet", dates: ["2026-11-09", "2026-11-16", "2026-11-23", "2026-11-30"] }], bonus: { scheme: "best-n", total: 10, required: 8, proportional: false, max_bonus: 0.25 } }],
    }),
  );
  const c = courseById("s")!;
  const b = bonusFor(c, { bonus_banked: "5 / 6 passed" }, MON);
  assert.equal(b.headline, "3 more passed sheets needed (4 left)");
  assert.equal(b.bonusNow, 0);
  assert.equal(b.tone, "warn", "only one spare sitting");
  assert.deepEqual(b.meter, { value: 5, max: 10, marker: 8, ghost: 6 });
  assert.equal(bonusFor(c, { bonus_banked: "8 / 9" }, MON).headline, "Requirement met");
  assert.equal(ruleText(c), "8 of 10 must be passed");
  useFixtureRegistry();
});
check("custom and none", () => {
  setRegistry(
    buildRegistry({
      term: { week0_monday: "2026-09-14" },
      courses: [
        { id: "c", bonus: { scheme: "custom", description: "Best 3 labs average, see the card", rule: "computed by the agents" } },
        { id: "n", bonus: { scheme: "none" } },
      ],
    }),
  );
  const c = bonusFor(courseById("c")!, { bonus_banked: "2 / 4 labs" }, MON);
  assert.equal(c.headline, "Best 3 labs average, see the card");
  assert.equal(c.bonusNow, null);
  assert.deepEqual(c.meter, { value: 2, max: 4 });
  assert.equal(c.tone, "unknown");
  const n = bonusFor(courseById("n")!, { bonus_banked: "1 / 2" }, MON);
  assert.equal(n.headline, "No bonus in this course");
  assert.equal(n.meter, null);
  useFixtureRegistry();
});
check("max_bonus = 0 (not known): shares and headlines, but no bonus figure", () => {
  setRegistry(buildRegistry({ term: { week0_monday: "2026-09-14" }, courses: [{ id: "u", bonus: { scheme: "threshold", max_bonus: 0, threshold: 0.8 } }] }));
  const b = bonusFor(courseById("u")!, { bonus_banked: "40 / 50", bonus_target: "~120 pts" }, MON);
  assert.equal(b.bonusNow, null);
  assert.match(b.detail, /for the full bonus\./);
  assert.deepEqual(b.meter, { value: 40, max: 120, marker: 96, ghost: 50 });
  useFixtureRegistry();
});
check("no numbers on the card yet", () => {
  const b = bonusFor(courseById("prog")!, { bonus_target: "80 % of all bonus points" }, MON);
  assert.equal(b.headline, "No bonus data on the course card");
  assert.equal(b.big, "—");
  assert.equal(b.meter, null);
});
check("a fresh card ('0 / 0 graded', as the courses module writes it) never reads as 'full bonus reached'", () => {
  setRegistry(
    buildRegistry({
      term: { week0_monday: "2026-09-14" },
      courses: [
        { id: "t", bonus: { scheme: "threshold", max_bonus: 0.25 } },
        { id: "p", bonus: { scheme: "points", max_bonus: 0.25 } },
        { id: "q", bonus: { scheme: "points", max_bonus: 0.25, full_at: 8 } },
        { id: "b", bonus: { scheme: "best-n", max_bonus: 0.25 } },
      ],
    }),
  );
  const fresh = { bonus_banked: "0 / 0 graded", bonus_target: "not known yet" };
  const t = bonusFor(courseById("t")!, fresh, MON);
  assert.equal(t.headline, "Nothing graded yet (full bonus needs 80 %)");
  assert.equal(t.tone, "unknown");
  for (const id of ["p", "b"]) {
    const x = bonusFor(courseById(id)!, fresh, MON);
    assert.equal(x.headline, "Nothing graded yet", id);
    assert.equal(x.tone, "unknown", id);
    assert.equal(x.bonusNow, null, id);
    assert.match(x.detail, /under \[courses\.bonus\] in uni-os\.toml/, id);
  }
  const q = bonusFor(courseById("q")!, fresh, MON);
  assert.equal(q.headline, "Linear, no slack: every point counts", "full_at alone is enough: linear up to 8");
  assert.equal(q.of, "/ 8 points");
  assert.equal(q.bonusNow, 0);
  const later = bonusFor(courseById("p")!, { bonus_banked: "3 / 12" }, MON);
  close(later.bonusNow, (0.25 * 3) / 12);
  useFixtureRegistry();
});
check("generated rule texts", () => {
  assert.equal(ruleText(courseById("algo")!), "full +0.25 at 80 % of all points, proportionally less below; total not published");
  assert.equal(ruleText(courseById("la")!), "5 of 7 quiz points give the full +0.25");
  assert.equal(ruleText(courseById("dm")!), "0.25 × points / 12, linear, no threshold");
});

finish();
