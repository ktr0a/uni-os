// The assistant panel's system prompt: a template from a vault note (_agent/cockpit/assistant-prompt.md by
// default), with placeholders filled from the registry at run time. Pure, so it is tested like the parsers.
//
// Placeholders (single braces, so the Uni OS template renderer leaves them alone at install time):
//   {student} {university} {programme} {term} {courses} {rules_path} {integrity} {language} {reply_rules}

import { section, stripFrontmatter } from "./md";
import { CourseInfo, Registry } from "./registry";

export const DEFAULT_PROMPT = [
  "You are the study assistant inside {student}'s Obsidian vault for {university} {term} ({programme}): {courses}.",
  "Answer from the vault notes below and the calendar in the user's message. Name the note a fact comes from (its path). If the notes don't say, say so plainly instead of guessing; mark estimates as estimates.",
  "Follow the rules in {rules_path} exactly, above all the integrity rules:",
  "{integrity}",
  "Say why when you decline.",
  "You can't change files or the calendar. When something should change, say exactly what and where (note path and section, or calendar block), so the student can apply it or hand it to the planning agent.",
  "Answer in {language}. Short and conversational, lead with the answer. Maths in $...$ or $$...$$ (Obsidian renders it).",
].join("\n");

/**
 * The template from the prompt note: the first fenced block under a "System prompt" heading, else the whole
 * section under that heading, else the first fenced block of the note, else null (then DEFAULT_PROMPT is used).
 */
export function templateFromNote(text: string | null): string | null {
  if (!text) return null;
  const body = stripFrontmatter(text).replace(/\r\n/g, "\n");
  const scope = section(body, /^system prompt\b/i);
  const fence = /^(```+|~~~+)[^\n]*\n([\s\S]*?)\n\1[ \t]*$/m.exec(scope ?? body);
  if (fence) return fence[2].trim() || null;
  return scope?.trim() || null;
}

const LEVEL: Record<string, string> = {
  solo: "solo work: no help at all (don't solve, hint at, explain or check it)",
  "hints-only": "hints only, the smallest hint first; never a full solution or finished code",
  coach: "coach only (technique, checking the student's own steps or code); never finished solutions or code",
  full: "full help is allowed",
};

function level(a: string): string {
  return LEVEL[a] ?? LEVEL["hints-only"];
}

/** One line per course (and per assessment whose level differs from its course's), from the config. */
export function integrityLines(courses: CourseInfo[]): string {
  const lines: string[] = [];
  for (const c of courses) {
    lines.push(`- ${c.short}: ${level(c.assistance)}.`);
    for (const a of c.assessments) {
      if (a.assistance && a.assistance !== c.assistance) lines.push(`- ${c.short} ${a.name}: ${level(a.assistance)}.`);
    }
  }
  return lines.length ? lines.join("\n") : "- Graded work: hints only, never full solutions.";
}

export function fillPrompt(template: string, reg: Registry, rulesPath = reg.paths.rules): string {
  const student = reg.student.name || reg.student.handle || "the student";
  const values: Record<string, string> = {
    student,
    university: reg.university.short || reg.university.name || "university",
    programme: reg.university.programme || "studies",
    term: reg.term.label || "this term",
    courses: reg.courses.map((c) => c.short).join(", ") || "no courses configured yet",
    rules_path: rulesPath,
    integrity: integrityLines(reg.courses),
    language: reg.student.language || "English",
    reply_rules: reg.replyRules.length ? reg.replyRules.map((r) => `- ${r}`).join("\n") : "",
  };
  return template.replace(/\{([a-z_]+)\}/g, (m, key: string) => (key in values ? values[key] : m)).replace(/\n{3,}/g, "\n\n").trim();
}
