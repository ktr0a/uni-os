// Glue smoke test: loads the BUILT plugin (../dist/main.js) with a minimal stand-in for the Obsidian API, points
// it at a temporary copy of the week-7 fixture vault, and runs load -> model -> Done tap -> refresh -> Undo.
// It checks the vault glue (data.ts, main.ts, the inbox writes); it renders nothing (no DOM).
//   npm run smoke      (builds first)
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const assert = require("node:assert/strict");
const Module = require("node:module");

// ---------- a stand-in for the "obsidian" module ----------
class TAbstractFile {}
class TFile extends TAbstractFile {
  constructor(root, p) {
    super();
    this.path = p;
    this.name = path.basename(p);
    this.extension = path.extname(p).slice(1);
    this.basename = this.name.replace(/\.[^.]+$/, "");
    this.stat = { mtime: fs.statSync(path.join(root, p)).mtimeMs };
  }
}
class Notice {
  constructor(msg) {
    Notice.log.push(typeof msg === "string" ? msg : "[fragment]");
  }
  hide() {}
}
Notice.log = [];
class Component {
  addChild(c) {
    return c;
  }
  load() {}
  unload() {}
  register() {}
}
class Plugin extends Component {
  constructor(app, manifest) {
    super();
    this.app = app;
    this.manifest = manifest;
    this.data = null;
  }
  async loadData() {
    return this.data;
  }
  async saveData(d) {
    this.data = JSON.parse(JSON.stringify(d));
  }
  registerView() {}
  addSettingTab() {}
  addRibbonIcon() {}
  addCommand() {}
  registerObsidianProtocolHandler() {}
  registerMarkdownCodeBlockProcessor() {}
  registerEvent() {}
  registerInterval(i) {
    clearInterval(i);
    return i;
  }
  registerDomEvent() {}
}
const obsidian = {
  TAbstractFile,
  TFile,
  Notice,
  Component,
  Plugin,
  ItemView: class extends Component {},
  PluginSettingTab: class {},
  Setting: class {},
  SecretComponent: class {},
  Menu: class {},
  MarkdownRenderer: { render() {} },
  debounce: (fn) => fn,
  setIcon() {},
  setTooltip() {},
  normalizePath: (p) => p.split(path.sep).join("/"),
  requestUrl: async () => {
    throw new Error("offline");
  },
};
const load = Module._load;
Module._load = function (request, ...rest) {
  return request === "obsidian" ? obsidian : load.call(this, request, ...rest);
};
global.window = globalThis;
global.document = { visibilityState: "visible" };
global.createFragment = (fn) => {
  const f = { createSpan: () => ({}), createEl: () => ({ addEventListener() {} }) };
  fn(f);
  return f;
};

// ---------- a temporary vault ----------
const fixtures = path.join(__dirname, "fixtures");
const root = fs.mkdtempSync(path.join(os.tmpdir(), "uni-os-cockpit-smoke-"));
fs.cpSync(path.join(fixtures, "nov02"), root, { recursive: true });
fs.copyFileSync(path.join(fixtures, "uni-os.json"), path.join(root, "_agent", "uni-os.json"));

const norm = (p) => p.split(path.sep).join("/");
const walk = (d) => fs.readdirSync(path.join(root, d), { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [norm(path.join(d, e.name))]));
const fm = (text) => {
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  const o = {};
  if (m) for (const l of m[1].split(/\r?\n/)) {
    const kv = /^(\w+):\s*(.*)$/.exec(l);
    if (kv) o[kv[1]] = /^\d+$/.test(kv[2]) ? +kv[2] : kv[2].replace(/^"(.*)"$/, "$1");
  }
  return o;
};
const abs = (p) => path.join(root, p);
const app = {
  vault: {
    on: () => ({}),
    getMarkdownFiles: () => walk("").map((p) => new TFile(root, p)).filter((f) => f.extension === "md"),
    getAbstractFileByPath: (p) => (fs.existsSync(abs(p)) ? (fs.statSync(abs(p)).isFile() ? new TFile(root, p) : {}) : null),
    cachedRead: async (f) => fs.readFileSync(abs(f.path), "utf8"),
    read: async (f) => fs.readFileSync(abs(f.path), "utf8"),
    create: async (p, t) => {
      if (fs.existsSync(abs(p))) throw new Error("exists");
      fs.writeFileSync(abs(p), t);
    },
    createFolder: async (p) => fs.mkdirSync(abs(p), { recursive: true }),
    adapter: {
      exists: async (p) => fs.existsSync(abs(p)),
      read: async (p) => fs.readFileSync(abs(p), "utf8"),
      write: async (p, t) => fs.writeFileSync(abs(p), t),
      list: async (p) => ({ files: fs.readdirSync(abs(p)).map((n) => `${p.replace(/\/$/, "")}/${n}`), folders: [] }),
    },
  },
  metadataCache: {
    on: () => ({}),
    getFileCache: (f) => (f.extension === "md" ? { frontmatter: fm(fs.readFileSync(abs(f.path), "utf8")) } : null),
    getFirstLinkpathDest: () => null,
  },
  workspace: {
    onLayoutReady(cb) {
      this.ready = cb;
    },
    getLeavesOfType: () => [],
    trigger() {},
  },
  secretStorage: { getSecret: () => null },
  loadLocalStorage: () => null,
  saveLocalStorage() {},
};

