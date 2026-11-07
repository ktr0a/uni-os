// The cockpit tab: a thin frame (navigation, actions) around the chosen layout. Read-only.

import { Component, ItemView, Menu, Notice, ViewStateResult, WorkspaceLeaf, setIcon, setTooltip } from "obsidian";
import { contextPack } from "./context";
import { appliedWhen } from "./done";
import { hm, shortDay } from "./model";
import { Ctx, ViewState } from "./render/ctx";
import { renderCourses } from "./render/courses";
import { renderAgenda, renderDashboard, renderFocus } from "./render/home";
import { renderWeek } from "./render/week";
import type { ColorMode, Layout, Tab } from "./settings";
import { iconButton, noteLink } from "./ui";
import type UniOsCockpitPlugin from "./main";

export const COCKPIT_VIEW = "uni-os-cockpit";

const NAV: Array<{ id: Tab; label: string }> = [
  { id: "home", label: "Home" },
  { id: "week", label: "Week" },
  { id: "courses", label: "Courses" },
];

const LAYOUTS: Array<{ id: Layout; label: string; icon: string }> = [
  { id: "focus", label: "Focus", icon: "target" },
  { id: "dashboard", label: "Dashboard", icon: "layout-grid" },
  { id: "agenda", label: "Agenda", icon: "list" },
];

const MODES: Array<{ id: ColorMode; label: string }> = [
  { id: "accent", label: "Course accents" },
  { id: "mono", label: "Monochrome" },
  { id: "vivid", label: "Vivid blocks" },
];

export class CockpitView extends ItemView {
  private tab: Tab | null = null;
  private state: ViewState = { selected: null, weekOffset: 0, doneOpen: false, dueExpanded: false, pastOpen: false, prepOpen: {} };
  private renderScope: Component | null = null;

  constructor(
    leaf: WorkspaceLeaf,
    private plugin: UniOsCockpitPlugin,
  ) {
    super(leaf);
  }

  getViewType(): string {
    return COCKPIT_VIEW;
  }
  getDisplayText(): string {
    return "Cockpit";
  }
  getIcon(): string {
    return "layout-dashboard";
  }

  getState(): Record<string, unknown> {
    return { tab: this.tab };
  }
  async setState(state: { tab?: Tab }, result: ViewStateResult): Promise<void> {
    if (state?.tab && NAV.some((n) => n.id === state.tab)) this.tab = state.tab;
    this.render();
    return super.setState(state, result);
  }

  async onOpen(): Promise<void> {
    this.contentEl.addClass("uni-cockpit");
    this.render();
  }

  async onClose(): Promise<void> {
    this.renderScope?.unload();
  }

  onPaneMenu(menu: Menu, source: string): void {
    super.onPaneMenu(menu, source);
    const s = this.plugin.settings;
    for (const l of LAYOUTS) {
      menu.addItem((i) =>
        i
          .setSection("uc-layout")
          .setTitle(`Layout: ${l.label}`)
          .setIcon(l.icon)
          .setChecked(s.layout === l.id)
          .onClick(() => this.plugin.updateSettings({ layout: l.id })),
      );
    }
    for (const m of MODES) {
      menu.addItem((i) =>
        i
          .setSection("uc-colour")
          .setTitle(`Colours: ${m.label}`)
          .setIcon("palette")
          .setChecked(s.colorMode === m.id)
          .onClick(() => this.plugin.updateSettings({ colorMode: m.id })),
      );
    }
    menu.addItem((i) =>
      i
        .setSection("uc-colour")
        .setTitle(s.density === "compact" ? "Comfortable spacing" : "Compact spacing")
        .setIcon("rows-3")
        .onClick(() => this.plugin.updateSettings({ density: s.density === "compact" ? "comfortable" : "compact" })),
    );
    menu.addItem((i) => i.setSection("uc-actions").setTitle("Refresh").setIcon("refresh-cw").onClick(() => this.plugin.requestRefresh(0)));
    menu.addItem((i) => i.setSection("uc-actions").setTitle("Cockpit settings").setIcon("settings").onClick(() => this.plugin.openSettings()));
  }

  showTab(tab: Tab): void {
    this.tab = tab;
    this.state.selected = null;
    this.render();
  }

