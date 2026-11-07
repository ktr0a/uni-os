"""Tests for config loading, layered defaults, derived fields, validation and JSON export."""

import copy
import datetime as dt
import json
import tomllib
import unittest
from pathlib import Path

import support
from uni_os import config, modules
from uni_os.errors import ConfigError


def base_raw():
    return {
        "student": {"name": "Alex Example"},
        "university": {"name": "Example Institute of Technology"},
        "term": {"label": "Autumn 2026", "timezone": "Europe/Zurich", "week0_monday": dt.date(2026, 9, 14)},
        "courses": [
            {"id": "algo", "name": "Algorithms", "short": "AD", "folder": "A&D", "slug": "ad", "colour": "#1e66f5"},
        ],
    }


def errors(issues):
    return [i for i in issues if i.level == "error"]


def where(issues):
    return {i.where for i in issues}


class MergeTests(unittest.TestCase):
    def test_deep_merge_user_wins_and_lists_replace(self):
        base = {"a": {"x": 1, "y": [1, 2]}, "b": 1}
        out = config.deep_merge(base, {"a": {"y": [3]}, "c": 2})
        self.assertEqual(out, {"a": {"x": 1, "y": [3]}, "b": 1, "c": 2})
        self.assertEqual(base["a"]["y"], [1, 2], "inputs are not modified")

    def test_base_defaults_fill_missing_keys(self):
        cfg = config.resolve(base_raw())
        self.assertEqual(cfg["schedule"]["daily_prep"], ["17:30", "19:30"])
        self.assertEqual(cfg["notify"]["max_per_day"], 3)
        self.assertEqual(cfg["paths"]["agent_dir"], "_agent")
        self.assertEqual(cfg["student"]["language"], "English")

    def test_module_defaults_layering(self):
        catalog = modules.discover(support.FIXTURE_MODULES)
        raw = base_raw()
        raw["schedule"] = {"week_page": {"day": "Sat"}}  # partial table: time comes from defaults
        cfg = config.resolve(raw, catalog, ["core", "progress"])
        self.assertEqual(cfg["schedule"]["week_page"], {"day": "Sat", "time": "10:00"})
        # [defaults.course] applied to courses lacking the key
        self.assertEqual(cfg["courses"][0]["sheet_label"], "sheet")
        self.assertEqual(cfg["modules"]["enabled"], ["core", "progress"])

    def test_course_defaults_do_not_override_course_values(self):
        catalog = modules.discover(support.FIXTURE_MODULES)
        raw = base_raw()
        raw["courses"][0]["sheet_label"] = "series"
        cfg = config.resolve(raw, catalog, ["core", "progress"])
        self.assertEqual(cfg["courses"][0]["sheet_label"], "series")

    def test_computed_and_derived_course_fields(self):
        raw = base_raw()
        raw["student"]["language"] = "German"
        raw["study"] = {"assistance_default": "coach"}
        raw["courses"][0]["error_log_streams"] = ["theory", "programming"]
        raw["courses"][0]["assessments"] = [{"name": "Quiz", "kind": "quiz"}, {"name": "Solo", "kind": "sheet", "assistance": "solo"}]
        c = config.resolve(raw)["courses"][0]
        self.assertEqual(c["language"], "German")
        self.assertEqual(c["assistance"], "coach")
        self.assertEqual(c["colour_rgb"], "30, 102, 245")
        self.assertEqual(c["colour_int"], 0x1E66F5)
        self.assertTrue(config.HEX_RE.match(c["colour_light"]))
        self.assertEqual(c["card"], "A&D/ad.md")
        self.assertEqual(c["error_log_files"], ["ad-error-log-theory.md", "ad-error-log-programming.md"])
        self.assertEqual(c["error_logs"][0]["path"], "A&D/ad-error-log-theory.md")
        self.assertEqual(c["assessments"][0]["assistance"], "coach")
        self.assertEqual(c["assessments"][0]["counts_for"], "none")
        self.assertEqual(c["assessments"][1]["assistance"], "solo")
        self.assertEqual(c["bonus"]["scheme"], "none")

    def test_single_stream_error_log_name(self):
        c = config.resolve(base_raw())["courses"][0]
        self.assertEqual(c["error_log_files"], ["ad-error-log.md"])

    def test_string_dates_are_normalised(self):
        raw = base_raw()
        raw["term"]["week0_monday"] = "2026-09-14"
        cfg = config.resolve(raw)
        self.assertEqual(cfg["term"]["week0_monday"], dt.date(2026, 9, 14))

    def test_get_path(self):
        cfg = config.resolve(base_raw())
        self.assertEqual(config.get_path(cfg, "courses.algo.short"), "AD")
        self.assertEqual(config.get_path(cfg, "courses.0.slug"), "ad")
        with self.assertRaises(KeyError) as cm:
            config.get_path(cfg, "schedule.daily_perp")
        self.assertIn("daily_prep", str(cm.exception))


