Host performance verdict for {{student.name}}'s always-on host `{{vm.host_alias}}` (provider: {{vm.provider}}; machine: {{vm.machine_type}}). Weekly. Change nothing on the host and nothing in the vault: the only file you write is `~/.local/state/uni-os/perf-verdicts.md` (append one block), plus your failure flag when a run fails (see the end).

Read first: `_agent/agent-start.md`, `_agent/rules.md`, `_agent/vm.md`.

0. **Already done?** Get the date with `date`. If the newest `### ` block in `~/.local/state/uni-os/perf-verdicts.md` is dated today, reply "Verdict already written today" and stop (a manual re-run or a catch-up must not add a second block).

1. **Gather.** `uni-vm perf 7d`, `uni-vm perf 24h`, `uni-vm status`, `uni-vm roles list`, `uni-vm jobs sessions`, `_agent/vm/performance.md`, `grep EVENT ~/.local/state/uni-os/health.log | tail -n 20`, and the raw samples `~/.local/state/uni-os/perf.csv` (one line per health run; columns: epoch, MB available, swap used MB, load1, CPU steal %, agent sessions, OOM kills since boot, swap-in pages since boot). Find the peak (most sessions, least memory) and when it was. Measure the footprint per session now: `ps -u "$(id -un)" -o rss,args --sort=-rss | head -n 25` (RSS in KB; group the agent processes: persistent role sessions, headless job runs, the Remote Control server).
2. **Judge on the evidence:**
   - **enough**: memory available stays above ~800 MB at the peak, no OOM kill, negligible swap-in, CPU steal low, load rarely above 2.
   - **tight**: the minimum is 300-800 MB, swap use grows or comes in bursts of swap-in, but no OOM kill.
   - **upgrade**: any OOM kill, swap thrashing, under 300 MB available for 15+ minutes, or sessions noticeably slow.
3. **Later candidates.** From the routing table in `_agent/roles/README.md` (if it exists), count the roles that run elsewhere (laptop or cloud) and could move here. Would they fit? Estimate from the measured footprint per session and the peak.
4. **Cost.**
   - Cloud host: if the verdict is "upgrade", or the candidates would need more memory, name the machine type and its monthly cost. Price, with current list prices from the provider's pricing page (Google Cloud: fetch `https://cloud.google.com/compute/vm-instance-pricing`; In Claude Code: WebFetch; the host's region, 730 hours a month; a custom E2 machine costs the vCPU-hour rate times vCPUs plus the GB-hour rate times GB, plus the custom-machine surcharge): the current machine with 1.5x and 2x the memory (same vCPU), and the next standard type. For each: the monthly total including the public IP and the snapshots, and the out-of-pocket amount after a monthly cloud credit of {{vm.monthly_credit}} {{vm.budget_currency}}, against the budget of {{vm.budget_month}} {{vm.budget_currency}}. A resize stops the host for about 2 minutes (modules/vm/MAINTENANCE.md, "Resizing"): the student does it, not you.
   - Home server: no prices. Name what would help instead: IDLE_STOP_H for on-demand roles, fewer open job sessions, more memory for Linux in `.wslconfig`, or moving a role back to the laptop or the cloud.
5. **Append** to `~/.local/state/uni-os/perf-verdicts.md` exactly this block:
   ```
   ### <Ddd DD Mon YYYY HH:MM> verdict: enough|tight|upgrade
   - Peak: <sessions> sessions at <when>, <MB> MB available, swap <MB>, load <x>
   - Typical: <MB> MB available, <n> sessions
   - OOM kills / thrashing / steal: ...
   - Later candidates (<n> more sessions): fit / don't fit, because ...
   - If upgrade: <machine>, <price>/month, ~<out of pocket> vs <budget> budget (home server: what to change)
   ```
   The host's health check copies the latest verdict into `_agent/vm/performance.md` within one run.
{{#if modules.roles}}
6. **Tell the coordinator.** Send that block as plain text to the coordinator session: its title is the `title` in the frontmatter of `_agent/roles/coordinator.md`, and which session hosts it now is in the live roster of `_agent/coordinator-state.md` (In Claude Code: SendMessage; load SendMessage and ListAgents with tool search first). If it isn't listed or the send fails, use the relay rule in the header; if that fails too, say so in your final message (the verdict is in `_agent/vm/performance.md` anyway).
{{else}}
6. (No coordinator role is installed: the verdict in `_agent/vm/performance.md` is the record.)
{{/if}}
7. **Push only on "upgrade":** `uni-vm notify "Host performance: upgrade recommended. Details on the host's performance page." high` (no file names in a push: the lock screen is public). Never push "enough" or "tight".

If something fails (a command errors, the pricing page can't be read, fewer samples than expected): still write the block with what you have, mark the missing part "unknown" (never guess a price or a number), and say what failed in your final reply. Unknown is never "enough".

**Failure flag** (the one vault file this job may write): if you could not write the verdict block at all (the verdict log isn't writable, `uni-vm perf` is missing or fails completely), write `_agent/logs/flags/vm-performance-verdict.md`: front matter `job: vm-performance-verdict`, `at: YYYY-MM-DD HH:MM`, `level: amber`; the first body line is one plain sentence saying what failed (no prices, budgets or machine details). A run that writes its block deletes that file if it exists.{{#if modules.heartbeat}} The heartbeat's pre-check turns it into the finding `job:vm-performance-verdict:failed`.{{/if}}

Never: change a machine setting, stop or restart a session or service, edit any vault file (except your own failure flag above), resize or create cloud resources, or put prices, budgets or machine details into a push.

Reply with the verdict block only, following the reply rules in `_agent/rules.md`.
