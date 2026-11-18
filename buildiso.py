#!/usr/bin/env python3
"""GTA V Legacy build stages.

Overlays the mod content from ``src/`` onto the supported US NTSC-U v1.03 GTA
San Andreas (PS2) ISO, rebuilds the ``.img`` archives and writes a new image.
PAL is temporarily disabled until its executable and patches are ported.

This module owns the individual build stages and their order. Use ``build.py``
for the central command line interface; ``python buildiso.py`` still works and
runs every stage exactly like before.

Examples
--------
    python build.py
    python build.py --iso "Grand Theft Auto - San Andreas (USA) (v1.03).iso"
    python build.py iso --output "GTA V Legacy.iso" --verbose
    python build.py check

Run ``python build.py --help`` for all options.
"""

from __future__ import annotations

import argparse
import collections
import configparser
import hashlib
import importlib
import io
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import imgtool

APP_NAME = "GTA V Legacy builder"
APP_VERSION = "0.4"

DEFAULT_CONFIG = "config.ini"
BUF_SIZE = 65536

EXPECTED_MD5 = "c383c015065f8060343032480928d08d"
EXPECTED_SHA1 = "66cb01a8281cc132e023a1e52afc75d1fad3fbe1"

#: Fallback when ``config.ini`` has no ``iso_name`` yet.
DEFAULT_ISO_NAME = "Grand Theft Auto - San Andreas (USA) (v1.03).iso"

#: Matches the split 7z parts, e.g. ``STREAMS.7z.001``.
STREAM_PART_RE = re.compile(r"^STREAMS\.7z\.(\d+)$", re.IGNORECASE)

#: Files that are documentation, not game assets.
IGNORED_SUFFIXES = (".txt", ".cfg", ".ide", ".dat")

#: Operating-system metadata that can appear beside extracted assets.
IGNORED_FILENAMES = {"desktop.ini", "thumbs.db", ".ds_store"}
IGNORED_PROJECT_NAMES = IGNORED_FILENAMES | {".vscode", "__pycache__", ".git"}

#: Which asset folders go into which IMG archive.
IMG_ASSET_GROUPS: dict[str, tuple[str, ...]] = {
    "gta3.img": ("Anims", "Radar", "Map", "Peds", "Vegetation", "Vehicles", "Weapons"),
    "gta_int.img": ("Interiors",),
}

ISO_NAME_RE = re.compile(r"^[A-Z0-9_]+$")

#: Packages that the ISO build always needs.
REQUIRED_PACKAGES: dict[str, str] = {"pycdlib": "pycdlib"}

#: Packages that are only needed when the audio streams are present.
OPTIONAL_PACKAGES: dict[str, str] = {"py7zr": "py7zr"}

#: Rough space estimate: input ISO + extracted build folder + output ISO.
DISK_SPACE_FACTOR = 2.5
ISO_LOGICAL_BLOCK_SIZE = 2048
PS2_DVD_TYPE_L_PATH_TABLE_LBA = 257
PS2_DVD_TYPE_M_PATH_TABLE_LBA = 259
PS2_UDF_VRS = ((18, b"\x00BEA01"), (19, b"\x00NSR02"), (20, b"\x00TEA01"))
PS2_UDF_ANCHOR_LBA = 256
PS2_SYSTEM_IDENTIFIER = b"PLAYSTATION"

#: Entries shared by every finished build.
REQUIRED_ISO_ENTRIES = (
    "/SYSTEM.CNF;1",
    "/MODELS/GTA3.IMG;1",
    "/MODELS/GTA_INT.IMG;1",
    "/MOVIES/OPEN1.PSS;1",
    "/MOVIES/VCNTSC.PSS;1",
)

log = logging.getLogger("gtavlegacy")


class BuildError(RuntimeError):
    """Raised when the build cannot continue."""


@dataclass(frozen=True)
class RegionProfile:
    """A game release whose executable and regional mode are recognized."""

    executable: str
    label: str
    version: str | None
    reference_checksums: tuple[str, str] | None = None


REGION_PROFILES: dict[str, RegionProfile] = {
    "SLUS_209.46": RegionProfile(
        executable="SLUS_209.46",
        label="US NTSC-U v1.03",
        version="1.03",
        reference_checksums=(EXPECTED_MD5, EXPECTED_SHA1),
    ),
}

DISABLED_PAL_EXECUTABLE = "SLES_529.27"


