import { Notice, Plugin, TAbstractFile, WorkspaceLeaf, debounce } from "obsidian";
import { ASSISTANT_VIEW, AssistantView } from "./assistant-view";
import { COCKPIT_VIEW, CockpitView } from "./cockpit-view";
import { contextPack } from "./context";
import { VaultSource } from "./data";
import { doneNote, syncWhen, undoNote } from "./done";
import { FeedCache, sameSnapshot, snapshotFromLive } from "./feeds";
import { addDays, dayKey, hm, mondayOf, relative, shortDay } from "./model";
import { CockpitModel, DueItem, RawEvent, nowAndNext, plain, tapKey } from "./parse";
import { Registry, buildRegistry, paletteOf, registry, setRegistry } from "./registry";
import { CockpitSettings, Layout, mergeSettings } from "./settings";
import { CockpitSettingTab } from "./settings-tab";
import { courseVars, iconButton, setPalette } from "./ui";

/** Time to undo a Done tap before its note is written. */
const UNDO_MS = 10_000;
/** How long a saved tap is still counted here: the vault index may lag behind the new note. */
const KEEP_MS = 10 * 60_000;

/** One Done tap on its way to a note in the inbox. */
interface Tap {
  item: string;
  stage: "waiting" | "writing" | "saved";
  notice: Notice | null;
  timer: number;
}

export default class UniOsCockpitPlugin extends Plugin {
  settings: CockpitSettings = mergeSettings(null);
  model: CockpitModel | null = null;
  source!: VaultSource;
  feeds!: FeedCache;
  private banners = new Set<HTMLElement>();
  /** Done taps not yet in the vault index, by tapKey: the rows count as done meanwhile. */
  private taps = new Map<string, Tap>();
  /** Undos not yet in the vault index, by tapKey (the value is the timer that forgets them). */
  private undos = new Map<string, number>();
  private refreshSeq = 0;
  private refreshSoon = debounce(() => void this.refreshNow(), 400, true);

  async onload(): Promise<void> {
    const saved = (await this.loadData()) as Partial<CockpitSettings> | null;
    // The registry first (its [cockpit] table holds the first-run defaults), then the settings on top.
    await this.loadRegistry(saved?.configPath);
    this.settings = mergeSettings(saved, registry());
    this.applyPalette();
    this.source = new VaultSource(this.app, () => this.settings);
    this.feeds = new FeedCache(this.app, () => this.settings);

    this.registerView(COCKPIT_VIEW, (leaf) => new CockpitView(leaf, this));
    this.registerView(ASSISTANT_VIEW, (leaf) => new AssistantView(leaf, this));
    this.addSettingTab(new CockpitSettingTab(this.app, this));

    this.addRibbonIcon("layout-dashboard", "Open cockpit", () => void this.activateCockpit());
    this.addCommand({ id: "open-cockpit", name: "Open cockpit", callback: () => void this.activateCockpit() });
    this.addCommand({ id: "open-assistant", name: "Open assistant", callback: () => void this.activateAssistant() });
    this.addCommand({ id: "copy-context", name: "Copy status for your AI chat", callback: () => void this.copyContext() });
    this.addCommand({ id: "refresh", name: "Refresh cockpit", callback: () => void this.refreshNow() });
    this.addCommand({
      id: "reload-config",
      name: "Reload the course config (uni-os.json)",
      callback: async () => {
        await this.loadRegistry();
        await this.refreshNow();
        new Notice(`Config read: ${registry().courses.length} courses.`);
      },
    });
    this.addCommand({
      id: "refresh-calendar",
      name: "Refresh the live calendar now",
      callback: async () => {
        const r = await this.checkFeeds();
        new Notice(r.text, 8000);
      },
    });
    for (const [id, name] of [
      ["focus", "Focus"],
      ["dashboard", "Dashboard"],
      ["agenda", "Agenda"],
    ] as Array<[Layout, string]>) {
      this.addCommand({
        id: `layout-${id}`,
        name: `Use the ${name} layout`,
        callback: async () => {
          await this.updateSettings({ layout: id });
          await this.activateCockpit();
        },
      });
    }
    this.registerObsidianProtocolHandler("uni-os-cockpit", () => void this.activateCockpit());

    // ```uni-os-cockpit``` in any note: a one-line status banner with a button to the cockpit.
    this.registerMarkdownCodeBlockProcessor("uni-os-cockpit", (_src, el) => {
      this.banners.add(el);
      this.renderBanner(el);
    });

    const onChange = (file: TAbstractFile) => {
      if (file.path === this.settings.configPath) {
        void this.loadRegistry().then(() => this.refreshSoon());
        return;
      }
      if (this.source.isRelevant(file.path)) this.refreshSoon();
    };
    this.registerEvent(this.app.vault.on("modify", onChange));
    this.registerEvent(this.app.vault.on("create", onChange));
    this.registerEvent(this.app.vault.on("delete", onChange));
    this.registerEvent(this.app.vault.on("rename", onChange));
    this.registerEvent(this.app.metadataCache.on("changed", onChange));
    // Countdowns, the "now" marker and the headline move with the clock.
    this.registerInterval(window.setInterval(() => void this.refreshNow(), 60_000));
    // Waking the laptop or coming back to Obsidian shouldn't wait for the next minute.
    this.registerDomEvent(window, "focus", () => this.refreshSoon());
    this.registerDomEvent(document, "visibilitychange", () => {
      if (document.visibilityState === "visible") this.refreshSoon();
    });

    this.app.workspace.onLayoutReady(async () => {
      // The vault index is complete now; the config file may only be readable from here on.
      if (!registry().loaded) await this.loadRegistry();
      await this.refreshNow();
      if (this.settings.openOnStartup) await this.activateCockpit();
    });
  }

