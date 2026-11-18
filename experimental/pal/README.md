# PAL investigation (paused)

PAL support is temporarily disabled. The supported build target is US NTSC-U v1.03 (`SLUS_209.46`). The CLI rejects PAL v1.00 (`SLES_529.27`) before changing the build folder; `--allow-modded` does not re-enable it.

## What has been observed

- The original PAL-based output did not start.
- After correcting the DVD filesystem layout, the PS2 startup screen appeared, but the game still did not continue.
- A second PAL test image omitted the NTSC-specific overlays and CLEO plugins; it also did not continue.
- The overlays and plugins contain hard-coded addresses for the US executable, so they are not safe to reuse on PAL without a port.
- The file named `GTA V Legacy PAL Safe Boot Test.iso` is PAL, despite being tried as the NTSC test: its boot entry is `SLES_529.27` and `VMODE = PAL`.
- The untouched PAL game starts on the same PS2 and OPL setup. This confirms the console, display, and general loader setup can run that original PAL release.

The DVD filesystem issue is fixed. The remaining cause in the modified PAL image is not confirmed. The GTA San Andreas folder checked for this investigation contains the PAL original but no US NTSC-U v1.03 ISO, so an actual NTSC build has not yet been tested.

## Resume PAL work

1. Resume only if PAL support becomes a priority; the untouched PAL boot is already confirmed on this console and loader.
2. Record exactly when the modified PAL image turns white: before or after the PS2 logo, and whether it returns to the browser.
3. Compare the PAL executable and startup files with the US NTSC-U v1.03 versions.
4. Port every executable-dependent overlay, plugin, and script memory address for PAL.
5. Re-enable the PAL profile only after it boots in an emulator and on real hardware.

For OPL, leave GSM/video forcing and compatibility modes at their defaults during the first test. OPL's GSM is off by default and is a per-game video override; changing it would confound diagnosis of the image itself. See the [OPL GSM guide](https://www.ps2homebrew.org/Open-PS2-Loader-User-Guide/gsm.html).

Do not move NTSC assets or patch sources into this directory. This folder keeps PAL-specific investigation notes isolated while the normal build remains NTSC-only.
