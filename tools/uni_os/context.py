"""Open a "session": vault + config file + module catalogue + resolved config.

Every command starts here so they all find things the same way:

- config file: ``--config``, else ``<vault>/_agent/uni-os.toml``;
- vault: ``--vault``, else the vault containing ``--config`` (when it is
  ``<vault>/_agent/uni-os.toml``); without ``--config``: ``$UNI_OS_VAULT``, else
  walking up from the current folder. ``paths.vault`` in a config file elsewhere
  is never used as a write target (pass ``--vault`` explicitly);
- modules: ``--modules-dir``, else ``$UNI_OS_MODULES_DIR``, else ``<repo>/modules``;
- enabled modules: ``--modules`` / ``--preset`` override, else ``modules.enabled``,
  else the preset named in ``uni_os.preset``; dependencies added.
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import __version__, config, modules, paths, presets, semester, template
from .errors import ConfigError, Issue, ModuleError, UniOsError


@dataclass
class Session:
    vault: Path | None
    config_path: Path
    raw: dict
    cfg: dict
    catalog: modules.Catalog
    requested: list[str]
    enabled: list[str]
    agent_dir: str
    module_problems: list[Issue] = field(default_factory=list)
    #: Preset modules left out because they do not support the laptop's system
    #: (``presets.filter_for_os``), with that system and where it came from.
    preset_dropped: list[str] = field(default_factory=list)
    preset_os: str | None = None
    preset_os_source: str = ""

    def preset_note(self) -> list[str]:
        """Printable lines about preset modules left out for the laptop's system ([] = none)."""
        return presets.left_out_note(self.preset_dropped, self.catalog, self.preset_os, self.preset_os_source)

    @property
    def inbox(self) -> str:
        return (self.cfg.get("paths") or {}).get("inbox", "inbox")

    def require_vault(self) -> Path:
        if self.vault is None:
            raise UniOsError(
                "no vault given",
                hint="pass --vault <folder>, run the command inside the vault, or set $UNI_OS_VAULT",
            )
        return self.vault

    def vault_path(self, *parts: str) -> Path:
        return self.require_vault().joinpath(*parts)

    def agent_path(self, *parts: str) -> Path:
        return self.require_vault().joinpath(self.agent_dir, *parts)

    def context(self, *, date: dt.date | None = None, with_generated_info: bool = True) -> dict:
        """The template render context for this session.

        ``generated`` holds ``date`` (ISO, ``2026-11-07``), ``date_long`` (the same day as
        the vault writes dates in text, ``Sat 7 Nov 2026``, locale-independent),
        ``version`` and the lists from :func:`uni_os.install.generated_info`.
        """
        from . import install

        day = date or generation_date(self.cfg)
        gen = {"date": day.isoformat(), "date_long": config.date_long(day), "version": __version__}
        ctx = template.build_context(self.cfg, enabled=self.enabled, generated=gen)
        if with_generated_info:
            try:
                ctx["generated"].update(install.generated_info(self.catalog, self.enabled, ctx))
            except Exception:  # noqa: BLE001 - info lists are a convenience; plan errors surface elsewhere
                ctx["generated"].update({"modules": [], "roles": [], "jobs": [], "skills": []})
        return ctx

    def validate(self) -> list[Issue]:
        return config.validate(self.cfg, catalog=self.catalog, vault=self.vault, raw=self.raw)


def generation_date(cfg: dict | None = None, explicit: str | None = None) -> dt.date:
    """``generated.date``: ``--date``, ``$UNI_OS_TODAY``, ``$SOURCE_DATE_EPOCH``, else today (term time zone)."""
    if explicit:
        parsed = config.as_date(explicit)
        if parsed is None:
            raise UniOsError(f"--date '{explicit}' is not a date (YYYY-MM-DD)")
        return parsed
    if os.environ.get(semester.ENV_TODAY):
        return semester.today(cfg)
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.isdigit():
        return dt.datetime.fromtimestamp(int(epoch), tz=dt.timezone.utc).date()
    return semester.today(cfg)


def _vault_of_config(config_path: Path) -> Path | None:
    """If the config sits at ``<vault>/<agent_dir>/uni-os.toml``, return ``<vault>``."""
    parent = config_path.resolve().parent
    if config_path.name == paths.CONFIG_NAME and parent.parent != parent:
        candidate = parent.parent
        if (parent / paths.MANIFEST_NAME).exists() or parent.name == paths.DEFAULT_AGENT_DIR:
            return candidate
    return None


