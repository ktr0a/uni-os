// Reads the notes the cockpit needs from the vault and hands them to the pure parser. Every path comes from the
// registry (_agent/uni-os.json), so a vault laid out differently only needs different config values.

import { App, TFile } from "obsidian";
import { otherUpdates, tapsFromNotes } from "./done";
import { frontmatter } from "./md";
import { dayKey, minutesOf, semesterWeek } from "./model";
import { PrepNote, PrepState, parsePrep, prepState } from "./prep";
import { CalendarInfo, CockpitModel, LiveCalendar, NoteRef, RawInput, buildModel } from "./parse";
import { courses, moduleEnabled, registry } from "./registry";
import { CockpitSettings, defaultContextNotes } from "./settings";

export class VaultSource {
  constructor(
    private app: App,
    private settings: () => CockpitSettings,
  ) {}

  /** Where update notes for the inbox sync (the Done taps among them) wait to be applied, with a trailing "/". */
  inbox(): string {
    return registry().paths.inbox.replace(/\/+$/, "") + "/";
  }

  private file(path: string): TFile | null {
    const f = this.app.vault.getAbstractFileByPath(path);
    return f instanceof TFile ? f : null;
  }

  private async text(path: string): Promise<{ path: string; text: string } | null> {
    const f = this.file(path);
    return f ? { path, text: await this.app.vault.cachedRead(f) } : null;
  }

  private ref(f: TFile): NoteRef {
    return { path: f.path, title: f.basename, mtime: f.stat.mtime };
  }

  /** The week page marked `status: current` (highest week wins), else the one for this term week. */
  currentWeekFile(now: Date): TFile | null {
    const folder = registry().paths.weeks.replace(/\/$/, "") + "/";
    let best: { f: TFile; week: number } | null = null;
    for (const f of this.app.vault.getMarkdownFiles()) {
      if (!f.path.startsWith(folder)) continue;
      const fm = this.app.metadataCache.getFileCache(f)?.frontmatter;
      if (fm?.type === "week" && fm?.status === "current") {
        const week = Number(fm.week ?? 0);
        if (!best || week > best.week) best = { f, week };
      }
    }
    if (best) return best.f;
    const nn = String(semesterWeek(now)).padStart(2, "0");
    return this.file(`${folder}week-${nn}.md`);
  }

  /** The plugin's calendars, for the parser (ids, roles, on/off). */
  calendars(): CalendarInfo[] {
    return this.settings().feeds.map((f) => ({ id: f.id, label: f.label, role: f.role, on: f.on }));
  }

