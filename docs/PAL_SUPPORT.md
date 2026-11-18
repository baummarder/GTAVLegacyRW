# PAL support roadmap

## Current status

The builder recognizes and packages PAL v1.00 (`SLES_529.27`) as an **experimental profile**. In-game compatibility is not verified. US NTSC-U v1.03 (`SLUS_209.46`) remains the only profile with a reference image checksum.

The previous writer produced ISO9660 only and omitted the UDF DVD structures present in the original disc. Packaging now uses the bundled `mkps2iso` PS2 DVD writer. The build checks its UDF volume sequence and anchor, the `PLAYSTATION` system identifier, and the ISO9660 path-table sectors.

Passing `--allow-modded` skips checksum comparison so a clean PAL dump without a configured reference hash can be used. The PAL profile currently omits the NTSC-specific overlays and plugins, which use hard-coded addresses for the US executable. This is a safer boot diagnostic, but game-side modifications and region-specific behavior still need real-console testing. Treat PAL output as experimental.

## Porting work

1. **Record a clean baseline** – preserve the original PAL image and record its disc ID, `SYSTEM.CNF`, executable size, and hashes. Confirm that the unmodified image boots on PCSX2 and the target PS2 setup.
2. **Inventory executable-dependent changes** – identify every address, hook, and binary assumption in `SLUS_209.46`, `src/overlays/`, `src/plugins/`, and scripts that write game memory. Compare the PAL executable and its game data before changing any patch.
3. **Port the patches** – make PAL-specific executable patches and adjust any regional data or asset references that differ. Keep the NTSC-U files and behavior intact.
4. **Complete profile-specific patching** – region detection and output verification are in place for NTSC-U v1.03 and PAL v1.00. Add PAL-specific patches or prove the shared patches work at PAL addresses. Never use `--allow-modded` as a region selector.
5. **Validate both profiles** – check NTSC and PAL packaging, then boot each image in PCSX2. For PAL, test the output on the physical PS2, including startup, loading, gameplay, audio, saves, and modified features. Record the console model, boot method, and results.

## Console test notes

Use a legally obtained image and keep an untouched copy of the original. For each test build, note the image hash, region profile, console model, and boot method (for example, OPL). First confirm the stock PAL image boots with the same setup; that distinguishes a patch problem from a media or loader problem.

Do not describe PAL builds as working until they pass both the emulator checks and a real-console boot and gameplay pass. A successful ISO build or a file listing alone is not evidence of compatibility.
