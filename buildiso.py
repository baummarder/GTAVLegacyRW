#!/usr/bin/env python3
"""GTA V Legacy builder.

Overlays the mod content from ``src/`` onto an unmodified GTA San Andreas
(PS2, NTSC-U v1.03) ISO, rebuilds the ``.img`` archives and writes a new,
patched ISO. Everything is done in pure Python, so the build runs on Windows,
Linux and macOS without UltraISO or other external tools.

Examples
--------
    python buildiso.py
    python buildiso.py --iso "Grand Theft Auto - San Andreas (USA) (v1.03).iso"
    python buildiso.py --output "GTA V Legacy.iso" --verbose
    python buildiso.py --reuse-build

Run ``python buildiso.py --help`` for all options.
"""

from __future__ import annotations

import argparse
import collections
import configparser
import hashlib
import importlib
import logging
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import imgtool

APP_NAME = "GTA V Legacy builder"
APP_VERSION = "0.3"

DEFAULT_CONFIG = "config.ini"
BUF_SIZE = 65536

EXPECTED_MD5 = "c383c015065f8060343032480928d08d"
EXPECTED_SHA1 = "66cb01a8281cc132e023a1e52afc75d1fad3fbe1"

#: Matches the split 7z parts, e.g. ``STREAMS.7z.001``.
STREAM_PART_RE = re.compile(r"^STREAMS\.7z\.(\d+)$", re.IGNORECASE)

#: Files that are documentation, not game assets.
IGNORED_SUFFIXES = (".txt", ".cfg", ".ide", ".dat")

#: Which asset folders go into which IMG archive.
IMG_ASSET_GROUPS: dict[str, tuple[str, ...]] = {
    "gta3.img": ("Anims", "Radar", "Map", "Peds", "Vegetation", "Vehicles", "Weapons"),
    "gta_int.img": ("Interiors",),
}

ISO_NAME_RE = re.compile(r"^[A-Z0-9_]+$")

log = logging.getLogger("gtavlegacy")


class BuildError(RuntimeError):
    """Raised when the build cannot continue."""


@dataclass
class Settings:
    """Fully resolved build settings."""

    iso: Path
    output: Path
    project: Path
    build: Path
    allow_modded: bool = False
    reuse_build: bool = False


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def require_module(module_name: str, pip_name: str):
    """Import a third-party module lazily to keep ``--help`` dependency-free."""
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise BuildError(
            f"Missing Python package '{pip_name}'. Install it with: pip install {pip_name}"
        ) from exc


def resolve_path(value: str | os.PathLike) -> Path:
    """Expand ``$cwd`` and ``~`` in a path from ``config.ini``."""
    return Path(str(value).replace("$cwd", os.getcwd())).expanduser()


def checksum(src: Path) -> dict[str, str]:
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    with src.open("rb") as handle:
        while True:
            chunk = handle.read(BUF_SIZE)
            if not chunk:
                break
            md5.update(chunk)
            sha1.update(chunk)
    return {"md5": md5.hexdigest(), "sha1": sha1.hexdigest()}


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024.0 or unit == "GiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024.0
    return f"{size} B"


def copy_tree(src: Path, dst: Path) -> None:
    """Copy ``src`` into ``dst``, ignoring missing sources."""
    if not src.is_dir():
        log.debug("Skipping missing folder: %s", src)
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def copy_tree_contents(src: Path, dst: Path) -> None:
    """Copy the *contents* of ``src`` into ``dst``."""
    if not src.is_dir():
        log.debug("Skipping missing folder: %s", src)
        return
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        target = dst / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target, dirs_exist_ok=True)
        else:
            shutil.copy2(entry, target)


def collect_assets(folder: Path) -> list[Path]:
    """Return all asset files below ``folder``, skipping documentation."""
    if not folder.is_dir():
        log.debug("Skipping missing asset folder: %s", folder)
        return []

    found: list[Path] = []
    for root, directories, files in os.walk(folder):
        directories.sort()
        for name in sorted(files):
            if name.lower().endswith(IGNORED_SUFFIXES):
                continue
            found.append(Path(root) / name)
    return found


