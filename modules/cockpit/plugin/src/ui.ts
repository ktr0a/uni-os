// Small DOM helpers shared by the cockpit and assistant views.

import { App, setIcon, setTooltip } from "obsidian";
import type { Meter } from "./bonus";

let palette: Record<string, { main: string; light: string }> = {};

/** Course colours (from the registry, with the settings' overrides); everything reads them from here. */
export function setPalette(p: Record<string, { main: string; light: string }>): void {
  palette = p;
}

/** A CSS-safe class suffix for a course id. */
function cls(id: string): string {
  return id.replace(/[^A-Za-z0-9_-]/g, "-");
}

export function courseVars(el: HTMLElement, id: string | null): void {
  if (!id || !palette[id]) return;
  el.style.setProperty("--c", palette[id].main);
  el.style.setProperty("--c-light", palette[id].light);
  el.addClass(`uc-course-${cls(id)}`);
}

export function dot(parent: HTMLElement, id: string | null, extra = ""): HTMLElement {
  const d = parent.createSpan({ cls: `uc-dot ${extra}` });
  courseVars(d, id);
  return d;
}

/** File types Obsidian shows itself; anything else in the vault (HTML study pages) opens in its default app. */
const OBSIDIAN_TYPES = /\.(md|canvas|base|pdf|png|jpe?g|gif|svg|webp|mp3|mp4|webm)$/i;

/** The vault file a link points to, or null when it isn't in the vault (yet). */
export function vaultTarget(app: App, path: string, source = ""): string | null {
  if (app.vault.getAbstractFileByPath(path)) return path;
  const viaLink = app.metadataCache.getFirstLinkpathDest(path.replace(/\.md$/, ""), source);
  return viaLink?.path ?? null;
}

function openVaultFile(app: App, path: string, source: string, newLeaf: boolean): void {
  if (OBSIDIAN_TYPES.test(path) || !/\.\w+$/.test(path)) void app.workspace.openLinkText(path, source, newLeaf);
  else (app as unknown as { openWithDefaultApp(p: string): void }).openWithDefaultApp(path);
}

/** Internal link that opens a vault path, with Obsidian's hover preview. Missing targets are marked, not hidden. */
export function noteLink(app: App, parent: HTMLElement, text: string, path: string, source = "", hoverParent?: unknown): HTMLAnchorElement {
  const target = vaultTarget(app, path, source);
  const a = parent.createEl("a", { cls: `internal-link uc-link${target ? "" : " is-missing"}`, text, attr: { "data-href": path, href: path } });
  if (!target) setTooltip(a, "Not in the vault yet");
  else if (!OBSIDIAN_TYPES.test(target)) setTooltip(a, "Opens in your browser");
  a.addEventListener("click", (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    openVaultFile(app, target ?? path, source, ev.ctrlKey || ev.metaKey);
  });
  if (target && /\.md$/.test(target)) {
    a.addEventListener("mouseover", (event) => {
      app.workspace.trigger("hover-link", { event, source: "uni-os-cockpit", hoverParent: hoverParent ?? a, targetEl: a, linktext: target, sourcePath: source });
    });
  }
  return a;
}

/**
 * Renders the small subset of inline Markdown used in the vault's tables and prep notes: **bold**, [text](link),
 * `code`. A `code` span that names a file in the vault (e.g. an HTML study page) becomes a link.
 */
export function inline(app: App, parent: HTMLElement, md: string, source = "", hoverParent?: unknown): void {
  const re = /\*\*([^*]+)\*\*|\[([^\]]+)\]\(<?([^)>]+)>?\)|`([^`]+)`/g;
  let last = 0;
  for (let m = re.exec(md); m; m = re.exec(md)) {
    if (m.index > last) parent.appendText(md.slice(last, m.index));
    if (m[1] !== undefined) parent.createEl("strong", { text: m[1] });
    else if (m[2] !== undefined) {
      const target = m[3];
      if (/^https?:/.test(target)) parent.createEl("a", { text: m[2], href: target, cls: "external-link" });
      else if (/^[a-z][a-z0-9+.-]*:/i.test(target)) parent.appendText(m[2]); // mailto:, javascript: and friends stay text
      else noteLink(app, parent, m[2], resolveRelative(source, target), source, hoverParent);
    } else if (m[4] !== undefined) {
      const code = m[4].trim();
      if (/^[\w\-./ &()]+\.\w{2,5}$/.test(code) && app.vault.getAbstractFileByPath(code)) noteLink(app, parent, code.split("/").pop()!, code, source, hoverParent);
      else parent.createEl("code", { text: m[4] });
    }
    last = re.lastIndex;
  }
  if (last < md.length) parent.appendText(md.slice(last));
}

/** Resolves "../x.md" against the folder of `source`, dropping any "#heading". */
export function resolveRelative(source: string, target: string): string {
  let clean = target.split("#")[0];
  try {
    clean = decodeURI(clean);
  } catch {
    // a stray "%" in a link: keep it as written
  }
  if (!source || !clean.startsWith(".")) return clean;
  const parts = source.split("/").slice(0, -1);
  for (const seg of clean.split("/")) {
    if (seg === "..") parts.pop();
    else if (seg !== ".") parts.push(seg);
  }
  return parts.join("/");
}

/** A bullet graph (Stephen Few's replacement for gauges): bar = banked, tick = full-bonus mark. */
export function meter(parent: HTMLElement, m: Meter): HTMLElement {
  const el = parent.createDiv({ cls: "uc-meter" });
  const pct = (v: number) => `${Math.max(0, Math.min(100, (v / m.max) * 100))}%`;
  if (m.ghost !== undefined) el.createDiv({ cls: "uc-meter-ghost" }).style.width = pct(m.ghost);
  el.createDiv({ cls: "uc-meter-fill" }).style.width = pct(m.value);
  if (m.marker !== undefined && m.marker < m.max) el.createDiv({ cls: "uc-meter-marker" }).style.left = pct(m.marker);
  return el;
}

export function iconButton(parent: HTMLElement, icon: string, label: string, onClick: () => void, extra = ""): HTMLButtonElement {
  const b = parent.createEl("button", { cls: `uc-btn ${extra}`, attr: { "aria-label": label } });
  const i = b.createSpan({ cls: "uc-btn-icon" });
  setIcon(i, icon);
  b.createSpan({ text: label, cls: "uc-btn-label" });
  b.addEventListener("click", onClick);
  if (extra.includes("uc-icon-only")) setTooltip(b, label);
  return b;
}

/** A titled block. `quiet` drops the box and keeps just the small heading (for minimal layouts). */
export function section(parent: HTMLElement, title: string, opts: { aside?: string; quiet?: boolean; cls?: string } = {}): { el: HTMLElement; body: HTMLElement; head: HTMLElement } {
  const el = parent.createDiv({ cls: `uc-section${opts.quiet ? " is-quiet" : ""} ${opts.cls ?? ""}` });
  const head = el.createDiv({ cls: "uc-section-head" });
  head.createDiv({ cls: "uc-section-label", text: title });
  if (opts.aside) head.createDiv({ cls: "uc-section-aside", text: opts.aside });
  const body = el.createDiv({ cls: "uc-section-body" });
  return { el, body, head };
}
