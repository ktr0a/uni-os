"""Tests for modules/scheduler-local/scripts (jobconf, list_jobs, run_job --print-only).

Run from the repo root:  python -m unittest discover -s modules/scheduler-local/tests
"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import jobconf as jc  # noqa: E402
import list_jobs  # noqa: E402
import run_job  # noqa: E402

CONF = '''# comment line
TITLE="Inbox sync (apply update notes)"
KIND="agent"
SLOTS="07:15, 13:15, 18:15"
DAYS="Mon,Tue,Wed,Thu,Fri,Sat,Sun"
MODEL=""  EFFORT="high"
PRECHECK='! ls "inbox" >/dev/null 2>&1 || compgen -G "inbox/*-update.md" >/dev/null'
export HEARTBEAT_MODE=freeze-safe
LAPTOP_TASK="inbox-sync"
RUNTIME="any"
'''


def make_vault(root: Path) -> Path:
    vault = root / "My Vault & Co"
    j = vault / "_agent" / "jobs" / "inbox-sync"
    j.mkdir(parents=True)
    (j / "job.conf").write_text(CONF, encoding="utf-8")
    (j / "prompt.md").write_text("# Job: inbox sync\nDo the thing.\n", encoding="utf-8")
    hb = vault / "_agent" / "jobs" / "heartbeat"
    hb.mkdir()
    (hb / "job.conf").write_text('KIND="agent"\nSLOTS="07:50, 13:05, 18:05"\nDAYS="Mon,Tue,Wed,Thu,Fri"\n')
    (hb / "prompt.md").write_text("beat\n")
    poll = vault / "_agent" / "jobs" / "inbox-poll"
    poll.mkdir()
    (poll / "job.conf").write_text('KIND="command"\nCOMMAND=\'echo "hi"\'\nEVERY_MIN="10"\n'
                                   'SCHEDULE="*-*-* *:00/10:00"\nDRY_OK="yes"\n')
    (vault / "_agent" / "jobs" / "_header.md").write_text(
        "<!-- comment -->\nJob {{job.title}} ({{job.id}}) on {{host.name}}, vault `{{host.vault}}`, "
        "slots {{job.slots}}, keep {{student.name}}.\n\n--- task (verbatim) ---\n", encoding="utf-8")
    return vault


class ParseTests(unittest.TestCase):
    def test_parse_conf(self):
        c = jc.parse_conf_text(CONF)
        self.assertEqual(c["TITLE"], "Inbox sync (apply update notes)")
        self.assertEqual(c["MODEL"], "")
        self.assertEqual(c["EFFORT"], "high")
        self.assertEqual(c["PRECHECK"], '! ls "inbox" >/dev/null 2>&1 || compgen -G "inbox/*-update.md" >/dev/null')
        self.assertEqual(c["HEARTBEAT_MODE"], "freeze-safe")
        self.assertNotIn("export", c)

    def test_multiline_value(self):
        c = jc.parse_conf_text('A="one\ntwo"\nB=3\n')
        self.assertEqual(c["A"], "one\ntwo")
        self.assertEqual(c["B"], "3")

    def test_days_and_dates(self):
        self.assertEqual(jc.parse_days("Mon-Fri"), [0, 1, 2, 3, 4])
        self.assertEqual(jc.parse_days(""), list(range(7)))
        r = jc.parse_dates("2026-11-09..2026-11-29; 2026-12-05")
        self.assertTrue(jc.date_allowed(datetime(2026, 11, 20).date(), r))
        self.assertFalse(jc.date_allowed(datetime(2026, 12, 1).date(), r))


class CronAndSlotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = make_vault(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_cron_groups_by_minute(self):
        sync = jc.load_job(self.vault, "inbox-sync")
        lines, notes = jc.cron_lines(sync)
        self.assertEqual(lines, ["15 7,13,18 * * *"])
        hb = jc.load_job(self.vault, "heartbeat")
        lines, notes = jc.cron_lines(hb)
        self.assertEqual(lines, ["5 13,18 * * 1-5", "50 7 * * 1-5"])
        self.assertTrue(any("one task per line" in n for n in notes))
        poll = jc.load_job(self.vault, "inbox-poll")
        self.assertEqual(jc.cron_lines(poll)[0], ["*/10 * * * *"])

    def test_cron_weekend_days(self):
        j = jc.Job("x", Path("."), {"SLOTS": "10:00", "DAYS": "Sat,Sun"})
        self.assertEqual(jc.cron_lines(j)[0], ["0 10 * * 0,6"])

    def test_nominal_slot(self):
        sync = jc.load_job(self.vault, "inbox-sync")
        self.assertEqual(jc.nominal_slot(sync, datetime(2026, 11, 9, 13, 27)), datetime(2026, 11, 9, 13, 15))
        self.assertEqual(jc.nominal_slot(sync, datetime(2026, 11, 9, 6, 0)), datetime(2026, 11, 8, 18, 15))
        hb = jc.load_job(self.vault, "heartbeat")  # weekdays only: Mon morning -> Fri evening
        self.assertEqual(jc.nominal_slot(hb, datetime(2026, 11, 9, 7, 0)), datetime(2026, 11, 6, 18, 5))

    def test_disabled_jobs_hidden(self):
        (self.vault / "_agent" / "jobs" / "heartbeat" / "DISABLED").write_text("")
        ids = [j.id for j in jc.load_jobs(self.vault)]
        self.assertNotIn("heartbeat", ids)
        self.assertIn("heartbeat", [j.id for j in jc.load_jobs(self.vault, include_disabled=True)])

    def test_ran_marker(self):
        sync = jc.load_job(self.vault, "inbox-sync")
        self.assertIsNone(jc.ran_marker_slot(self.vault, sync))
        ran = self.vault / "_agent" / "vm" / "ran"
        ran.mkdir(parents=True)
        (ran / "inbox-sync.md").write_text("---\ntype: agent\n---\nslot: 2026-11-09 13:15\nexit: 0\n")
        self.assertEqual(jc.ran_marker_slot(self.vault, sync), "2026-11-09 13:15")

    def test_prompt_assembly(self):
        sync = jc.load_job(self.vault, "inbox-sync")
        host = jc.Host(name="laptop", vault="V:/x")
        text = jc.assemble_prompt(self.vault, sync, host)
        self.assertTrue(text.startswith("Job Inbox sync (apply update notes) (inbox-sync) on laptop"))
        self.assertIn("slots 07:15, 13:15, 18:15", text)
        self.assertIn("{{student.name}}", text)   # not a runtime root: untouched
        self.assertIn("--- task (verbatim) ---\n\n# Job: inbox sync", text)
        self.assertNotIn("<!--", text)
        dry = jc.assemble_prompt(self.vault, sync, host, dry_run=True)
        self.assertTrue(dry.startswith("DRY RUN"))

    def test_shipped_header_push_command_is_filled(self):
        # The laptop header's push line names the framework clone (no `uni-os` shim on a laptop).
        shipped = (HERE.parent / "vault" / "_agent" / "jobs" / "_header.md").read_text(encoding="utf-8")
        self.assertNotIn("`uni-os push`", shipped)
        self.assertIn("{{host.framework}}/tools/uni_os.py", shipped)
        (self.vault / "_agent" / "jobs" / "_header.md").write_text("push: {{host.python}} \"{{host.framework}}/tools/uni_os.py\" push\n\n--- task (verbatim) ---\n", encoding="utf-8")
        text = jc.assemble_prompt(self.vault, jc.load_job(self.vault, "inbox-sync"), jc.Host(python="py"))
        self.assertIn(f'push: py "{jc.framework_root()}/tools/uni_os.py" push', text)
        self.assertNotIn("{{host.", text)

    def test_list_jobs_cli(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = list_jobs.main(["--vault", str(self.vault)])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("inbox-sync", out)
        self.assertIn("every 10 min", out)
        buf = io.StringIO()
        with redirect_stdout(buf):
            list_jobs.main(["--vault", str(self.vault), "windows", "heartbeat", "--python", "pythonw.exe"])
        ps = buf.getvalue()
        self.assertIn("-DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 07:50", ps)
        self.assertIn("Register-ScheduledTask -TaskName 'Uni OS - heartbeat'", ps)

    def test_run_job_print_only(self):
        os.environ["UNI_STATE_DIR"] = str(Path(self.tmp.name) / "state")
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_job.main(["--vault", str(self.vault), "--job", "inbox-sync", "--print-only",
                                   "--agent-cmd", "myagent --model {model} --prompt-file {prompt_file}"])
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("myagent", out)
            self.assertIn("prompt:", out)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_job.main(["--vault", str(self.vault), "--job", "inbox-poll", "--print-only"])
            self.assertEqual(rc, 0)
        finally:
            os.environ.pop("UNI_STATE_DIR", None)

    def test_config_prefers_generated_json(self):
        agent = self.vault / "_agent"
        (agent / "uni-os.toml").write_text('[agent]\nprimary = "claude-code"\n', encoding="utf-8")
        self.assertEqual(run_job.load_config(self.vault)["agent"], {"primary": "claude-code"})
        (agent / "uni-os.json").write_text(
            '{"_generated": "do not edit", "agent": {"primary": "claude-code", "cli": "claude", '
            '"permission_posture": "bypass"}}', encoding="utf-8")
        cfg = run_job.load_config(self.vault)
        self.assertEqual(cfg["agent"]["permission_posture"], "bypass")
        job = jc.load_job(self.vault, "inbox-sync")

        class A:  # minimal argparse namespace
            permission = None
            agent_cmd = None
        argv, on_stdin = run_job.agent_command(cfg, job, "job: x", Path("p.md"), A())
        self.assertIn("bypassPermissions", argv)
        self.assertTrue(on_stdin)
        argv, _ = run_job.agent_command({"agent": {}}, job, "job: x", Path("p.md"), A())
        self.assertIn("acceptEdits", argv)  # no config: the config default, never bypass

    def _run_recorded(self, args: list[str], stdout_encoding: str = "cp1252") -> tuple[int, str, str]:
        """run_job.main with stdout as a non-UTF-8 pipe would be (cp1252: a task's stdout on Windows).
        Returns (exit code, jobs.log text, console text)."""
        state = Path(self.tmp.name) / "state"
        os.environ["UNI_STATE_DIR"] = str(state)
        raw = io.BytesIO()
        fake = io.TextIOWrapper(raw, encoding=stdout_encoding, errors="strict", newline="\n")
        old = sys.stdout
        sys.stdout = fake
        try:
            rc = run_job.main(["--vault", str(self.vault)] + args)
        finally:
            sys.stdout = old
            os.environ.pop("UNI_STATE_DIR", None)
        fake.flush()
        jobs_log = state / "jobs.log"
        return rc, jobs_log.read_text(encoding="utf-8") if jobs_log.exists() else "", raw.getvalue().decode("utf-8", "replace")

    def test_unicode_output_on_a_cp1252_pipe_keeps_the_record(self):
        if run_job.find_bash() is None:
            self.skipTest("no bash")
        j = self.vault / "_agent" / "jobs" / "zz-unicode"
        j.mkdir()
        (j / "job.conf").write_text("KIND=\"command\"\nCOMMAND='echo \"applied 2 notes ✓ → done\"'\n",
                                    encoding="utf-8")
        rc, jobs_log, console = self._run_recorded(["--job", "zz-unicode"])
        self.assertEqual(rc, 0)
        self.assertIn("| zz-unicode | exit 0 |", jobs_log)
        self.assertIn("✓", console)
        logs = list((Path(self.tmp.name) / "state" / "jobs" / "zz-unicode").glob("*.log"))
        self.assertIn("✓ → done", logs[0].read_text(encoding="utf-8"))

    def test_agent_cli_that_cannot_start_is_recorded(self):
        rc, jobs_log, console = self._run_recorded(
            ["--job", "inbox-sync", "--force", "--agent-cmd", "uni-os-no-such-agent-cli -p"])
        self.assertEqual(rc, 127)
        self.assertIn("| inbox-sync | exit 127 |", jobs_log)
        self.assertIn("could not start uni-os-no-such-agent-cli", console)

    def test_agent_without_headless_command_is_recorded(self):
        (self.vault / "_agent" / "uni-os.json").write_text('{"agent": {"primary": "codex"}}', encoding="utf-8")
        rc, jobs_log, console = self._run_recorded(["--job", "inbox-sync", "--force"])
        self.assertEqual(rc, 2)
        self.assertIn("| inbox-sync | exit 2 |", jobs_log)
        self.assertIn("agent.headless_command", console)

    def test_failure_push_contract(self):
        # run_job's failure push must use options the push gate accepts (`uni-os push`).
        src = (HERE.parent / "scripts" / "run_job.py").read_text(encoding="utf-8")
        self.assertNotIn('"--key"', src)
        self.assertIn('"--id"', src)
        try:
            import argparse
            sys.path.insert(0, str(HERE.parents[2] / "tools"))
            from uni_os.commands import push as push_cmd
        except Exception:  # noqa: BLE001  framework not importable: skip
            return
        p = argparse.ArgumentParser()
        push_cmd.register(p.add_subparsers())
        ns = p.parse_args(["push", "--source", "job:x", "--direct", "--id", "job-failed:x", "text"])
        self.assertTrue(ns.direct)


if __name__ == "__main__":
    unittest.main()