@dataclass
class Settings:
    """Fully resolved build settings."""

    iso: Path
    output: Path
    project: Path
    build: Path
    allow_modded: bool = False
    reuse_build: bool = False
    region: RegionProfile | None = None


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


def format_duration(seconds: float) -> str:
    """Format a duration for the build summary."""
    if seconds < 1.0:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60.0:
        return f"{seconds:.1f} s"
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes} min {rest} s"


def missing_packages(modules: tuple[str, ...] | dict[str, str]) -> list[str]:
    """Return the pip names of packages that cannot be imported."""
    names = modules.items() if isinstance(modules, dict) else ((name, name) for name in modules)
    missing: list[str] = []
    for module_name, pip_name in names:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name)
    return missing


def require_packages(modules: tuple[str, ...] | dict[str, str]) -> None:
    missing = missing_packages(modules)
    if missing:
        packages = ", ".join(sorted(set(missing)))
        raise BuildError(
            f"Missing Python package(s): {packages}\n"
            f"Install them with: {sys.executable} -m pip install -r requirements.txt\n"
            "Or run: python build.py deps --install"
        )


def copy_tree(src: Path, dst: Path, *, ignored_suffixes: tuple[str, ...] = ()) -> None:
    """Copy ``src`` into ``dst``, ignoring missing sources."""
    if not src.is_dir():
        log.debug("Skipping missing folder: %s", src)
        return
    def ignored_entries(_directory: str, names: list[str]) -> set[str]:
        return {
            name for name in names
            if name.lower() in IGNORED_PROJECT_NAMES
            or Path(name).suffix.lower() in ignored_suffixes
        }

    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignored_entries)


def copy_tree_contents(src: Path, dst: Path) -> None:
    """Copy the *contents* of ``src`` into ``dst``."""
    if not src.is_dir():
        log.debug("Skipping missing folder: %s", src)
        return
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.name.lower() in IGNORED_PROJECT_NAMES:
            continue
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
            if name.lower() in IGNORED_FILENAMES or name.lower().endswith(IGNORED_SUFFIXES):
                continue
            found.append(Path(root) / name)
    return found


# --------------------------------------------------------------------------- #
# Build steps
# --------------------------------------------------------------------------- #


def detect_iso_region(src: Path) -> RegionProfile:
    """Identify a supported release from SYSTEM.CNF and its boot executable."""
    pycdlib = require_module("pycdlib", "pycdlib")
    iso = pycdlib.PyCdlib()
    try:
        iso.open(str(src))
        try:
            system_buffer = io.BytesIO()
            iso.get_file_from_iso_fp(system_buffer, iso_path="/SYSTEM.CNF;1")
            system_text = system_buffer.getvalue().decode("ascii", "replace")
        except Exception as exc:
            raise BuildError("The ISO is missing a readable SYSTEM.CNF boot file.") from exc

        boot_match = re.search(
            r"(?im)^\s*BOOT2\s*=\s*cdrom0:[\\/]+([^;\s]+)(?:;\d+)?",
            system_text,
        )
        boot_executable = None
        if boot_match:
            boot_executable = boot_match.group(1).replace("\\", "/").rsplit("/", 1)[-1].upper()

        root_executables: list[str] = []
        for record in iso.list_children(iso_path="/"):
            if record is None or record.is_dot() or record.is_dotdot() or record.is_dir():
                continue
            name = record.file_identifier().decode("ascii", "replace").split(";", 1)[0].upper()
            if re.match(r"^(?:SLUS|SLES|SCUS|SCES)_", name):
                root_executables.append(name)

        executable = boot_executable
        if executable is None and len(root_executables) == 1:
            # Keep simple fixture ISOs identifiable even without BOOT2 metadata.
            executable = root_executables[0]

        profile = REGION_PROFILES.get(executable or "")
        if profile is None:
            if executable == DISABLED_PAL_EXECUTABLE:
                raise BuildError(
                    "PAL v1.00 (SLES_529.27) is temporarily disabled: the game reaches "
                    "the PS2 startup screen but does not continue. Use the supported US "
                    "NTSC-U v1.03 (SLUS_209.46) image. PAL investigation notes: "
                    "experimental/pal/README.md."
                )
            found = ", ".join(sorted(root_executables)) or "no recognized executable"
            raise BuildError(
                "Unsupported GTA San Andreas release. The only supported profile is "
                "US NTSC-U v1.03 (SLUS_209.46); "
                f"SYSTEM.CNF points to {boot_executable or found}."
            )

        try:
            iso.get_record(iso_path=f"/{profile.executable};1")
        except Exception as exc:
            raise BuildError(
                f"SYSTEM.CNF points to {profile.executable}, but that executable is missing from the ISO."
            ) from exc

        version_match = re.search(r"(?im)^\s*VER\s*=\s*([^\s]+)", system_text)
        version = version_match.group(1).strip() if version_match else None

        if version and version != profile.version:
            raise BuildError(
                f"{profile.executable} detected with VER={version}; this profile requires v{profile.version}."
            )

        return profile
    except BuildError:
        raise
    except Exception as exc:
        raise BuildError(f"Could not inspect the ISO region: {exc}") from exc
    finally:
        iso.close()


