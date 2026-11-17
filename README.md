# GTA V Legacy (PS2)

A build tool and asset pack that brings **GTA V content into GTA San Andreas on the PlayStation 2**. Instead of writing a new engine, it takes an existing **GTA San Andreas (NTSC-U, v1.03) ISO**, unpacks it, overlays it with assets converted from GTA V, and repacks it into a new ISO.

Everything runs in **pure Python** – no UltraISO, no Windows-only helper tools. The build works on Windows, Linux and macOS.

The result is a playable ISO for real PS2 hardware (e.g. via FreeMcBoot/OPL) or emulators such as PCSX2.

> **Status:** "Closed Alpha" – a hobby/fan project in active, unfinished development. Expect missing assets, placeholders and crashes.
>
> **This repository continues the legacy of [GTAVLegacy by Daniel Santos](https://github.com/DanielSant0s/GTAVLegacy).** See [Project lineage](#project-lineage).

*German version: [README.de.md](README.de.md)*

---

## Contents

- [Project lineage](#project-lineage)
- [What this project does](#what-this-project-does)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Command line](#command-line)
- [config.ini](#configini)
- [How the build works](#how-the-build-works)
- [Project layout](#project-layout)
- [Adding assets](#adding-assets)
- [Audio / radio streams](#audio--radio-streams)
- [Known pitfalls](#known-pitfalls)
- [Continuing the project](#continuing-the-project)
- [Publishing this fork](#publishing-this-fork)
- [Development notes](#development-notes)
- [Legal](#legal)
- [Credits](#credits)

---

## Project lineage

This project did not start from scratch. It is a **continuation (legacy fork)** of the original GTA V Legacy project:

| | |
|---|---|
| **Original project** | [DanielSant0s/GTAVLegacy](https://github.com/DanielSant0s/GTAVLegacy) |
| **Original author** | Daniel Santos ([@DanielSant0s](https://github.com/DanielSant0s)) |
| **Original work** | Build system, asset conversions, PS2 overlays and plugins, `SLUS_209.46` toolchain |
| **This continuation** | [baummarder/GTAVLegacyRW](https://github.com/baummarder/GTAVLegacyRW) – documentation, pure-Python build, tests, maintenance |
| **Maintainer** | [@baummarder](https://github.com/baummarder) |
| **License** | MIT for the code (see `LICENSE`, © 2023 Daniel Santos) |

The 15 original commits (2023–2024) are preserved unchanged and remain authored by Daniel Santos. All changes made in this continuation are additional commits on top, and every commit made here credits the AI assistance used for it via `Co-authored-by` trailers.

If you build on this project, please keep the lineage visible and credit the original author.

---

## What this project does

`buildiso.py` is the heart of the project. It:

1. verifies that the original ISO is present and unmodified (MD5/SHA1),
2. extracts the ISO into `build/`,
3. copies the project's own files from `src/` over the extracted ISO,
4. unpacks the split `STREAMS.7z.*` archives (GTA V radio stations as PS2 audio streams),
5. merges the converted assets into `gta3.img` and `gta_int.img` with a built-in IMG writer,
6. builds the final ISO with `pycdlib`.

The repo also ships PS2 binary patches (`src/overlays/*.NM`, `src/plugins/*.dep`) that extend the game at console level (CLEO support and custom opcodes, among other things).

Asset categories included:

| Category | Examples |
|---|---|
| Vehicles | Annis Remus, Declasse Impaler/Vigero, Pfister Comet, HVY Nightshark, Imponte Ruiner 2000, Blimp |
| Weapons | AK47, M4, MP5, RPG, Desert Eagle, knife, shovel |
| Peds | Alien, Barry, Chopper, Cop |
| Map / interiors | Billboards, Munation interiors, vending machines, underwater |
| Vegetation | Palms, grass |
| HUD / UI | `VLHUD.TXD`, `VHUD.TXD`, `VPHONE*.TXD`, radar tiles |
| Audio | GTA V radio stations as PS2 streams (`src/audio/STREAMS`) |

---

## Requirements

| Needed | Details |
|---|---|
| **Python 3.9+** | Tested with Python 3.14 on Windows. Invoke it as `python` (or `python3` on Linux/macOS). |
| **Python packages** | `pip install -r requirements.txt` (installs `pycdlib` and `py7zr`) |
| **Original ISO** | *Grand Theft Auto - San Andreas (USA) (v1.03)* – NTSC-U. Other versions will not work without adapting the `data/` files. |
| **Free disk space** | Several GB – the ISO is extracted, the new ISO is written next to it, and audio archives are unpacked temporarily. |
| **Operating system** | Windows, Linux or macOS. No external tools required. |

### ISO checksums

By default the build only accepts this ISO:

```
MD5:  c383c015065f8060343032480928d08d
SHA1: 66cb01a8281cc132e023a1e52afc75d1fad3fbe1
```

If you have a different (already modded) version, pass `--allow-modded` or set `allow_modded = True` in `config.ini`. That skips the checksum verification – at your own risk.

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Put the original ISO into the project folder
#    The filename must match config.ini, e.g.:
#    "Grand Theft Auto - San Andreas (USA) (v1.03).iso"

# 3. Check config.ini (see below)

# 4. Build
python buildiso.py
```

On Windows the PowerShell wrapper forwards all arguments:

```powershell
.\build.ps1 --output "GTA V Legacy.iso" -v
```

The finished image is named according to `config.ini` (default `GTA V Legacy Closed Alpha.iso`). Test it in **PCSX2** or on a PS2 (OPL/FreeMcBoot).

---

## Command line

Every option overrides the matching `config.ini` value.

| Option | Description |
|---|---|
| `--iso PATH` | Input ISO. |
| `--output PATH` | Output ISO. |
| `--config PATH` | Config file to read (default `config.ini`). |
| `--project-dir PATH` | Mod source folder (default `./src`). |
| `--build-dir PATH` | Working folder for the extracted ISO (default `./build`). |
| `--allow-modded` | Skip the ISO checksum verification. |
| `--reuse-build` | Reuse an existing extraction instead of extracting again. |
| `--clean` | Force a clean build (remove the build folder). Default unless `--reuse-build` is given. |
| `-v`, `--verbose` | Debug logging, including every file that is added. |
| `-h`, `--help` | Show all options. |

The script exits with `0` on success and `1` on a build error (with a readable message instead of a traceback).

---

## config.ini

```ini
[DEFAULT]
iso_name = Grand Theft Auto - San Andreas (USA) (v1.03).iso
output = GTA V Legacy Closed Alpha.iso
project_path = ./src
build_path = ./build
allow_modded = False
reuse_build = False
```

| Key | Meaning |
|---|---|
| `iso_name` | Path/name of the original ISO (relative to the project folder). |
| `output` | Name of the finished ISO. Overwritten on every build. |
| `project_path` | Source folder with the mod files. |
| `build_path` | Working folder for the extracted ISO. **Removed on every build** unless `reuse_build`/`--reuse-build` is set. |
| `allow_modded` | `True` = skip the ISO checksum verification. |
| `reuse_build` | `True` = keep and reuse an existing `build/` extraction (faster, but stale files can leak into the ISO). |

The script no longer rewrites `config.ini`; the old `[SAVED_CONFIG]` section is gone. The former `uiso_path` and `imgconsole_path` keys are obsolete because no external tools are used any more.

---

## How the build works

`buildiso.py` runs these steps in order:

1. **Check the input ISO** – existence plus optional MD5/SHA1. This happens *before* anything is deleted, so a typo cannot wipe an existing extraction.
2. **Prepare the build folder** – `build/` is removed (unless reusing) and recreated.
3. **Extract the ISO** – recursively into `build/` via `pycdlib`.
4. **Copy mod files** – `intro/`, `text/`, `data/`, `models/`, `audio/CONFIG`, `audio/SFX`, `anim/`, `plugins/`, plus the contents of `overlays/`. Stale files that must not ship (`models/gta3_1.img`, `movies/`) are removed.
5. **Unpack audio streams** – all `STREAMS.7z.*` parts in `src/audio/STREAMS/` are joined into `result.7z`, extracted, and the archive is deleted.
6. **Rebuild the IMG archives** – every file under `src/assets/` is merged into `gta3.img` / `gta_int.img` by `imgtool.py`: entries that already exist are replaced, new ones are appended. The archives are rewritten sector by sector, so they never have to fit into memory.
7. **Write the ISO** – `pycdlib` creates a fresh ISO9660 level 1 image from `build/`.
8. **Verify the output** – the resulting ISO must exist and be non-empty.

Expected output (roughly):

```
GTA V Legacy builder v0.3
      Project: src
      Build:   build
[1/8] Checking input ISO ...
      ISO: Grand Theft Auto - San Andreas (USA) (v1.03).iso
[2/8] Preparing build folder ...
[3/8] Extracting ISO ...
[4/8] Copying mod files ...
[5/8] Unpacking audio streams ...
[6/8] Rebuilding IMG archives ...
      gta3.img: 10632 entries (412 replaced, 96 added, 1.1 GiB)
      gta_int.img: 1221 entries (18 replaced, 0 added, 98.0 MiB)
[7/8] Writing ISO ...
      Packaging 78 files ...
[8/8] Verifying output ...
      GTA V Legacy Closed Alpha.iso (4.2 GiB)

Done.
```

Notes on the formats used by the Python implementation:

- IMG archives are **VER2** (GTA San Andreas). Entries are limited to 65535 sectors (~128 MiB) and 23 characters per name, exactly like the original tools. Violations abort the build with a clear message.
- The ISO is written as plain **ISO9660 level 1**: names must be 8.3, uppercase, `A-Z 0-9 _`. The original game files already satisfy this; unusual new filenames abort the build with the offending path.
- The ISO is rebuilt from the file contents, not by patching the original image byte by byte. The directory order may therefore differ from the retail disc.

---

## Project layout

```
GTAVLegacy/
├─ buildiso.py               # Build script (entry point, CLI)
├─ imgtool.py                # IMG (VER2) reader/writer, pure Python
├─ build.ps1                 # PowerShell wrapper, forwards arguments
├─ config.ini                # Paths & options
├─ requirements.txt          # pycdlib, py7zr
├─ tests/test_smoke.py       # end-to-end test with a fake ISO
├─ .githooks/                # prepare-commit-msg hook (co-author trailers)
├─ IMGconsole_32-bit/        # legacy: fastman92 IMG Console, no longer used
├─ src/                      # All mod content
│  ├─ anim/                  # IFP animations (ped.ifp, gangs.ifp)
│  ├─ assets/                # Source files that go into the IMGs
│  │  ├─ Anims/  Map/  Peds/  Radar/  Vegetation/
│  │  ├─ Vehicles/  Weapons/  Interiors/
│  │  ├─ Cars to convert/    # GTA V models not converted yet
│  │  ├─ Maps to convert/  Objects to convert/  Wrecked cars/
│  │  └─ build.txt           # legacy IMG Console script, no longer used
│  ├─ audio/                 # CONFIG/, SFX/ and STREAMS/ (7z parts)
│  ├─ data/                  # GTA SA data tables (handling, ide, ipl ...)
│  ├─ intro/                 # RGM intro videos
│  ├─ models/                # IMGs, TXDs, effects, HUD
│  ├─ overlays/              # PS2 overlays: INIT.NM, FILELOAD.NM, relocator.nm
│  ├─ plugins/               # CLEO/opcode patches (.dep) + plugins.ini
│  ├─ text/                  # AMERICAN.GXT/INI
│  └─ STREAM.INI
├─ plugins/                  # Working folder/placeholder for plugin subfolders
├─ SLUS_209.46               # PS2 executable of GTA San Andreas (NTSC-U)
├─ Wav 2 GTA V Legacy PS2.exe # Tool to convert WAVs into PS2 streams
└─ *.png / *.dds             # HUD, radar and shop UI graphics
```

Important: `build/` and the temporary `IMGconsole_32-bit/gta3*` folders are **artifacts**, not sources (and git-ignored). Changes always belong in `src/`.

---

## Adding assets

### Vehicles, weapons, peds, map objects

1. Create a new folder under the matching category, e.g.:
   ```
   src/assets/Vehicles/Cars/MyCar/my_car.dff
   src/assets/Vehicles/Cars/MyCar/my_car.txd
   ```
2. The build merges the whole folder recursively into `gta3.img`. Files ending in `.txt`, `.cfg`, `.ide`, `.dat` are **ignored** – handy for notes.
3. Add entries to `src/data/VEHICLES.IDE`, `HANDLING.CFG`, `CARCOLS.DAT`, `CARMODS.DAT` etc., otherwise the model is unusable in-game.
4. Texture/model names must match the IDE file.

### Peds and map

Same principle: folders under `src/assets/Peds/` or `src/assets/Map/`, plus matching entries in `PEDS.IDE`, `DEFAULT.IDE` and the IPL files under `src/data/MAPS/`.

### Interiors

Everything under `src/assets/Interiors/` ends up in `gta_int.img`.

### HUD / textures

Put TXDs (e.g. `VLHUD.TXD`) into `src/models/` or `src/models/txd/`. The PNG/DDS files in the repo root are intermediate results or sources for the TXDs.

---

## Audio / radio streams

The GTA V radio stations are stored as a multi-part 7z archive:

```
src/audio/STREAMS/STREAMS.7z.001 … STREAMS.7z.085
```

The build detects the parts automatically and joins them in numeric order:

```python
parts = collect_stream_parts(project / "audio" / "STREAMS")
```

You can add or remove parts freely – there is no `range()` constant to maintain. If the numbering has gaps, the build warns instead of silently producing broken audio.

To create your own streams, `Wav 2 GTA V Legacy PS2.exe` is included in the repo root (Windows). Convert WAV files with it and place the result in `src/audio/STREAMS/`.

If the folder is missing entirely, the build warns and continues without custom audio.

---

## Known pitfalls

| Problem | Cause / fix |
|---|---|
| Checksum error | Wrong ISO version. Only NTSC-U v1.03 has the expected hashes; otherwise use `--allow-modded`. |
| `gta3.img` not found | The ISO extraction is incomplete – delete `build/` and rebuild. |
| Stale assets in the ISO | `reuse_build = True` or `--reuse-build` was used. Run with `--clean`. |
| `... cannot be stored in a plain ISO9660 image` | A file in `build/` is not 8.3/uppercase. Rename it in `src/`. |
| `Entry name ... is N characters long` | IMG entry names are limited to 23 characters. |
| `needs N sectors, the format only allows 65535` | A single file is larger than ~128 MiB and cannot be stored in a VER2 archive. |
| Huge memory usage | The 7z parts are joined as one `result.7z` inside `build/`; use a machine with enough free disk space. |
| No audio in-game | The `STREAMS.7z.*` parts are incomplete or numbers have gaps (see the warning). |
| Crash on load | Usually missing IDE/IPL/handling entries for newly added assets. |
| Missing Python package | `pip install -r requirements.txt`. |

Fixed in this continuation compared to the original script:

- Runs on Windows, Linux and macOS: UltraISO and fastman92 IMG Console are replaced by pure Python (`pycdlib` + `imgtool.py`).
- `build.ps1` no longer calls the non-existent `python3` on Windows.
- `result.7z` is written fresh (`wb`) instead of appended (`ab`), so rebuilds cannot corrupt it.
- Failures are reported as readable errors with exit code `1` instead of tracebacks.
- The ISO is validated *before* the build folder is deleted.
- The number of audio parts is detected instead of hardcoded.
- Every option can be overridden from the command line.
- There is an end-to-end smoke test that builds a complete (tiny) ISO.

Remaining technical debt:

- No asset validation (missing TXD/IDE references are not detected).
- The generated ISO uses a fresh layout instead of preserving the retail disc order.
- Only `gta3.img` and `gta_int.img` are rebuilt; `player.img` is untouched.

---

## Continuing the project

Roadmap for the next steps:

1. **Take stock** – Which assets are fully converted, which still sit under `* to convert/`? Collect TODOs from `src/assets/*/build.txt` and the `.txt` notes.
2. **Document the asset pipeline** – Which tools (Blender, ZModeler, Magic.TXD, …) and which conversion steps take you from GTA V to PS2-compatible DFF/TXD? That is the biggest knowledge loss in this repo.
3. **Validation** – Before writing the ISO, check that every DFF has a matching TXD and an IDE entry; print warnings for missing references.
4. **Compatibility check on hardware** – Verify a release build in PCSX2 and on a real PS2 (OPL/FreeMcBoot), including audio streaming.
5. **Release process** – Versioning, changelog, publish the hash of the generated ISO.
6. **Cleanup** – Remove the legacy `IMGconsole_32-bit/` tools and `src/assets/build.txt` once the Python build has proven itself.

When developing further, remember: **`src/` is the source of truth.** Anything that only exists in `build/` or `IMGconsole_32-bit/` is disposable.

---

## Publishing this fork

`origin` points to the continuation repository, `upstream` to the original project:

```bash
git remote -v
# origin   https://github.com/baummarder/GTAVLegacyRW.git
# upstream https://github.com/DanielSant0s/GTAVLegacy.git

git push -u origin main
```

In the GitHub repository settings, use a description like:

> Continuation of GTA V Legacy (PS2) by Daniel Santos – GTA V content for GTA San Andreas on PlayStation 2.

Do **not** publish ISO files or any game assets you are not allowed to redistribute.

---

## Development notes

### Tests

```bash
python -m unittest discover -s tests -v
```

The smoke test creates a miniature ISO with the same structure, runs the full build and checks the resulting archives and image. It needs no game data.

### AI co-authors

This continuation is developed with AI assistance. A `prepare-commit-msg` hook in `.githooks/` appends the co-author trailers to every commit:

```
Co-authored-by: opencode-agent[bot] <opencode-agent[bot]@users.noreply.github.com>
Co-authored-by: DeepSeek <service@deepseek.com>
```

Activate it once per clone:

```bash
git config core.hooksPath .githooks
```

The hook skips merge/squash/fixup commits and never adds the trailers twice.

### Working on the build script

```bash
python buildiso.py --help          # no ISO or dependencies required
python buildiso.py -v              # full build with debug output
python buildiso.py --reuse-build   # skip re-extracting an existing build/
```

---

## Legal

- The code in this repo is licensed under the **MIT License** (see `LICENSE`, © 2023 Daniel Santos, © 2026 Baummarder).
- **GTA San Andreas** and **GTA V**, along with all assets, are property of **Rockstar Games / Take-Two Interactive**.
- This repo contains **no** complete game and must not be redistributed as one. You need a legally acquired copy of GTA San Andreas (PS2).
- This is an unofficial fan project and is not affiliated with Rockstar Games.

---

## Credits

- **Daniel Santos** ([@DanielSant0s](https://github.com/DanielSant0s)) – original GTAVLegacy project, build script, asset conversion, PS2 overlays
- **@baummarder** – maintainer of this continuation
- **fastman92** – IMG Console (used by the original build, now replaced by `imgtool.py`)
- **UltraISO** – ISO creation (used by the original build, now replaced by `pycdlib`)
- **pycdlib**, **py7zr** – Python libraries for ISO and 7z handling
- **opencode-agent[bot]** and **DeepSeek** – documentation, build tooling and maintenance of this continuation
