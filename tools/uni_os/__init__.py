"""Uni OS tools: the ``uni-os`` command line and its helper library.

Pure Python standard library (3.11+). Entry point: ``python tools/uni_os.py <command>``.

Modules worth importing from other code (stable helpers; the full list is under
"Library helpers" in ``tools/README.md``):

- ``uni_os.config.load(vault)``: the resolved config of a vault (dict).
- ``uni_os.semester.week_of(date, cfg)``: the term week of a date.
- ``uni_os.jobs.parse_conf(path)`` / ``uni_os.jobs.list_jobs(vault)``: job definitions.
- ``uni_os.template.render(text, context)``: the template engine.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