(async () => {
  const UniOsCockpitPlugin = require("../../dist/main.js").default;
  const plugin = new UniOsCockpitPlugin(app, { id: "uni-os-cockpit" });
  await plugin.onload();
  await app.workspace.ready();
  const m = plugin.model;
  assert.ok(m, "the plugin built a model");
  assert.equal(m.due.length, 15, "the due table of the current week page");
  assert.equal(m.weekPath, "progress/weeks/week-07.md");
  assert.deepEqual(Object.keys(m.bonus), ["algo", "dm", "la", "prog"]);
  assert.deepEqual(
    plugin.settings.feeds.map((f) => f.id),
    ["courses", "study_blocks", "events", "busy"],
  );
  console.log(`ok   loaded: week ${m.week}, ${m.due.length} due rows, ${m.events.length} events, ${m.warnings.length} warnings`);

  const row = m.due.find((d) => /LA hand-in 6/.test(d.item));
  plugin.markDone(row);
  await plugin.writeTap(row.item.toLowerCase().replace(/\s+/g, " "));
  let inbox = fs.readdirSync(abs("inbox"));
  assert.equal(inbox.length, 1);
  assert.match(inbox[0], /_cockpit-done-la-hand-in-6-a6-out-wed-28-oct-update\.md$/);
  assert.match(fs.readFileSync(abs(`inbox/${inbox[0]}`), "utf8"), /Done tap by Alex Example/);
  console.log(`ok   Done tap wrote ${inbox[0]}`);

  await plugin.refreshNow();
  const tapped = plugin.model.due.find((d) => /LA hand-in 6/.test(d.item));
  assert.ok(tapped.tapped && tapped.tapWaiting, "the waiting note, read from disk, marks the row");
  console.log("ok   after a refresh the row reads as tapped (note read from disk)");

  await plugin.markUndone(tapped);
  inbox = fs.readdirSync(abs("inbox"));
  assert.equal(inbox.length, 2);
  await plugin.refreshNow();
  assert.equal(plugin.model.due.find((d) => /LA hand-in 6/.test(d.item)).tapped, false);
  console.log("ok   Undo wrote a second note and reopened the row");

  // `uni-os disable daily-prep` rewrites modules.enabled: the prep card and its warnings go, schedule.daily_prep stays.
  assert.ok(plugin.model.prep, "daily-prep on: the model has a prep state");
  const cfg = JSON.parse(fs.readFileSync(abs("_agent/uni-os.json"), "utf8"));
  cfg.modules.enabled = cfg.modules.enabled.filter((id) => id !== "daily-prep");
  fs.writeFileSync(abs("_agent/uni-os.json"), JSON.stringify(cfg));
  await plugin.loadRegistry();
  await plugin.refreshNow();
  assert.equal(plugin.model.prep, null, "daily-prep off: no prep state");
  assert.ok(!plugin.model.warnings.some((w) => /prep/i.test(w)), plugin.model.warnings.join(" | "));
  const n = plugin.model.warnings.length;
  console.log(`ok   daily-prep disabled: no prep card, ${n} warning${n === 1 ? "" : "s"}, none about prep`);

  fs.rmSync(root, { recursive: true, force: true });
  console.log("\nsmoke test passed");
  process.exit(0);
})().catch((err) => {
  console.error("SMOKE TEST FAILED\n", err);
  process.exit(1);
});
