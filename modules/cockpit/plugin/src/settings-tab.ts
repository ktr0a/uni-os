import { App, PluginSettingTab, SecretComponent, Setting } from "obsidian";
import { checkKey } from "./claude";
import { morningWarnText, prepRunsText } from "./prep";
import { FeedRole, courses, moduleEnabled, registry } from "./registry";
import { CockpitSettings, Effort, FeedConfig, PRESETS, ROLE_INFO, SECTION_INFO, defaultContextNotes, mergeSettings } from "./settings";
import type UniOsCockpitPlugin from "./main";

/** Shown next to the prep settings while modules.enabled leaves daily-prep out. */
const PREP_OFF = "The daily-prep module is off, so the prep card, its presence line and its warnings are hidden.";

/** Settings changes apply live: an open cockpit redraws as you click. */
export class CockpitSettingTab extends PluginSettingTab {
  private confirmReset = false;

  constructor(
    app: App,
    private plugin: UniOsCockpitPlugin,
  ) {
    super(app, plugin);
  }

  private get s(): CockpitSettings {
    return this.plugin.settings;
  }

  private set(patch: Partial<CockpitSettings>, opts: { reload?: boolean; redisplay?: boolean } = {}): Promise<void> {
    return this.plugin.updateSettings(patch, opts.reload).then(() => {
      if (opts.redisplay) this.display();
    });
  }

  private heading(el: HTMLElement, name: string, desc?: string): void {
    const h = new Setting(el).setName(name).setHeading();
    if (desc) h.setDesc(desc);
  }

  private setFeed(i: number, patch: Partial<FeedConfig>, redisplay = false): Promise<void> {
    const feeds = this.s.feeds.map((f, j) => (j === i ? { ...f, ...patch } : { ...f }));
    return this.set({ feeds }, { redisplay }).then(() => this.plugin.requestRefresh(0));
  }