class ReadTests(support.TempDirTestCase):
    def test_read_toml_errors_are_helpful(self):
        bad = self.tmp / "bad.toml"
        bad.write_text("[schedule]\nprep_check = 07:30\n", encoding="utf-8")
        with self.assertRaises(ConfigError) as cm:
            config.read_toml(bad)
        self.assertIn("quoted", cm.exception.hint)
        with self.assertRaises(ConfigError):
            config.read_toml(self.tmp / "missing.toml")

    def test_load_from_vault(self):
        self.init()
        cfg = config.load(self.vault, modules_dir=support.FIXTURE_MODULES)
        self.assertEqual(cfg["student"]["name"], "Alex Example")
        self.assertEqual(cfg["schedule"]["week_page"]["time"], "10:00")

    def test_load_tolerates_unknown_modules(self):
        self.init()
        toml = self.vault / "_agent" / "uni-os.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('enabled = ["progress", "study"]', 'enabled = ["progress", "nope"]'), encoding="utf-8")
        cfg = config.load(self.vault, modules_dir=support.FIXTURE_MODULES)
        self.assertEqual(cfg["term"]["label"], "Autumn 2026")


class ValidationTests(unittest.TestCase):
    def validate(self, raw, **kw):
        return config.validate(config.resolve(raw), raw=raw, **kw)

    def test_valid_config_has_no_errors(self):
        self.assertEqual(errors(self.validate(base_raw())), [])

    def test_required_keys(self):
        raw = base_raw()
        del raw["student"]["name"]
        raw["term"]["label"] = ""
        found = where(errors(self.validate(raw)))
        self.assertIn("student.name", found)
        self.assertIn("term.label", found)

    def test_required_keys_come_from_the_user_file(self):
        """A module's fallback default (error-logs ships term.label = "this term") must not
        hide a required key the user left out."""
        raw = base_raw()
        del raw["term"]["label"]
        resolved = config.deep_merge(config.resolve(raw), {"term": {"label": "this term"}})
        self.assertIn("term.label", where(errors(config.validate(resolved, raw=raw))))
        self.assertNotIn("term.label", where(errors(config.validate(resolved))))  # without raw: resolved value

    def test_week0_must_be_monday_and_a_date(self):
        raw = base_raw()
        raw["term"]["week0_monday"] = dt.date(2026, 9, 15)
        msgs = [i.message for i in errors(self.validate(raw))]
        self.assertTrue(any("Monday" in m for m in msgs), msgs)
        raw["term"]["week0_monday"] = "14.09.2026"
        self.assertIn("term.week0_monday", where(errors(self.validate(raw))))

    def test_date_order_and_holidays(self):
        raw = base_raw()
        raw["term"]["exam_session_start"] = dt.date(2027, 2, 1)
        raw["term"]["exam_session_end"] = dt.date(2027, 1, 1)
        raw["term"]["holidays"] = [{"name": "x", "from": dt.date(2026, 11, 2), "to": dt.date(2026, 11, 1)}, {"from": "nope"}]
        found = where(errors(self.validate(raw)))
        self.assertIn("term.exam_session_end", found)
        self.assertIn("term.holidays[0].to", found)
        self.assertIn("term.holidays[1].name", found)
        self.assertIn("term.holidays[1].from", found)

    def test_timezone(self):
        import zoneinfo

        raw = base_raw()
        raw["term"]["timezone"] = "Mars Olympus!"  # malformed: an error with or without a tz database
        self.assertIn("term.timezone", where(errors(self.validate(raw))))
        raw["term"]["timezone"] = "Mars/Olympus"  # well-formed but unknown: needs the tz database
        if not zoneinfo.available_timezones():
            self.skipTest("no IANA tz database here (Windows Python without the tzdata package)")
        self.assertIn("term.timezone", where(errors(self.validate(raw))))

    def test_enums_with_suggestion(self):
        raw = base_raw()
        raw["storage"] = {"provider": "google-driv"}
        raw["agent"] = {"permission_posture": "yolo"}
        issues = errors(self.validate(raw))
        storage = [i for i in issues if i.where == "storage.provider"]
        self.assertTrue(storage and "google-drive" in storage[0].message)
        self.assertIn("agent.permission_posture", where(issues))

    def test_types(self):
        raw = base_raw()
        raw["obsidian"] = {"enabled": "yes"}
        raw["notify"] = {"max_per_day": "3"}
        found = where(errors(self.validate(raw)))
        self.assertIn("obsidian.enabled", found)
        self.assertIn("notify.max_per_day", found)

    def test_times_and_ranges(self):
        raw = base_raw()
        raw["schedule"] = {
            "daily_prep": ["17:30", "7:5"],
            "prep_check": "25:00",
            "week_page": {"day": "Sunday", "time": "10"},
            "heartbeat_days": ["Mon", "Funday"],
            "poll_window": "07:00-22:00",
            "bad_window": "07:00-24:30",
            "raw_calendar": "*-*-* 07..21:00/10:00",
        }
        raw["notify"] = {"quiet_hours": "9pm-7am"}
        found = where(errors(self.validate(raw)))
        for key in ("schedule.daily_prep[1]", "schedule.prep_check", "schedule.week_page.day", "schedule.week_page.time", "schedule.heartbeat_days", "schedule.bad_window", "notify.quiet_hours"):
            self.assertIn(key, found)
        for key in ("schedule.daily_prep[0]", "schedule.poll_window", "schedule.raw_calendar"):
            self.assertNotIn(key, found)

    def test_course_rules(self):
        raw = base_raw()
        raw["courses"].append({"id": "Algo", "name": "Dup", "short": "AD", "folder": "a&d", "slug": "AD x", "colour": "blue"})
        raw["courses"].append({"id": "x", "name": "Bad folder", "short": "X", "folder": "progress", "slug": "x", "colour": "#000000", "error_log_streams": ["Main Stream"]})
        raw["courses"].append({"id": "y", "name": "Slash", "short": "Y", "folder": "a/b", "slug": "y", "colour": "#000000", "assistance": "lots"})
        raw["courses"].append({"name": "No id"})
        issues = errors(self.validate(raw))
        found = where(issues)
        self.assertIn("courses.Algo.id", found)  # bad id pattern
        self.assertIn("courses.Algo.slug", found)
        self.assertIn("courses.Algo.folder", found)  # duplicate folder (case-insensitive)
        self.assertIn("courses.Algo.colour", found)
        self.assertIn("courses.x.folder", found)  # reserved vault folder
        self.assertIn("courses.x.error_log_streams", found)
        self.assertIn("courses.y.folder", found)  # slash
        self.assertIn("courses.y.assistance", found)
        self.assertIn("courses[4].id", found)
        self.assertIn("courses[4].colour", found)

    def test_duplicate_ids_and_slugs(self):
        raw = base_raw()
        raw["courses"].append(dict(raw["courses"][0], folder="Other"))
        found = where(errors(self.validate(raw)))
        self.assertIn("courses.algo.id", found)
        self.assertIn("courses.algo.slug", found)

    def test_assessments_and_bonus(self):
        raw = base_raw()
        raw["courses"][0]["assessments"] = [{"kind": "exam-ish", "counts_for": "fun", "points_max": -1}]
        raw["courses"][0]["bonus"] = {"scheme": "magic", "max_bonus": "lots"}
        found = where(errors(self.validate(raw)))
        for key in ("name", "kind", "counts_for", "points_max"):
            self.assertIn(f"courses.algo.assessments[0].{key}", found)
        self.assertIn("courses.algo.bonus.scheme", found)
        self.assertIn("courses.algo.bonus.max_bonus", found)

    def test_slot_format_is_a_warning(self):
        raw = base_raw()
        raw["courses"][0]["lecture_slots"] = ["Tuesday morning"]
        issues = self.validate(raw)
        self.assertEqual(errors(issues), [])
        self.assertIn("courses.algo.lecture_slots", where(issues))

    def test_formats(self):
        raw = base_raw()
        raw["study"] = {"formats": ["html", "docx"]}
        self.assertIn("study.formats", where(errors(self.validate(raw))))

    def test_secrets_are_refused(self):
        raw = base_raw()
        raw["notify"] = {"ntfy_token": "abc123def456"}
        raw["calendar"] = {"courses": "https://calendar.google.com/calendar/ical/x%40y.com/private-" + "ab12" * 8 + "/basic.ics"}
        found = where(errors(self.validate(raw)))
        self.assertIn("notify.ntfy_token", found)
        self.assertIn("calendar.courses", found)

    def test_topic_file_inside_vault_is_refused(self):
        raw = base_raw()
        vault = Path(support.TESTS)  # any existing folder works as a stand-in vault
        raw["notify"] = {"ntfy_topic_file": str(vault / "secret.txt")}
        self.assertIn("notify.ntfy_topic_file", where(errors(self.validate(raw, vault=vault))))

    def test_unknown_keys_warn_with_suggestion(self):
        raw = base_raw()
        raw["schedule"] = {"daily_perp": ["17:30"]}
        raw["notfiy"] = {}
        raw["courses"][0]["colur"] = "#000000"
        issues = self.validate(raw)
        warns = {i.where: i.message for i in issues if i.level == "warning"}
        self.assertIn("daily_prep", warns.get("schedule.daily_perp", ""))
        self.assertIn("notify", warns.get("notfiy", ""))
        self.assertIn("colour", warns.get("courses[0].colur", ""))

    def test_unknown_assessment_keys_warn_with_suggestion(self):
        raw = base_raw()
        raw["courses"][0]["assessments"] = [
            {"name": "Quiz", "kind": "quiz", "scope": "chapters 1-3", "dates": ["2026-11-19 08:00", dt.date(2026, 12, 3)]},
            {"name": "Sheets", "kind": "sheet", "scop": "all sheets", "pointsmax": 10},
        ]
        issues = self.validate(raw)
        self.assertEqual(errors(issues), [])
        warns = {i.where: i.message for i in issues if i.level == "warning"}
        self.assertNotIn("courses.algo.assessments[0].scope", warns, "scope is a known key")
        self.assertIn("did you mean 'scope'?", warns.get("courses.algo.assessments[1].scop", ""))
        self.assertIn("did you mean 'points_max'?", warns.get("courses.algo.assessments[1].pointsmax", ""))

    def test_assessment_dates_and_scope_types(self):
        raw = base_raw()
        raw["courses"][0]["assessments"] = [{"name": "Quiz", "dates": ["19 Nov"], "scope": 3},
                                            {"name": "Oral", "dates": "2026-12-03"}]
        found = where(errors(self.validate(raw)))
        for key in ("assessments[0].dates", "assessments[0].scope", "assessments[1].dates"):
            self.assertIn(f"courses.algo.{key}", found)

    def test_old_stuck_aliases_get_an_info_note(self):
        raw = base_raw()
        raw["heartbeat"] = {"inbox_stuck_hours": 6, "inbox_tap_stuck_hours": 0}
        raw["vm"] = {"tap_stuck_h": 20}
        notes = {i.where: i.message for i in self.validate(raw) if i.level == "info"}
        self.assertIn("notify.inbox_stale_hours", notes.get("heartbeat.inbox_stuck_hours", ""))
        self.assertIn("host", notes.get("vm.tap_stuck_h", ""))
        self.assertNotIn("heartbeat.inbox_tap_stuck_hours", notes, "0 = use notify.*: nothing to say")

    def test_module_ids_checked_against_catalog(self):
        catalog = modules.discover(support.FIXTURE_MODULES)
        raw = base_raw()
        raw["modules"] = {"enabled": ["progres"]}
        issues = errors(config.validate(config.resolve(raw, catalog, []), catalog=catalog, raw=raw))
        self.assertTrue(any("did you mean 'progress'" in i.message for i in issues))


