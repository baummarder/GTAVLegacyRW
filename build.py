#!/usr/bin/env python3
"""Central build tool for GTA V Legacy.

One command takes you from the original GTA San Andreas (PS2) ISO to a
finished GTA V Legacy ISO. Every stage of the pipeline lives in
``buildiso.py``; this script is the single entry point that decides which
stages run and in which order.

Start it in a terminal and it asks for the original ISO (drag & drop works),
the output name and the usual options, then builds:

    python build.py

Commands
--------
    python build.py                 # interactive wizard (asks for the ISO)
    python build.py wizard          # same, explicitly
    python build.py --iso PATH      # direct build, no questions
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
    python build.py --non-interactive    # never ask, use config.ini/--iso only

Every option from ``buildiso.py`` is supported as well; run
``python build.py --help`` for the complete list.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import buildiso

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"

COMMANDS = ("all", "iso", "wizard", "check", "deps", "clean", "stages", "info")

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
        help="What to do (default: all, wizard in interactive terminal)",
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
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Never start the wizard; use config.ini and the command line only",
    )
    return parser.parse_args(argv)


# --------------------------------------------------------------------------- #
# Interactive wizard
# --------------------------------------------------------------------------- #


def is_interactive() -> bool:
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):  # pragma: no cover - exotic streams
        return False


def clean_path(value: str) -> Path:
    """Accept drag & drop paths with quotes, ``&`` prefixes, ``~`` and variables."""
    text = value.strip().lstrip("&").strip().strip('"').strip("'").strip()
    return Path(os.path.expandvars(os.path.expanduser(text)))


def ask(prompt: str, default: str | None = None) -> str | None:
    """Ask for a line. Returns ``None`` on EOF/Ctrl+C so callers can abort."""
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    return answer or default


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        try:
            answer = input(f"  {prompt} ({hint}): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return default
        if not answer:
            return default
        if answer in {"y", "yes", "j", "ja"}:
            return True
        if answer in {"n", "no", "nein"}:
            return False
        print("  Please answer with yes or no.")


def find_iso_candidates(settings: buildiso.Settings) -> list[Path]:
    """Collect ISO files from the config, the working directory and the repo."""
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        if not path.is_file():
            return
        try:
            key = path.resolve()
        except OSError:  # pragma: no cover - unusual on real systems
            key = path
        if key in seen:
            return
        seen.add(key)
        candidates.append(path)

    add(settings.iso)

    for base in (Path.cwd(), ROOT):
        for pattern in ("*.iso", "*.ISO"):
            for path in sorted(base.glob(pattern)):
                add(path)

    return candidates[:8]


def choose_iso(settings: buildiso.Settings) -> Path | None:
    candidates = find_iso_candidates(settings)

    print("\nGTA San Andreas (PS2) ISO")
    if candidates:
        print("  Found:")
        for index, path in enumerate(candidates, 1):
            print(f"    {index}. {path}  ({buildiso.human_size(path.stat().st_size)})")
        print()
    print("  Drag the ISO into this window or type/paste its path.")

    while True:
        default = str(candidates[0]) if candidates else None
        answer = ask("ISO", default)
        if answer is None:
            return None
        if not answer:
            print("  Please enter an ISO path.")
            continue
        if candidates and answer.isdigit():
            index = int(answer)
            if 1 <= index <= len(candidates):
                return candidates[index - 1]
        path = clean_path(answer)
        if path.is_file():
            return path
        print(f"  Not found: {path}")


def choose_output(settings: buildiso.Settings) -> Path:
    answer = ask("Output ISO", str(settings.output))
    if not answer:
        return settings.output
    path = clean_path(answer)
    if path.suffix.lower() != ".iso":
        path = path.with_suffix(".iso")
    return path


def open_folder(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError as exc:  # pragma: no cover - depends on the desktop
        print(f"Could not open {path}: {exc}")


def run_wizard(args: argparse.Namespace) -> int:
    print(f"{buildiso.APP_NAME} v{buildiso.APP_VERSION} - interactive build")

    settings = buildiso.load_settings(args)

    iso = choose_iso(settings)
    if iso is None:  # pragma: no cover - only on an empty stdin
        return 1
    settings.iso = iso
    settings.region = buildiso.detect_iso_region(iso)
    settings.output = choose_output(settings)

    if not settings.allow_modded:
        if settings.region.reference_checksums is None:
            print(
                f"  Detected: {settings.region.label}. No reference checksum is configured; "
                "PAL patch compatibility is experimental."
            )
            if not ask_yes_no("Continue with checksum verification skipped?", False):
                print("Cancelled.")
                return 0
            settings.allow_modded = True
        else:
            settings.allow_modded = not ask_yes_no(
                f"Verify the checksum for {settings.region.label}?",
                True,
            )

    if settings.build.exists():
        settings.reuse_build = ask_yes_no(
            f"Reuse the existing build folder ({settings.build})?", True
        )

    only = split_stages(args.only)
    skip = split_stages(args.skip)
    if only is not None or skip is not None:
        selected = buildiso.select_stages(only, skip)
    else:
        selected = [stage.key for stage in buildiso.STAGES]
        if ask_yes_no("Skip the radio streams (faster, no custom audio)?", False):
            selected = [key for key in selected if key != "audio"]

    print("\nSummary")
    print(f"  Input ISO:    {settings.iso}")
    print(f"  Game region:  {settings.region.label}")
    print(f"  Output ISO:   {settings.output}")
    print(f"  Build folder: {settings.build}")
    print(f"  Checksum:     {'skip' if settings.allow_modded else 'verify'}")
    print(f"  Reuse build:  {'yes' if settings.reuse_build else 'no'}")
    print(f"  Stages:       {len(selected)}")
    print()

    if not ask_yes_no("Start the build?", True):
        print("Cancelled.")
        return 0

    try:
        buildiso.run(settings, selected)
    except buildiso.BuildError as exc:
        if "checksum mismatch" in str(exc).lower() and ask_yes_no(
            "The ISO is not the expected dump. Continue without the checksum?", False
        ):
            settings.allow_modded = True
            buildiso.run(settings, selected)
        else:
            raise

    if settings.output.is_file() and ask_yes_no("Open the output folder?", False):
        open_folder(settings.output.parent)

    return 0


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


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
    region_state = "not detected"
    if settings.iso.is_file():
        iso_state = buildiso.human_size(settings.iso.stat().st_size)
        try:
            settings.region = buildiso.detect_iso_region(settings.iso)
            region_state = settings.region.label
        except buildiso.BuildError as exc:
            region_state = f"unsupported ({exc})"

    print(f"{buildiso.APP_NAME} v{buildiso.APP_VERSION}\n")
    print(f"  Input ISO:    {settings.iso} ({iso_state})")
    print(f"  Game region:  {region_state}")
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

        if args.command == "wizard":
            if args.dry_run:
                selected = buildiso.select_stages(
                    split_stages(args.only),
                    split_stages(args.skip),
                )
                print_plan(selected)
                return 0
            return run_wizard(args)

        if args.command in ("all", "iso"):
            selected = buildiso.select_stages(
                split_stages(args.only),
                split_stages(args.skip),
            )

            if args.dry_run:
                print_plan(selected)
                return 0

            if is_interactive() and not args.non_interactive and args.iso is None:
                return run_wizard(args)

            settings = buildiso.load_settings(args)
            buildiso.run(settings, selected)
            return 0

        settings = buildiso.load_settings(args)

        if args.command == "info":
            show_info(settings)
            return 0

        if args.command == "clean":
            clean(settings)
            return 0

        if args.command == "check":
            buildiso.run(settings, ["preflight"])
            return 0
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
