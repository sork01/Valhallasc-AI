# Firefox world scrolling

Owner report, 2026-11-27: walking and world scrolling stutter continuously in
Firefox, including in Low Graphics mode.

The ground cache rasterizes each chunk at `chunkScale`, then rounds its canvas
width and height up to whole backing pixels. Drawing that entire canvas into the
original logical rectangle squeezed the rounding padding into the scene. For
example, at scale 0.8 an 812 × 556 chunk allocated 650 × 445 pixels, then scaled
all of them into 649.6 × 444.8 backing pixels. This prevented the intended 1:1
copy and made Firefox rescale every visible chunk on every frame.

`drawGroundChunk()` selects the exact painted source extent, 649.6 × 444.8 in
that example. Both current-zone and neighbouring-zone ground use it. Destination
coordinates, clipping, logical dimensions, camera motion, cache retention and the
1.5 raster-scale cap stay the same. It also preserves the intended proportional
scaling when a resize leaves slightly different raster/backing scales, or when
the backing scale exceeds the cap. There is no browser-specific rendering mode.

`node tests/ground-blit.cjs` checks 21 combinations of fractional raster scales,
placements, resizing and backing scales. `MUTATE=padding` restores the old full
canvas source and must fail.

The bounded `tests/ground-blit-ui.cjs` draws actual cached ground while walking
in Greenmeadow and alongside Rán's Deep from Nacrehold. It checks both ground
owners, source and destination geometry, and exact synthetic pixel preservation
at raster scales 0.6, 0.8, 1.2 and 1.5. Actors use the normal test stubs; terrain
and scenery use the actual renderers. `BROWSER=chromium` selects Chromium;
Firefox is the default. `GROUND_CASE=1` selects the reported Low Graphics
configuration. Cases 2 and 3 cover normal graphics at DPR 2, below and above the
ground raster cap. A new browser is closed after each viewport.

The reproducible `scripts/profile-ground-scrolling.cjs` measures idle and walking
frames against a private world at noon with clear weather, 1280 × 800 viewport,
DPR 1 and Low Graphics. `BASELINE=1` routes the pinned pre-fix `b75fdb20` field
script without changing checkout files. `ONE_ZONE=1` selects Greenmeadow only.
Reports are written under `test-results/firefox-scrolling/`.

Run every browser command through `bash scripts/test-touch-bounded.sh <script>`.
Keep its 1536 MiB, no-swap, one-CPU, 128-task and ten-minute limits. Firefox's
background process count is reduced in the fixtures to fit the task cap. On this
host, use `NODE_OPTIONS=--v8-pool-size=1`, `UV_THREADPOOL_SIZE=1`,
`TOKIO_WORKER_THREADS=1`, `STYLO_THREADS=1`, `RAYON_NUM_THREADS=1`,
`MOZ_TASKCONTROLLER_THREADCOUNT=1` and `taskset -c 0` for Firefox. The missing GTK
and Xinerama libraries were downloaded and extracted locally under
`.tools/firefox-libs`; set `LD_LIBRARY_PATH` to its `usr/lib/x86_64-linux-gnu`.
No host packages or browser resource limits were changed. Set `VALHALLA_BINARY`
to the current optimized private-test executable. These headless, CPU-limited
measurements describe the reproduction, not the owner's device frame rate.

Mozilla's [canvas optimization guide](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas)
also recommends avoiding repeated image scaling.

## Measured result and checks

In the final bounded Firefox comparison, mean ground drawing fell from 24.29 to
9.23 ms per idle frame, and from 24.44 to 9.19 ms while walking (62% less time).
Median frame intervals fell from 58 to 42 ms idle and from 58 to 43 ms walking.
Both runs used the same fixture, executable and resource limits; neither hit a
memory or task limit. Raw reports are `firefox-baseline.json` and
`firefox-candidate.json` under `test-results/firefox-scrolling/`.

Firefox passes 16 focused checks in the reported Low Graphics configuration.
Chromium passes 48 across all three viewport/DPR/graphics configurations. Both
engines preserve the exact synthetic pixels at all four matched scales, and the
walking checks exercise current and neighbouring ground. Those runs peaked at
956 MiB (Firefox) and 1256 MiB (Chromium), within the unchanged 1536 MiB cap.
The 21 non-browser geometry checks, actor-motion unit checks, 27 tutorial/cache
regressions and release-note/Swedish checks also pass.

Both padding mutations fail as intended: the Node check rejects the full-canvas
source, and Chromium reports 120,184 differing channel values in the scale-0.6
pixel comparison. The existing bounded `actor-motion-ui.cjs` also passes when
run alone (motion-clock robust CV 0.022 against the unchanged 0.1 limit). Its
first run overlapped release validation and failed; that run is not claimed as
a pass. The exclusive run replaces it.

Client update: 1.15.7. Release receipt:
`www/Valhalla/firefox-scrolling-release-receipt.json`. The previous client,
`1.15.6-d9df8cc1`, is retained for rollback through the client release helper.