class KeysOfDisabledModulesTests(support.TempDirTestCase):
    """config validate warns about a value that only modules which are not enabled read."""

    MODULES = {
        "core": 'tier = "core"\n',
        # owns a schedule key, a key of its own table, and a base key (schedule.check_in)
        "watcher": 'requires = ["core"]\n\n[defaults.schedule]\nwatch = "08:00"\ncheck_in = { day = "Sat", time = "19:45", every = "week" }\n\n'
                   '[defaults.watcher]\nscopes = ["notes"]\nlimit = 5\n',
        # reads watcher.scopes (config_keys) without defining it
        "reader": 'requires = ["core"]\nconfig_keys = ["watcher.scopes"]\n',
        # defines the same key as another module
        "twin": 'requires = ["core"]\n\n[defaults.watcher]\nlimit = 5\n',
        # pulls watcher in as a dependency
        "consumer": 'requires = ["watcher"]\n',
    }

    def setUp(self):
        super().setUp()
        root = self.tmp / "mods"
        for mid, body in self.MODULES.items():
            (root / mid).mkdir(parents=True)
            (root / mid / "module.toml").write_text(f'id = "{mid}"\nname = "{mid}"\nsummary = "s"\n{body}', encoding="utf-8")
        self.catalog = modules.discover(root)

    def warnings(self, raw, enabled):
        """The notes of this check (level info: disable keeps a module's settings on purpose)."""
        cfg = config.resolve(raw, self.catalog, modules.resolve(enabled, self.catalog))
        issues = config.validate(cfg, catalog=self.catalog, raw=raw)
        self.assertFalse([i for i in issues if i.level == "warning" and "is not enabled" in i.message],
                         "a setting of a disabled module is a note, never a warning (doctor --strict)")
        return {i.where: i.message for i in issues if i.level == "info" and "enabled" in i.message}

    def test_changed_key_of_a_disabled_module_warns(self):
        raw = base_raw()
        raw["schedule"] = {"watch": "09:30"}
        warns = self.warnings(raw, ["core"])
        self.assertEqual(warns.get("schedule.watch"), "is set, but its module watcher is not enabled, so the value has "
                         "no effect (enable the module with `uni-os enable watcher`, or remove the line)")
        self.assertNotIn("schedule.watch", self.warnings(raw, ["watcher"]), "enabled: the value counts")

    def test_default_values_and_base_keys_are_not_reported(self):
        raw = base_raw()
        raw["schedule"] = {"watch": "08:00", "check_in": {"day": "Sun", "time": "18:00", "every": "week"}}
        raw["watcher"] = {"scopes": ["notes"]}
        warns = self.warnings(raw, ["core"])
        self.assertNotIn("schedule.watch", warns, "equal to the module default: copied from the example, harmless")
        self.assertNotIn("watcher.scopes", warns)
        self.assertFalse(any(w.startswith("schedule.check_in") for w in warns), "base keys may be read by any template")

    def test_a_reader_from_config_keys_counts(self):
        raw = base_raw()
        raw["watcher"] = {"scopes": ["notes", "views"]}
        self.assertIn("watcher.scopes", self.warnings(raw, ["core"]))
        self.assertNotIn("watcher.scopes", self.warnings(raw, ["reader"]))

    def test_key_of_two_modules(self):
        raw = base_raw()
        raw["watcher"] = {"limit": 9}
        warns = self.warnings(raw, ["core"])
        self.assertIn("none of its modules (twin, watcher) is enabled", warns.get("watcher.limit", ""))
        self.assertNotIn("watcher.limit", self.warnings(raw, ["twin"]))

    def test_dependencies_count_as_enabled(self):
        raw = base_raw()
        raw["schedule"] = {"watch": "10:00"}
        raw["modules"] = {"enabled": ["consumer"]}
        cfg = config.resolve(raw)  # modules.enabled as written: the dependency watcher is not listed
        issues = config.validate(cfg, catalog=self.catalog, raw=raw)
        self.assertNotIn("schedule.watch", {i.where for i in issues})
        raw["modules"] = {"enabled": ["reader"]}
        issues = config.validate(config.resolve(raw), catalog=self.catalog, raw=raw)
        self.assertIn("schedule.watch", {i.where for i in issues})

    def test_no_catalog_no_check(self):
        raw = base_raw()
        raw["schedule"] = {"watch": "09:30"}
        issues = config.validate(config.resolve(raw), raw=raw)
        self.assertNotIn("is not enabled", " ".join(i.message for i in issues))


