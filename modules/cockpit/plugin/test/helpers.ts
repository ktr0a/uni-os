// Shared test helpers: a tiny check() runner, the synthetic fixtures (Alex Example, see test/fixtures/*/README.md)
// and the registry built from test/fixtures/uni-os.json. Tests are bundled to test/out/, so fixtures are one level up.
import fs from "node:fs";
import path from "node:path";
import { frontmatter } from "../src/md";
import { RawInput } from "../src/parse";
import { buildRegistry, courses, setRegistry } from "../src/registry";

export const FIXTURES = path.resolve(__dirname, "../fixtures");

export function readFixture(p: string): string {
  return fs.readFileSync(path.join(FIXTURES, p), "utf8");
}

export function fixtureJson(): Record<string, unknown> {
  return JSON.parse(readFixture("uni-os.json"));
}

/** Loads the fixture registry (Alex Example's four example courses) as the active one. */
export function useFixtureRegistry(patch?: (j: Record<string, any>) => void): void {
  const j = fixtureJson() as Record<string, any>;
  patch?.(j);
  setRegistry(buildRegistry(j, "test/fixtures/uni-os.json"));
}

/** The course cards of a fixture vault, keyed by course id, at the paths the registry gives them. */
export function courseCards(vault: string): RawInput["courses"] {
  const out: RawInput["courses"] = {};
  for (const c of courses()) {
    const p = path.join(vault, c.card);
    if (!fs.existsSync(path.join(FIXTURES, p))) continue;
    const text = readFixture(p);
    out[c.id] = { path: c.card, text, fm: frontmatter(text) };
  }
  return out;
}

let failures = 0;
let passes = 0;
export function check(name: string, fn: () => void): void {
  try {
    fn();
    passes++;
    console.log(`ok   ${name}`);
  } catch (e) {
    failures++;
    console.log(`FAIL ${name}\n     ${(e as Error).message.split("\n").join("\n     ")}`);
  }
}

export function finish(): void {
  console.log(failures ? `\n${failures} failing, ${passes} passing` : `\nall ${passes} passing`);
  process.exit(failures ? 1 : 0);
}
