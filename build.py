#!/usr/bin/env python3
"""Central build tool for GTA V Legacy.

One command takes you from the original GTA San Andreas (PS2) ISO to a
finished GTA V Legacy ISO. Every stage of the pipeline lives in
``buildiso.py``; this script is the single entry point that decides which
stages run and in which order.

Commands
--------
    python build.py                 # full build (check, extract, overlay, audio, IMG, ISO, verify)
    python build.py iso             # same as above
    python build.py check           # only validate the environment and the input ISO
    python build.py deps            # show missing Python packages
    python build.py deps --install-deps   # install them with pip
    python build.py stages          # list all stages
    python build.py info            # show the resolved paths and settings
    python build.py clean           # remove the build folder and the output ISO

Examples
--------
    python build.py --only preflight,prepare,extract
    python build.py --skip audio
    python build.py --iso "Grand Theft Auto - San Andreas (USA) (v1.03).iso" -v
    python build.py --dry-run

Every option from ``buildiso.py`` is supported as well; run
``python build.py --help`` for the complete list.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

import buildiso

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"

COMMANDS = ("all", "iso", "check", "deps", "clean", "stages", "info")

log = logging.getLogger("gtavlegacy")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="build.py",
        description=f"{buildiso.APP_NAME} v{buildiso.APP_VERSION} - central build tool.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=COMMANDS,
        help="What to do",
    )

    buildiso.add_build_arguments(parser)

    parser.add_argument(
        "--only",
        metavar="STAGE[,STAGE...]",
        help="Run only these stages (see 'python build.py stages')",
    )
    parser.add_argument(
        "--skip",
        metavar="STAGE[,STAGE...]",
        help="Skip these stages",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install the Python packages from requirements.txt",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the plan without changing anything",
    )
    return parser.parse_args(argv)


def split_stages(value: str | None) -> list[str] | None:
    if not value:
        return None
    keys = [part.strip().lower() for part in value.split(",") if part.strip()]
    return keys or None


def run_deps(install: bool) -> int:
    """Check (or install) the Python packages used by the build."""
    packages = {**buildiso.REQUIRED_PACKAGES, **buildiso.OPTIONAL_PACKAGES}
    missing = buildiso.missing_packages(packages)

    if not missing:
        print("All Python packages are installed.")
        return 0

    names = ", ".join(sorted(set(missing)))
    print(f"Missing Python packages: {names}")

    if not install:
        print(f"Install them with: {sys.executable} -m pip install -r requirements.txt")
        print("Or run: python build.py deps --install-deps")
        return 1

    if not REQUIREMENTS.is_file():
        print(f"requirements.txt not found: {REQUIREMENTS}", file=sys.stderr)
        return 1

    command = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    print("Running: " + " ".join(command))
    return subprocess.call(command)


def list_stages() -> None:
    print(f"{buildiso.APP_NAME} v{buildiso.APP_VERSION} - stages\n")
    width = max(len(stage.key) for stage in buildiso.STAGES)
    for index, stage in enumerate(buildiso.STAGES, 1):
        print(f"  {index}. {stage.key:<{width}}  {stage.description}")
    print()
    print("Run a subset with: python build.py --only preflight,extract")
    print("Skip a stage with:  python build.py --skip audio")


def print_plan(selected: list[str]) -> None:
    print(f"{buildiso.APP_NAME} v{buildiso.APP_VERSION} - plan\n")
    for index, key in enumerate(selected, 1):
        stage = buildiso.STAGES_BY_KEY[key]
        print(f"  {index}. {stage.key:<10} {stage.title}")
    print(f"\n{len(selected)} stage(s). Nothing was changed (--dry-run).")


def folder_size(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:  # pragma: no cover - racing filesystems
                continue
    return total


def clean(settings: buildiso.Settings) -> None:
    freed = 0
    for path in (settings.build, settings.output):
        if path.is_dir():
            size = folder_size(path)
            shutil.rmtree(path)
            freed += size
            print(f"Removed {path}")
        elif path.is_file():
            freed += path.stat().st_size
            path.unlink()
            print(f"Removed {path}")

    if freed:
        print(f"Freed {buildiso.human_size(freed)}.")
    else:
        print("Nothing to clean.")


def show_info(settings: buildiso.Settings) -> None:
    streams = buildiso.collect_stream_parts(settings.project / "audio" / "STREAMS")
    packages = {**buildiso.REQUIRED_PACKAGES, **buildiso.OPTIONAL_PACKAGES}
    missing = buildiso.missing_packages(packages)

    iso_state = "missing"
    if settings.iso.is_file():
        iso_state = buildiso.human_size(settings.iso.stat().st_size)

    print(f"{buildiso.APP_NAME} v{buildiso.APP_VERSION}\n")
    print(f"  Input ISO:    {settings.iso} ({iso_state})")
    print(f"  Output ISO:   {settings.output}")
    print(f"  Project:      {settings.project}")
    print(f"  Build folder: {settings.build}")
    print(f"  Allow modded: {'yes' if settings.allow_modded else 'no'}")
    print(f"  Reuse build:  {'yes' if settings.reuse_build else 'no'}")
    print(f"  Stream parts: {len(streams)}")
    print(f"  Packages:     {'all installed' if not missing else 'missing ' + ', '.join(missing)}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    buildiso.setup_logging(args.verbose)

    try:
        if args.command == "stages":
            list_stages()
            return 0

        if args.command == "deps":
            return run_deps(args.install_deps)

        if args.install_deps and run_deps(install=True) != 0:
            return 1

        settings = buildiso.load_settings(args)

        if args.command == "info":
            show_info(settings)
            return 0

        if args.command == "clean":
            clean(settings)
            return 0

        if args.command == "check":
            selected = ["preflight"]
        else:
            selected = buildiso.select_stages(
                split_stages(args.only),
                split_stages(args.skip),
            )

        if args.dry_run:
            print_plan(selected)
            return 0

        buildiso.run(settings, selected)
    except buildiso.BuildError as exc:
        log.error("")
        log.error("Build failed: %s", exc)
        return 1
    except KeyboardInterrupt:
        log.error("")
        log.error("Build interrupted.")
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
