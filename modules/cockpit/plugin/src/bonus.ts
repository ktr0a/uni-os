// The bonus / coursework rule engine. The original cockpit had one bespoke formula per course; here a small set
// of schemes, configured per course in uni-os.toml ([courses.bonus]), covers the same cases:
//
//   threshold  full bonus at a share of all points (e.g. 80 %), proportionally less below (or all or nothing).
//              The total is the course card's "~N pts" estimate in bonus_target, a plugin override, or bonus.total.
//   points     linear in points up to full_at (e.g. "5 of 7 quiz points give the full bonus"); full_at = total
//              means no slack ("0.25 x B / 12"). Dated assessments say how many sittings are left.
//   best-n     k of n assessments must be passed (admission-style); proportional below if configured.
//   custom     no maths: the card's numbers and the rule text, computed by your agents.
//   none       the course has no bonus.
//
// The banked numbers always come from the course card's properties (bonus_banked "x / y ...", bonus_target,
// next_bonus), which the progress agents keep current. Pure: no Obsidian imports.

import { firstNumberPair, num, plain } from "./md";
import { parseStamp } from "./model";
import type { BonusRule, CourseInfo } from "./registry";

export interface Meter {
  value: number;
  max: number;
  marker?: number;
  ghost?: number;
}

export interface BonusInfo {
  course: string;
  scheme: BonusRule["scheme"];
  banked: string;
  target: string;
  next: string;
  /** Bonus implied by what is banked, if computable (grade units, or percent with maxIsPercent). */
  bonusNow: number | null;
  big: string;
  of: string;
  /** `of` without its unit word, for the compact figure ("40 / 50"). */
  ofShort: string;
  headline: string;
  detail: string;
  /** How the bonus is computed, shown next to every number. */
  rule: string;
  tone: "good" | "warn" | "unknown";
  meter: Meter | null;
}

/** "+0.25" or "+10 %": the size of a bonus in the course's unit. */
export function bonusText(value: number, rule: BonusRule): string {
  if (rule.maxIsPercent) return `+${num(value, 1)} %`;
  return `+${rule.maxBonus < 1 ? value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "") : num(value, 2)}`;
}

/** The figure in the course's unit with fixed decimals, for tiles: "+0.125". */
export function bonusFigure(value: number, rule: BonusRule): string {
  return rule.maxIsPercent ? `+${value.toFixed(1)} %` : `+${value.toFixed(rule.maxBonus < 1 ? 3 : 2)}`;
}

function plural(word: string, n: number): string {
  if (n === 1) return word;
  if (/(s|x|ch|sh)$/.test(word)) return word + "es";
  if (/z$/.test(word)) return word + "zes";
  if (/[^aeiou]y$/.test(word)) return word.slice(0, -1) + "ies";
  return word + "s";
}

/** The assessments whose dates count as "left" for this course's bonus. */
function counted(c: CourseInfo) {
  const r = c.bonus;
  if (r.counts.length) return c.assessments.filter((a) => r.counts.includes(a.name));
  const bonus = c.assessments.filter((a) => a.countsFor === "bonus");
  return bonus.length ? bonus : c.assessments;
}

/** How many dated sittings are still ahead (null when no dates are configured), and what they are called. */
export function sittings(c: CourseInfo, now: Date): { left: number | null; count: number; label: string; solo: string[] } {
  const as = counted(c);
  const dates = as.flatMap((a) => a.dates);
  const kinds = [...new Set(as.map((a) => (a.kind && a.kind !== "other" ? a.kind : a.name.toLowerCase())))];
  const label = kinds.length === 1 ? kinds[0] : "assessment";
  let left: number | null = null;
  if (dates.length) {
    left = 0;
    for (const d of dates) {
      const s = parseStamp(d);
      if (!s) continue;
      // A date-only sitting (read as 23:59) is still ahead all of that day; a timed one until it starts.
      if (s.date.getTime() > now.getTime()) left++;
    }
  }
  return { left, count: dates.length, label, solo: as.filter((a) => (a.assistance || c.assistance) === "solo").map((a) => a.name) };
}