  onunload(): void {
    this.banners.clear();
    // A tap still in its undo window is written now, so a reload doesn't lose it.
    for (const [key, tap] of [...this.taps]) {
      window.clearTimeout(tap.timer);
      void this.writeTap(key, true);
    }
  }

  /** Reads _agent/uni-os.json (or the configured path) into the registry. A missing or broken file leaves a warning. */
  async loadRegistry(path = this.settings.configPath): Promise<Registry> {
    const p = path || "_agent/uni-os.json";
    let reg: Registry;
    try {
      const adapter = this.app.vault.adapter;
      reg = (await adapter.exists(p)) ? buildRegistry(JSON.parse(await adapter.read(p)), p) : buildRegistry(null, p);
    } catch (err) {
      reg = buildRegistry(null, p);
      reg.problems.splice(0, reg.problems.length, `${p} could not be read (${(err as Error).message}); the cockpit knows no courses until it is fixed.`);
    }
    setRegistry(reg);
    this.applyPalette();
    return reg;
  }

  private applyPalette(): void {
    setPalette(paletteOf(registry(), this.settings.courseColors));
  }

  async saveSettings(): Promise<void> {
    this.applyPalette();
    await this.saveData(this.settings);
  }

  /** Change settings from anywhere (pane menu, commands, settings tab) and redraw everything. */
  async updateSettings(patch: Partial<CockpitSettings>, reload = false): Promise<void> {
    Object.assign(this.settings, structuredClone(patch));
    await this.saveSettings();
    if (reload) await this.refreshNow();
    else this.redraw();
  }

  redraw(): void {
    for (const leaf of this.app.workspace.getLeavesOfType(COCKPIT_VIEW)) {
      if (leaf.view instanceof CockpitView) leaf.view.render();
    }
    for (const el of [...this.banners]) {
      if (!el.isConnected) this.banners.delete(el);
      else this.renderBanner(el);
    }
    this.refreshAssistants();
  }

  requestRefresh(delay = 400): void {
    if (delay === 0) void this.refreshNow();
    else this.refreshSoon();
  }

