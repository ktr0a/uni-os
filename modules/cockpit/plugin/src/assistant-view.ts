// Side panel that answers from the vault with Claude, on the student's own API key.
// Read-only: it never edits notes or the calendar. "Save to inbox" is an explicit click.

import Anthropic from "@anthropic-ai/sdk";
import { Component, ItemView, MarkdownRenderer, Menu, Notice, TFile, WorkspaceLeaf, normalizePath } from "obsidian";
import { contextPack } from "./context";
import { dayKey, hm, shortDay, zparts } from "./model";
import { DEFAULT_PROMPT, fillPrompt, templateFromNote } from "./prompt";
import { courses, registry } from "./registry";
import type { CockpitSettings, ModelChoice } from "./settings";
import { apiKey, describeError, makeClient } from "./claude";
import { iconButton } from "./ui";
import type UniOsCockpitPlugin from "./main";

export const ASSISTANT_VIEW = "uni-os-cockpit-assistant";

/** USD per million tokens, for the cost line. Unknown models get a token count without a price. */
const PRICES: Record<string, { inPerM: number; outPerM: number; cacheReadPerM: number; cacheWritePerM: number }> = {
  // Haiku 5.5 prices are for prompts up to 100k tokens.
  "claude-haiku-5-5": { inPerM: 0.1, outPerM: 0.5, cacheReadPerM: 0.01, cacheWritePerM: 0.125 },
  "claude-sonnet-5-5": { inPerM: 2, outPerM: 10, cacheReadPerM: 0.2, cacheWritePerM: 2.5 },
};

/** "claude-sonnet-5-5" -> "Sonnet 5.5" */
export function modelLabel(id: string): string {
  const m = /^claude-([a-z]+)-(\d+)(?:-(\d+))?/.exec(id);
  if (!m) return id;
  return `${m[1][0].toUpperCase()}${m[1].slice(1)} ${m[2]}${m[3] ? `.${m[3]}` : ""}`;
}

interface Turn {
  role: "user" | "assistant";
  text: string;
  meta?: string;
  error?: boolean;
}

export class AssistantView extends ItemView {
  private turns: Turn[] = [];
  private history: Anthropic.MessageParam[] = [];
  private busy = false;
  private stream: { abort(): void } | null = null;
  private includeNote = false;
  private spent = 0;
  private renderScope: Component | null = null;
  private logEl!: HTMLElement;
  private inputEl!: HTMLTextAreaElement;

  constructor(
    leaf: WorkspaceLeaf,
    private plugin: UniOsCockpitPlugin,
  ) {
    super(leaf);
  }

  getViewType(): string {
    return ASSISTANT_VIEW;
  }
  getDisplayText(): string {
    return "Study assistant";
  }
  getIcon(): string {
    return "sparkles";
  }

  async onOpen(): Promise<void> {
    this.contentEl.addClass("uni-assistant");
    this.render();
  }

  async onClose(): Promise<void> {
    this.stream?.abort();
    this.renderScope?.unload();
  }

  private apiKey(): string | null {
    return apiKey(this.app, this.plugin.settings);
  }

  private models(s: CockpitSettings) {
    return { fast: s.fastModel, strong: s.strongModel };
  }