  render(): void {
    const model = this.plugin.model;
    const s = this.plugin.settings;
    const root = this.contentEl;
    const tab = this.tab ?? s.defaultTab;
    // Re-rendered every minute and on every note change: keep the reader's place.
    const scroll = root.scrollTop;
    this.renderScope?.unload();
    this.renderScope = new Component();
    this.addChild(this.renderScope);
    root.empty();
    root.className = root.className.replace(/\buc-(mode|density|width)-\S+/g, "").trim();
    root.addClasses([`uc-mode-${s.colorMode}`, `uc-density-${s.density}`, `uc-width-${s.width}`]);
    root.style.setProperty("--uc-scale", String(s.fontScale / 100));
    if (!model) {
      root.createDiv({ cls: "uc-empty", text: "Reading your notes…" });
      return;
    }
    window.requestAnimationFrame(() => (root.scrollTop = scroll));

    const top = root.createDiv({ cls: "uc-top" });
    const nav = top.createDiv({ cls: "uc-nav" });
    for (const n of NAV) {
      const b = nav.createEl("button", { cls: `uc-nav-item${n.id === tab ? " is-active" : ""}`, text: n.id === "home" ? LAYOUTS.find((l) => l.id === s.layout)!.label : n.label });
      b.addEventListener("click", () => this.showTab(n.id));
    }
    const actions = top.createDiv({ cls: "uc-actions" });
    iconButton(actions, "refresh-cw", "Refresh now", () => this.plugin.requestRefresh(0), "uc-quiet uc-icon-only");
    iconButton(actions, "clipboard-copy", "Copy status for your AI chat", () => void this.copyContext(), "uc-quiet uc-icon-only");
    iconButton(actions, "sparkles", "Open the assistant", () => void this.plugin.activateAssistant(), "uc-quiet uc-icon-only");
    iconButton(actions, "settings-2", "Cockpit settings", () => this.plugin.openSettings(), "uc-quiet uc-icon-only");

    if (model.warnings.length) {
      const w = root.createDiv({ cls: "uc-warnings" });
      for (const text of model.warnings) {
        const line = w.createDiv({ cls: "uc-warning" });
        setIcon(line.createSpan({ cls: "uc-warning-icon" }), "info");
        line.createSpan({ text });
      }
    }

    const main = root.createDiv({ cls: "uc-main" });
    const ctx: Ctx = {
      app: this.app,
      model,
      s,
      hover: this,
      scope: this.renderScope,
      state: this.state,
      rerender: () => this.render(),
      go: (t) => this.showTab(t),
      markDone: (d) => this.plugin.markDone(d),
      markUndone: (d) => void this.plugin.markUndone(d),
    };
    if (tab === "week") renderWeek(ctx, main);
    else if (tab === "courses") renderCourses(ctx, main);
    else if (s.layout === "dashboard") renderDashboard(ctx, main);
    else if (s.layout === "agenda") renderAgenda(ctx, main);
    else renderFocus(ctx, main);

    if (s.showFooter) {
      const foot = root.createDiv({ cls: "uc-foot" });
      foot.appendText("Live from ");
      if (model.statusPath) noteLink(this.app, foot, "progress", model.statusPath, "", this);
      if (model.weekPath) {
        foot.appendText(", ");
        noteLink(this.app, foot, `week ${model.week}`, model.weekPath, "", this);
      }
      foot.appendText(" and the course cards · ");
      if (model.liveCals.length && model.liveAt) {
        const names = model.liveCals.map((c) => s.feeds.find((f) => f.id === c)?.label ?? c).join(", ");
        foot.appendText(`calendar live (${names}), fetched ${hm(new Date(model.liveAt))}`);
        if (model.liveCals.length < s.feeds.filter((f) => f.on).length) foot.appendText(", others from the snapshot");
      } else {
        foot.appendText(`calendar snapshot ${model.snapshotGenerated ? `${shortDay(new Date(model.snapshotGenerated))} ${hm(new Date(model.snapshotGenerated))}` : "missing"}`);
      }
      // How fresh the rows are: the pages only change when a session edits them (or the Done button files a note).
      const stamp = (ms: number) => `${shortDay(new Date(ms))} ${hm(new Date(ms))}`;
      const changed = [model.weekMtime ? `week page ${stamp(model.weekMtime)}` : "", model.statusMtime ? `progress page ${stamp(model.statusMtime)}` : ""].filter(Boolean);
      const fresh = foot.createDiv({ cls: "uc-foot-line", text: `${changed.length ? `Changed: ${changed.join(", ")} · ` : ""}read at ${hm(model.now)}` });
      setTooltip(fresh, "A row only changes when an agent edits the week page or the Done button is used.");
      // Updates from sessions that the sync has not applied yet: the reason a row may look behind.
      if (model.inboxWaiting) {
        const n = model.inboxWaiting;
        foot.createDiv({ cls: "uc-foot-line uc-foot-inbox", text: `${n} update${n > 1 ? "s" : ""} waiting in the inbox, ${appliedWhen(model.now)}.` });
      }
    }
  }

  private async copyContext(): Promise<void> {
    const model = this.plugin.model;
    if (!model) return;
    await navigator.clipboard.writeText(contextPack(model));
    new Notice("Copied. Paste it into your AI chat as context.");
  }
}
