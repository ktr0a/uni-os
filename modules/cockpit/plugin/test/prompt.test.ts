// The assistant's prompt: template note extraction, placeholders, integrity lines from the config; settings merge. `npm test`
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import { DEFAULT_PROMPT, fillPrompt, integrityLines, templateFromNote } from "../src/prompt";
import { courses, registry } from "../src/registry";
import { DEFAULT_SECTIONS, defaultContextNotes, defaultSettings, mergeSettings } from "../src/settings";
import { check, finish, useFixtureRegistry } from "./helpers";

useFixtureRegistry();

check("integrity lines: one per course, plus assessments whose level differs", () => {
  const lines = integrityLines(courses()).split("\n");
  assert.equal(lines[0], "- AD: hints only, the smallest hint first; never a full solution or finished code.");
  assert.ok(lines.includes("- AD Programming sheets: coach only (technique, checking the student's own steps or code); never finished solutions or code."));
  assert.ok(lines.includes("- DM Oral bonus: solo work: no help at all (don't solve, hint at, explain or check it)."));
  assert.ok(lines.includes("- PROG: coach only (technique, checking the student's own steps or code); never finished solutions or code."));
});

check("the default prompt is filled from the config, with no placeholder left", () => {
  const p = fillPrompt(DEFAULT_PROMPT, registry());
  assert.match(p, /^You are the study assistant inside Alex Example's Obsidian vault for EIT Autumn 2026 \(BSc Computer Science\): AD, DM, LA, PROG\./);
  assert.match(p, /Follow the rules in _agent\/rules\.md exactly/);
  assert.match(p, /Answer in English\./);
  assert.doesNotMatch(p, /\{[a-z_]+\}/);
});

check("template from a note: the fenced block under 'System prompt'; unknown placeholders stay", () => {
  const note = "---\ntype: agent\n---\n# Assistant prompt\n\nIntro text.\n\n## System prompt\n\n```text\nHi {student}. {unknown} stays.\n```\n\n## Notes\nnot part of it\n";
  assert.equal(templateFromNote(note), "Hi {student}. {unknown} stays.");
  assert.equal(fillPrompt(templateFromNote(note)!, registry()), "Hi Alex Example. {unknown} stays.");
  assert.equal(templateFromNote("## System prompt\nPlain text prompt for {student}.\n## Other\nx"), "Plain text prompt for {student}.");
  assert.equal(templateFromNote("# Nothing here"), null);
  assert.equal(templateFromNote(null), null);
});

check("the shipped prompt note parses to a template with every placeholder known", () => {
  const p = path.resolve(__dirname, "../../../vault/_agent/cockpit/assistant-prompt.md");
  const t = templateFromNote(fs.readFileSync(p, "utf8"));
  assert.ok(t, "a template");
  assert.doesNotMatch(fillPrompt(t!, registry()), /\{[a-z_]+\}/);
});

check("settings: first-run defaults from [cockpit], feeds from [calendar], forward-compatible merge", () => {
  const d = defaultSettings(registry());
  assert.equal(d.prepSwitchHour, 18);
  assert.deepEqual(d.feeds.map((f) => `${f.id}:${f.role}:${f.label}`), ["courses:classes:Courses", "study_blocks:study:Study blocks", "events:personal:Events", "busy:personal:Busy"]);
  const merged = mergeSettings({ layout: "agenda", sections: [{ id: "due", on: true }], feeds: [{ id: "mine", label: "Mine", role: "study", secret: "s", on: true }] }, registry());
  assert.equal(merged.layout, "agenda");
  assert.equal(merged.sections.length, DEFAULT_SECTIONS.length, "new sections slot in");
  assert.equal(merged.feeds.length, 1, "a saved feed list is kept as it is");
  assert.equal(merged.contextNotes, null);
  assert.deepEqual(defaultContextNotes(registry()).slice(0, 3), ["progress/current-status.md", "courses-overview.md", "AD/ad.md"]);
});

finish();