def check_iso(src: Path, allow_modded: bool) -> RegionProfile:
    log.info("      ISO: %s", src)

    if not src.is_file():
        raise BuildError(
            f"ISO not found: {src}\n"
            "Choose a supported US NTSC-U v1.03 San Andreas ISO, "
            "or pass its path with --iso."
        )

    profile = detect_iso_region(src)
    log.info("      Detected game: %s (%s)", profile.label, profile.executable)

    if allow_modded:
        log.info("      Checksum verification skipped (--allow-modded).")
        return profile

    if profile.reference_checksums is None:
        raise BuildError(
            f"Detected {profile.label}, but no reference checksum is configured. "
            "Configure its reference checksum before building."
        )

    expected_md5, expected_sha1 = profile.reference_checksums
    log.info("      Calculating MD5/SHA1, this can take a while ...")
    digest = checksum(src)

    if digest["md5"] != expected_md5 or digest["sha1"] != expected_sha1:
        raise BuildError(
            "ISO checksum mismatch.\n"
            f"  expected md5  {expected_md5}\n"
            f"  actual   md5  {digest['md5']}\n"
            f"  expected sha1 {expected_sha1}\n"
            f"  actual   sha1 {digest['sha1']}\n"
            "For a modified copy of a recognized release, pass --allow-modded."
        )
    return profile


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


def restore_required_movies(src: Path, build: Path) -> None:
    """Keep the original NTSC intro movies available in reused build folders."""
    movie_names = ("OPEN1.PSS", "VCNTSC.PSS")
    missing = [name for name in movie_names if not (build / "movies" / name).is_file()]
    if not missing:
        return

    pycdlib = require_module("pycdlib", "pycdlib")
    iso = pycdlib.PyCdlib()
    try:
        iso.open(str(src))
        for name in missing:
            target = build / "movies" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with target.open("wb") as outfile:
                    iso.get_file_from_iso_fp(outfile, iso_path=f"/MOVIES/{name};1")
            except Exception as exc:
                raise BuildError(
                    f"Could not restore required startup movie MOVIES/{name} from the input ISO."
                ) from exc
    finally:
        iso.close()


def install_project_files(project: Path, build: Path) -> None:
    for name in ("intro", "text", "data"):
        copy_tree(project / name, build / name)

    # PNG/PSD files under models/txd/vphone are source artwork; the game uses
    # the compiled TXD dictionaries copied alongside them instead.
    copy_tree(project / "models", build / "models", ignored_suffixes=(".png", ".psd"))

    for name in ("CONFIG", "SFX"):
        copy_tree(project / "audio" / name, build / "audio" / name)

    for name in ("anim", "plugins"):
        copy_tree(project / name, build / name)

    copy_tree_contents(project / "overlays", build)

    # This split image is an extraction artifact; the original movies folder
    # contains the intro videos GTA SA needs during startup.
    for stale in (build / "models" / "gta3_1.img",):
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
    """Convert a relative path into a validated ISO9660 level 2 path."""
    parts: list[str] = []
    for part in relative.parts:
        name = part.upper()
        stem, dot, extension = name.rpartition(".")
        if not dot:
            stem, extension = name, ""

        valid = (
            ISO_NAME_RE.match(stem)
            and 1 <= len(stem) + (1 + len(extension) if dot else 0) <= 31
            and (not dot or (extension and ISO_NAME_RE.match(extension)))
        )
        if not valid:
            raise BuildError(
                f"'{part}' cannot be stored in a plain ISO9660 image. "
                "Names must be at most 31 characters and use A-Z, 0-9, _ and one dot."
            )
        parts.append(name)

    path = "/" + "/".join(parts)
    return f"{path};1" if is_file else path