  display(): void {
    const el = this.containerEl;
    const s = this.s;
    const reg = registry();
    const prepOn = moduleEnabled("daily-prep");
    el.empty();
    el.addClass("uni-cockpit-settings");

    // ---------- presets ----------
    this.heading(el, "Start from a preset", "Each preset sets layout, colours, density and width in one click. Everything below can then be fine-tuned.");
    const presets = el.createDiv({ cls: "ucs-presets" });
    for (const p of PRESETS) {
      const b = presets.createEl("button", { cls: "ucs-preset" });
      b.createDiv({ cls: "ucs-preset-name", text: p.label });
      b.createDiv({ cls: "ucs-preset-desc", text: p.desc });
      const matches = Object.entries(p.apply).every(([k, v]) => k === "sections" || JSON.stringify((s as unknown as Record<string, unknown>)[k]) === JSON.stringify(v));
      if (matches) b.addClass("is-active");
      b.addEventListener("click", () => this.set(p.apply, { redisplay: true }));
    }

    // ---------- general ----------
    this.heading(el, "General");
    new Setting(el)
      .setName("Home layout")
      .setDesc("Focus: one screen, only what matters now. Dashboard: the sections you pick, in your order. Agenda: today and the next days as one list.")
      .addDropdown((d) => d.addOptions({ focus: "Focus", dashboard: "Dashboard", agenda: "Agenda" }).setValue(s.layout).onChange((v) => this.set({ layout: v as CockpitSettings["layout"] }, { redisplay: true })));
    new Setting(el)
      .setName("Page the cockpit opens on")
      .addDropdown((d) => d.addOptions({ home: "Home", week: "Week", courses: "Courses" }).setValue(s.defaultTab).onChange((v) => this.set({ defaultTab: v as CockpitSettings["defaultTab"] })));
    new Setting(el)
      .setName("Open the cockpit when Obsidian starts")
      .setDesc("Off keeps Home.md as the first page; the cockpit stays one click away (ribbon icon, the banner on Home, or a command).")
      .addToggle((t) => t.setValue(s.openOnStartup).onChange((v) => this.set({ openOnStartup: v })));
    new Setting(el)
      .setName("Banner in notes")
      .setDesc("What a ```uni-os-cockpit``` block (the one at the top of Home) shows.")
      .addToggle((t) => t.setTooltip("Show the banner").setValue(s.bannerEnabled).onChange((v) => this.set({ bannerEnabled: v })))
      .addDropdown((d) => d.addOptions({ next: "Next event only", due: "Next event + open deadlines" }).setValue(s.bannerDue ? "due" : "next").onChange((v) => this.set({ bannerDue: v === "due" })));
    new Setting(el)
      .setName("Source line at the bottom")
      .setDesc("Which notes the page was read from and when the calendar was fetched.")
      .addToggle((t) => t.setValue(s.showFooter).onChange((v) => this.set({ showFooter: v })));

    // ---------- appearance ----------
    this.heading(el, "Appearance", "Follows Obsidian's light or dark theme.");
    new Setting(el)
      .setName("Colours")
      .setDesc("Course accents: neutral page, course colours on dots, bars and block edges. Monochrome: grey everywhere, colour only on the small course dots. Vivid: filled colour blocks.")
      .addDropdown((d) => d.addOptions({ accent: "Course accents", mono: "Monochrome", vivid: "Vivid blocks" }).setValue(s.colorMode).onChange((v) => this.set({ colorMode: v as CockpitSettings["colorMode"] })));
    new Setting(el).setName("Spacing").addDropdown((d) => d.addOptions({ comfortable: "Comfortable", compact: "Compact" }).setValue(s.density).onChange((v) => this.set({ density: v as CockpitSettings["density"] })));
    new Setting(el)
      .setName("Text size")
      .setDesc("In percent of Obsidian's interface size.")
      .addSlider((sl) => sl.setLimits(80, 130, 5).setValue(s.fontScale).setDynamicTooltip().onChange((v) => this.set({ fontScale: v })));
    new Setting(el)
      .setName("Content width")
      .addDropdown((d) => d.addOptions({ narrow: "Narrow (reading column)", medium: "Medium", wide: "Wide", full: "Full width" }).setValue(s.width).onChange((v) => this.set({ width: v as CockpitSettings["width"] })));
    const colours = new Setting(el)
      .setName("Course colours")
      .setDesc("Lecture and exercise-class colour per course. The defaults come from uni-os.toml (courses[].colour, colour_light); keep them in step with your calendar colours.");
    colours.addExtraButton((b) =>
      b
        .setIcon("rotate-ccw")
        .setTooltip("Back to the colours from the config")
        .onClick(() => this.set({ courseColors: {} }, { redisplay: true })),
    );
    for (const c of courses()) {
      const cur = { main: s.courseColors[c.id]?.main || c.colour, light: s.courseColors[c.id]?.light || c.colourLight };
      new Setting(el)
        .setClass("ucs-indent")
        .setName(c.short)
        .addColorPicker((p) => p.setValue(cur.main).onChange((v) => this.set({ courseColors: { ...s.courseColors, [c.id]: { ...s.courseColors[c.id], main: v } } })))
        .addColorPicker((p) => p.setValue(cur.light).onChange((v) => this.set({ courseColors: { ...s.courseColors, [c.id]: { ...s.courseColors[c.id], light: v } } })));
    }

    // ---------- layouts ----------
    this.heading(el, "Focus layout");
    new Setting(el)
      .setName("Deadlines shown")
      .setDesc("The rest sit behind “more due this week”.")
      .addSlider((sl) => sl.setLimits(1, 8, 1).setValue(s.focusDueCount).setDynamicTooltip().onChange((v) => this.set({ focusDueCount: v })));
    new Setting(el).setName("Day strip").setDesc("A thin bar of today's events under the headline.").addToggle((t) => t.setValue(s.focusStrip).onChange((v) => this.set({ focusStrip: v })));
    new Setting(el).setName("Bonus row").addToggle((t) => t.setValue(s.focusBonus).onChange((v) => this.set({ focusBonus: v })));
    new Setting(el)
      .setName("Prep card")
      .setDesc(`The next block opens, the others fold; Dashboard has it as a section, Agenda under each block.${prepOn ? "" : ` ${PREP_OFF}`}`)
      .addToggle((t) => t.setValue(s.focusPrep).onChange((v) => this.set({ focusPrep: v })));

    this.heading(el, "Dashboard layout", "Switch sections on or off and move them. Wide sections span the page; the others flow into columns in this order.");
    s.sections.forEach((sec, i) => {
      const info = SECTION_INFO[sec.id];
      new Setting(el)
        .setClass("ucs-indent")
        .setName(info.label)
        .setDesc(sec.id === "prep" && !prepOn ? `${info.desc} ${PREP_OFF}` : info.desc)
        .addExtraButton((b) =>
          b
            .setIcon("arrow-up")
            .setTooltip("Move up")
            .setDisabled(i === 0)
            .onClick(() => {
              const next = s.sections.map((x) => ({ ...x }));
              [next[i - 1], next[i]] = [next[i], next[i - 1]];
              void this.set({ sections: next }, { redisplay: true });
            }),
        )
        .addExtraButton((b) =>
          b
            .setIcon("arrow-down")
            .setTooltip("Move down")
            .setDisabled(i === s.sections.length - 1)
            .onClick(() => {
              const next = s.sections.map((x) => ({ ...x }));
              [next[i + 1], next[i]] = [next[i], next[i + 1]];
              void this.set({ sections: next }, { redisplay: true });
            }),
        )
        .addToggle((t) => t.setValue(sec.on).onChange((v) => this.set({ sections: s.sections.map((x, j) => (j === i ? { ...x, on: v } : { ...x })) })));
    });

    this.heading(el, "Agenda layout");
    new Setting(el).setName("Days shown").addSlider((sl) => sl.setLimits(1, 7, 1).setValue(s.agendaDays).setDynamicTooltip().onChange((v) => this.set({ agendaDays: v })));
    new Setting(el).setName("Fold away what's over today").addToggle((t) => t.setValue(s.agendaFoldPast).onChange((v) => this.set({ agendaFoldPast: v })));
    new Setting(el)
      .setName("FOCUS lines of the current block")
      .setDesc("0 hides them.")
      .addSlider((sl) => sl.setLimits(0, 8, 1).setValue(s.agendaFocusLines).setDynamicTooltip().onChange((v) => this.set({ agendaFocusLines: v })));

    // ---------- live calendar ----------
    this.heading(
      el,
      "Live calendar (iCal feeds)",
      "Reads your calendars straight from their private iCal addresses, every few minutes while Obsidian is open. Read-only. Calendars without an address keep using the snapshot file that your agents write.",
    );
    const how = el.createDiv({ cls: "ucs-steps" });
    how.createDiv({
      text: "Getting an address (Google): Google Calendar on the web → ⚙ Settings → under “Settings for my calendars” pick the calendar → Integrate calendar → “Secret address in iCal format” → copy. Outlook: Settings → Calendar → Shared calendars → Publish a calendar → ICS link. Apple iCloud: share the calendar as a public calendar and copy the webcal link.",
    });
    how.createDiv({
      text: "Then here: Link… → Add secret… → name it (e.g. ical-courses), paste, select it, Save. The address stays in Obsidian's secret storage on this device, never in the vault. Treat it like a password: anyone with it can read that calendar; you can reset it at the provider. Your agent must never copy or type these addresses for you.",
    });
    s.feeds.forEach((f, i) => {
      const row = new Setting(el)
        .setClass("ucs-indent")
        .setName(f.label)
        .setDesc(`id "${f.id}" · ${ROLE_INFO[f.role].desc}`)
        .addText((t) => t.setPlaceholder("Label").setValue(f.label).onChange((v) => void this.setFeed(i, { label: v.trim() || f.id })))
        .addDropdown((d) =>
          d
            .addOptions(Object.fromEntries(Object.entries(ROLE_INFO).map(([k, v]) => [k, v.label])))
            .setValue(f.role)
            .onChange((v) => void this.setFeed(i, { role: v as FeedRole }, true)),
        )
        .addComponent((c) => new SecretComponent(this.app, c).setValue(f.secret).onChange((v) => void this.setFeed(i, { secret: v ?? "" })))
        .addToggle((t) =>
          t
            .setTooltip("Use this feed")
            .setValue(f.on)
            .onChange((v) => void this.setFeed(i, { on: v })),
        );
      if (!reg.calendars.some((c) => c.id === f.id)) {
        row.addExtraButton((b) =>
          b
            .setIcon("trash-2")
            .setTooltip("Remove this calendar")
            .onClick(() => void this.set({ feeds: s.feeds.filter((_, j) => j !== i) }, { redisplay: true }).then(() => this.plugin.requestRefresh(0))),
        );
      }
    });
    new Setting(el)
      .setClass("ucs-indent")
      .setName("Add a calendar")
      .setDesc("For a second study or busy calendar. Agents writing the snapshot use the id as the event's \"cal\".")
      .addButton((b) =>
        b.setButtonText("Add").onClick(() => {
          let n = s.feeds.length + 1;
          while (s.feeds.some((f) => f.id === `calendar-${n}`)) n++;
          void this.set({ feeds: [...s.feeds, { id: `calendar-${n}`, label: `Calendar ${n}`, role: "study", secret: "", on: true }] }, { redisplay: true });
        }),
      );
    const feedCheck = new Setting(el).setName("Check the feeds").setDesc("Fetches every linked calendar now and compares it with the snapshot file.");
    feedCheck.addButton((b) =>
      b.setButtonText("Check").onClick(async () => {
        b.setDisabled(true).setButtonText("Checking…");
        const r = await this.plugin.checkFeeds();
        b.setDisabled(false).setButtonText("Check");
        feedCheck.setDesc(r.text);
        feedCheck.descEl.toggleClass("ucs-ok", r.ok);
        feedCheck.descEl.toggleClass("ucs-bad", !r.ok);
        feedCheck.descEl.style.whiteSpace = "pre-line";
      }),
    );
    new Setting(el)
      .setName("Fetch every")
      .setDesc("minutes, while Obsidian is open. The last good copy is kept on this device for offline use.")
      .addSlider((sl) => sl.setLimits(5, 60, 5).setValue(s.feedMinutes).setDynamicTooltip().onChange((v) => this.set({ feedMinutes: v })));
    new Setting(el)
      .setName("Keep the vault's calendar snapshot up to date")
      .setDesc(`Rewrites ${reg.paths.snapshot} (this week and next) whenever the live calendar changes, so agents reading the vault see the same calendar. Busy-only calendars stay time only there.`)
      .addToggle((t) => t.setValue(s.feedWriteSnapshot).onChange((v) => this.set({ feedWriteSnapshot: v })));
    new Setting(el)
      .setName("Show titles from busy-only calendars")
      .setDesc("Off: they show as “Busy”. Only affects this device's view; the snapshot file never gets them.")
      .addToggle((t) =>
        t.setValue(s.personalTitles).onChange(async (v) => {
          await this.set({ personalTitles: v });
          await this.plugin.feeds.refresh(true);
          this.plugin.requestRefresh(0);
        }),
      );

    const hours = (from: number, to: number) => Object.fromEntries(Array.from({ length: to - from + 1 }, (_, i) => [String(from + i), `${String(from + i).padStart(2, "0")}:00`]));

    // ---------- study prep ----------
    const runs = prepRunsText();
    const warn = morningWarnText();
    if (!prepOn) {
      this.heading(el, "Study prep", `${PREP_OFF} Turn it on with \`python tools/uni_os.py enable daily-prep\`; the plugin picks the change up by itself.`);
    } else {
      this.heading(
        el,
        "Study prep",
        `Material per block from the daily prep note (${reg.paths.prep}${runs ? `; the jobs ${runs}` : ""}, from schedule.daily_prep and schedule.prep_check).${warn ? ` If today's is missing, the warning starts at ${warn}.` : ""}`,
      );
      new Setting(el)
        .setName("Show tomorrow's prep from")
        .setDesc("Before this hour the card shows today's prep.")
        .addDropdown((d) => d.addOptions(hours(12, 23)).setValue(String(s.prepSwitchHour)).onChange((v) => this.set({ prepSwitchHour: Number(v) }, { reload: true })));
      const halfHours = Object.fromEntries(
        Array.from({ length: 14 }, (_, i) => {
          const m = 17 * 60 + i * 30;
          const t = `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
          return [t, t];
        }),
      );
      if (!(s.prepWarnAfter in halfHours)) halfHours[s.prepWarnAfter] = s.prepWarnAfter;
      new Setting(el)
        .setName("Warn when tomorrow's prep is still missing after")
        .addDropdown((d) => d.addOptions(halfHours).setValue(s.prepWarnAfter).onChange((v) => this.set({ prepWarnAfter: v }, { reload: true })));
    }

    this.heading(el, "Calendar and timeline");
    new Setting(el)
      .setName("Day runs from")
      .setDesc("The range of the timeline and the week grid.")
      .addDropdown((d) => d.addOptions(hours(5, 12)).setValue(String(s.dayStart)).onChange((v) => this.set({ dayStart: Number(v) })))
      .addDropdown((d) => d.addOptions(hours(15, 24)).setValue(String(s.dayEnd)).onChange((v) => this.set({ dayEnd: Number(v) })));
    new Setting(el).setName("Stretch to fit early or late events").addToggle((t) => t.setValue(s.fitDay).onChange((v) => this.set({ fitDay: v })));
    new Setting(el).setName("Busy time from busy-only calendars").setDesc("Shown without titles.").addToggle((t) => t.setValue(s.showPersonal).onChange((v) => this.set({ showPersonal: v })));
    new Setting(el).setName("Optional blocks").setDesc("Blocks titled “(X)” or “OP …” in the block notation.").addToggle((t) => t.setValue(s.showOptional).onChange((v) => this.set({ showOptional: v })));
    new Setting(el).setName("Weekend in the week grid").addToggle((t) => t.setValue(s.showWeekend).onChange((v) => this.set({ showWeekend: v })));
    new Setting(el).setName("Hour height in the week grid").addSlider((sl) => sl.setLimits(28, 96, 4).setValue(s.hourHeight).setDynamicTooltip().onChange((v) => this.set({ hourHeight: v })));
    new Setting(el)
      .setName("Warn when the calendar snapshot is older than")
      .setDesc("days")
      .addSlider((sl) => sl.setLimits(1, 7, 1).setValue(s.staleDays).setDynamicTooltip().onChange((v) => this.set({ staleDays: v }, { reload: true })));

    // ---------- deadlines ----------
    this.heading(el, "Deadlines");
    new Setting(el)
      .setName("Flag a deadline as urgent when it is less than")
      .setDesc("hours away (0 = never). Urgent ones show under the headline in the alert colour.")
      .addSlider((sl) => sl.setLimits(0, 72, 6).setValue(s.urgentHours).setDynamicTooltip().onChange((v) => this.set({ urgentHours: v })));
    new Setting(el)
      .setName("Countdown")
      .addDropdown((d) => d.addOptions({ relative: "in 2 h 15 min", absolute: "today 23:59", both: "today 23:59 · in 2 h 15 min" }).setValue(s.countdown).onChange((v) => this.set({ countdown: v as CockpitSettings["countdown"] })));
    new Setting(el)
      .setName("Personal targets")
      .setDesc("The week page's target column (e.g. “Sunday target”), while the date is still ahead.")
      .addToggle((t) => t.setValue(s.showTarget).onChange((v) => this.set({ showTarget: v })));
    new Setting(el)
      .setName("Finished items")
      .addDropdown((d) => d.addOptions({ hide: "Hide", collapsed: "Folded away", show: "Show" }).setValue(s.showDone).onChange((v) => this.set({ showDone: v as CockpitSettings["showDone"] })));

    // ---------- bonus ----------
    this.heading(el, "Bonus", "The rules come from uni-os.toml ([courses.bonus]); the banked numbers from each course card's bonus_banked / bonus_target properties.");
    new Setting(el)
      .setName("Figure next to each course")
      .addDropdown((d) =>
        d
          .addOptions({ points: "Points (40 / 50)", bonus: "Bonus (+0.125)", percent: "Share of the full bonus (50 %)" })
          .setValue(s.bonusFigure)
          .onChange((v) => this.set({ bonusFigure: v as CockpitSettings["bonusFigure"] })),
      );
    for (const c of courses().filter((x) => x.bonus.scheme === "threshold")) {
      new Setting(el)
        .setClass("ucs-indent")
        .setName(`${c.short}: total points (estimate)`)
        .setDesc(`Only when the course doesn't publish its maximum. Empty: the card's "~N pts" in bonus_target, else bonus.total. Full bonus = ${Math.round(c.bonus.threshold * 100)} % of it.`)
        .addText((t) =>
          t
            .setPlaceholder("e.g. 120")
            .setValue(s.totalOverrides[c.id] ? String(s.totalOverrides[c.id]) : "")
            .onChange((v) => {
              const n = Number(v);
              const next = { ...s.totalOverrides };
              if (v.trim() === "" || !(n > 0)) delete next[c.id];
              else next[c.id] = n;
              void this.set({ totalOverrides: next }, { reload: true });
            }),
        );
    }

    // ---------- assistant ----------
    this.heading(el, "Assistant", "Answers from your notes with Claude, on your own API key. It never edits notes or the calendar; “Save to inbox” is the only write.");
    new Setting(el)
      .setName("Anthropic API key")
      .setDesc("Pick or create a secret in Obsidian's secret storage. The key stays on this device: it is not written into the vault, so it never syncs or lands in git. Use a workspace-scoped key with a monthly spend limit. Your agent must never type a key for you.")
      .addComponent((c) =>
        new SecretComponent(this.app, c).setValue(s.apiKeySecret).onChange(async (v) => {
          await this.set({ apiKeySecret: v ?? "" });
          this.plugin.refreshAssistants();
        }),
      );
    const check = new Setting(el).setName("Check the key").setDesc("Sends one tiny request to the fast model (a fraction of a cent) and tells you whether the key, the network and the settings work.");
    check.addButton((b) =>
      b.setButtonText("Check").onClick(async () => {
        b.setDisabled(true).setButtonText("Checking…");
        const r = await checkKey(this.app, s);
        b.setDisabled(false).setButtonText("Check");
        check.setDesc(r.text);
        check.descEl.toggleClass("ucs-ok", r.ok);
        check.descEl.toggleClass("ucs-bad", !r.ok);
      }),
    );
    new Setting(el)
      .setName("Model")
      .setDesc("Auto: the fast model for lookups, the strong one for explanations, plans and anything with the open note.")
      .addDropdown((d) => d.addOptions({ auto: "Auto (recommended)", fast: "Fast model only (cheapest)", strong: "Strong model only" }).setValue(s.model).onChange((v) => this.set({ model: v as CockpitSettings["model"] })));
    new Setting(el)
      .setName("Model ids")
      .setDesc("Fast, then strong. The cost line knows the prices of claude-haiku-5-5 and claude-sonnet-5-5; other ids show tokens only.")
      .addText((t) => t.setValue(s.fastModel).onChange((v) => this.set({ fastModel: v.trim() || "claude-haiku-5-5" })))
      .addText((t) => t.setValue(s.strongModel).onChange((v) => this.set({ strongModel: v.trim() || "claude-sonnet-5-5" })));
    const efforts = { low: "Low (fast)", medium: "Medium", high: "High (thorough)" };
    new Setting(el)
      .setName("Effort")
      .setDesc("How much the model thinks before answering: fast model, then strong model. More effort costs more tokens.")
      .addDropdown((d) => d.addOptions(efforts).setValue(s.effortFast).onChange((v) => this.set({ effortFast: v as Effort })))
      .addDropdown((d) => d.addOptions(efforts).setValue(s.effortStrong).onChange((v) => this.set({ effortStrong: v as Effort })));
    new Setting(el)
      .setName("Longest answer")
      .setDesc("Output cap per reply, in tokens. A cost guard.")
      .addSlider((sl) => sl.setLimits(1000, 16000, 1000).setValue(s.maxTokens).setDynamicTooltip().onChange((v) => this.set({ maxTokens: v })));
    new Setting(el).setName("Show tokens and cost under each answer").addToggle((t) => t.setValue(s.showCost).onChange((v) => this.set({ showCost: v })));
    new Setting(el)
      .setName("Strip a sign-off when saving to the inbox")
      .setDesc("A regular expression for a last line your personal reply rules add (it belongs in chat, not in vault notes). Empty: nothing is stripped.")
      .addText((t) => t.setPlaceholder("e.g. Cheers!").setValue(s.stripSignoff).onChange((v) => this.set({ stripSignoff: v })));
    new Setting(el)
      .setClass("ucs-wide")
      .setName("Quick questions")
      .setDesc("One per line; shown as buttons above the input.")
      .addTextArea((t) => {
        t.setValue(s.quickAsks.join("\n")).onChange((v) => this.set({ quickAsks: v.split("\n").map((x) => x.trim()).filter(Boolean) }));
        t.inputEl.rows = 5;
      });
    new Setting(el)
      .setClass("ucs-wide")
      .setName("Notes the assistant reads")
      .setDesc(`One path per line. The rules note (${reg.paths.rules}) and the current week page are always included. More notes = more context and a higher cost per question. Clear the box to go back to the default list.`)
      .addTextArea((t) => {
        t.setValue((s.contextNotes ?? defaultContextNotes(reg)).join("\n")).onChange((v) => {
          const lines = v.split("\n").map((x) => x.trim()).filter(Boolean);
          void this.set({ contextNotes: lines.length ? lines : null });
        });
        t.inputEl.rows = 8;
      });
    new Setting(el)
      .setName("Prompt template")
      .setDesc(`The assistant's instructions come from ${reg.paths.prompt} (the fenced block under “System prompt”), with {student}, {courses}, {integrity} and the other placeholders filled from the config. Without that note a built-in template is used.`);
    new Setting(el)
      .setName("Workspace ID")
      .setDesc("Only for organisation-wide keys (wrkspc_…). Leave empty with a workspace-scoped key.")
      .addText((t) => t.setPlaceholder("wrkspc_…").setValue(s.workspaceId).onChange((v) => this.set({ workspaceId: v.trim() })));
    new Setting(el)
      .setName("API base URL")
      .setDesc("Leave empty for api.anthropic.com. Only for testing against a local stand-in.")
      .addText((t) => t.setPlaceholder("https://api.anthropic.com").setValue(s.baseUrl).onChange((v) => this.set({ baseUrl: v.trim() })));

    // ---------- data ----------
    this.heading(el, "Where the data comes from", "Paths, courses, schedules and vocabulary come from the config, not from these settings: edit _agent/uni-os.toml (or ask your agent) and run `python tools/uni_os.py render`.");
    new Setting(el)
      .setName("Config file")
      .setDesc(`Generated from uni-os.toml. ${reg.loaded ? `Read: ${courses().length} course${courses().length === 1 ? "" : "s"}, time zone ${reg.term.timezone}, week 0 = ${reg.term.week0 ?? "not set"}.` : "Not found."}`)
      .addText((t) => t.setValue(s.configPath).onChange((v) => this.set({ configPath: v.trim() || "_agent/uni-os.json" })))
      .addButton((b) =>
        b.setButtonText("Reload").onClick(async () => {
          await this.plugin.loadRegistry();
          await this.plugin.refreshNow();
          this.display();
        }),
      );
    const paths = el.createDiv({ cls: "ucs-steps" });
    for (const [k, v] of [
      ["Progress page", reg.paths.status],
      ["Week pages", reg.paths.weeks],
      ["Week plans", reg.paths.plans],
      ["Prep notes", reg.paths.prep],
      ["Inbox (Done taps)", reg.paths.inbox],
      ["Calendar snapshot", reg.paths.snapshot],
      ["Rules for AI", reg.paths.rules],
      ["Course cards", courses().map((c) => c.card).join(", ") || "none"],
    ])
      paths.createDiv({ text: `${k}: ${v}` });
    for (const p of reg.problems) paths.createDiv({ cls: "ucs-bad", text: p });

    // ---------- reset ----------
    new Setting(el)
      .setName("Reset everything to the defaults")
      .setDesc("Reads the [cockpit] defaults from the config again. Keeps the API key and the calendar addresses in secret storage; only the links to them are cleared.")
      .addButton((b) =>
        b
          .setButtonText(this.confirmReset ? "Click again to reset" : "Reset")
          .setWarning()
          .onClick(async () => {
            if (!this.confirmReset) {
              this.confirmReset = true;
              this.display();
              return;
            }
            this.confirmReset = false;
            this.plugin.settings = mergeSettings({ configPath: s.configPath }, registry());
            await this.plugin.updateSettings({}, true);
            this.display();
          }),
      );
  }
}
