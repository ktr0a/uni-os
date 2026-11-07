// Builds the plugin.
//   node esbuild.config.mjs              -> ../dist/ and ../vault/.obsidian/plugins/uni-os-cockpit/
//                                           (main.js, manifest.json, styles.css; both copies are committed so
//                                           students without Node can install, and `uni-os init` copies the vault one)
//   node esbuild.config.mjs --out "<dir>" -> also into <dir>, e.g. "<your vault>/.obsidian/plugins/uni-os-cockpit"
//   node esbuild.config.mjs --test       -> test/out/*.test.cjs (pure parsers, run with node; see test/run-all.mjs)
// Never run `npm install` inside a synced vault folder (Google Drive, OneDrive, ...): node_modules would sync.
import esbuild from "esbuild";
import builtins from "builtin-modules";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

if (process.argv.includes("--test")) {
  const testDir = path.join(here, "test");
  const entryPoints = fs
    .readdirSync(testDir)
    .filter((f) => f.endsWith(".test.ts"))
    .map((f) => path.join(testDir, f));
  await esbuild.build({
    entryPoints,
    bundle: true,
    platform: "node",
    format: "cjs",
    target: "node20",
    outdir: path.join(testDir, "out"),
    outExtension: { ".js": ".cjs" },
    logLevel: "warning",
  });
} else {
  const outDirs = [path.resolve(here, "../dist"), path.resolve(here, "../vault/.obsidian/plugins/uni-os-cockpit")];
  const extra = process.argv.indexOf("--out");
  if (extra !== -1 && process.argv[extra + 1]) outDirs.push(path.resolve(process.argv[extra + 1]));
  const primary = outDirs[0];
  fs.mkdirSync(primary, { recursive: true });
  await esbuild.build({
    entryPoints: [path.join(here, "src/main.ts")],
    bundle: true,
    external: ["obsidian", "electron", "@codemirror/*", "@lezer/*", ...builtins],
    format: "cjs",
    platform: "browser",
    target: "es2022",
    treeShaking: true,
    minify: true,
    sourcemap: false,
    logLevel: "warning",
    legalComments: "none",
    outfile: path.join(primary, "main.js"),
  });
  fs.copyFileSync(path.join(here, "manifest.json"), path.join(primary, "manifest.json"));
  fs.copyFileSync(path.join(here, "styles.css"), path.join(primary, "styles.css"));
  for (const dir of outDirs.slice(1)) {
    fs.mkdirSync(dir, { recursive: true });
    for (const f of ["main.js", "manifest.json", "styles.css"]) fs.copyFileSync(path.join(primary, f), path.join(dir, f));
  }
  const kb = (f) => (fs.statSync(path.join(primary, f)).size / 1024).toFixed(0) + " KB";
  console.log(`built main.js ${kb("main.js")}, styles.css ${kb("styles.css")} into:\n  ${outDirs.join("\n  ")}`);
}