def ps2iso_tools() -> tuple[Path, Path]:
    """Return the bundled dumps2iso and mkps2iso executables for this platform."""
    if sys.platform == "win32":
        folder, suffix = "windows-x64", ".exe"
    elif sys.platform == "darwin":
        folder, suffix = "macos", ""
    elif sys.platform.startswith("linux"):
        folder, suffix = "linux-x64", ""
    else:  # pragma: no cover - depends on the host platform
        raise BuildError(f"PS2 ISO packaging is not supported on {sys.platform}.")

    machine = platform.machine().lower()
    supported = (
        {"amd64", "x86_64"}
        if folder != "macos"
        else {"amd64", "x86_64", "arm64", "aarch64"}
    )
    if machine not in supported:
        raise BuildError(f"Bundled PS2 ISO tools do not support {platform.machine()}.")

    tools_dir = Path(__file__).resolve().parent / "tools" / "mkps2iso" / folder
    dumper = tools_dir / f"dumps2iso{suffix}"
    writer = tools_dir / f"mkps2iso{suffix}"
    missing = [str(path) for path in (dumper, writer) if not path.is_file()]
    if missing:
        raise BuildError("Bundled PS2 ISO tools are missing: " + ", ".join(missing))
    return dumper, writer


def run_packaging_tool(command: list[str], label: str) -> None:
    """Run a bundled PS2 ISO utility and report its output on failure."""
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise BuildError(f"Could not start {label}: {exc}") from exc
    if result.returncode:
        details = (result.stdout + "\n" + result.stderr).strip()
        raise BuildError(f"{label} failed (exit code {result.returncode}).\n{details}")
    if result.stdout.strip():
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        for line in lines[-5:]:
            log.info("      %s", line)
    if result.stderr.strip():
        for line in result.stderr.splitlines():
            log.warning("      %s", line)


def write_iso(settings: Settings) -> None:
    dumper, writer = ps2iso_tools()
    settings.output.parent.mkdir(parents=True, exist_ok=True)
    profile = settings.region or detect_iso_region(settings.iso)
    serial = profile.executable.replace("_", "").replace(".", "")
    serial = f"{serial[:4]}-{serial[4:]}"
    disc_region = "america"
    temporary_path: Path | None = None
    try:
        fd, temporary_name = tempfile.mkstemp(
            prefix=f"{settings.output.stem}.", suffix=".tmp.iso", dir=settings.output.parent
        )
        os.close(fd)
        temporary_path = Path(temporary_name)
        temporary_path.unlink()

        with tempfile.TemporaryDirectory(prefix="gtavlegacy-ps2iso-") as workspace:
            xml_path = Path(workspace) / "build.xml"
            run_packaging_tool(
                [str(dumper), "-q", "-x", str(xml_path), str(settings.build.resolve())],
                "dumps2iso",
            )
            if not xml_path.is_file():
                raise BuildError("dumps2iso did not create the PS2 image project file.")

            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                identifiers = root.find("identifiers")
                if root.tag != "iso_project" or identifiers is None:
                    raise ValueError("unexpected XML project layout")
            except (ET.ParseError, ValueError) as exc:
                raise BuildError(f"Could not prepare the PS2 image project: {exc}") from exc

            root.set("image_name", settings.output.name)
            root.set("serial", serial)
            root.set("region", disc_region)
            identifiers.set("system", "PLAYSTATION")
            identifiers.set("application", "PLAYSTATION")
            identifiers.set("volume", "SAN_ANDREAS")
            tree.write(xml_path, encoding="utf-8", xml_declaration=True)

            run_packaging_tool(
                [str(writer), "-y", "-o", str(temporary_path), str(xml_path)],
                "mkps2iso",
            )

        if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
            raise BuildError(f"PS2 ISO writer produced no image: {temporary_path}")
        os.replace(temporary_path, settings.output)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# Stages
# --------------------------------------------------------------------------- #


def warn_free_space(settings: Settings, iso_size: int) -> None:
    """Warn when the target drives are too small for a full build."""
    needed = int(iso_size * DISK_SPACE_FACTOR)

    probes = {"build folder": settings.build, "output": settings.output.parent}
    seen: set[Path] = set()
    for label, path in probes.items():
        probe = path
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        try:
            resolved = probe.resolve()
        except OSError:  # pragma: no cover - unusual on real systems
            continue
        if resolved in seen:
            continue
        seen.add(resolved)

        try:
            free = shutil.disk_usage(probe).free
        except OSError:  # pragma: no cover - unusual on real systems
            continue

        log.info("      Free space (%s): %s", label, human_size(free))
        if free < needed:
            log.warning(
                "      Only %s left for the %s; a full build needs roughly %s.",
                human_size(free),
                label,
                human_size(needed),
            )