  /** `extraTaps`, `extraUndos`: taps and undos made here whose note may not show up in the vault index yet (tapKey of each). */
  async load(now = new Date(), live: LiveCalendar | null = null, extraTaps: string[] = [], extraUndos: string[] = []): Promise<CockpitModel> {
    const s = this.settings();
    const reg = registry();
    const weekFile = this.currentWeekFile(now);
    const weekNo = weekFile ? Number(this.app.metadataCache.getFileCache(weekFile)?.frontmatter?.week ?? semesterWeek(now)) : semesterWeek(now);
    const planPath = `${reg.paths.plans}/week-${String(weekNo).padStart(2, "0")}-plan.md`;

    const cards: RawInput["courses"] = {};
    for (const c of courses()) {
      const f = this.file(c.card);
      if (!f) continue;
      const text = await this.app.vault.cachedRead(f);
      // The metadata cache may not know a just-synced card yet; the file's own frontmatter is the fallback.
      const fm = (this.app.metadataCache.getFileCache(f)?.frontmatter as Record<string, unknown> | undefined) ?? frontmatter(text);
      cards[c.id] = { path: f.path, text, fm };
    }

    const md = this.app.vault.getMarkdownFiles();
    const agentDir = reg.paths.agentDir + "/";
    const recent = md
      .filter((f) => !f.path.startsWith(agentDir) && !f.path.startsWith("_templates/"))
      .sort((a, b) => b.stat.mtime - a.stat.mtime)
      .slice(0, 8)
      .map((f) => this.ref(f));

    const studyPages: Record<string, NoteRef[]> = {};
    for (const c of courses()) {
      studyPages[c.id] = md
        .filter((f) => c.studyFolders.some((folder) => f.path.startsWith(folder)))
        .sort((a, b) => b.stat.mtime - a.stat.mtime)
        .slice(0, 5)
        .map((f) => this.ref(f));
    }

    // Daily study prep notes: every prep-*.md in the prep folder (only with the daily-prep module enabled).
    let prep: PrepState | null = null;
    if (moduleEnabled("daily-prep")) {
      const prepFolder = reg.paths.prep.replace(/\/$/, "") + "/";
      const prepNotes: PrepNote[] = [];
      for (const f of md) {
        if (!f.path.startsWith(prepFolder) || !/prep-\d{4}-\d{2}-\d{2}/.test(f.name)) continue;
        const n = parsePrep(f.path, await this.app.vault.cachedRead(f));
        if (n) prepNotes.push(n);
      }
      prep = prepState(prepNotes, dayKey(now), now, s.prepSwitchHour, minutesOf(s.prepWarnAfter) ?? 19 * 60 + 30);
    }

    // Done taps and undos whose update note still waits in the inbox (the sync applies them to the week page later).
    // Read from disk, not the vault index: the index keeps a note for minutes after the sync moves it away.
    const notes: string[] = [];
    const adapter = this.app.vault.adapter;
    const inbox = this.inbox();
    const inboxFiles = (await adapter.exists(inbox)) ? (await adapter.list(inbox)).files : [];
    for (const path of inboxFiles) {
      if (!path.endsWith("-update.md")) continue;
      try {
        notes.push(await adapter.read(path));
      } catch {
        // The sync may have moved the note since the listing; it no longer waits then.
      }
    }
    const waiting = tapsFromNotes(notes);
    const inboxWaiting = otherUpdates(notes);
    // What was tapped here a moment ago is newer than any note.
    const taps = [...waiting.taps.filter((k) => !extraUndos.includes(k)), ...extraTaps];
    const undos = [...waiting.undos.filter((k) => !extraTaps.includes(k)), ...extraUndos];

    return buildModel({
      prep,
      now,
      status: await this.text(reg.paths.status),
      statusMtime: this.file(reg.paths.status)?.stat.mtime,
      week: weekFile ? { path: weekFile.path, text: await this.app.vault.cachedRead(weekFile) } : null,
      weekMtime: weekFile?.stat.mtime,
      taps,
      undos,
      inboxWaiting,
      weekPlanPath: this.file(planPath) ? planPath : null,
      courses: cards,
      snapshot: await this.text(reg.paths.snapshot),
      recent,
      studyPages,
      totalOverrides: s.totalOverrides,
      calendars: this.calendars(),
      live,
      staleDays: s.staleDays,
    });
  }

  /** Paths whose changes should refresh the cockpit. */
  isRelevant(path: string): boolean {
    const reg = registry();
    return (
      path === this.settings().configPath ||
      path === reg.paths.status ||
      path === reg.paths.snapshot ||
      path === reg.paths.overview ||
      path.startsWith(reg.paths.weeks + "/") ||
      // Notes only: the course folders also hold the official PDFs and handwritten-note uploads.
      courses().some((c) => path.startsWith(`${c.folder}/`) && path.endsWith(".md")) ||
      path.startsWith(reg.paths.plans + "/") ||
      (moduleEnabled("daily-prep") && path.startsWith(reg.paths.prep + "/")) ||
      // Done-tap notes waiting for the sync.
      path.startsWith(this.inbox())
    );
  }

  /** The notes the assistant reads: the rules first, then the current week page, then the chosen notes. */
  contextPaths(model: CockpitModel): string[] {
    const reg = registry();
    const chosen = this.settings().contextNotes ?? defaultContextNotes(reg);
    return [...new Set([reg.paths.rules, model.weekPath, ...chosen].filter((p): p is string => !!p))];
  }

  /** Full text of the notes the assistant gets as context. */
  async assistantContext(model: CockpitModel): Promise<Array<{ path: string; text: string }>> {
    const out: Array<{ path: string; text: string }> = [];
    for (const p of this.contextPaths(model)) {
      const t = await this.text(p);
      if (t) out.push(t);
    }
    return out;
  }

  /** The assistant's prompt template note, if there is one. */
  async promptNote(): Promise<string | null> {
    return (await this.text(registry().paths.prompt))?.text ?? null;
  }
}
