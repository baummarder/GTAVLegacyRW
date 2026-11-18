# GTA V Legacy

**Los Santos. San Andreas. PlayStation 2.**

An unofficial conversion project bringing selected **GTA V vehicles, weapons, audio and visual assets** to **GTA San Andreas for PlayStation 2**. A cross-platform Python tool applies the project files to a compatible game ISO and creates a new image.

Build on **Windows, Linux or macOS** with Python. UltraISO and the original Windows-only tools are not required.

The output is intended for emulators such as PCSX2 and PS2 hardware using OPL/FreeMcBoot. Compatibility and gameplay are not guaranteed.

> **🧪 CLOSED ALPHA** · An early, limited test phase—not a finished release. Features and assets may be incomplete, and crashes are possible.
>
> **This repository continues the legacy of [GTAVLegacy by Daniel Santos](https://github.com/DanielSant0s/GTAVLegacy).** See [Project lineage](#project-lineage).

**A personal note:** This project is currently at the bottom of my active to-do list. Other priorities come first for now.

[Build your ISO](#quick-start) · [Requirements](#requirements) · [CLI reference](#command-line) · [Project lineage](#project-lineage) · [Deutsch](README.de.md)

---

<details>
<summary>📚 Contents</summary>

- [Project lineage](#project-lineage)
- [What this project does](#what-this-project-does)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Command line](#command-line)
- [config.ini](#configini)
- [How the build works](#how-the-build-works)
- [Project layout](#project-layout)
- [Language and naming](#language-and-naming)
- [Adding assets](#adding-assets)
- [Audio / radio streams](#audio--radio-streams)
- [Known pitfalls](#known-pitfalls)
- [Continuing the project](#continuing-the-project)
- [Publishing this fork](#publishing-this-fork)
- [Development notes](#development-notes)
- [Legal](#legal)
- [Credits](#credits)

</details>

---

## 🧬 Project lineage

This project did not start from scratch. It is a **continuation (legacy fork)** of the original GTA V Legacy project:

| | |
|---|---|
| **Original project** | [DanielSant0s/GTAVLegacy](https://github.com/DanielSant0s/GTAVLegacy) |
| **Original author** | Daniel Santos ([@DanielSant0s](https://github.com/DanielSant0s)) |
| **Original work** | Build system, asset conversions, PS2 overlays and plugins, `SLUS_209.46` toolchain |
| **This continuation** | [baummarder/GTAVLegacyRW](https://github.com/baummarder/GTAVLegacyRW) – documentation, pure-Python build, tests, maintenance |
| **Maintainer** | [@baummarder](https://github.com/baummarder) |
| **License** | MIT for the code (see `LICENSE`, © 2023 Daniel Santos) |

The 15 original commits (2023–2024) are preserved unchanged and remain authored by Daniel Santos. Changes made in this continuation are additional commits on top. AI co-authors are credited per commit when applicable.

If you build on this project, please keep the lineage visible and credit the original author.

---

## 🎮 What this project does

`build.py` is the central build tool. One command runs every stage from `buildiso.py`:

1. verifies that the original ISO is present and unmodified (MD5/SHA1),
2. extracts the ISO into `build/`,
3. copies the project's own files from `src/` over the extracted ISO,
4. unpacks the split `STREAMS.7z.*` archives (GTA V radio stations as PS2 audio streams),
5. merges the converted assets into `gta3.img` and `gta_int.img` with a built-in IMG writer,
6. packages the final image with the bundled `mkps2iso` PS2 DVD tools,
7. reopens the finished ISO and verifies the important entries.

The repo also ships PS2 binary patches (`src/overlays/*.NM`, `src/plugins/*.dep`) that extend the game at console level (CLEO support and custom opcodes, among other things).

### Compatibility at a glance

| Area | Status | Notes |
|---|---|---|
| Build pipeline | ✅ Implemented | Creates an ISO and checks its required files. |
| NTSC-U v1.03 input | ✅ Accepted | The current build and patches target this release. |
| PAL (`SLES_529.27`) | ⛔ Temporarily disabled | The PS2 startup screen appears, but the game does not continue. PAL investigation is isolated under `experimental/pal/`. |
| Other regions/revisions | ⚪ Not supported | Use the supported US NTSC-U v1.03 release. |
| In-game compatibility | ⚪ Not verified | A successful ISO build does not confirm that gameplay works on PCSX2 or PS2 hardware. |

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

### 📸 Screenshots

There are no verified gameplay screenshots of the current build in the repository yet. Genuine captures will be added after the build has been checked in-game; no mockups are used as screenshots.

---

## 🧰 Requirements

| Needed | Details |
|---|---|
| **Python 3.9+** | Tested with Python 3.14 on Windows. Invoke it as `python` (or `python3` on Linux/macOS). |
| **Python packages** | `pip install -r requirements.txt` (installs `pycdlib` and `py7zr`) |
| **PS2 DVD writer** | Bundled `mkps2iso` 1.1.1 tools for Windows, Linux and macOS |
| **Original ISO** | US NTSC-U v1.03 (`SLUS_209.46`) only. PAL and other revisions are temporarily unsupported. |
| **Free disk space** | Several GB – the ISO is extracted, the new ISO is written next to it, and audio archives are unpacked temporarily. |
| **Operating system** | Windows, Linux or macOS. No external tools required. |

### 🔐 ISO checksums

The US NTSC-U v1.03 profile is checked against this reference image:

```
MD5:  c383c015065f8060343032480928d08d
SHA1: 66cb01a8281cc132e023a1e52afc75d1fad3fbe1
```

The builder identifies the release from `SYSTEM.CNF` and its boot executable. PAL v1.00 is temporarily rejected because it reaches the PS2 startup screen but does not continue, even after the NTSC-specific overlays and plugins were omitted. `--allow-modded` skips checksum verification only; it does not enable PAL builds.

See [experimental PAL notes](experimental/pal/README.md) for the current evidence and what remains to diagnose.

---

## 🚀 Quick start

### 1. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Add your original game ISO

Use a legally obtained **GTA San Andreas (USA, NTSC-U v1.03)** PS2 ISO. The builder checks the release automatically. Put the ISO in the repository folder or pass its path with `--iso`.

The build detects the release before changing the build folder. NTSC-U v1.03 is checked against its MD5/SHA1 reference. PAL and other versions are rejected before the build folder is touched.

### 3. Check the setup and build

```bash
python build.py check
python build.py
```

In a terminal, `python build.py` opens the interactive wizard. It asks for the ISO and output path, shows the selected options, then starts the build after you confirm. You can drag the ISO file into the terminal when it asks for its path.

To build without prompts, pass the ISO path directly:

```bash
python build.py --iso "D:/Games/Grand Theft Auto - San Andreas.iso" --output "D:/Games/GTA V Legacy.iso"
```

On Windows, the PowerShell wrapper is also available:

```powershell
.\build.ps1 --iso "D:\Games\Grand Theft Auto - San Andreas.iso" --output "D:\Games\GTA V Legacy.iso"
```

The output file is overwritten if it already exists. A normal build also recreates the working `build/` folder; use `--reuse-build` only when you intentionally want to reuse its extracted files.

### Useful first commands

```bash
python build.py --help       # show all commands and options
python build.py deps         # check required Python packages
python build.py info         # show resolved paths and stream/package status
python build.py stages       # list the build stages
python build.py --dry-run    # preview the stage plan; does not validate the ISO
```

The finished image uses the output path from `config.ini` unless you pass `--output`. Try it in **PCSX2** or on a PS2 with OPL/FreeMcBoot.

---

## 🖥️ Command line

### Commands

| Command | Description |
|---|---|
| `all` (default) | Interactive wizard in a terminal, or direct build with `--iso` / `--non-interactive`. |
| `iso` | Same as `all`. |
| `wizard` | Run the interactive build wizard explicitly. |
| `check` | Only run preflight (packages, paths, free space, region and checksum checks). |
| `deps` | Show missing Python packages. With `--install-deps` they are installed via pip. |
| `stages` | List all stages with their keys. |
| `info` | Show the resolved paths, stream parts and package status. |
| `clean` | Remove the build folder and the output ISO. |

### Stages

| Key | What it does |
|---|---|
| `preflight` | Validate config, Python packages, free space, ISO region and checksum policy. |
| `prepare` | Create a clean build folder (or keep an existing one). |
| `extract` | Unpack the original ISO into the build folder. |
| `overlay` | Overlay `src/` onto the extracted ISO. |
| `audio` | Join and extract the `STREAMS.7z.*` parts. |
| `images` | Merge the assets into `gta3.img` and `gta_int.img`. |
| `package` | Package the build folder as an ISO9660 level 2 image. |
| `verify` | Reopen the finished ISO and check its contents. |

### Options

Every option overrides the matching `config.ini` value.

| Option | Description |
|---|---|
| `--iso PATH` | Input ISO. |
| `--output PATH` | Output ISO. |
| `--config PATH` | Config file to read (default `config.ini`). |
| `--project-dir PATH` | Mod source folder (default `./src`). |
| `--build-dir PATH` | Working folder for the extracted ISO (default `./build`). |
| `--only STAGE[,STAGE...]` | Run only these stages. |
| `--skip STAGE[,STAGE...]` | Skip these stages. |
| `--allow-modded` | Skip the ISO checksum verification. |
| `--reuse-build` | Reuse an existing extraction instead of extracting again. |
| `--clean` | Force a clean build (remove the build folder). Default unless `--reuse-build` is given. |
| `--install-deps` | Install the Python packages from `requirements.txt` before running. |
| `--dry-run` | Show the plan without changing anything. |
| `--non-interactive` | Never start the interactive wizard; use config.ini and CLI options only. |
| `-v`, `--verbose` | Debug logging, including every file that is added. |
| `-h`, `--help` | Show all options. |

Examples:

```bash
python build.py                              # interactive wizard
python build.py wizard                       # same, explicitly
python build.py --non-interactive            # direct build using config.ini, no prompts
python build.py --iso "path/to/game.iso"     # direct build with a specific ISO
python build.py --only preflight,prepare,extract   # stop after extracting
python build.py --skip audio                       # build without radio streams
python build.py --dry-run                          # show the plan only
```

`python buildiso.py` still works for compatibility and runs every stage; `python build.py` is the recommended entry point.

The tool exits with `0` on success and `1` on a build error (with a readable message instead of a traceback).

---

## ⚙️ config.ini

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
| `iso_name` | Path/name of the original ISO (relative to the current working directory; normally run from the repository folder). |
| `output` | Name of the finished ISO. Overwritten on every build. |
| `project_path` | Source folder with the mod files. |
| `build_path` | Working folder for the extracted ISO. **Removed on every build** unless `reuse_build`/`--reuse-build` is set. |
| `allow_modded` | `True` = skip the ISO checksum verification. |
| `reuse_build` | `True` = keep and reuse an existing `build/` extraction (faster, but stale files can leak into the ISO). |

The script no longer rewrites `config.ini`; the old `[SAVED_CONFIG]` section is gone. The former `uiso_path` and `imgconsole_path` keys are obsolete because no external tools are used any more.

---

## 🔧 How the build works

`build.py` runs the stages from `buildiso.py` in this order (use `--only`/`--skip` to change that):

1. **Preflight** – project folder, Python packages, free space and the input ISO (existence plus optional MD5/SHA1). This happens *before* anything is deleted, so a typo cannot wipe an existing extraction.
2. **Prepare the build folder** – `build/` is removed (unless reusing) and recreated.
3. **Extract the ISO** – recursively into `build/` via `pycdlib`.
4. **Copy mod files** – `intro/`, `text/`, `data/`, `models/`, `audio/CONFIG`, `audio/SFX`, `anim/`, `plugins/`, plus the contents of `overlays/`. The GTA V intro clips replace San Andreas's `MOVIES/VCNTSC.PSS` and `MOVIES/OPEN1.PSS`; only the split archive `models/gta3_1.img` is removed.
5. **Unpack audio streams** – all `STREAMS.7z.*` parts in `src/audio/STREAMS/` are joined into `result.7z`, extracted, and the archive is deleted.
6. **Rebuild the IMG archives** – every file under `src/assets/` is merged into `gta3.img` / `gta_int.img` by `imgtool.py`: entries that already exist are replaced, new ones are appended. The archives are rewritten sector by sector, so they never have to fit into memory.
7. **Write the ISO** – the bundled `mkps2iso` tools create a PS2 DVD image with its UDF filesystem, ISO9660 bridge, boot identifiers and region-matched boot logo. The Type-L and Type-M path tables are checked at sectors 257 and 259.
8. **Verify the output** – the ISO is reopened and must contain `SYSTEM.CNF`, the detected region's executable, `MODELS/GTA3.IMG` and `MODELS/GTA_INT.IMG`; the file and folder counts are printed.

Expected output (roughly):

```
GTA V Legacy builder v0.4
      Project: src
      Build:   build
      Output:  GTA V Legacy Closed Alpha.iso

[1/8] Checking configuration and input ISO ...
      ISO: Grand Theft Auto - San Andreas (USA) (v1.03).iso
      Free space (build folder): 120.4 GiB
      done in 3.1 s
[2/8] Preparing build folder ...
      done in 8 ms
[3/8] Extracting ISO ...
      done in 42.6 s
[4/8] Copying mod files ...
      done in 2.4 s
[5/8] Unpacking audio streams ...
      done in 55.1 s
[6/8] Rebuilding IMG archives ...
      gta3.img: 10632 entries (412 replaced, 96 added, 1.1 GiB)
      gta_int.img: 1221 entries (18 replaced, 0 added, 98.0 MiB)
      done in 1 min 12 s
[7/8] Writing ISO ...
      Packaging 78 files ...
      done in 2 min 3 s
[8/8] Verifying output ...
      GTA V Legacy Closed Alpha.iso (4.2 GiB)
      78 files, 24 folders
      done in 1.2 s

Done. 8 stage(s) in 5 min 14 s.
```

Notes on the formats used by the Python implementation:

- IMG archives are **VER2** (GTA San Andreas). Entries are limited to 65535 sectors (~128 MiB) and 23 characters per name, exactly like the original tools. Violations abort the build with a clear message.
- The final image is written by `mkps2iso` 1.1.1, which creates the PS2 DVD UDF structures and ISO9660 bridge. The build checks the UDF volume sequence and anchor, the `PLAYSTATION` system identifier, and path tables at sectors 257 and 259. The third-party tool and its license are in `tools/mkps2iso/`. Raw PNG/PSD editor artwork and IDE metadata are left out of the game image.
- The ISO is rebuilt from the file contents, not by patching the original image byte by byte. The directory order may therefore differ from the retail disc.

---

## 🗂️ Project layout

```
GTAVLegacy/
├─ build.py                  # Central build tool (entry point, CLI)
├─ buildiso.py               # Build stages: preflight … verify (also usable directly)
├─ imgtool.py                # IMG (VER2) reader/writer, pure Python
├─ build.ps1                 # PowerShell wrapper, forwards arguments to build.py
├─ config.ini                # Paths & options
├─ requirements.txt          # pycdlib, py7zr
├─ tools/mkps2iso/           # bundled PS2 DVD image tools and license
├─ tests/test_smoke.py       # end-to-end test with a fake ISO
├─ .githooks/                # optional prepare-commit-msg co-author hook
├─ IMGconsole_32-bit/        # legacy: fastman92 IMG Console, no longer used
├─ music-installer/          # legacy: GTA SA music and audio installer tools
├─ legalize/                 # normalised GTA V audio (cutscenes, voices, music)
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
│  ├─ intro/                 # GTA V boot/logo and loading clips (RGM)
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

## 📝 Language and naming

The repository is English-first so that it can be worked on internationally:

| Rule | Reason |
|---|---|
| Folders, file names, code, comments and documentation are English. | Keeps the build and the workflow understandable for everyone. |
| [`README.de.md`](README.de.md) is the only German file. | It is an explicit translation, not the primary documentation. |
| Game data keeps its original names (`HANDLING.CFG`, `VEHICLES.IDE`, `GTA3.IMG`, …). | The engine looks these up by name; renaming them breaks the game. |
| Converted models and textures keep their asset names (`stretch.dff`, `comet.txd`, …). | IDE files and scripts reference them by name. |
| PS2 DVD layout / filenames | Created by bundled `mkps2iso`; ISO9660 Level 2 names are limited to 31 characters. |

Non-English legacy folders have been translated: `Instalador de Musicas` → `music-installer`, `legalize/legalize/falas` → `voices`, `legalize/legalize/musicas` → `music`, and the Russian folders under `src/assets/Cars to convert/` are English now as well. The non-English readmes shipped with the converted asset packs were translated too.

---

## 🎨 Adding assets

### Vehicles, weapons, peds, map objects

1. Create a new folder under the matching category, e.g.:
   ```
   src/assets/Vehicles/Cars/MyCar/my_car.dff
   src/assets/Vehicles/Cars/MyCar/my_car.txd
   ```
2. The build merges the whole folder recursively into `gta3.img`. Files ending in `.txt`, `.cfg`, `.ide`, `.dat`, plus common OS metadata such as `desktop.ini`, are **ignored** – handy for notes and Windows folders.
3. Add entries to `src/data/VEHICLES.IDE`, `HANDLING.CFG`, `CARCOLS.DAT`, `CARMODS.DAT` etc., otherwise the model is unusable in-game.
4. Texture/model names must match the IDE file.

### Peds and map

Same principle: folders under `src/assets/Peds/` or `src/assets/Map/`, plus matching entries in `PEDS.IDE`, `DEFAULT.IDE` and the IPL files under `src/data/MAPS/`.

### Interiors

Everything under `src/assets/Interiors/` ends up in `gta_int.img`.

### HUD / textures

Put TXDs (e.g. `VLHUD.TXD`) into `src/models/` or `src/models/txd/`. The PNG/DDS files in the repo root are intermediate results or sources for the TXDs.

---

## 🎧 Audio / radio streams

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

`sfx-tool/`, `music-installer/` and `IMGconsole_32-bit/` are legacy Windows-only authoring helpers from the original project. They are **not** needed to build the ISO: `build.py` replaces the IMG Console and uses the prepared audio files from `src/` directly.

If the folder is missing entirely, the build warns and continues without custom audio.

---

## ⚠️ Known pitfalls

| Problem | Cause / fix |
|---|---|
| Checksum or region error | Use US NTSC-U v1.03. `--allow-modded` skips checksum verification only; PAL and unsupported revisions remain rejected. |
| White screen in OPL | Check the actual boot ID in `SYSTEM.CNF`; `PAL Safe Boot Test.iso` is PAL (`SLES_529.27`), not NTSC. Keep GSM and compatibility modes at defaults. For USB/network loading, try the legacy name `SLUS_209.46.Game Name.iso`; OPL documents this as a workaround for some titles. |
| `gta3.img` not found | The ISO extraction is incomplete – delete `build/` and rebuild. |
| Stale assets in the ISO | `reuse_build = True` or `--reuse-build` was used. Run with `--clean`. |
| `... cannot be stored in a plain ISO9660 image` | A name in `build/` is longer than 31 characters or contains unsupported characters. Rename it in `src/`. |
| `Entry name ... is N characters long` | IMG entry names are limited to 23 characters. |
| `needs N sectors, the format only allows 65535` | A single file is larger than ~128 MiB and cannot be stored in a VER2 archive. |
| Huge memory usage | The 7z parts are joined as one `result.7z` inside `build/`; use a machine with enough free disk space. |
| No audio in-game | The `STREAMS.7z.*` parts are incomplete or numbers have gaps (see the warning). |
| Crash on load | Usually missing IDE/IPL/handling entries for newly added assets. |
| Missing Python package | `pip install -r requirements.txt`. |

Fixed in this continuation compared to the original script:

- Runs on Windows, Linux and macOS: image packaging uses bundled `mkps2iso`; IMG archive handling uses `imgtool.py`.
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

## 🧭 Continuing the project

Roadmap for the next steps:

1. **Take stock** – Which assets are fully converted, which still sit under `* to convert/`? Collect TODOs from `src/assets/*/build.txt` and the `.txt` notes.
2. **Document the asset pipeline** – Which tools (Blender, ZModeler, Magic.TXD, …) and which conversion steps take you from GTA V to PS2-compatible DFF/TXD? That is the biggest knowledge loss in this repo.
3. **Validation** – Before writing the ISO, check that every DFF has a matching TXD and an IDE entry; print warnings for missing references.
4. **Compatibility check on hardware** – Verify a release build in PCSX2 and on a real PS2 (OPL/FreeMcBoot), including audio streaming.
5. **Release process** – Versioning, changelog, publish the hash of the generated ISO.
6. **Cleanup** – Remove the legacy `IMGconsole_32-bit/` tools and `src/assets/build.txt` once the Python build has proven itself.

When developing further, remember: **`src/` is the source of truth.** Anything that only exists in `build/` or `IMGconsole_32-bit/` is disposable.

---

## 📤 Publishing this fork

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

## 🧪 Development notes

### Tests

```bash
python -m unittest discover -s tests -v
```

The smoke test creates a miniature ISO with the same structure, runs the full build and checks the resulting archives and image. It needs no game data.

### AI co-authors

The Devin and OpenCode identities are available for commits where they contributed. The `prepare-commit-msg` hook does not add them by default. To opt in for one commit, set `GTAV_ADD_AI_COAUTHORS=1` in that commit's environment:

```
Co-authored-by: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>
Co-authored-by: opencode-agent[bot] <opencode-agent[bot]@users.noreply.github.com>
```

Enable the hook in a clone once:

```bash
git config core.hooksPath .githooks
```

The identities stay out of commits unless you explicitly set `GTAV_ADD_AI_COAUTHORS=1` for a commit or add the trailers yourself. The hook skips merge/squash/fixup commits and does not override existing co-author trailers.

### Working on the build script

```bash
python build.py                 # interactive wizard
python build.py wizard --dry-run  # show the stage plan
python build.py --help            # no ISO or dependencies required
python build.py --dry-run         # show the stage plan
python build.py -v                # full build with debug output
python build.py --skip audio      # build without the radio streams
python build.py --reuse-build     # skip re-extracting an existing build/
python build.py stages            # list the stage keys
```

---

## ⚖️ Legal

- The code in this repo is licensed under the **MIT License** (see `LICENSE`, © 2023 Daniel Santos, © 2026 Baummarder).
- **GTA San Andreas** and **GTA V**, along with all assets, are property of **Rockstar Games / Take-Two Interactive**.
- This repo contains **no** complete game and must not be redistributed as one. You need a legally acquired copy of GTA San Andreas (PS2).
- This is an unofficial fan project and is not affiliated with Rockstar Games.

---

## 🙌 Credits

- **Daniel Santos** ([@DanielSant0s](https://github.com/DanielSant0s)) – original GTAVLegacy project, build script, asset conversion, PS2 overlays
- **@baummarder** – maintainer of this continuation
- **fastman92** – IMG Console (used by the original build, now replaced by `imgtool.py`)
- **mkps2iso** – PS2 DVD image creation (bundled under GPL-2.0; see `tools/mkps2iso/LICENSE`)
- **pycdlib**, **py7zr** – Python libraries for ISO and 7z handling
- **Devin**, **opencode-agent[bot]** and **DeepSeek** – AI assistance with documentation, build tooling and maintenance of this continuation