# --------------------------------------------------------------------------- #
# Build steps
# --------------------------------------------------------------------------- #


def check_iso(src: Path, allow_modded: bool) -> None:
    log.info("      ISO: %s", src)

    if not src.is_file():
        raise BuildError(
            f"ISO not found: {src}\n"
            "Put the original 'Grand Theft Auto - San Andreas (USA) (v1.03).iso' "
            "next to this script or pass --iso."
        )

    if allow_modded:
        log.info("      Checksum verification skipped (--allow-modded).")
        return

    log.info("      Calculating MD5/SHA1, this can take a while ...")
    digest = checksum(src)

    if digest["md5"] != EXPECTED_MD5 or digest["sha1"] != EXPECTED_SHA1:
        raise BuildError(
            "ISO checksum mismatch.\n"
            f"  expected md5  {EXPECTED_MD5}\n"
            f"  actual   md5  {digest['md5']}\n"
            f"  expected sha1 {EXPECTED_SHA1}\n"
            f"  actual   sha1 {digest['sha1']}\n"
            "Use the NTSC-U v1.03 dump, or pass --allow-modded to build anyway."
        )


def extract_iso(src: Path, dst: Path) -> None:
    pycdlib = require_module("pycdlib", "pycdlib")

    dst.mkdir(parents=True, exist_ok=True)
    iso = pycdlib.PyCdlib()
    try:
        iso.open(str(src))
        root = iso.get_record(iso_path="/")
        pending = collections.deque([root])

        while pending:
            record = pending.popleft()
            iso_path = iso.full_path_from_dirrecord(record, False)
            relative = iso_path.lstrip("/")

            if record.is_dir():
                if relative:
                    (dst / relative).mkdir(parents=True, exist_ok=True)
                for child in iso.list_children(iso_path=iso_path):
                    if child is None or child.is_dot() or child.is_dotdot():
                        continue
                    pending.append(child)
            else:
                target = dst / relative.replace(";1", "")
                target.parent.mkdir(parents=True, exist_ok=True)
                iso.get_file_from_iso(str(target), iso_path=iso_path)
    finally:
        iso.close()


def install_project_files(project: Path, build: Path) -> None:
    for name in ("intro", "text", "data", "models"):
        copy_tree(project / name, build / name)

    for name in ("CONFIG", "SFX"):
        copy_tree(project / "audio" / name, build / "audio" / name)

    for name in ("anim", "plugins"):
        copy_tree(project / name, build / name)

    copy_tree_contents(project / "overlays", build)

    # Files that must not end up in the final ISO.
    for stale in (build / "models" / "gta3_1.img", build / "movies"):
        if stale.is_dir():
            log.debug("Removing stale folder: %s", stale)
            shutil.rmtree(stale)
        elif stale.exists():
            log.debug("Removing stale file: %s", stale)
            stale.unlink()


def collect_stream_parts(streams_dir: Path) -> list[Path]:
    """Return the split 7z parts in numeric order, independent of the count."""
    if not streams_dir.is_dir():
        return []

    parts: list[tuple[int, Path]] = []
    for entry in streams_dir.iterdir():
        if not entry.is_file():
            continue
        match = STREAM_PART_RE.match(entry.name)
        if match:
            parts.append((int(match.group(1)), entry))

    return [path for _, path in sorted(parts)]