def open_session(
    *,
    vault: str | os.PathLike | None = None,
    config: str | os.PathLike | None = None,
    modules_dir: str | os.PathLike | None = None,
    modules_override: Iterable[str] | None = None,
    preset_override: str | None = None,
    strict_modules: bool = True,
) -> Session:
    """Build a :class:`Session`; see the module docstring for the lookup order.

    With ``strict_modules=False`` unknown modules or cycles are recorded in
    ``session.module_problems`` instead of raising (used by ``doctor`` and
    ``config.load``).
    """
    from . import config as cfgmod

    vault_path = paths.expand(vault) if vault else None
    config_path: Path | None = paths.expand(config) if config else None
    if config_path is None:
        if vault_path is None:
            vault_path = paths.find_vault()
        if vault_path is None:
            raise UniOsError(
                "no vault found",
                hint="pass --vault <folder> (or --config <file>), set $UNI_OS_VAULT, or run inside the vault",
            )
        config_path = paths.config_in_vault(vault_path)
        if config_path is None:
            raise ConfigError(
                f"no {paths.DEFAULT_AGENT_DIR}/{paths.CONFIG_NAME} in {vault_path}",
                hint="create the vault with `uni-os init --config <your.toml> --vault <folder>`",
            )
    raw = cfgmod.read_toml(config_path)
    if vault_path is None:
        vault_path = _vault_of_config(config_path)
    # Deliberately NOT falling back to `paths.vault` of an outside config file: a
    # command must never write into a folder the user did not name or stand in.

    catalog = modules.discover(modules_dir)
    obsidian = bool((raw.get("obsidian") or {}).get("enabled", True)) if isinstance(raw.get("obsidian"), dict) else True
    dropped: list[str] = []
    preset_os, preset_os_source = None, ""
    if modules_override is not None:
        requested = modules.parse_id_list(modules_override)
    elif preset_override:
        if preset_override not in presets.PRESETS:
            raise UniOsError(f"unknown preset '{preset_override}' (use {', '.join(presets.PRESETS)})")
        # A preset is a recommendation: resolve it for the laptop's system (the config's
        # runtime.laptop_os, else this computer's) and say what was left out.
        preset_os, preset_os_source = presets.laptop_os_for(raw, detect=True)
        requested, dropped = presets.filter_for_os(presets.preset_modules(preset_override, obsidian=obsidian), catalog, preset_os)
    else:
        requested = modules.requested_from_config(raw, obsidian=obsidian)
        if modules.uses_config_preset(raw):
            # Only the config's own value: every machine must resolve the same list.
            preset_os, preset_os_source = presets.laptop_os_for(raw, detect=False)
            requested, dropped = presets.filter_for_os(requested, catalog, preset_os)

    problems: list[Issue] = []
    try:
        enabled = modules.resolve(requested, catalog)
    except ModuleError as exc:
        if strict_modules:
            raise
        problems.append(Issue("error", "modules", str(exc) + (f" ({exc.hint})" if exc.hint else "")))
        enabled = [m for m in requested if m in catalog.modules]
        try:
            enabled = modules.resolve(enabled, catalog)
        except ModuleError:
            pass

    cfg = cfgmod.resolve(raw, catalog, enabled)
    agent_dir = (cfg.get("paths") or {}).get("agent_dir", paths.DEFAULT_AGENT_DIR)
    return Session(
        vault=vault_path,
        config_path=config_path,
        raw=raw,
        cfg=cfg,
        catalog=catalog,
        requested=requested,
        enabled=enabled,
        agent_dir=agent_dir if isinstance(agent_dir, str) else paths.DEFAULT_AGENT_DIR,
        module_problems=problems,
        # A left-out module that another one requires came back as a dependency.
        preset_dropped=[m for m in dropped if m not in enabled],
        preset_os=preset_os,
        preset_os_source=preset_os_source,
    )


def session_from_args(args, **kwargs) -> Session:
    """``open_session`` using ``--vault``, ``--config`` and ``--modules-dir`` from argparse."""
    return open_session(
        vault=getattr(args, "vault", None),
        config=getattr(args, "config", None),
        modules_dir=getattr(args, "modules_dir", None),
        **kwargs,
    )