  async refreshNow(): Promise<void> {
    // Live calendar feeds refresh in the background; when one changes, everything is rebuilt once more.
    if (this.feeds.isDue()) {
      void this.feeds.refresh().then(async (changed) => {
        if (changed) await this.refreshNow();
      });
    }
    const seq = ++this.refreshSeq;
    try {
      // Whatever refreshed the feeds (timer, settings, the check button), the snapshot file follows;
      // it is only rewritten when the calendar in it actually differs.
      await this.writeSnapshotFromFeeds();
      const model = await this.source.load(new Date(), this.feeds.live(), [...this.taps.keys()], [...this.undos.keys()]);
      // A newer refresh (a Done tap, an Undo) started meanwhile and knows more; don't draw over it.
      if (seq !== this.refreshSeq) return;
      this.model = model;
    } catch (err) {
      console.error("uni-os-cockpit: refresh failed", err);
      new Notice(`The cockpit couldn't read the notes: ${(err as Error).message}`);
      return;
    }
    for (const leaf of this.app.workspace.getLeavesOfType(COCKPIT_VIEW)) {
      if (leaf.view instanceof CockpitView) leaf.view.render();
    }
    for (const el of [...this.banners]) {
      if (!el.isConnected) this.banners.delete(el);
      else this.renderBanner(el);
    }
  }

  /**
   * The Done button. The row moves to the done list at once; its update note for the inbox is written after a
   * 10 s window to undo, so a mis-tap leaves nothing behind.
   */
  markDone(d: DueItem): void {
    const key = tapKey(d.item);
    if (this.taps.has(key)) return;
    window.clearTimeout(this.undos.get(key));
    this.undos.delete(key);
    const notice = new Notice(
      createFragment((f) => {
        f.createSpan({ text: `Marked done: ${plain(d.item)}. ` });
        f.createEl("button", { cls: "uc-notice-undo", text: "Undo" }).addEventListener("click", () => this.undoTap(key));
      }),
      UNDO_MS,
    );
    this.taps.set(key, { item: d.item, stage: "waiting", notice, timer: window.setTimeout(() => void this.writeTap(key), UNDO_MS) });
    this.requestRefresh(0);
  }

  /**
   * The Undo on a tapped row, at any time. In the first 10 s nothing was written yet, so nothing needs writing;
   * later a small undo note follows the Done note, and the row reopens at once.
   */
  async markUndone(d: DueItem): Promise<void> {
    const key = tapKey(d.item);
    const tap = this.taps.get(key);
    if (tap?.stage === "waiting") return this.undoTap(key);
    if (tap) {
      window.clearTimeout(tap.timer);
      this.taps.delete(key);
    }
    this.undos.set(
      key,
      window.setTimeout(() => this.undos.delete(key), KEEP_MS),
    );
    this.requestRefresh(0);
    const weekFile = this.source.currentWeekFile(new Date());
    const note = undoNote({ weekPath: weekFile?.path ?? "the current week page", item: d.item, now: new Date(), source: "cockpit" });
    const inbox = this.source.inbox();
    try {
      await this.ensureFolder(inbox);
      await this.app.vault.create(await this.freePath(inbox + note.title), note.text);
      new Notice(`Reopened. The week page catches up ${syncWhen(new Date())}.`, 8000);
    } catch (err) {
      window.clearTimeout(this.undos.get(key));
      this.undos.delete(key);
      new Notice(`Couldn't undo ${plain(d.item)}: the note could not be written to ${inbox} (${(err as Error).message}).`, 12_000);
      this.requestRefresh(0);
    }
  }

  private undoTap(key: string): void {
    const tap = this.taps.get(key);
    if (!tap || tap.stage !== "waiting") return;
    window.clearTimeout(tap.timer);
    tap.notice?.hide();
    this.taps.delete(key);
    this.requestRefresh(0);
  }

  /** A tap, an undo and a tap again within one minute would share a name: number the later ones (the "-update.md" end stays). */
  private async freePath(path: string): Promise<string> {
    let candidate = path;
    for (let n = 2; await this.app.vault.adapter.exists(candidate); n++) candidate = path.replace(/-update\.md$/, `-${n}-update.md`);
    return candidate;
  }

  private async ensureFolder(folder: string): Promise<void> {
    const path = folder.replace(/\/+$/, "");
    if (!(await this.app.vault.adapter.exists(path))) await this.app.vault.createFolder(path);
  }

