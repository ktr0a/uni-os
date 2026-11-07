// Markdown helpers shared by the parsers. Pure: no Obsidian or DOM imports, so the parsers and their
// tests run under plain Node.

export function stripFrontmatter(md: string): string {
  if (!md.startsWith("---")) return md;
  const end = md.indexOf("\n---", 3);
  return end === -1 ? md : md.slice(md.indexOf("\n", end + 4) + 1);
}

/** Flat `key: value` frontmatter (enough for the properties the cockpit reads). Quotes around values are dropped. */
export function frontmatter(text: string): Record<string, string> {
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  const out: Record<string, string> = {};
  if (!m) return out;
  for (const line of m[1].split(/\r?\n/)) {
    const kv = /^([A-Za-z_][\w-]*):\s*(.*)$/.exec(line);
    if (kv) out[kv[1]] = kv[2].trim().replace(/^"(.*)"$/, "$1").replace(/^'(.*)'$/, "$1");
  }
  return out;
}

/**
 * Body under a heading (any level) whose text starts with `title` (case-insensitive), up to the next heading of
 * the same or a higher level. `title` may also be a RegExp tested against the heading text.
 */
export function section(md: string, title: string | RegExp): string | null {
  const lines = md.split(/\r?\n/);
  let start = -1;
  let level = 0;
  const matches = (h: string) => (typeof title === "string" ? h.trim().toLowerCase().startsWith(title.toLowerCase()) : title.test(h.trim()));
  for (let i = 0; i < lines.length; i++) {
    const m = /^(#{1,6})\s+(.*)$/.exec(lines[i]);
    if (!m) continue;
    if (start === -1) {
      if (matches(m[2])) {
        start = i + 1;
        level = m[1].length;
      }
    } else if (m[1].length <= level) {
      return lines.slice(start, i).join("\n").trim();
    }
  }
  return start === -1 ? null : lines.slice(start).join("\n").trim();
}

/** Sub-sections ("### AD", "### DM", ...) of a block, keyed by heading text. */
export function subsections(md: string): Array<{ title: string; body: string }> {
  const out: Array<{ title: string; body: string }> = [];
  let cur: { title: string; lines: string[] } | null = null;
  for (const line of md.split(/\r?\n/)) {
    const m = /^#{2,6}\s+(.*)$/.exec(line);
    if (m) {
      if (cur) out.push({ title: cur.title, body: cur.lines.join("\n").trim() });
      cur = { title: m[1].trim(), lines: [] };
    } else if (cur) cur.lines.push(line);
  }
  if (cur) out.push({ title: cur.title, body: cur.lines.join("\n").trim() });
  return out;
}

function splitRow(line: string): string[] {
  // Protect escaped pipes and wikilink aliases before splitting.
  const safe = line.replace(/\\\|/g, "\u0000").replace(/\[\[([^\]]*?)\|([^\]]*?)\]\]/g, (_m, a, b) => `[[${a}\u0000${b}]]`);
  let cells = safe.trim().split("|");
  if (cells[0].trim() === "") cells = cells.slice(1);
  if (cells.length && cells[cells.length - 1].trim() === "") cells = cells.slice(0, -1);
  return cells.map((c) => c.replace(/\u0000/g, "|").trim());
}

/** First Markdown table in a block, as header + rows of cells. */
export function firstTable(md: string): { header: string[]; rows: string[][] } | null {
  const lines = md.split(/\r?\n/);
  for (let i = 0; i + 1 < lines.length; i++) {
    if (/^\s*\|/.test(lines[i]) && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
      const header = splitRow(lines[i]);
      const rows: string[][] = [];
      for (let j = i + 2; j < lines.length && /^\s*\|/.test(lines[j]); j++) rows.push(splitRow(lines[j]));
      return { header, rows };
    }
  }
  return null;
}

/** Plain text of an inline-markdown cell (for matching, not display). */
export function plain(s: string): string {
  return s
    .replace(/\*\*|__/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/`/g, "")
    .trim();
}

export function firstNumberPair(s: string): { a: number; b: number } | null {
  const m = /(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)/.exec(plain(s));
  return m ? { a: parseFloat(m[1]), b: parseFloat(m[2]) } : null;
}

/** A figure as the notes write it: whole, or with at most `digits` decimals (2.33, not 2.3333). */
export function num(n: number, digits = 2): string {
  const f = 10 ** digits;
  return Number.isInteger(n) ? String(n) : String(Math.round(n * f) / f);
}

/** Escapes a literal for use inside a RegExp. */
export function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
