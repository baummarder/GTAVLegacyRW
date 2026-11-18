# PAL support roadmap

## Current status

PAL is **not supported yet**. The build targets the US NTSC-U v1.03 release (`SLUS_209.46`). The PAL disc available for development identifies itself as PAL v1.00 and boots `SLES_529.27`.

Passing `--allow-modded` only skips the checksum comparison. It does not translate executable patches, overlays, plugins, or regional game data. The build must keep rejecting PAL input until a PAL-specific patch set has been ported and tested.

## Porting work

1. **Record a clean baseline** – preserve the original PAL image and record its disc ID, `SYSTEM.CNF`, executable size, and hashes. Confirm that the unmodified image boots on PCSX2 and the target PS2 setup.
2. **Inventory executable-dependent changes** – identify every address, hook, and binary assumption in `SLUS_209.46`, `src/overlays/`, and `src/plugins/`. Compare the PAL executable and its game data before changing any patch.
3. **Port the patches** – make PAL-specific executable patches and adjust any regional data or asset references that differ. Keep the NTSC-U files and behavior intact.
4. **Add explicit region profiles to the builder** – select a profile from the verified disc ID. Each profile must define its accepted executable, checksum policy, patch assets, and output verification entries. Never use `--allow-modded` as a region selector.
5. **Validate both profiles** – run automated checks for NTSC and PAL packaging, then boot each image in PCSX2. For PAL, test the output on the physical PS2, including startup, loading, gameplay, audio, saves, and the modified features. Record the console model, boot method, and results.

## Console test notes

Use a legally obtained image and keep an untouched copy of the original. For each test build, note the image hash, region profile, console model, and boot method (for example, OPL). First confirm the stock PAL image boots with the same setup; that distinguishes a patch problem from a media or loader problem.

Do not describe PAL builds as working until they pass both the emulator checks and a real-console boot and gameplay pass. A successful ISO build or a file listing alone is not evidence of compatibility.