  /** Writes the update note for a tap whose undo window is over. `quiet`: the plugin is unloading, so don't redraw. */
  private async writeTap(key: string, quiet = false): Promise<void> {
    const tap = this.taps.get(key);
    if (!tap || tap.stage !== "waiting") return;
    tap.stage = "writing";
    tap.notice?.hide();
    tap.notice = null;
    const name = plain(tap.item);
    const inbox = this.source.inbox();
    const fail = (why: string) => {
      this.taps.delete(key);
      new Notice(`Couldn't save the Done tap for ${name}: ${why} It is back in the list.`, 12_000);
      if (!quiet) this.requestRefresh(0);
    };
    // The week page is read now, not at the tap: the row may have changed in the meantime.
    const weekFile = this.source.currentWeekFile(new Date());
    if (!weekFile) return fail("there is no current week page.");
    let note: { title: string; text: string } | null;
    try {
      note = doneNote({ weekPath: weekFile.path, weekText: await this.app.vault.read(weekFile), item: tap.item, now: new Date(), source: "cockpit" });
    } catch (err) {
      return fail(`the week page could not be read (${(err as Error).message}).`);
    }
    if (!note) return fail("its row is no longer on the week page.");
    try {
      await this.ensureFolder(inbox);
      await this.app.vault.create(await this.freePath(inbox + note.title), note.text);
    } catch (err) {
      return fail(`the note could not be written to ${inbox} (${(err as Error).message}).`);
    }
    tap.stage = "saved";
    // The vault index may lag behind the new note, so the tap stays counted for a while.
    if (!quiet) tap.timer = window.setTimeout(() => this.taps.delete(key), KEEP_MS);
    new Notice(`Saved. The week page updates ${syncWhen(new Date())}.`, 8000);
  }

  /**
   * Rewrites the vault's calendar snapshot from the live feeds (if switched on), so agents that read the vault
   * see the same calendar. Only writes when the calendar actually changed.
   */
  async writeSnapshotFromFeeds(): Promise<boolean> {
    const live = this.feeds.live();
    if (!this.settings.feedWriteSnapshot || !live || !live.cals.length) return false;
    const path = registry().paths.snapshot;
    let previous: { range?: unknown; events?: RawEvent[] } | null = null;
    try {
      previous = (await this.app.vault.adapter.exists(path)) ? JSON.parse(await this.app.vault.adapter.read(path)) : null;
    } catch {
      previous = null;
    }
    const next = snapshotFromLive(live, previous?.events ?? [], new Date(), this.settings.feeds);
    if (sameSnapshot(previous, next)) return false;
    const folder = path.split("/").slice(0, -1).join("/");
    if (folder) await this.ensureFolder(folder);
    await this.app.vault.adapter.write(path, JSON.stringify(next, null, 1) + "\n");
    return true;
  }

  /** Fetches every linked feed now and describes the result, compared with the snapshot file. */
  async checkFeeds(): Promise<{ ok: boolean; text: string }> {
    const ids = this.feeds.configured();
    if (!ids.length) return { ok: false, text: "No calendar address linked yet: use Link… on a calendar above first." };
    const before = this.model?.snapshotRaw ?? [];
    const range = this.model?.snapshotRange ?? null;
    await this.feeds.refresh(true);
    const mon = mondayOf(dayKey(new Date()));
    const lines: string[] = [];
    let ok = true;
    for (const f of this.settings.feeds) {
      if (!ids.includes(f.id)) {
        lines.push(`${f.label}: ${f.on ? "not linked" : "switched off"} (the snapshot is used).`);
        continue;
      }
      const st = this.feeds.status(f.id);
      if (!st || st.error) {
        ok = false;
        lines.push(`${f.label}: failed: ${st?.error ?? "no answer"}.`);
        continue;
      }
      const busy = f.role === "personal";
      const thisWeek = st.events.filter((e) => mondayOf(dayKey(new Date(e.start))) === mon).length;
      let cmp = "";
      if (range) {
        const inRange = (e: RawEvent) => {
          const k = dayKey(new Date(e.start));
          return k >= range.start && k <= range.end;
        };
        const key = (e: RawEvent) => `${busy ? "" : e.title}|${Date.parse(e.start)}|${Date.parse(e.end)}`;
        const label = (e: RawEvent) => `${shortDay(new Date(e.start))} ${hm(new Date(e.start))} ${busy ? "busy" : e.title}`;
        const old = before.filter((e) => e.cal === f.id && inRange(e));
        const now = st.events.filter(inRange);
        const oldKeys = new Set(old.map(key));
        const newKeys = new Set(now.map(key));
        const added = now.filter((e) => !oldKeys.has(key(e)));
        const gone = old.filter((e) => !newKeys.has(key(e)));
        cmp =
          added.length || gone.length
            ? ` Compared with the snapshot: ${added.length} new${added.length ? ` (${added.slice(0, 3).map(label).join("; ")})` : ""}, ${gone.length} gone${gone.length ? ` (${gone.slice(0, 3).map(label).join("; ")})` : ""}.`
            : " Same as the snapshot.";
      }
      lines.push(`${f.label}: OK, ${st.events.length} entries over 6 weeks, ${thisWeek} this week, fetched in ${st.ms ?? "?"} ms.${cmp}`);
    }
    await this.writeSnapshotFromFeeds();
    await this.refreshNow();
    return { ok, text: lines.join("\n") };
  }