class TermWeeksTests(unittest.TestCase):
    """term.weeks: derived from term.week0_monday through the week of term.last_lecture_day."""

    def test_through_the_week_of_the_last_lecture_day(self):
        raw = base_raw()
        raw["term"]["last_lecture_day"] = dt.date(2026, 12, 18)  # a Friday of week 13
        weeks = config.resolve(raw)["term"]["weeks"]
        self.assertEqual(len(weeks), 14)
        self.assertEqual(weeks[0], {"number": 0, "nn": "00", "start": "Mon 14 Sep 2026", "start_iso": "2026-09-14"})
        self.assertEqual(weeks[7], {"number": 7, "nn": "07", "start": "Mon 2 Nov 2026", "start_iso": "2026-11-02"})
        self.assertEqual(weeks[-1], {"number": 13, "nn": "13", "start": "Mon 14 Dec 2026", "start_iso": "2026-12-14"})

    def test_last_lecture_day_on_a_monday_starts_its_week(self):
        raw = base_raw()
        raw["term"]["last_lecture_day"] = "2026-12-21"  # string dates are normalised first
        weeks = config.resolve(raw)["term"]["weeks"]
        self.assertEqual(weeks[-1]["number"], 14)
        self.assertEqual(weeks[-1]["start"], "Mon 21 Dec 2026")

    def test_fourteen_weeks_without_a_last_lecture_day(self):
        weeks = config.resolve(base_raw())["term"]["weeks"]
        self.assertEqual([w["number"] for w in weeks], list(range(14)))
        self.assertEqual(weeks[-1]["start"], "Mon 14 Dec 2026")
        raw = base_raw()
        raw["term"]["last_lecture_day"] = dt.date(2026, 9, 1)  # before week 0: the default length
        self.assertEqual(len(config.resolve(raw)["term"]["weeks"]), config.DEFAULT_TERM_WEEKS)

    def test_years_and_limits(self):
        raw = base_raw()
        raw["term"]["last_lecture_day"] = dt.date(2027, 1, 8)
        weeks = config.resolve(raw)["term"]["weeks"]
        self.assertEqual(weeks[15]["start"], "Mon 28 Dec 2026")
        self.assertEqual(weeks[16]["start"], "Mon 4 Jan 2027")
        raw["term"]["last_lecture_day"] = dt.date(2036, 1, 1)  # a mistyped year
        self.assertEqual(len(config.resolve(raw)["term"]["weeks"]), config.MAX_TERM_WEEKS)

    def test_no_week0_no_weeks(self):
        raw = base_raw()
        raw["term"]["week0_monday"] = "14.09.2026"
        self.assertEqual(config.resolve(raw)["term"]["weeks"], [])

    def test_in_the_json_copy(self):
        data = json.loads(config.export_json(config.resolve(base_raw())))
        self.assertEqual(data["term"]["weeks"][1]["start_iso"], "2026-09-21")

    def test_setting_it_by_hand_warns_and_is_ignored(self):
        raw = base_raw()
        raw["term"]["weeks"] = 16
        cfg = config.resolve(raw)
        self.assertEqual(len(cfg["term"]["weeks"]), 14)
        warns = {i.where: i.message for i in config.validate(cfg, raw=raw) if i.level == "warning"}
        self.assertIn("computed by the tools", warns.get("term.weeks", ""))

    def test_date_long(self):
        self.assertEqual(config.date_long(dt.date(2026, 11, 7)), "Sat 7 Nov 2026")
        self.assertEqual(config.date_long(dt.date(2027, 1, 1)), "Fri 1 Jan 2027")
        self.assertEqual(config.date_long(dt.date(2026, 9, 14)), "Mon 14 Sep 2026")

    def test_date_long_ignores_the_locale(self):
        import locale

        old = locale.setlocale(locale.LC_TIME)
        for name in ("de_DE.UTF-8", "de_DE", "German_Germany.1252", "fr_FR.UTF-8"):
            try:
                locale.setlocale(locale.LC_TIME, name)
                break
            except locale.Error:
                continue
        try:
            self.assertEqual(config.date_long(dt.date(2026, 3, 2)), "Mon 2 Mar 2026")
            self.assertEqual(config.term_weeks({"term": {"week0_monday": dt.date(2026, 10, 5)}})[0]["start"], "Mon 5 Oct 2026")
        finally:
            locale.setlocale(locale.LC_TIME, old)


