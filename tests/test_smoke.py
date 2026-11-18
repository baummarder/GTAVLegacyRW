"""End-to-end smoke test using a miniature fake game ISO.

Run with::

    python -m unittest discover -s tests -v

The test does not need the real game: it creates a tiny ISO with the same
structure, runs the complete build and checks the resulting image.
"""

from __future__ import annotations

import contextlib
import io
import logging
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402
import buildiso  # noqa: E402
import imgtool  # noqa: E402
import pycdlib  # noqa: E402


def make_img(path: Path, files: dict[str, bytes]) -> None:
    """Write a minimal VER2 archive containing ``files``."""
    count = len(files)
    header_bytes = imgtool.HEADER_SIZE + imgtool.ENTRY_SIZE * count
    first_sector = -(-header_bytes // imgtool.SECTOR_SIZE)

    layout: list[tuple[str, int, int]] = []
    sector = first_sector
    for name, data in files.items():
        sectors = -(-len(data) // imgtool.SECTOR_SIZE)
        layout.append((name, sector, sectors))
        sector += sectors

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(imgtool.MAGIC)
        handle.write(struct.pack("<I", count))
        for name, offset, sectors in layout:
            handle.write(struct.pack("<IHH", offset, sectors, 0))
            handle.write(name.encode("latin-1").ljust(24, b"\0"))
        handle.write(b"\0" * (first_sector * imgtool.SECTOR_SIZE - header_bytes))
        for name, data in files.items():
            handle.write(data)
            handle.write(b"\0" * (-len(data) % imgtool.SECTOR_SIZE))


def make_iso(path: Path, files: dict[str, bytes]) -> None:
    """Write an ISO9660 level 1 image containing ``files``."""
    work = path.parent / "iso-source"
    iso = pycdlib.PyCdlib()
    try:
        iso.new(interchange_level=1, vol_ident="TEST", joliet=None, rock_ridge=None)

        directories: set[str] = set()
        for relative in files:
            parts = Path(relative).parts[:-1]
            for depth in range(1, len(parts) + 1):
                directories.add("/".join(parts[:depth]))
        for directory in sorted(directories):
            iso.add_directory(iso_path="/" + directory)

        for relative, data in sorted(files.items()):
            local = work / relative
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(data)
            iso.add_file(str(local), iso_path=f"/{relative};1")

        iso.write(str(path))
    finally:
        iso.close()


def iso_children(iso, iso_path: str = "/") -> list[str]:
    names = []
    for record in iso.list_children(iso_path=iso_path):
        if record is None or record.is_dot() or record.is_dotdot():
            continue
        names.append(record.file_identifier().decode())
    return sorted(names)


def make_fixture(work: Path) -> tuple[Path, Path]:
    """Create a miniature ISO and the matching project folder."""
    gta3_source = work / "source-gta3.img"
    make_img(gta3_source, {"LANDSTAL.DFF": b"old-model", "KEEP.TXD": b"keep"})
    interior_source = work / "source-int.img"
    make_img(interior_source, {"MUNATION.TXD": b"shop"})

    original_iso = work / "game.iso"
    make_iso(
        original_iso,
        {
            "SYSTEM.CNF": b"BOOT2 = cdrom0:\\SLUS_209.46;1\r\n",
            "SLUS_209.46": b"fake-elf" * 16,
            "MODELS/GTA3.IMG": gta3_source.read_bytes(),
            "MODELS/GTA_INT.IMG": interior_source.read_bytes(),
            "MODELS/GTA3_1.IMG": b"should-be-dropped",
            "MOVIES/LOGO.PSS": b"should-be-dropped",
            "DATA/HANDLING.CFG": b"original-handling",
        },
    )

    project = work / "project"
    (project / "models").mkdir(parents=True)
    (project / "models" / "gta3.img").write_bytes(gta3_source.read_bytes())
    (project / "models" / "gta_int.img").write_bytes(interior_source.read_bytes())
    (project / "data").mkdir()
    (project / "data" / "HANDLING.CFG").write_bytes(b"patched-handling")
    (project / "data" / "OTHER_SCRIPTS.SC").write_text("level two filename", encoding="ascii")

    vehicle = project / "assets" / "Vehicles" / "Cars" / "Landstal"
    vehicle.mkdir(parents=True)
    (vehicle / "landstal.dff").write_bytes(b"NEW-MODEL-DATA")
    (vehicle / "notes.txt").write_bytes(b"ignored documentation")

    interior = project / "assets" / "Interiors"
    interior.mkdir(parents=True)
    (interior / "new_interior.txd").write_bytes(b"interior-texture")

    return original_iso, project


class ImgToolTest(unittest.TestCase):
    def test_roundtrip_replace_and_add(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            original = work / "gta3.img"
            make_img(original, {"OLD.DFF": b"A" * 10, "KEEP.DFF": b"K" * 5000})

            replacement = work / "new.dff"
            replacement.write_bytes(b"B" * 3000)
            addition = work / "added.txd"
            addition.write_bytes(b"C" * 4096)

            result = imgtool.rebuild(
                original,
                work / "out.img",
                {"OLD.DFF": replacement},
                [addition],
            )

            self.assertEqual(result.total, 3)
            self.assertEqual(result.replaced, 1)
            self.assertEqual(result.added, 1)

            entries = {entry.name: entry for entry in imgtool.read_directory(work / "out.img")}
            self.assertEqual(set(entries), {"OLD.DFF", "KEEP.DFF", "ADDED.TXD"})
            self.assertEqual(entries["OLD.DFF"].byte_size, 4096)
            self.assertEqual(entries["ADDED.TXD"].byte_size, 4096)

            data = (work / "out.img").read_bytes()
            old = entries["OLD.DFF"]
            self.assertEqual(
                data[old.byte_offset : old.byte_offset + 3000],
                b"B" * 3000,
            )
            keep = entries["KEEP.DFF"]
            self.assertEqual(
                data[keep.byte_offset : keep.byte_offset + 5000],
                b"K" * 5000,
            )

    def test_rejects_non_ver2(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.img"
            path.write_bytes(b"VER1" + b"\0" * 64)
            with self.assertRaises(imgtool.ImgError):
                imgtool.read_directory(path)


class BuildTest(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)

    def test_full_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            original_iso, project = make_fixture(work)

            output = work / "out.iso"
            options = [
                "--config", str(ROOT / "config.ini"),
                "--iso", str(original_iso),
                "--project-dir", str(project),
                "--build-dir", str(work / "build"),
                "--output", str(output),
                "--allow-modded",
            ]

            # The central tool runs the complete pipeline, including verification.
            self.assertEqual(build.main(options), 0, "build failed")
            self.assertTrue(output.is_file())

            # A second run with --reuse-build reuses the extraction.
            self.assertEqual(build.main(options + ["--reuse-build"]), 0, "rebuild failed")
            self.assertTrue(output.is_file())

            iso = pycdlib.PyCdlib()
            try:
                iso.open(str(output))
                root = iso_children(iso)
                self.assertIn("SYSTEM.CNF;1", root)
                self.assertNotIn("MOVIES", root)
                iso.get_record(iso_path="/DATA/OTHER_SCRIPTS.SC;1")

                extracted = work / "check"
                extracted.mkdir()
                iso.get_file_from_iso(str(extracted / "handling.cfg"), iso_path="/DATA/HANDLING.CFG;1")
                self.assertEqual((extracted / "handling.cfg").read_bytes(), b"patched-handling")

                iso.get_file_from_iso(
                    str(extracted / "gta3.img"), iso_path="/MODELS/GTA3.IMG;1"
                )
                entries = {
                    entry.name: entry
                    for entry in imgtool.read_directory(extracted / "gta3.img")
                }
                self.assertIn("LANDSTAL.DFF", entries)
                self.assertNotIn("NOTES.TXT", entries)
                self.assertIn("KEEP.TXD", entries)

                payload = (extracted / "gta3.img").read_bytes()
                landstal = entries["LANDSTAL.DFF"]
                self.assertEqual(
                    payload[landstal.byte_offset : landstal.byte_offset + len(b"NEW-MODEL-DATA")],
                    b"NEW-MODEL-DATA",
                )

                iso.get_file_from_iso(
                    str(extracted / "gta_int.img"), iso_path="/MODELS/GTA_INT.IMG;1"
                )
                interiors = {
                    entry.name
                    for entry in imgtool.read_directory(extracted / "gta_int.img")
                }
                self.assertIn("NEW_INTERIOR.TXD", interiors)
                self.assertIn("MUNATION.TXD", interiors)

                self.assertNotIn("GTA3_1.IMG", iso_children(iso, "/MODELS"))
            finally:
                iso.close()


class StageTest(unittest.TestCase):
    def test_stage_registry(self) -> None:
        keys = [stage.key for stage in buildiso.STAGES]
        self.assertEqual(
            keys,
            ["preflight", "prepare", "extract", "overlay", "audio", "images", "package", "verify"],
        )
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(buildiso.STAGES_BY_KEY), set(keys))

    def test_select_stages(self) -> None:
        self.assertEqual(buildiso.select_stages(["extract", "images"]), ["extract", "images"])
        self.assertEqual(
            buildiso.select_stages(None, ["audio"]),
            ["preflight", "prepare", "extract", "overlay", "images", "package", "verify"],
        )
        with self.assertRaises(buildiso.BuildError):
            buildiso.select_stages(["nope"])


class AssetCollectionTest(unittest.TestCase):
    def test_ignores_documentation_and_os_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets = Path(temporary)
            for name in ("model.dff", "desktop.ini", "thumbs.db", ".DS_Store", "notes.txt"):
                (assets / name).write_bytes(b"asset")

            self.assertEqual(
                [path.name for path in buildiso.collect_assets(assets)],
                ["model.dff"],
            )


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)

    def test_dry_run_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            original_iso = work / "game.iso"
            make_iso(original_iso, {"SYSTEM.CNF": b"boot"})
            output = work / "out.iso"
            build_dir = work / "build"

            code = build.main(
                [
                    "--config", str(ROOT / "config.ini"),
                    "--iso", str(original_iso),
                    "--project-dir", str(ROOT / "src"),
                    "--build-dir", str(build_dir),
                    "--output", str(output),
                    "--allow-modded",
                    "--dry-run",
                ]
            )

            self.assertEqual(code, 0)
            self.assertFalse(output.exists())
            self.assertFalse(build_dir.exists())

    def test_check_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            original_iso = work / "game.iso"
            make_iso(original_iso, {"SYSTEM.CNF": b"boot", "SLUS_209.46": b"fake-elf"})

            code = build.main(
                [
                    "check",
                    "--config", str(ROOT / "config.ini"),
                    "--iso", str(original_iso),
                    "--project-dir", str(ROOT / "src"),
                    "--build-dir", str(work / "build"),
                    "--output", str(work / "out.iso"),
                    "--allow-modded",
                ]
            )

            self.assertEqual(code, 0)

    def test_check_rejects_other_region_even_if_hash_check_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            original_iso = work / "pal-game.iso"
            make_iso(original_iso, {"SYSTEM.CNF": b"BOOT2 = cdrom0:\\SLES_529.27;1\r\n", "SLES_529.27": b"fake-elf"})

            with contextlib.redirect_stdout(io.StringIO()):
                code = build.main(
                    [
                        "check",
                        "--config", str(ROOT / "config.ini"),
                        "--iso", str(original_iso),
                        "--project-dir", str(ROOT / "src"),
                        "--build-dir", str(work / "build"),
                        "--output", str(work / "out.iso"),
                        "--allow-modded",
                    ]
                )

            self.assertEqual(code, 1)
            self.assertFalse((work / "build").exists())

    def test_wizard_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            original_iso, project = make_fixture(work)
            output = work / "wizard.iso"

            answers = [
                str(original_iso),  # ISO path
                str(output),        # output ISO
                "n",                # do not verify the checksum
                "n",                # do not skip the radio streams
                "y",                # start the build
                "n",                # do not open the output folder
            ]

            with mock.patch("builtins.input", side_effect=answers), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = build.main(
                    [
                        "wizard",
                        "--config", str(ROOT / "config.ini"),
                        "--project-dir", str(project),
                        "--build-dir", str(work / "build"),
                    ]
                )

            self.assertEqual(code, 0)
            self.assertTrue(output.is_file())

    def test_unknown_stage_fails(self) -> None:
        code = build.main(["all", "--only", "nope"])
        self.assertEqual(code, 1)


class IsoPathTest(unittest.TestCase):
    def test_valid_names(self) -> None:
        self.assertEqual(buildiso.iso_path(Path("MODELS/GTA3.IMG"), is_file=True),
                         "/MODELS/GTA3.IMG;1")
        self.assertEqual(buildiso.iso_path(Path("MOVIES"), is_file=False), "/MOVIES")

    def test_invalid_names(self) -> None:
        for name in ("DATA/" + "A" * 32, "DATA/BAD-NAME.CFG", "DATA/NAME.BAD-NAME"):
            with self.assertRaises(buildiso.BuildError):
                buildiso.iso_path(Path(name), is_file=True)

    def test_level_two_names(self) -> None:
        self.assertEqual(
            buildiso.iso_path(Path("DATA/SCRIPT/OTHER_SCRIPTS.SC"), is_file=True),
            "/DATA/SCRIPT/OTHER_SCRIPTS.SC;1",
        )


class OverlayInstallTest(unittest.TestCase):
    def test_pal_profile_removes_executable_specific_patches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "src"
            build_dir = root / "build"

            for name in ("intro", "text", "data", "models", "anim"):
                (project / name).mkdir(parents=True)
            for name in ("CONFIG", "SFX"):
                (project / "audio" / name).mkdir(parents=True)
            overlays = project / "overlays"
            plugins = project / "plugins"
            overlays.mkdir()
            plugins.mkdir()
            for name in ("INIT.NM", "FILELOAD.NM", "relocator.nm"):
                (overlays / name).write_bytes(b"NTSC patch")
                (build_dir / name).parent.mkdir(parents=True, exist_ok=True)
                (build_dir / name).write_bytes(b"stale patch")
            for name in ("cleo.dep", "plugins.ini"):
                (plugins / name).write_bytes(b"NTSC plugin")
                (build_dir / "plugins" / name).parent.mkdir(parents=True, exist_ok=True)
                (build_dir / "plugins" / name).write_bytes(b"stale plugin")

            buildiso.install_project_files(project, build_dir, include_console_patches=False)

            self.assertFalse((build_dir / "INIT.NM").exists())
            self.assertFalse((build_dir / "FILELOAD.NM").exists())
            self.assertFalse((build_dir / "relocator.nm").exists())
            self.assertFalse((build_dir / "plugins" / "cleo.dep").exists())
            self.assertFalse((build_dir / "plugins" / "plugins.ini").exists())


if __name__ == "__main__":
    unittest.main()