  refreshAssistants(): void {
    for (const leaf of this.app.workspace.getLeavesOfType(ASSISTANT_VIEW)) {
      if (leaf.view instanceof AssistantView) leaf.view.render();
    }
  }

  async activateCockpit(): Promise<void> {
    const existing = this.app.workspace.getLeavesOfType(COCKPIT_VIEW)[0];
    const leaf: WorkspaceLeaf = existing ?? this.app.workspace.getLeaf("tab");
    if (!existing) await leaf.setViewState({ type: COCKPIT_VIEW, active: true });
    await this.app.workspace.revealLeaf(leaf);
  }

  async activateAssistant(): Promise<void> {
    let leaf = this.app.workspace.getLeavesOfType(ASSISTANT_VIEW)[0];
    if (!leaf) {
      const right = this.app.workspace.getRightLeaf(false);
      if (!right) return;
      await right.setViewState({ type: ASSISTANT_VIEW, active: true });
      leaf = right;
    }
    await this.app.workspace.revealLeaf(leaf);
  }

  openSettings(): void {
    const setting = (this.app as unknown as { setting?: { open(): void; openTabById(id: string): void } }).setting;
    setting?.open();
    setting?.openTabById(this.manifest.id);
  }

  async copyContext(): Promise<void> {
    if (!this.model) await this.refreshNow();
    if (!this.model) return;
    await navigator.clipboard.writeText(contextPack(this.model));
    new Notice("Copied. Paste it into your AI chat as context.");
  }

  private renderBanner(el: HTMLElement): void {
    el.empty();
    if (!this.settings.bannerEnabled) return;
    const m = this.model;
    const b = el.createDiv({ cls: `uc-banner uc-mode-${this.settings.colorMode}` });
    const text = b.createDiv({ cls: "uc-banner-text" });
    if (!m) {
      text.setText("The cockpit is loading…");
    } else {
      const { current, next } = nowAndNext(m);
      const cur = current.find((e) => e.kind === "study") ?? current[0];
      const n = next[0];
      const lead = text.createDiv({ cls: "uc-banner-lead" });
      if (cur) {
        lead.setText(`Now: ${cur.title} until ${hm(cur.end)}`);
        courseVars(lead, cur.course);
      } else if (n) {
        const when = dayKey(n.start) === m.today ? hm(n.start) : dayKey(n.start) === addDays(m.today, 1) ? `tomorrow ${hm(n.start)}` : `${shortDay(n.start)} ${hm(n.start)}`;
        lead.setText(`Next: ${n.title}, ${when}`);
        courseVars(lead, n.course);
      } else lead.setText("Nothing ahead in the calendar");
      if (this.settings.bannerDue) {
        const open = m.due.filter((d) => d.state === "open" || d.state === "overdue");
        const soonest = open.filter((d) => d.deadline).sort((a, c) => a.deadline!.getTime() - c.deadline!.getTime())[0];
        text.createDiv({
          cls: "uc-banner-sub",
          text: `${open.length} open this week${soonest ? ` · next: ${plain(soonest.item)} ${relative(m.now, soonest.deadline!)}` : ""}`,
        });
      }
    }
    iconButton(b, "layout-dashboard", "Open cockpit", () => void this.activateCockpit(), "mod-cta");
  }
}