def check_environment(settings: Settings) -> None:
    """Validate packages, paths, disc space and the input ISO."""
    if not settings.project.is_dir():
        raise BuildError(f"Project folder not found: {settings.project}")

    packages = dict(REQUIRED_PACKAGES)
    if collect_stream_parts(settings.project / "audio" / "STREAMS"):
        packages.update(OPTIONAL_PACKAGES)
    require_packages(packages)
    ps2iso_tools()

    settings.region = check_iso(settings.iso, settings.allow_modded)
    warn_free_space(settings, settings.iso.stat().st_size)


def prepare_build_folder(settings: Settings) -> None:
    if settings.build.exists() and not settings.reuse_build:
        log.info("      Removing previous build folder.")
        shutil.rmtree(settings.build)
    settings.build.mkdir(parents=True, exist_ok=True)


def extract_stage(settings: Settings) -> None:
    if settings.reuse_build and (settings.build / "models" / "gta3.img").is_file():
        log.info("      Existing extraction found, skipping.")
        restore_required_movies(settings.iso, settings.build)
        return
    extract_iso(settings.iso, settings.build)


def overlay_stage(settings: Settings) -> None:
    install_project_files(settings.project, settings.build)


def audio_stage(settings: Settings) -> None:
    unpack_streams(
        settings.project / "audio" / "STREAMS",
        settings.build / "audio" / "STREAMS",
    )


def images_stage(settings: Settings) -> None:
    rebuild_img_archives(settings)


def package_stage(settings: Settings) -> None:
    write_iso(settings)


def verify_output(settings: Settings) -> None:
    """Reopen the finished ISO and make sure the important entries exist."""
    pycdlib = require_module("pycdlib", "pycdlib")
    output = settings.output

    if not output.is_file() or output.stat().st_size == 0:
        raise BuildError(f"Output ISO is missing or empty: {output}")

    profile = detect_iso_region(output)
    if settings.region is not None and profile.executable != settings.region.executable:
        raise BuildError(
            f"The output region changed unexpectedly: expected {settings.region.executable}, "
            f"found {profile.executable}."
        )

    required_entries = (
        *REQUIRED_ISO_ENTRIES,
        f"/{profile.executable};1",
    )
    files = 0
    directories = 0
    iso = pycdlib.PyCdlib()
    try:
        iso.open(str(output))

        if (
            iso.pvd.path_table_location_le != PS2_DVD_TYPE_L_PATH_TABLE_LBA
            or iso.pvd.path_table_location_be != PS2_DVD_TYPE_M_PATH_TABLE_LBA
        ):
            raise BuildError(
                "The output ISO does not use the PS2 DVD path-table layout "
                "(Type-L at sector 257, Type-M at sector 259)."
            )
        if PS2_SYSTEM_IDENTIFIER not in iso.pvd.system_identifier:
            raise BuildError("The output ISO is missing the PLAYSTATION system identifier.")
        if not iso.has_udf():
            raise BuildError("The output ISO is missing its PS2 DVD UDF filesystem.")

        with output.open("rb") as image:
            for sector, signature in PS2_UDF_VRS:
                image.seek(sector * ISO_LOGICAL_BLOCK_SIZE)
                if image.read(len(signature)) != signature:
                    raise BuildError(
                        f"The output ISO is missing the UDF volume sequence at sector {sector}."
                    )
            image.seek(PS2_UDF_ANCHOR_LBA * ISO_LOGICAL_BLOCK_SIZE)
            if image.read(2) != b"\x02\x00":
                raise BuildError("The output ISO is missing the UDF anchor at sector 256.")

        for required in required_entries:
            try:
                iso.get_record(iso_path=required)
            except Exception as exc:  # pycdlib raises different errors per version
                raise BuildError(
                    f"The generated ISO is missing {required.strip('/')}."
                ) from exc

        pending = [iso.get_record(iso_path="/")]
        while pending:
            record = pending.pop()
            iso_path = iso.full_path_from_dirrecord(record, False)
            for child in iso.list_children(iso_path=iso_path):
                if child is None or child.is_dot() or child.is_dotdot():
                    continue
                if child.is_dir():
                    directories += 1
                    pending.append(child)
                else:
                    files += 1
    finally:
        iso.close()

    log.info("      %s (%s)", output, human_size(output.stat().st_size))
    log.info("      %d files, %d folders", files, directories)


