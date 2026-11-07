"""Tests of the push gate (`uni-os push`, tools/uni_os/pushgate.py).

Ported from the original system's push-gate test suite: fake inputs only, every send goes
to a file (UNI_OS_PUSH_FAKE_SEND) or a fake opener, state in a temp dir. Run from the repo
root:  python -m unittest tests.test_push -v
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
try:  # the real package; a minimal stub if it is not importable
    import uni_os  # noqa: F401
    if not hasattr(uni_os, "__path__"):
        raise ImportError
except ImportError:
    _pkg = types.ModuleType("uni_os")
    _pkg.__path__ = [str(TOOLS / "uni_os")]
    sys.modules["uni_os"] = _pkg

from uni_os import pushgate  # noqa: E402
from uni_os.commands import push as push_cmd  # noqa: E402

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None


def raw_load_config(vault, config_path=None, modules_dir=None):
    """Test stub: read <vault>/_agent/uni-os.toml as it is, so these tests do not depend on
    the shared loader's module catalogue (other modules may not be installed yet)."""
    p = Path(config_path) if config_path else Path(vault) / "_agent" / "uni-os.toml"
    if not p.is_file():
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)

ENV_KEYS = ["UNI_OS_STATE", "UNI_STATE_DIR", "UNI_OS_PUSH_STATE", "UNI_OS_PUSH_FAKE_SEND", "UNI_OS_PUSH_DRY_LOG", "UNI_DRY_RUN",
            "UNI_OS_NOW", "UNI_OS_VAULT", "UNI_VAULT", "UNI_OS_NTFY_SERVER", "UNI_OS_NTFY_TOPIC_FILE"]

