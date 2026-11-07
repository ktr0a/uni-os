// Anthropic API client for the assistant panel and the key check in the settings.
// The key is read from Obsidian's secret storage on this device; it is never written into the vault.

import Anthropic from "@anthropic-ai/sdk";
import type { App } from "obsidian";
import type { CockpitSettings } from "./settings";

export function apiKey(app: App, s: CockpitSettings): string | null {
  return s.apiKeySecret ? app.secretStorage.getSecret(s.apiKeySecret) || null : null;
}

export function makeClient(key: string, s: CockpitSettings): Anthropic {
  return new Anthropic({
    apiKey: key,
    baseURL: s.baseUrl || undefined,
    // Obsidian is a browser page as far as the SDK is concerned; the key never leaves this device
    // except to the API itself.
    dangerouslyAllowBrowser: true,
    maxRetries: 1,
    defaultHeaders: s.workspaceId ? { "anthropic-workspace-id": s.workspaceId } : undefined,
  });
}

export function describeError(err: unknown): string {
  if (err instanceof Anthropic.APIUserAbortError) return "Stopped.";
  if (err instanceof Anthropic.AuthenticationError) return "The API key was rejected (401). Check the key in the Uni OS cockpit settings.";
  if (err instanceof Anthropic.PermissionDeniedError) return `The key isn't allowed to do this (403): ${err.message}`;
  if (err instanceof Anthropic.NotFoundError) return `Not found (404): ${err.message}. Is the model id in the settings right?`;
  if (err instanceof Anthropic.BadRequestError) {
    return /workspace/i.test(err.message)
      ? `${err.message}\n\nThis happens with organisation-wide keys. Easiest fix: create a key inside one workspace (Console → API keys → Create key → pick a workspace). Or put the workspace ID into the settings.`
      : `Bad request (400): ${err.message}`;
  }
  if (err instanceof Anthropic.RateLimitError) return "Rate limited (429). Wait a minute and try again.";
  if (err instanceof Anthropic.APIConnectionError) return `Couldn't reach the API: ${err.message}`;
  if (err instanceof Anthropic.APIError) return `API error ${err.status ?? ""}: ${err.message}`;
  return `Something went wrong: ${(err as Error)?.message ?? String(err)}`;
}

/** One tiny request to the fast model (a fraction of a cent) to prove the key, network and headers work. */
export async function checkKey(app: App, s: CockpitSettings): Promise<{ ok: boolean; text: string }> {
  const key = apiKey(app, s);
  if (!key) return { ok: false, text: "No key linked yet: pick or create a secret above first." };
  const started = Date.now();
  try {
    const msg = await makeClient(key, s).messages.create({
      model: s.fastModel,
      max_tokens: 256,
      output_config: { effort: "low" },
      messages: [{ role: "user", content: "Reply with the single word OK." }],
    });
    const text = msg.content.map((b) => (b.type === "text" ? b.text : "")).join("").trim();
    return { ok: true, text: `The key works: ${msg.model} answered “${text || "(no text)"}” in ${((Date.now() - started) / 1000).toFixed(1)} s.` };
  } catch (err) {
    return { ok: false, text: describeError(err) };
  }
}
