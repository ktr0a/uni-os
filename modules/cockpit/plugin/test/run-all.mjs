// Runs every bundled test in test/out/ one after the other; exits non-zero if any fails.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const out = path.join(path.dirname(fileURLToPath(import.meta.url)), "out");
const files = fs.readdirSync(out).filter((f) => f.endsWith(".test.cjs")).sort();
const failed = [];
for (const f of files) {
  console.log(`\n=== ${f}`);
  const r = spawnSync(process.execPath, [path.join(out, f)], { stdio: "inherit" });
  if (r.status !== 0) failed.push(f);
}
console.log(failed.length ? `\n${failed.length} of ${files.length} test files failed: ${failed.join(", ")}` : `\nall ${files.length} test files passed`);
process.exit(failed.length ? 1 : 0);