BASE_CONFIG = """
[term]
timezone = "Europe/Zurich"
week0_monday = 2026-09-14

[notify]
provider = "ntfy"
ntfy_server = "https://ntfy.example.test"
ntfy_topic_file = "{topic}"
max_per_day = 3
min_gap_hours = 2
quiet_hours = "21:00-07:30"
dedupe_hours = 24
never_all_good = true
quiet_windows = [
  {{ from = "2026-11-19 07:30", to = "2026-11-19 10:00", reason = "LA quiz 5" }},
  {{ from = "2026-11-24", to = "2026-11-24", reason = "DM oral" }},
  {{ day = "Mon", from = "08:00", to = "10:00", until = "2026-12-21", reason = "weekly AD quiz" }},
]
"""


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class GateTestBase(unittest.TestCase):
    def setUp(self):
        self._env = {k: os.environ.get(k) for k in ENV_KEYS}
        self._orig_load = pushgate.load_config
        pushgate.load_config = raw_load_config
        for k in ENV_KEYS:
            os.environ.pop(k, None)
        self.tmp = Path(tempfile.mkdtemp(prefix="uni-os-push-test-"))
        self.vault = self.tmp / "vault"
        (self.vault / "_agent").mkdir(parents=True)
        self.secret = self.tmp / "secret"
        self.secret.mkdir()
        self.topic = self.secret / "ntfy-topic"
        self.topic.write_text("alex-example-topic-123\n", encoding="utf-8")
        os.environ["UNI_OS_STATE"] = str(self.tmp / "state")
        self.sent = self.tmp / "sent.txt"
        os.environ["UNI_OS_PUSH_FAKE_SEND"] = str(self.sent)
        self.write_config()

    def tearDown(self):
        pushgate.load_config = self._orig_load
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_config(self, extra=""):
        text = BASE_CONFIG.format(topic=str(self.topic).replace("\\", "/")) + extra
        (self.vault / "_agent" / "uni-os.toml").write_text(text, encoding="utf-8")

    def settings(self):
        s, _ = pushgate.settings_for(str(self.vault))
        return s

    def push(self, *argv):
        """Run `uni-os push ...` with --vault; returns (exit code, output)."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = push_cmd.main(["push", *argv, "--vault", str(self.vault)])
        return code, buf.getvalue()

    def code(self, *argv):
        return self.push(*argv)[0]

    def sent_lines(self):
        return self.sent.read_text(encoding="utf-8").splitlines() if self.sent.exists() else []


class RefusalsAndBudget(GateTestBase):
    """The original's push-gate test sequence, generalised."""

    def test_sequence(self):
        c = self.code
        self.assertEqual(c("Uni: x", "--now", "2026-11-10 08:00"), 13, "no ids: refused")
        self.assertEqual(c("Uni: all good today", "--id", "a", "--now", "2026-11-10 08:00"), 13, "all good: refused")
        self.assertEqual(c("Uni: everything is on track", "--id", "a", "--now", "2026-11-10 08:00"), 13)
        self.assertEqual(c("Uni: write to alex@example.edu", "--id", "a", "--now", "2026-11-10 08:00"), 13, "mail")
        self.assertEqual(c("Uni: see https://x.example", "--id", "a", "--now", "2026-11-10 08:00"), 13, "link")
        self.assertEqual(c("Uni: call 0791234567", "--id", "a", "--now", "2026-11-10 08:00"), 13, "long number")
        self.assertEqual(c("Uni: LA hand-in due 23:59", "--id", "h", "--now", "2026-11-10 07:29"), 10, "07:29: held")
        self.assertEqual(self.sent_lines(), [], "nothing sent yet")
        self.assertEqual(c("Uni: prep note 2026-11-11 missing; quiz 2.67/4", "--id", "a", "--now", "2026-11-10 07:30"),
                         0, "dates and scores are fine")
        self.assertEqual(len(self.sent_lines()), 1)
        self.assertEqual(c("Uni: again", "--id", "a", "--now", "2026-11-10 12:00"), 12, "same id within 24 h")
        self.assertEqual(c("Uni: b", "--id", "b", "--now", "2026-11-10 09:00"), 11, "new id under 2 h: gap")
        self.assertEqual(c("--check", "--id", "b", "--now", "2026-11-10 09:00"), 11, "check")
        self.assertEqual(len(self.sent_lines()), 1, "check changes nothing")
        self.assertEqual(c("Uni: b", "--id", "b", "--urgent", "--now", "2026-11-10 09:00"), 0, "urgent skips the gap")
        self.assertEqual(c("Uni: c", "--id", "c", "--now", "2026-11-10 11:00"), 0, "third push after 2 h")
        self.assertEqual(c("Uni: d", "--id", "d", "--urgent", "--now", "2026-11-10 15:00"), 11, "fourth: day cap")
        self.assertEqual(c("Uni: e", "--id", "e", "--now", "2026-11-10 21:00"), 10, "21:00: held")
        self.assertEqual(c("Uni: a", "--id", "a", "--now", "2026-11-11 08:30"), 0, "next day, id a after 24 h")

    def test_dry_run_records_nothing(self):
        dry_log = self.tmp / "dry.log"
        os.environ["UNI_OS_PUSH_DRY_LOG"] = str(dry_log)
        code, out = self.push("Uni: z", "--id", "z", "--dry-run", "--now", "2026-11-11 12:00")
        self.assertEqual(code, 0)
        self.assertIn("DRY RUN would send", out)
        self.assertEqual(self.sent_lines(), [])
        self.assertFalse((self.tmp / "state" / "push-gate" / "state.json").exists(), "dry run writes no state")
        os.environ["UNI_DRY_RUN"] = "1"
        self.assertEqual(self.code("Uni: all good today", "--id", "q", "--now", "2026-11-11 12:00"), 13)
        self.assertIn("would not send (exit 13)", dry_log.read_text(encoding="utf-8"))
        self.assertEqual(self.sent_lines(), [])

    def test_extra_all_good_patterns(self):
        p = self.vault / "_agent" / "uni-os.toml"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "never_all_good = true", 'never_all_good = true\nextra_all_good_patterns = ["alles (gut|ok)"]'), encoding="utf-8")
        self.assertEqual(self.code("Uni: alles gut heute", "--id", "a", "--now", "2026-11-10 08:30"), 13)

    def test_require_id_off(self):
        text = (self.vault / "_agent" / "uni-os.toml").read_text(encoding="utf-8")
        (self.vault / "_agent" / "uni-os.toml").write_text(text.replace("never_all_good = true", "never_all_good = true\nrequire_id = false"),
                                                           encoding="utf-8")
        self.assertEqual(self.code("Uni: LA hand-in due tonight", "--now", "2026-11-10 08:30"), 0)

    def test_max_length(self):
        code, out = self.push("Uni: " + "x " * 400, "--id", "long", "--now", "2026-11-10 08:30")
        self.assertEqual(code, 0)
        line = self.sent_lines()[-1]
        body = line.split("] ", 1)[1]
        self.assertLessEqual(len(body), 300)
        self.assertTrue(body.endswith("…"))