class ExportTests(unittest.TestCase):
    def test_json_export(self):
        cfg = config.resolve(base_raw())
        text = config.export_json(cfg)
        data = json.loads(text)
        self.assertEqual(next(iter(data)), "_generated")
        self.assertEqual(data["_generated"], "do not edit; edit uni-os.toml")
        self.assertEqual(data["term"]["week0_monday"], "2026-09-14")
        self.assertEqual(data["courses"][0]["colour_rgb"], "30, 102, 245")
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(text, config.export_json(copy.deepcopy(cfg)), "deterministic")

    def test_flatten(self):
        flat = dict(config.flatten({"a": {"b": 1}, "courses": [{"id": "x", "n": 2}], "l": [1, 2]}))
        self.assertEqual(flat, {"a.b": 1, "courses.x.id": "x", "courses.x.n": 2, "l": [1, 2]})


class ExampleConfigTests(unittest.TestCase):
    """The shipped example configs parse, validate and list every base key."""

    FILES = [support.REPO / "config" / "uni-os.example.toml", support.REPO / "examples" / "alex.toml"]

    def test_examples_validate_without_errors(self):
        from uni_os import presets

        for path in self.FILES:
            raw = config.read_toml(path)
            cfg = config.resolve(raw)
            issues = config.validate(cfg, raw=raw)
            self.assertEqual(errors(issues), [], f"{path.name}: {errors(issues)}")
            for mid in raw["modules"]["enabled"]:
                self.assertIn(mid, presets.CATALOGUE, f"{path.name}: unknown module {mid}")

    def test_examples_list_every_base_key(self):
        for path in self.FILES:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
            for table, section in config.BASE_DEFAULTS.items():
                self.assertIn(table, raw, f"{path.name}: missing [{table}]")
                if isinstance(section, dict):
                    for key in section:
                        self.assertIn(key, raw[table], f"{path.name}: missing {table}.{key}")
            for key in config.REQUIRED:
                table, name = key.split(".")
                self.assertIn(name, raw[table], f"{path.name}: missing {key}")
            for course in raw["courses"]:
                for key in list(config.COURSE_DEFAULTS) + list(config.COURSE_REQUIRED) + ["language", "assistance"]:
                    self.assertIn(key, course, f"{path.name}: course {course.get('id')} lacks {key}")

    def test_example_and_alex_share_values(self):
        example = config.read_toml(self.FILES[0])
        alex = config.read_toml(self.FILES[1])
        for table in example:
            if table in ("modules", "uni_os"):
                continue
            self.assertEqual(example[table], alex[table], f"[{table}] differs between the two example configs")

    def test_alex_enables_standard_plus_inbox_sync_and_experiments(self):
        from uni_os import presets

        alex = config.read_toml(self.FILES[1])
        expected = presets.preset_modules("standard", obsidian=True) + ["inbox-sync", "experiments"]
        self.assertEqual(alex["modules"]["enabled"], expected)
        example = config.read_toml(self.FILES[0])
        self.assertEqual(example["modules"]["enabled"], presets.preset_modules("standard", obsidian=True))

    def test_exam_session_windows_are_soft(self):
        """A weeks-long window must let urgent pushes through and keep the heartbeat running."""
        for path in self.FILES:
            raw = config.read_toml(path)
            for win in raw["notify"]["quiet_windows"]:
                if "exam session" in str(win.get("reason", "")):
                    self.assertIs(win.get("urgent_ok"), True, f"{path.name}: {win}")


