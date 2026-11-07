"""Sub-commands of ``uni-os``, one module per command (auto-discovered by ``uni_os.cli``).

Contract for a command module (also under "Extending" in ``tools/README.md``)::

    ORDER = 50                     # optional, sorts --help

    def register(subparsers):
        from uni_os.cli import common_options
        p = subparsers.add_parser("name", parents=[common_options()], help="one line")
        p.set_defaults(func=run)

    def run(args) -> int | None:   # exit code; raise uni_os.errors.UniOsError for user errors
        ...

Open the vault/config with ``uni_os.context.session_from_args(args)`` and read the
resolved config from ``session.cfg``.
"""
