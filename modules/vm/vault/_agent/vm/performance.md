---
type: agent
audience: agent
updated: {{generated.date}}
tags: [uni/agent]
---
# Host performance ({{vm.host_alias}})

**Not written yet.** Once the host runs, its health check adds one row per day here (memory available min / typical, swap, load, CPU steal, agent sessions, OOM kills, swap-in), and the weekly job `vm-performance-verdict` adds its verdict (enough / tight / upgrade). Machine: `{{vm.machine_type}}`. About the host: [../vm.md](../vm.md).