/** The rule shown next to the numbers: the config's text, or one generated from the scheme. */
export function ruleText(c: CourseInfo): string {
  const r = c.bonus;
  if (r.rule) return r.rule;
  if (r.description) return r.description;
  const max = bonusText(r.maxBonus, r);
  switch (r.scheme) {
    case "threshold":
      return `full ${max} at ${Math.round(r.threshold * 100)} % of all points${r.proportional ? ", proportionally less below" : ", nothing below"}${r.total ? `; total ${num(r.total)}${r.totalEstimated ? " (estimate)" : ""}` : "; total not published"}`;
    case "points": {
      if (!r.total) return `linear in ${r.unit}`;
      const fullAt = r.fullAt || r.total;
      return fullAt < r.total ? `${num(fullAt)} of ${num(r.total)} ${r.unit} give the full ${max}` : `${num(r.maxBonus)} × points / ${num(r.total)}, linear, no threshold`;
    }
    case "best-n":
      return `${r.required || "?"} of ${r.total || "?"} must be passed`;
    case "none":
      return "no bonus in this course";
    default:
      return "custom rule (see the course card)";
  }
}

/**
 * The bonus standing of one course from its card's properties. `override` replaces the total of a threshold
 * course (the plugin setting for an unpublished maximum).
 */