class QuietWindowValidationTests(unittest.TestCase):
    """notify.quiet_windows: every shape the push gate reads validates; mistakes are named."""

    def issues(self, *windows):
        raw = base_raw()
        raw["notify"] = {"quiet_windows": list(windows)}
        found = config.validate(config.resolve(raw), raw=raw)
        return [i for i in found if i.where.startswith("notify.quiet_windows")]

    def test_every_gate_shape_is_valid(self):
        found = self.issues(
            {"from": "2026-11-19 07:30", "to": "2026-11-19 10:00", "reason": "LA quiz"},
            {"from": "2026-11-24", "to": "2026-11-24", "reason": "oral"},
            {"from": dt.date(2026, 11, 24), "to": dt.date(2026, 11, 24), "reason": "oral (TOML dates)"},
            {"from": "2026-11-19 07:30", "to": "10:00", "reason": "time-only end"},
            {"day": "Mon", "from": "08:00", "to": "10:00", "until": "2026-12-21", "reason": "weekly quiz"},
            {"days": ["Tue", "Thu"], "from": "13:00", "to": "14:00", "since": dt.date(2026, 10, 1), "reason": "x"},
            {"from": "2027-01-25", "to": "2027-02-19", "reason": "exam session", "urgent_ok": True},
        )
        self.assertEqual(found, [])

    def test_long_hard_window_warns(self):
        found = self.issues({"from": "2027-01-25", "to": "2027-02-19", "reason": "exam session"})
        self.assertEqual([i.level for i in found], ["warning"])
        self.assertIn("26 days", found[0].message)
        self.assertIn("urgent_ok = true", found[0].message)
        self.assertEqual(self.issues({"from": "2026-11-24", "to": "2026-11-24", "reason": "one day"}), [],
                         "a whole day (24 h) is fine")
        self.assertEqual([i.level for i in self.issues({"from": "2026-11-24", "to": "2026-11-25", "reason": "two"})],
                         ["warning"])

    def test_unknown_keys_and_bad_values(self):
        found = {i.where: (i.level, i.message) for i in self.issues(
            {"from": "2026-11-19 07:30", "to": "2026-11-19 10:00", "urgnet_ok": True},
            {"from": "2026-11-19 07:30", "to": "2026-11-19 10:00", "urgent_ok": "yes"},
            {"day": "Funday", "from": "8:00", "to": "10:00"},
            {"day": "Mon", "from": "22:00", "to": "06:00"},
            {"to": "2026-11-19"},
            {"from": "2026-11-19 10:00", "to": "2026-11-19 09:00"},
            "2026-11-19",
        )}
        self.assertEqual(found["notify.quiet_windows[0].urgnet_ok"][0], "warning")
        self.assertIn("did you mean 'urgent_ok'?", found["notify.quiet_windows[0].urgnet_ok"][1])
        self.assertEqual(found["notify.quiet_windows[1].urgent_ok"][0], "error")
        self.assertEqual(found["notify.quiet_windows[2].day"][0], "error")
        self.assertEqual(found["notify.quiet_windows[2].from"][0], "error")
        self.assertIn("past midnight", found["notify.quiet_windows[3].to"][1])
        self.assertEqual(found["notify.quiet_windows[4].from"][0], "error")
        self.assertIn("not after", found["notify.quiet_windows[5].to"][1])
        self.assertEqual(found["notify.quiet_windows[6]"][0], "error")


if __name__ == "__main__":
    unittest.main()