class QuietWindows(GateTestBase):
    def test_windows(self):
        for w in ("2026-11-24 13:00", "2026-11-19 08:00", "2026-11-16 09:00"):
            self.assertEqual(self.code("--check", "--id", "w" + w[-5:-3] + w[8:10], "--now", w), 10, w)
        for w in ("2026-11-25 08:00", "2026-11-16 10:00", "2026-11-19 10:00", "2026-12-28 09:00"):
            self.assertEqual(self.code("--check", "--id", "w" + w[8:10] + w[-5:-3], "--now", w), 0, w)

    def test_soft_window(self):
        p = self.vault / "_agent" / "uni-os.toml"
        soft = '  { from = "2027-01-25", to = "2027-02-19", reason = "exam session", urgent_ok = true },\n'
        p.write_text(p.read_text(encoding="utf-8").replace("quiet_windows = [\n", "quiet_windows = [\n" + soft),
                     encoding="utf-8")
        self.assertEqual(self.code("Uni: x", "--id", "x", "--now", "2027-02-01 10:00"), 10, "soft window holds ordinary pushes")
        self.assertEqual(self.code("Uni: y", "--id", "y", "--urgent", "--now", "2027-02-01 10:00"), 0, "urgent passes")
        self.assertEqual(self.code("Host problem", "--direct", "--now", "2027-02-01 10:05"), 0, "direct passes")

    def test_hard_window_holds_urgent_too(self):
        """A hard window (no urgent_ok) is for a timed quiz: nothing buzzes, not even --urgent."""
        self.assertEqual(self.code("Uni: z", "--id", "z", "--urgent", "--now", "2026-11-19 08:00"), 10)
        s = self.settings()
        now = pushgate.parse_when("2026-11-19 08:00")
        self.assertIn("LA quiz 5", pushgate.window_now(s, now, urgent=True))
        self.assertIn("LA quiz 5", pushgate.window_now(s, now, hard_only=True), "the heartbeat pre-check skips here")

    def test_soft_window_is_ignored_by_the_heartbeat_gate(self):
        p = self.vault / "_agent" / "uni-os.toml"
        soft = '  { from = "2027-01-25", to = "2027-02-19", reason = "exam session", urgent_ok = true },\n'
        p.write_text(p.read_text(encoding="utf-8").replace("quiet_windows = [\n", "quiet_windows = [\n" + soft),
                     encoding="utf-8")
        s = self.settings()
        now = pushgate.parse_when("2027-02-01 10:00")
        self.assertIn("soft", pushgate.window_now(s, now))
        self.assertIsNone(pushgate.window_now(s, now, urgent=True))
        self.assertIsNone(pushgate.window_now(s, now, hard_only=True), "the heartbeat keeps running")

    def test_weekly_until(self):
        s = self.settings()
        self.assertIsNotNone(pushgate.window_now(s, pushgate.parse_when("2026-12-21 08:30")))
        self.assertIsNone(pushgate.window_now(s, pushgate.parse_when("2026-12-28 08:30")), "after until")

    def test_held_is_deferred_not_queued(self):
        """The original gate's exit 10 "deferred: send again later": nothing is queued or recorded."""
        self.assertEqual(self.code("Uni: night thing", "--id", "n", "--now", "2026-11-10 22:00"), 10)
        self.assertEqual(self.code("Uni: quiz-time thing", "--id", "q", "--now", "2026-11-19 08:00"), 10)
        st_path = self.tmp / "state" / "push-gate" / "state.json"
        held = json.loads(st_path.read_text(encoding="utf-8"))["held"] if st_path.exists() else []
        self.assertEqual(held, [], "judgment pushes are never queued")
        self.assertEqual(self.code("--flush", "--now", "2026-11-19 10:05"), 0)
        self.assertEqual(self.sent_lines(), [], "nothing stale is released")
        self.assertEqual(self.code("Uni: night thing", "--id", "n", "--now", "2026-11-19 10:06"), 0,
                         "raised again later by its sender: sent normally")
        log = (self.tmp / "state" / "push-gate" / "notify.log").read_text(encoding="utf-8")
        self.assertIn("deferred | cli | n |", log)

    def test_direct_held_then_flush(self):
        self.assertEqual(self.code("Host problem: vault mount down", "--direct", "--now", "2026-11-19 08:00"), 10)
        self.assertEqual(self.code("Host problem: login missing", "--direct", "--now", "2026-11-19 08:10"), 10)
        self.assertEqual(self.code("Host problem: vault mount down", "--direct", "--now", "2026-11-19 08:20"), 10,
                         "same alert: not queued twice")
        st = json.loads((self.tmp / "state" / "push-gate" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(len(st["held"]), 2)
        self.assertEqual(self.code("--flush", "--now", "2026-11-19 09:00"), 10, "inside the window: still held")
        self.assertEqual(self.sent_lines(), [])
        self.assertEqual(self.code("--flush", "--now", "2026-11-19 10:05"), 0)
        self.assertEqual(len(self.sent_lines()), 1)
        self.assertIn("Held during a quiet window: Host problem: vault mount down; Host problem: login missing",
                      self.sent_lines()[0])
        self.assertEqual(pushgate.status(self.settings(), pushgate.parse_when("2026-11-19 10:06"))["pushes_today"], 0,
                         "released host alerts don't use the budget")
        self.assertEqual(self.code("--flush", "--now", "2026-11-19 14:00"), 0)
        self.assertEqual(len(self.sent_lines()), 1, "nothing held any more")

    def test_held_items_expire(self):
        self.assertEqual(self.code("Host problem: x", "--direct", "--now", "2026-11-19 08:00"), 10)
        self.assertEqual(self.code("--flush", "--now", "2026-11-21 08:00"), 0)
        self.assertEqual(self.sent_lines(), [], "older than hold_max_hours: dropped, not sent")


class ItemsAndDirect(GateTestBase):
    def test_items_only_fresh(self):
        self.assertEqual(self.code("--item", "outcome:x=first thing", "--prefix", "Outcome check: ",
                                   "--source", "oc", "--now", "2026-11-12 08:00"), 0)
        self.assertEqual(self.code("--item", "outcome:x=first thing", "--item", "outcome:y=second thing",
                                   "--prefix", "Outcome check: ", "--source", "oc", "--now", "2026-11-12 10:30"), 0)
        self.assertTrue(self.sent_lines()[-1].endswith("Outcome check: second thing"))

    def test_items_same_text_once(self):
        self.assertEqual(self.code("--item", "inbox:stuck:a=update note waiting in the inbox for over 4 h",
                                   "--item", "inbox:stuck:b=update note waiting in the inbox for over 4 h",
                                   "--now", "2026-11-12 08:00"), 0)
        self.assertTrue(self.sent_lines()[-1].endswith("] update note waiting in the inbox for over 4 h"))

    def test_outcome_texts_pass_the_refusals(self):
        # The shared outcome-check texts (every sender uses them word for word) must never be
        # refused as "all good" or as personal details, and two senders' items dedupe per id.
        from uni_os import heartbeat_rules as hr
        import datetime as _dt
        texts = {"inbox:stuck:a-update-md": hr.stuck_push_text(False, 4),
                 "inbox:stuck:b-cockpit-done-x-update-md": hr.stuck_push_text(True, 14),
                 "prep:gap-open:2026-11-12": hr.gap_open_text(24, _dt.date(2026, 11, 12)),
                 "prep:tomorrow-missing:2026-11-13": "no prep note for Fri 13 Nov yet"}
        argv = []
        for k, t in texts.items():
            argv += ["--item", "%s=%s" % (k, t)]
        self.assertEqual(self.code(*argv, "--prefix", "Outcome check: ", "--source", "outcome-checks",
                                   "--now", "2026-11-12 08:00"), 0)
        self.assertEqual(self.code("--item", "inbox:stuck:a-update-md=" + texts["inbox:stuck:a-update-md"],
                                   "--prefix", "Outcome check: ", "--source", "inbox-sync", "--now", "2026-11-12 10:30"),
                         12, "a second sender with the same id is deduped")

    def test_direct(self):
        for t, i in (("08:00", "a"), ("10:00", "b"), ("12:00", "c")):
            self.assertEqual(self.code("Uni: " + i, "--id", i, "--now", "2026-11-10 " + t), 0)
        self.assertEqual(self.code("Uni: d", "--id", "d", "--now", "2026-11-10 14:00"), 11, "day cap")
        self.assertEqual(self.code("Host problem: vault mount down", "--direct", "--now", "2026-11-10 14:00"), 0,
                         "direct: outside the budget")
        self.assertEqual(self.code("Host problem: login missing", "--direct", "--now", "2026-11-10 23:30"), 0,
                         "direct ignores quiet hours")
        self.assertEqual(self.code("Host problem: x", "--direct", "--now", "2026-11-19 08:00"), 10,
                         "direct is still held in a quiet window")
        st = pushgate.status(self.settings(), pushgate.parse_when("2026-11-10 23:40"))
        self.assertEqual(st["pushes_today"], 3, "direct pushes are not counted")
        self.assertIn("[p4]", self.sent_lines()[3], "direct default priority 4")
        self.assertEqual(self.code("Host problem: write to alex@example.edu", "--direct", "--now", "2026-11-10 23:45"), 13,
                         "direct pushes still carry no personal details")
        self.assertEqual(self.code("Host recovered: all clear", "--direct", "--now", "2026-11-10 23:46"), 0,
                         "the all-good rule is for judgment pushes only")


class Delivery(GateTestBase):
    def test_ntfy_request(self):
        os.environ.pop("UNI_OS_PUSH_FAKE_SEND")
        captured = {}

        def opener(req, timeout=None):
            captured["url"], captured["headers"], captured["data"] = req.full_url, dict(req.header_items()), req.data
            return FakeResponse()

        s = self.settings()
        code = pushgate.push(s, text="Uni: LA hand-in due 23:59", ids=["a"], click="https://claude.ai/code",
                             priority=4, now=pushgate.parse_when("2026-11-10 08:30"), opener=opener, out=lambda x: None)
        self.assertEqual(code, 0)
        self.assertEqual(captured["url"], "https://ntfy.example.test/alex-example-topic-123")
        self.assertEqual(captured["data"].decode("utf-8"), "Uni: LA hand-in due 23:59")
        self.assertEqual(captured["headers"]["Title"], "Uni OS")
        self.assertEqual(captured["headers"]["Priority"], "4")
        self.assertEqual(captured["headers"]["Click"], "https://claude.ai/code")

    def test_send_failure_records_nothing(self):
        os.environ.pop("UNI_OS_PUSH_FAKE_SEND")
        import urllib.error

        def opener(req, timeout=None):
            raise urllib.error.URLError("offline")

        s = self.settings()
        code = pushgate.push(s, text="Uni: x", ids=["a"], now=pushgate.parse_when("2026-11-10 08:30"),
                             opener=opener, out=lambda x: None)
        self.assertEqual(code, 1)
        self.assertEqual(pushgate.status(s, pushgate.parse_when("2026-11-10 08:31"))["pushes_today"], 0)

    def test_missing_topic_file(self):
        os.environ.pop("UNI_OS_PUSH_FAKE_SEND")
        self.topic.unlink()
        code, out = self.push("Uni: x", "--id", "a", "--now", "2026-11-10 08:30")
        self.assertEqual(code, 2)
        self.assertIn("no ntfy topic file", out)

    def test_topic_file_inside_vault_is_refused(self):
        os.environ.pop("UNI_OS_PUSH_FAKE_SEND")
        inside = self.vault / "_agent" / "ntfy-topic"
        inside.write_text("abc\n", encoding="utf-8")
        text = (self.vault / "_agent" / "uni-os.toml").read_text(encoding="utf-8")
        (self.vault / "_agent" / "uni-os.toml").write_text(
            text.replace(str(self.topic).replace("\\", "/"), str(inside).replace("\\", "/")), encoding="utf-8")
        code, out = self.push("Uni: x", "--id", "a", "--now", "2026-11-10 08:30")
        self.assertEqual(code, 2)
        self.assertIn("inside the vault", out)

    def test_provider_none_logs_only(self):
        os.environ.pop("UNI_OS_PUSH_FAKE_SEND")
        text = (self.vault / "_agent" / "uni-os.toml").read_text(encoding="utf-8")
        (self.vault / "_agent" / "uni-os.toml").write_text(text.replace('provider = "ntfy"', 'provider = "none"'),
                                                           encoding="utf-8")
        code, out = self.push("Uni: x", "--id", "a", "--now", "2026-11-10 08:30")
        self.assertEqual(code, 0)
        log = (self.tmp / "state" / "push-gate" / "notify.log").read_text(encoding="utf-8")
        self.assertIn("logged only", log)

    def test_cached_settings_when_vault_is_unreachable(self):
        self.assertEqual(self.code("Uni: a", "--id", "a", "--now", "2026-11-10 08:30"), 0)  # caches settings
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = push_cmd.main(["push", "Host problem: vault mount down", "--direct", "--now", "2026-11-19 08:00",
                                  "--vault", str(self.tmp / "missing-vault")])
        self.assertEqual(code, 10, "cached quiet windows still apply without the vault")


class BrokenConfig(GateTestBase):
    """An invalid vault config must not stop every push: the gate falls back to the cached
    notify settings (else its defaults), says so in one stderr line and keeps the cache."""

    def push_err(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = push_cmd.main(["push", *argv, "--vault", str(self.vault)])
        return code, out.getvalue(), err.getvalue()

    def cache(self):
        return json.loads((self.tmp / "state" / "push-gate" / "notify-settings.json").read_text(encoding="utf-8"))

    def test_invalid_toml_uses_the_cached_settings(self):
        pushgate.load_config = self._orig_load  # the real loader, then its raw fallback
        self.assertEqual(self.code("Uni: a", "--id", "a", "--now", "2026-11-10 08:30"), 0)  # caches settings
        cached = self.cache()
        (self.vault / "_agent" / "uni-os.toml").write_text("[notify\nmax_per_day = 3\n", encoding="utf-8")
        code, out, err = self.push_err("--check", "--id", "x", "--now", "2026-11-19 08:00")
        self.assertEqual(code, 10, "the cached quiet window still applies: %s %s" % (out, err))
        self.assertEqual(len(err.strip().splitlines()), 1, err)
        self.assertIn("push gate: the vault config can't be used", err)
        self.assertIn("not valid TOML", err)
        self.assertIn("using the last known notify settings", err)
        code, out, err = self.push_err("Uni: b", "--id", "b", "--now", "2026-11-10 10:45")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.cache(), cached, "a broken config never overwrites the cache")

    def test_invalid_toml_without_a_cache_uses_the_defaults(self):
        (self.vault / "_agent" / "uni-os.toml").write_text("not = = toml\n", encoding="utf-8")
        code, out, err = self.push_err("Uni: a", "--id", "a", "--now", "2026-11-10 08:30")
        self.assertEqual(code, 0, out + err)
        self.assertIn("using the default notify settings", err)
        self.assertEqual(len(self.sent_lines()), 1)
        code, out, err = self.push_err("Uni: b", "--id", "b", "--now", "2026-11-10 22:00")
        self.assertEqual(code, 10, "the default quiet hours apply")

    def test_invalid_notify_value(self):
        self.assertEqual(self.code("Uni: a", "--id", "a", "--now", "2026-11-10 08:30"), 0)
        text = (self.vault / "_agent" / "uni-os.toml").read_text(encoding="utf-8")
        (self.vault / "_agent" / "uni-os.toml").write_text(
            text.replace('quiet_hours = "21:00-07:30"', 'quiet_hours = "late evening"'), encoding="utf-8")
        code, out, err = self.push_err("--check", "--id", "x", "--now", "2026-11-19 08:00")
        self.assertEqual(code, 10, out + err)
        self.assertIn("notify.quiet_hours", err)

    def test_load_config_names_the_file(self):
        # the shared loader refuses invalid TOML too, so this reaches the raw fallback path
        (self.vault / "_agent" / "uni-os.toml").write_text("[term\n", encoding="utf-8")
        with self.assertRaises(pushgate.ConfigUnreadable) as cm:
            self._orig_load(self.vault)
        self.assertIsInstance(cm.exception, ValueError)
        self.assertIn("_agent/uni-os.toml is not valid TOML", str(cm.exception))
        self.assertNotIn(str(self.tmp), str(cm.exception), "no absolute path (it can name the user)")


class Locking(GateTestBase):
    """A call that can't get the gate's lock never runs unlocked: exit 1 "gate busy", nothing sent."""

    def setUp(self):
        super().setUp()
        self._wait = pushgate.LOCK_WAIT_S
        pushgate.LOCK_WAIT_S = 0.3
        self.lock = self.tmp / "state" / "push-gate" / ".lock"

    def tearDown(self):
        pushgate.LOCK_WAIT_S = self._wait
        super().tearDown()

    def test_wait_is_longer_than_a_send(self):
        self.assertGreater(self._wait, pushgate.HTTP_TIMEOUT_S)

    def test_held_lock_means_busy(self):
        with pushgate.file_lock(self.lock):
            code, out = self.push("Uni: a", "--id", "a", "--now", "2026-11-10 08:30")
            self.assertEqual(code, 1, out)
            self.assertIn("gate busy, try later", out)
            code, out = self.push("Host problem: mount down", "--direct", "--now", "2026-11-10 08:31")
            self.assertEqual(code, 1, out)
        self.assertEqual(self.sent_lines(), [], "nothing sent while another sender held the lock")
        self.assertEqual(pushgate.status(self.settings(), pushgate.parse_when("2026-11-10 08:32"))["pushes_today"], 0)
        self.assertIn("busy | cli | a | ", (self.tmp / "state" / "push-gate" / "notify.log").read_text(encoding="utf-8"))
        self.assertEqual(self.code("Uni: a", "--id", "a", "--now", "2026-11-10 08:33"), 0, "free again: sent once")
        self.assertEqual(len(self.sent_lines()), 1)

    def test_held_lock_flush(self):
        self.assertEqual(self.code("Host problem: x", "--direct", "--now", "2026-11-19 08:00"), 10)  # queued
        with pushgate.file_lock(self.lock):
            code, out = self.push("--flush", "--now", "2026-11-19 10:30")
            self.assertEqual(code, 1, out)
            self.assertIn("gate busy, try later", out)
        self.assertEqual(self.sent_lines(), [])
        self.assertEqual(self.code("--flush", "--now", "2026-11-19 10:31"), 0)
        self.assertEqual(len(self.sent_lines()), 1, "released once, after the lock was free")

    def test_dry_run_needs_no_lock(self):
        with pushgate.file_lock(self.lock):
            self.assertEqual(self.code("Uni: a", "--id", "a", "--dry-run", "--now", "2026-11-10 08:30"), 0)

    def test_file_lock_raises_gate_busy(self):
        with pushgate.file_lock(self.lock):
            with self.assertRaises(pushgate.GateBusy):
                with pushgate.file_lock(self.lock, wait=0.2):
                    self.fail("the body must not run without the lock")
        with pushgate.file_lock(self.lock, wait=0.2):
            pass


class Cli(GateTestBase):
    def test_usage_and_status(self):
        self.assertEqual(self.code("--now", "2026-11-10 08:30"), 2, "no message")
        self.assertEqual(self.code("x", "--id", "a", "--priority", "9", "--now", "2026-11-10 08:30"), 2)
        code, out = self.push("--status", "--now", "2026-11-10 08:30")
        self.assertEqual(code, 0)
        st = json.loads(out)
        self.assertEqual(st["left_today"], 3)

    def test_host_script_aliases(self):
        self.assertEqual(self.code("--direct", "--source", "host", "--text", "Host problem: mount down", "--prio", "high",
                                   "--now", "2026-11-10 10:00"), 0)
        self.assertIn("[p4] Host problem: mount down", self.sent_lines()[-1])
        self.assertEqual(self.code("--ids", "job-done", "--text", "One question for you", "--urgent",
                                   "--now", "2026-11-10 10:05"), 0)
        self.assertEqual(self.code("--flush-held", "--now", "2026-11-10 10:10"), 0)
        self.assertEqual(self.code("x", "--id", "a", "--prio", "loud", "--now", "2026-11-10 10:10"), 2)

    def test_key_alias(self):
        """The laptop job runner and the inbox poll pass the problem id as --key."""
        self.assertEqual(self.code("--source", "inbox-sync", "--key", "stuck-2026-11-10-la-update.md",
                                   "Uni OS: update note in inbox for over 4 h: 2026-11-10-la-update.md",
                                   "--now", "2026-11-10 10:00"), 0)
        self.assertEqual(self.code("--source", "inbox-sync", "--key", "stuck-2026-11-10-la-update.md", "Uni OS: again",
                                   "--now", "2026-11-10 13:00"), 12)

    def test_vault_from_runner_env(self):
        """Both job runners export UNI_VAULT; the gate finds the config through it."""
        os.environ["UNI_VAULT"] = str(self.vault)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = push_cmd.main(["push", "--check", "--id", "x", "--now", "2026-11-19 08:00"])
        self.assertEqual(code, 10, "the vault's quiet window applies")

    def test_register_contract(self):
        import argparse
        ap = argparse.ArgumentParser()
        sub = ap.add_subparsers(dest="command")
        push_cmd.register(sub)
        a = ap.parse_args(["push", "hello", "--id", "a,b"])
        self.assertTrue(callable(a.func))
        self.assertEqual(push_cmd._split_ids(a.id), ["a", "b"])


class ModuleFiles(unittest.TestCase):
    def test_module_defaults_match_code(self):
        if tomllib is None:
            self.skipTest("tomllib missing")
        with open(REPO / "modules" / "notifications" / "module.toml", "rb") as f:
            m = tomllib.load(f)
        self.assertEqual(m["id"], "notifications")
        self.assertEqual(m["defaults"]["notify"], pushgate.DEFAULTS)
        for key in pushgate.DEFAULTS:
            self.assertIn("notify." + key, m["config_keys"])


if __name__ == "__main__":
    unittest.main()