export function bonusFor(c: CourseInfo, fm: Record<string, unknown> | undefined, now: Date, override?: number): BonusInfo {
  const r = c.bonus;
  const banked = String(fm?.bonus_banked ?? "");
  const target = String(fm?.bonus_target ?? "");
  const next = String(fm?.next_bonus ?? "");
  // max_bonus = 0 means "not known": the shares are still shown, the bonus itself is not computed.
  const hasMax = r.maxBonus > 0;
  const maxText = hasMax ? bonusText(r.maxBonus, r) : "bonus";
  const capped = (v: number) => (hasMax ? v : null);
  const base: BonusInfo = {
    course: c.id,
    scheme: r.scheme,
    banked,
    target,
    next,
    bonusNow: null,
    big: banked ? plain(banked) : "—",
    of: "",
    ofShort: "",
    headline: "No bonus data on the course card",
    detail: r.description,
    rule: ruleText(c),
    tone: "unknown",
    meter: null,
  };
  if (r.scheme === "none") return { ...base, big: "—", headline: "No bonus in this course", detail: "" };
  const pair = firstNumberPair(banked);
  if (!pair) return base;
  const { a, b } = pair;

  if (r.scheme === "threshold") {
    const est = /(~)?\s*(\d+(?:\.\d+)?)\s*(?:pts|points)\b/i.exec(plain(target));
    let total = 0;
    let estimated = false;
    if (override && override > 0) {
      total = override;
      estimated = true;
    } else if (est) {
      total = parseFloat(est[2]);
      estimated = !!est[1] || /est/i.test(target);
    } else if (r.total > 0) {
      total = r.total;
      estimated = r.totalEstimated;
    }
    const thrPct = Math.round(r.threshold * 100);
    const pct = b > 0 ? (a / b) * 100 : 0;
    // A fresh card ("0 / 0 graded"): no share yet, and nothing to warn about.
    const headline = b > 0 ? `${Math.round(pct)} % of graded points (full bonus needs ${thrPct} %)` : `Nothing graded yet (full bonus needs ${thrPct} %)`;
    const tone = b <= 0 ? "unknown" : pct >= r.threshold * 100 ? "good" : "warn";
    if (total > 0) {
      const fullAt = r.threshold * total;
      const stillAvailable = Math.max(0, total - b);
      const needed = Math.max(0, fullAt - a);
      const share = stillAvailable > 0 ? (needed / stillAvailable) * 100 : 0;
      const totalNote = estimated ? `The total ~${num(total)} is an estimate, not official.` : `Total: ${num(total)} points.`;
      return {
        ...base,
        bonusNow: capped(r.proportional ? Math.min(r.maxBonus, (r.maxBonus * a) / fullAt) : a >= fullAt ? r.maxBonus : 0),
        big: num(a),
        of: `/ ${num(b)} graded`,
        ofShort: `/ ${num(b)}`,
        headline,
        detail: needed > 0 ? `About ${Math.round(needed)} more of the ~${Math.round(stillAvailable)} points still to come (${Math.round(share)} %) for the full ${maxText}. ${totalNote}` : `Enough for the full ${maxText} already. ${totalNote}`,
        tone,
        meter: { value: a, max: total, marker: fullAt, ghost: b },
      };
    }
    return {
      ...base,
      big: num(a),
      of: `/ ${num(b)} graded`,
      ofShort: `/ ${num(b)}`,
      headline,
      detail: `Total not published, so this is the share of what's graded so far. Full ${maxText} at ${thrPct} % of all points${r.proportional ? ", proportionally less below" : ""}.`,
      tone,
      meter: { value: a, max: b, marker: r.threshold * b },
    };
  }

  // Neither the config nor the card says how many points or passes are needed (a fresh "0 / 0 graded" card and
  // no total / full_at / required): show what is banked, never "full bonus reached".
  const notKnown = (what: string): BonusInfo => ({
    ...base,
    big: num(a),
    of: `/ ${num(b)}`,
    ofShort: `/ ${num(b)}`,
    headline: a === 0 && b === 0 ? "Nothing graded yet" : `${num(a)} banked`,
    detail: `Set ${what} under [courses.bonus] in uni-os.toml (or keep "x / total" on the course card) to see what is still needed.`,
    tone: "unknown",
    meter: b > 0 ? { value: a, max: b } : null,
  });

  if (r.scheme === "points") {
    // The card's "x / y" is banked / total for points courses, unless the config publishes the total.
    const fullAt = r.fullAt > 0 ? r.fullAt : r.total > 0 ? r.total : b;
    if (fullAt <= 0) return notKnown("total (and full_at)");
    const total = Math.max(r.total > 0 ? r.total : b, fullAt);
    const need = Math.max(0, fullAt - a);
    const ev = sittings(c, now);
    const unit = r.unit;
    const solo = ev.solo.length ? ` Solo work, no AI help: ${ev.solo.join(", ")}.` : "";
    const common = { ...base, bonusNow: fullAt > 0 ? capped(Math.min(r.maxBonus, (r.maxBonus * a) / fullAt)) : null, big: num(a), of: `/ ${num(total)} ${unit}`, ofShort: `/ ${num(total)}` };
    if (fullAt < total) {
      const perSitting = ev.count > 0 ? total / ev.count : null;
      const headline = need === 0 ? "Full bonus reached" : ev.left !== null ? `${num(need)} more from the ${ev.left} ${plural(ev.label, ev.left)} left` : `${num(need)} more ${unit} needed`;
      const rule = `${num(fullAt)} of ${num(total)} ${unit} give the full ${maxText}.`;
      const detail = need === 0 || !ev.left ? rule : `That is ${num(need / ev.left, 2)} per ${ev.label} on average. ${rule}`;
      const good = need === 0 || (!!ev.left && perSitting !== null && need / ev.left <= 0.75 * perSitting);
      return { ...common, headline, detail: detail + solo, tone: good ? "good" : "warn", meter: { value: a, max: total, marker: fullAt } };
    }
    const headline =
      need === 0
        ? "Full bonus reached"
        : ev.left === null
          ? "Linear, no slack: every point counts"
          : ev.left > 0
            ? `${ev.left} ${plural(ev.label, ev.left)} left, no slack: every point counts`
            : `All ${plural(ev.label, 2)} done`;
    return {
      ...common,
      headline,
      detail: `Linear: bonus = ${hasMax ? num(r.maxBonus) : "max"} × points / ${num(total)}, no threshold.${solo}`,
      tone: need === 0 ? "good" : "warn",
      meter: { value: a, max: total, marker: total },
    };
  }

  if (r.scheme === "best-n") {
    const ev = sittings(c, now);
    const required = r.required > 0 ? r.required : r.total > 0 ? r.total : ev.count || b;
    if (required <= 0) return notKnown("total and required");
    const nTotal = Math.max(r.total > 0 ? r.total : ev.count || b, required);
    const need = Math.max(0, required - a);
    const headline = need === 0 ? "Requirement met" : `${num(need)} more passed ${plural(ev.label, need)} needed${ev.left !== null ? ` (${ev.left} left)` : ""}`;
    const good = need === 0 || (ev.left !== null && ev.left - need >= 2);
    return {
      ...base,
      bonusNow: capped(a >= required ? r.maxBonus : r.proportional && required > 0 ? (r.maxBonus * a) / required : 0),
      big: num(a),
      of: `/ ${num(b)} passed`,
      ofShort: `/ ${num(b)}`,
      headline,
      detail: `${num(required)} of ${num(nTotal)} ${plural(ev.label, nTotal)} must be passed${r.proportional ? "; below that a proportional share" : ""}.`,
      tone: good ? "good" : "warn",
      meter: { value: a, max: nTotal, marker: required, ghost: b },
    };
  }

  // custom (or an unknown scheme name): the numbers as the card writes them.
  return {
    ...base,
    big: num(a),
    of: `/ ${num(b)}`,
    ofShort: `/ ${num(b)}`,
    headline: r.description || "Custom rule: see the course card",
    detail: r.rule,
    meter: { value: a, max: b },
  };
}
