# PAL investigation (paused)

PAL support is temporarily disabled. The supported build target is US NTSC-U v1.03 (`SLUS_209.46`). The CLI rejects PAL v1.00 (`SLES_529.27`) before changing the build folder; `--allow-modded` does not re-enable it.

## What has been observed

- The original PAL-based output did not start.
- After correcting the DVD filesystem layout, the PS2 startup screen appeared, but the game still did not continue.
- A second PAL test image omitted the NTSC-specific overlays and CLEO plugins; it also did not continue.
- The overlays and plugins contain hard-coded addresses for the US executable, so they are not safe to reuse on PAL without a port.

The DVD filesystem issue is fixed. The remaining cause is not confirmed. The next useful baseline is to test an untouched PAL ISO with the same console and boot method; that will distinguish a PAL game/loader issue from this project's modified files. A PCSX2 boot and a startup log would further narrow it down.

## Resume PAL work

1. Confirm the untouched PAL disc/image boots on the same PS2 and through the same loader.
2. Record where the modified image stops: before or after the PS2 logo, and whether it returns to the browser or stays black.
3. Compare the PAL executable and startup files with the US NTSC-U v1.03 versions.
4. Port every executable-dependent overlay, plugin, and script memory address for PAL.
5. Re-enable the PAL profile only after it boots in an emulator and on real hardware.

Do not move NTSC assets or patch sources into this directory. This folder keeps PAL-specific investigation notes isolated while the normal build remains NTSC-only.