@dataclass(frozen=True)
class Stage:
    """One independent step of the build."""

    key: str
    title: str
    description: str
    function: Callable[[Settings], None]


#: Every stage in the order the full build runs them.
STAGES: tuple[Stage, ...] = (
    Stage(
        "preflight",
        "Checking configuration and input ISO",
        "Validate the config, Python packages, free space, ISO region and checksum policy.",
        check_environment,
    ),
    Stage(
        "prepare",
        "Preparing build folder",
        "Create a clean working folder (or keep an existing one).",
        prepare_build_folder,
    ),
    Stage(
        "extract",
        "Extracting ISO",
        "Unpack the original ISO into the build folder.",
        extract_stage,
    ),
    Stage(
        "overlay",
        "Copying mod files",
        "Overlay src/ onto the extracted ISO.",
        overlay_stage,
    ),
    Stage(
        "audio",
        "Unpacking audio streams",
        "Join and extract the STREAMS.7z parts.",
        audio_stage,
    ),
    Stage(
        "images",
        "Rebuilding IMG archives",
        "Merge the assets into gta3.img and gta_int.img.",
        images_stage,
    ),
    Stage(
        "package",
        "Writing ISO",
        "Write ISO9660 level 2 and PS2 DVD path tables at their required sectors.",
        package_stage,
    ),
    Stage(
        "verify",
        "Verifying output",
        "Reopen the finished ISO and check its contents.",
        verify_output,
    ),
)

STAGES_BY_KEY: dict[str, Stage] = {stage.key: stage for stage in STAGES}


def select_stages(only: list[str] | None = None, skip: list[str] | None = None) -> list[str]:
    """Return the stage keys to run after applying ``--only``/``--skip``."""
    unknown = [key for key in (only or []) + (skip or []) if key not in STAGES_BY_KEY]
    if unknown:
        raise BuildError(
            "Unknown stage(s): " + ", ".join(unknown) + "\n"
            "Run 'python build.py stages' to list the available stages."
        )

    selected = [stage.key for stage in STAGES] if only is None else list(dict.fromkeys(only))
    skipped = set(skip or [])
    return [key for key in selected if key not in skipped]


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
    iso = args.iso or (resolve_path(iso_setting) if iso_setting else Path(DEFAULT_ISO_NAME))

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


def add_build_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add the options shared by ``build.py`` and ``buildiso.py``."""
    parser.add_argument("--config", type=Path, default=Path(DEFAULT_CONFIG),
                        help="Path to the build configuration")
    parser.add_argument("--iso", type=Path, help="Original supported GTA San Andreas (PS2) ISO")
    parser.add_argument("--output", type=Path, help="Path of the ISO to write")
    parser.add_argument("--project-dir", type=Path, help="Folder containing the mod files")
    parser.add_argument("--build-dir", type=Path, help="Working folder for the extracted ISO")
    parser.add_argument("--allow-modded", action="store_true",
                        help="Skip ISO checksum verification for a known, supported NTSC dump")

    extraction = parser.add_mutually_exclusive_group()
    extraction.add_argument("--reuse-build", action="store_true",
                            help="Reuse an existing build folder instead of extracting again")
    extraction.add_argument("--clean", action="store_true",
                            help="Force a clean build (removes the build folder)")

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return parser


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="buildiso.py",
        description=f"{APP_NAME} v{APP_VERSION} - builds a patched GTA San Andreas (PS2) ISO.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_build_arguments(parser)
    return parser.parse_args(argv)


def run(settings: Settings, selected: list[str] | None = None) -> list[tuple[Stage, float]]:
    """Run the selected stages and return their timings."""
    keys = select_stages(selected)
    stages = [STAGES_BY_KEY[key] for key in keys]

    log.info("%s v%s", APP_NAME, APP_VERSION)
    log.info("      Project: %s", settings.project)
    log.info("      Build:   %s", settings.build)
    log.info("      Output:  %s", settings.output)
    log.info("")

    results: list[tuple[Stage, float]] = []
    started_all = time.perf_counter()
    total = len(stages)

    for index, stage in enumerate(stages, 1):
        log.info("[%d/%d] %s ...", index, total, stage.title)
        started = time.perf_counter()
        stage.function(settings)
        elapsed = time.perf_counter() - started
        results.append((stage, elapsed))
        log.info("      done in %s", format_duration(elapsed))

    elapsed_all = time.perf_counter() - started_all
    log.info("")
    log.info(
        "Done. %d stage(s) in %s.",
        len(results),
        format_duration(elapsed_all),
    )
    return results


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