def unpack_streams(streams_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    parts = collect_stream_parts(streams_dir)

    if not parts:
        log.warning("      No STREAMS.7z.* parts found in %s - skipping audio.", streams_dir)
        return

    numbers = [int(STREAM_PART_RE.match(part.name).group(1)) for part in parts]
    if numbers != list(range(1, len(numbers) + 1)):
        log.warning(
            "      STREAMS parts are not numbered 1..%d without gaps: %s",
            len(numbers),
            numbers,
        )

    log.info("      Joining %d archive parts ...", len(parts))
    archive = target_dir / "result.7z"
    if archive.exists():
        archive.unlink()

    with archive.open("wb") as outfile:
        for part in parts:
            with part.open("rb") as infile:
                shutil.copyfileobj(infile, outfile, BUF_SIZE)

    py7zr = require_module("py7zr", "py7zr")
    try:
        with py7zr.SevenZipFile(str(archive), "r") as compressed:
            compressed.extractall(path=str(target_dir))
    finally:
        archive.unlink(missing_ok=True)


def rebuild_img_archives(settings: Settings) -> None:
    """Merge the assets from ``src/assets`` into the extracted IMG archives."""
    models = settings.build / "models"

    for archive_name, categories in IMG_ASSET_GROUPS.items():
        archive = models / archive_name
        if not archive.is_file():
            raise BuildError(
                f"Missing {archive_name} in {models}.\n"
                "The ISO extraction looks incomplete - delete the build folder and rebuild."
            )

        files: list[Path] = []
        for category in categories:
            files.extend(collect_assets(settings.project / "assets" / category))

        try:
            existing = {
                entry.name.upper() for entry in imgtool.read_directory(archive)
            }
            replacements: dict[str, Path] = {}
            additions: list[Path] = []
            for path in files:
                key = path.name.upper()
                if key in existing:
                    replacements[key] = path
                else:
                    additions.append(path)

            temporary = archive.with_name(archive.name + ".new")
            result = imgtool.rebuild(archive, temporary, replacements, additions)
            os.replace(temporary, archive)
        except imgtool.ImgError as exc:
            raise BuildError(f"Could not rebuild {archive_name}: {exc}") from exc

        log.info(
            "      %s: %d entries (%d replaced, %d added, %s)",
            archive_name,
            result.total,
            result.replaced,
            result.added,
            human_size(result.size),
        )


def iso_path(relative: Path, *, is_file: bool) -> str:
    """Convert a relative path into a validated ISO9660 level 1 path."""
    parts: list[str] = []
    for part in relative.parts:
        name = part.upper()
        stem, dot, extension = name.rpartition(".")
        if not dot:
            stem, extension = name, ""

        valid = (
            ISO_NAME_RE.match(stem)
            and 1 <= len(stem) <= 8
            and (extension == "" or (ISO_NAME_RE.match(extension) and len(extension) <= 3))
        )
        if not valid:
            raise BuildError(
                f"'{part}' cannot be stored in a plain ISO9660 image. "
                "Names must be 8.3 with A-Z, 0-9 and _ only."
            )
        parts.append(name)

    path = "/" + "/".join(parts)
    return f"{path};1" if is_file else path


def write_iso(settings: Settings) -> None:
    pycdlib = require_module("pycdlib", "pycdlib")

    if settings.output.exists():
        settings.output.unlink()
    settings.output.parent.mkdir(parents=True, exist_ok=True)

    iso = pycdlib.PyCdlib()
    added = 0
    try:
        iso.new(
            interchange_level=1,
            vol_ident="GTAVLEGACY",
            joliet=None,
            rock_ridge=None,
        )

        for root, directories, files in os.walk(settings.build):
            directories.sort()
            relative_root = Path(root).relative_to(settings.build)

            for directory in directories:
                iso.add_directory(iso_path=iso_path(relative_root / directory, is_file=False))

            for name in sorted(files):
                local = Path(root) / name
                iso.add_file(str(local), iso_path=iso_path(relative_root / name, is_file=True))
                added += 1
                log.debug("      + %s", relative_root / name)

        log.info("      Packaging %d files ...", added)
        iso.write(str(settings.output))
    finally:
        iso.close()

    if not settings.output.is_file() or settings.output.stat().st_size == 0:
        raise BuildError(f"Writing the ISO failed: {settings.output} is missing or empty.")


# --------------------------------------------------------------------------- #
# Configuration & CLI
# --------------------------------------------------------------------------- #


def read_config(path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if not path.is_file():
        raise BuildError(
            f"Config file not found: {path}\n"
            "Run the script from the repository root or pass --config."
        )
    try:
        with path.open("r", encoding="utf-8") as handle:
            config.read_file(handle)
    except configparser.Error as exc:
        raise BuildError(f"Could not parse {path}: {exc}") from exc
    return config


def load_settings(args: argparse.Namespace) -> Settings:
    config = read_config(args.config)

    def value(key: str, fallback: str | None = None) -> str | None:
        return config.get("DEFAULT", key, fallback=fallback)

    def flag(key: str, default: bool = False) -> bool:
        return config.getboolean("DEFAULT", key, fallback=default)

    iso_setting = value("iso_name")
    iso = args.iso or (resolve_path(iso_setting) if iso_setting else None)
    if iso is None:
        raise BuildError("No input ISO configured. Set iso_name in config.ini or pass --iso.")

    output_setting = value("output", "GTA V Legacy Closed Alpha.iso")
    output = args.output or resolve_path(output_setting)

    project = args.project_dir or resolve_path(value("project_path", "./src"))
    build = args.build_dir or resolve_path(value("build_path", "./build"))

    reuse_build = (args.reuse_build or flag("reuse_build")) and not args.clean

    return Settings(
        iso=iso,
        output=output,
        project=project,
        build=build,
        allow_modded=args.allow_modded or flag("allow_modded"),
        reuse_build=reuse_build,
    )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="buildiso.py",
        description=f"{APP_NAME} v{APP_VERSION} - builds a patched GTA San Andreas (PS2) ISO.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=Path(DEFAULT_CONFIG),
                        help="Path to the build configuration")
    parser.add_argument("--iso", type=Path, help="Original GTA San Andreas (NTSC-U v1.03) ISO")
    parser.add_argument("--output", type=Path, help="Path of the ISO to write")
    parser.add_argument("--project-dir", type=Path, help="Folder containing the mod files")
    parser.add_argument("--build-dir", type=Path, help="Working folder for the extracted ISO")
    parser.add_argument("--allow-modded", action="store_true",
                        help="Skip the ISO checksum verification")

    extraction = parser.add_mutually_exclusive_group()
    extraction.add_argument("--reuse-build", action="store_true",
                            help="Reuse an existing build folder instead of extracting again")
    extraction.add_argument("--clean", action="store_true",
                            help="Force a clean build (removes the build folder)")

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def run(settings: Settings) -> None:
    log.info("%s v%s", APP_NAME, APP_VERSION)
    log.info("      Project: %s", settings.project)
    log.info("      Build:   %s", settings.build)

    if not settings.project.is_dir():
        raise BuildError(f"Project folder not found: {settings.project}")

    # Validate everything *before* touching the build folder, so a typo in the
    # configuration cannot wipe an existing extraction.
    log.info("[1/8] Checking input ISO ...")
    check_iso(settings.iso, settings.allow_modded)

    log.info("[2/8] Preparing build folder ...")
    if settings.build.exists() and not settings.reuse_build:
        shutil.rmtree(settings.build)
    settings.build.mkdir(parents=True, exist_ok=True)

    log.info("[3/8] Extracting ISO ...")
    if settings.reuse_build and (settings.build / "models" / "gta3.img").is_file():
        log.info("      Existing extraction found, skipping.")
    else:
        extract_iso(settings.iso, settings.build)

    log.info("[4/8] Copying mod files ...")
    install_project_files(settings.project, settings.build)

    log.info("[5/8] Unpacking audio streams ...")
    unpack_streams(
        settings.project / "audio" / "STREAMS",
        settings.build / "audio" / "STREAMS",
    )

    log.info("[6/8] Rebuilding IMG archives ...")
    rebuild_img_archives(settings)

    log.info("[7/8] Writing ISO ...")
    write_iso(settings)

    log.info("[8/8] Verifying output ...")
    size = settings.output.stat().st_size
    log.info("      %s (%s)", settings.output, human_size(size))
    log.info("")
    log.info("Done.")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.verbose)

    try:
        settings = load_settings(args)
        run(settings)
    except BuildError as exc:
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