  render(): void {
    const root = this.contentEl;
    root.empty();
    const s = this.plugin.settings;
    const ids = this.models(s);
    const head = root.createDiv({ cls: "uca-head" });
    head.createSpan({ cls: "uca-title", text: "Assistant" });
    // The chip is also the model switch: click it to pick Auto, fast or strong (same setting as in Settings).
    const choice = s.model;
    const chipText = choice === "auto" ? `Auto: ${modelLabel(ids.fast)} / ${modelLabel(ids.strong)}` : modelLabel(choice === "fast" ? ids.fast : ids.strong);
    const chip = head.createEl("button", { cls: "uca-chip", text: `${chipText} ▾` });
    chip.setAttr("aria-label", "Choose the model");
    chip.addEventListener("click", (ev) => {
      const menu = new Menu();
      const options: Array<[ModelChoice, string]> = [
        ["auto", `Auto: ${modelLabel(ids.fast)} for lookups, ${modelLabel(ids.strong)} for explanations`],
        ["fast", `${modelLabel(ids.fast)} only (cheapest)`],
        ["strong", `${modelLabel(ids.strong)} only`],
      ];
      for (const [id, label] of options) {
        menu.addItem((i) => i.setTitle(label).setChecked(choice === id).onClick(() => this.plugin.updateSettings({ model: id })));
      }
      menu.showAtMouseEvent(ev);
    });
    if (this.turns.length) iconButton(head, "rotate-ccw", "New chat", () => this.reset(), "uc-quiet uc-icon-only");

    this.logEl = root.createDiv({ cls: "uca-log" });
    if (!this.apiKey()) {
      this.renderNoKey(this.logEl);
    } else if (!this.turns.length) {
      const intro = this.logEl.createDiv({ cls: "uca-intro" });
      intro.createDiv({ cls: "uca-intro-h", text: "Ask about your week." });
      intro.createDiv({
        cls: "uc-muted",
        text: "I read your progress page, this week's page, the course cards, your rules and the calendar. I can't change files or the calendar; when something should change, I'll say what and where.",
      });
    }
    this.renderTurns();

    const chips = root.createDiv({ cls: "uca-chips" });
    for (const q of s.quickAsks) {
      const b = chips.createEl("button", { cls: "uca-ask", text: q });
      b.addEventListener("click", () => this.send(q));
    }

    const box = root.createDiv({ cls: "uca-input" });
    const example = courses()[0]?.short;
    this.inputEl = box.createEl("textarea", { attr: { rows: "3", placeholder: example ? `Ask, e.g. “what's left for ${example} this week?”` : "Ask about your week" } });
    this.inputEl.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        void this.send(this.inputEl.value);
      }
    });
    const row = box.createDiv({ cls: "uca-input-row" });
    const label = row.createEl("label", { cls: "uca-toggle" });
    const cb = label.createEl("input", { type: "checkbox" });
    cb.checked = this.includeNote;
    cb.addEventListener("change", () => (this.includeNote = cb.checked));
    label.appendText(" include the open note");
    row.createSpan({ cls: "uc-muted uc-small uca-spent", text: this.spent && s.showCost ? `this chat ≈ $${this.spent.toFixed(4)}` : "" });
    if (this.busy) iconButton(row, "square", "Stop", () => this.stream?.abort(), "uc-quiet");
    else iconButton(row, "send", "Send", () => void this.send(this.inputEl.value), "mod-cta");
  }

  private renderNoKey(parent: HTMLElement): void {
    const box = parent.createDiv({ cls: "uca-intro" });
    box.createDiv({ cls: "uca-intro-h", text: "No API key set" });
    box.createDiv({
      cls: "uc-muted",
      text: "This panel calls Claude with your own Anthropic API key (billed separately from any chat subscription; roughly $1-5 a month at ~20 questions a day with the default models). The key goes into Obsidian's secret storage on this device: not into the vault, so it never syncs or ends up in git.",
    });
    const actions = box.createDiv({ cls: "uca-actions" });
    iconButton(actions, "settings", "Set the key", () => this.plugin.openSettings(), "mod-cta");
    iconButton(actions, "clipboard-copy", "Copy the status for your AI chat instead", () => void this.copyContext(), "uc-quiet");
  }

  private renderTurns(): void {
    this.renderScope?.unload();
    this.renderScope = new Component();
    this.addChild(this.renderScope);
    for (const t of this.turns) {
      const el = this.logEl.createDiv({ cls: `uca-msg uca-${t.role}${t.error ? " is-error" : ""}` });
      const body = el.createDiv({ cls: "uca-body" });
      if (t.role === "assistant" && !t.error) {
        if (!t.text) body.createDiv({ cls: "uca-thinking", text: "Thinking…" });
        else void MarkdownRenderer.render(this.app, t.text, body, "", this.renderScope);
      } else body.setText(t.text);
      if (t.meta) el.createDiv({ cls: "uca-meta", text: t.meta });
      if (t.role === "assistant" && t.text && !t.error && !this.busy) {
        const acts = el.createDiv({ cls: "uca-msg-actions" });
        iconButton(acts, "copy", "Copy", () => void navigator.clipboard.writeText(t.text).then(() => new Notice("Copied")), "uc-quiet uc-small-btn");
        iconButton(acts, "inbox", "Save to inbox", () => void this.saveToInbox(t), "uc-quiet uc-small-btn");
      }
    }
    this.logEl.scrollTop = this.logEl.scrollHeight;
  }

  private reset(): void {
    this.stream?.abort();
    this.turns = [];
    this.history = [];
    this.spent = 0;
    this.render();
  }

  private async copyContext(): Promise<void> {
    if (!this.plugin.model) return;
    await navigator.clipboard.writeText(contextPack(this.plugin.model));
    new Notice("Copied. Paste it into your AI chat as context.");
  }

  private pickModel(text: string): string {
    const s = this.plugin.settings;
    if (s.model === "fast") return s.fastModel;
    if (s.model === "strong") return s.strongModel;
    if (this.includeNote || text.length > 300) return s.strongModel;
    return /\b(explain|why|how (do|does|can)|prove|proof|derive|intuition|teach|walk me through|plan|replan|reschedule|compare)\b/i.test(text) ? s.strongModel : s.fastModel;
  }

  private async systemPrompt(): Promise<Anthropic.TextBlockParam[]> {
    const model = this.plugin.model!;
    const notes = await this.plugin.source.assistantContext(model);
    const template = templateFromNote(await this.plugin.source.promptNote()) ?? DEFAULT_PROMPT;
    const role = fillPrompt(template, registry());
    const vault = notes.map((n) => `<note path="${n.path}">\n${n.text}\n</note>`).join("\n\n");
    return [
      { type: "text", text: role },
      { type: "text", text: `<vault>\n${vault}\n</vault>`, cache_control: { type: "ephemeral" } },
    ];
  }

  private async userMessage(text: string): Promise<string> {
    const model = this.plugin.model!;
    const parts = [`<now>${shortDay(model.now)} ${zparts(model.now).y}, ${hm(model.now)} (term week ${model.week})</now>`];
    parts.push(`<status>\n${contextPack(model)}\n</status>`);
    if (this.includeNote) {
      const f = this.app.workspace.getActiveFile();
      if (f instanceof TFile && f.extension === "md") parts.push(`<open_note path="${f.path}">\n${await this.app.vault.cachedRead(f)}\n</open_note>`);
    }
    parts.push(text);
    return parts.join("\n\n");
  }

  async send(raw: string): Promise<void> {
    const text = raw.trim();
    if (!text || this.busy) return;
    const key = this.apiKey();
    if (!key) {
      new Notice("Set your Anthropic API key in the Uni OS cockpit settings first.");
      return;
    }
    if (!this.plugin.model) await this.plugin.refreshNow();
    if (text === "Explain the open note") this.includeNote = true;

    const s = this.plugin.settings;
    const modelId = this.pickModel(text);
    const label = modelLabel(modelId);
    const price = PRICES[modelId];
    const client = makeClient(key, s);

    const user: Anthropic.MessageParam = { role: "user", content: await this.userMessage(text) };
    const answer: Turn = { role: "assistant", text: "" };
    this.turns.push({ role: "user", text }, answer);
    this.busy = true;
    this.render();

    try {
      const stream = client.messages.stream({
        model: modelId,
        max_tokens: s.maxTokens,
        system: await this.systemPrompt(),
        output_config: { effort: modelId === s.fastModel ? s.effortFast : s.effortStrong },
        messages: [...this.history, user],
      });
      this.stream = stream;
      let pending = false;
      stream.on("text", (delta) => {
        answer.text += delta;
        if (pending) return;
        pending = true;
        window.requestAnimationFrame(() => {
          pending = false;
          this.updateLast(answer);
        });
      });
      const msg = await stream.finalMessage();
      if (msg.stop_reason === "refusal") answer.text += "\n\n*(Claude declined this request.)*";
      if (msg.stop_reason === "max_tokens") answer.text += "\n\n*(Cut off at the length limit.)*";
      const u = msg.usage;
      const inTok = (u.input_tokens ?? 0) + (u.cache_read_input_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0);
      const cost = price
        ? ((u.input_tokens ?? 0) * price.inPerM + (u.cache_read_input_tokens ?? 0) * price.cacheReadPerM + (u.cache_creation_input_tokens ?? 0) * price.cacheWritePerM + (u.output_tokens ?? 0) * price.outPerM) / 1e6
        : null;
      if (cost !== null) this.spent += cost;
      answer.meta = s.showCost
        ? `${label} · ${(inTok / 1000).toFixed(1)}k in${u.cache_read_input_tokens ? ` (${(u.cache_read_input_tokens / 1000).toFixed(1)}k cached)` : ""} · ${u.output_tokens} out${cost !== null ? ` · ≈ $${cost.toFixed(4)}` : " · price unknown for this model"}`
        : label;
      this.history.push(user, { role: "assistant", content: msg.content });
    } catch (err) {
      answer.error = true;
      answer.text = describeError(err);
      if (!(err instanceof Anthropic.APIUserAbortError)) answer.meta = `${label} · nothing was saved`;
    } finally {
      this.busy = false;
      this.stream = null;
      this.render();
    }
  }

  private updateLast(t: Turn): void {
    const last = this.logEl.querySelector(".uca-msg:last-child .uca-body") as HTMLElement | null;
    if (!last) return;
    last.empty();
    last.createDiv({ cls: "uca-streaming", text: t.text });
    this.logEl.scrollTop = this.logEl.scrollHeight;
  }

  private async saveToInbox(t: Turn): Promise<void> {
    const now = new Date();
    const inbox = registry().paths.inbox;
    const idx = this.turns.indexOf(t);
    const q = this.turns.slice(0, idx).reverse().find((x) => x.role === "user")?.text ?? "assistant answer";
    const slug = q.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "answer";
    let path = normalizePath(`${inbox}/${dayKey(now)}_assistant-${slug}.md`);
    for (let i = 2; this.app.vault.getAbstractFileByPath(path); i++) path = normalizePath(`${inbox}/${dayKey(now)}_assistant-${slug}-${i}.md`);
    let answer = t.text;
    // A sign-off line from your personal reply rules belongs in chat replies, not in vault files.
    if (this.plugin.settings.stripSignoff) {
      try {
        answer = answer.replace(new RegExp(`\\n+\\s*(?:${this.plugin.settings.stripSignoff})\\s*$`), "");
      } catch {
        // an invalid pattern in the settings: keep the answer as it is
      }
    }
    const body = [
      "---",
      "type: inbox",
      `added: "${dayKey(now)}"`,
      "course: ",
      "audience: both",
      "---",
      `# Assistant answer: ${q.slice(0, 80)}`,
      "",
      `Saved from the cockpit's assistant panel, ${shortDay(now)} ${hm(now)}. Sort it into the right note (see ${registry().paths.agentDir}/CONVENTIONS.md).`,
      "",
      `> [!question] ${q.replace(/\n/g, " ")}`,
      "",
      answer,
      "",
    ].join("\n");
    if (!this.app.vault.getAbstractFileByPath(inbox)) await this.app.vault.createFolder(inbox).catch(() => undefined);
    await this.app.vault.create(path, body);
    new Notice(`Saved to ${path}`);
  }
}
