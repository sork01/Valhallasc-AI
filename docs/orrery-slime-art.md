# Obsidian Orrery enemy artwork

Owner-approved candidate, Beta 1.39.22. Deployment verification pending. This is art only: enemy kinds, mechanics, world data and the server are unchanged.

Six new editable PixelFlow sources are listed in `scripts/orrery_slime_sources.txt`. Each uses a 192×154 frame and (70,148) anchor, with the existing 34-frame, five-clip layout and 10 fps timing. The production loader derives health-bar tops from the idle art. The Bronze Mantis has six jointed legs and swinging scythes; the Gearling charges; the Orbit Seer hovers and fires an eye beam; the Chronoguard thrusts its spear; the Pendulum Matron swings her pendulum; and the Epoch Engine winds up its gear fists. Their deaths crack and settle the clockwork, lower the armour or gown, or drop the hovering eye to the ground.

```sh
python3 scripts/make_orrery_sprites.py preview   # inspect all 34 frames
python3 scripts/make_orrery_sprites.py build     # preserve registered sources
python3 scripts/make_orrery_sprites.py export    # export saved editor frames
python3 scripts/make_orrery_sprites.py verify    # compare editor and atlas
```

The exporter refuses `--replace` and retains editor edits. `refresh <kind>` explicitly redraws named candidate sources. The original six atlases, manifest, hashes and original PixelFlow IDs are saved at `/media/raid/valhallasc-data/orrery-slime-original-20261104`.

```sh
python3 scripts/rollback_orrery_art.py --target /path/to/checkout          # dry run
python3 scripts/rollback_orrery_art.py --target /path/to/checkout --apply  # restore
```

All seven backup hashes and destinations are checked before writing. Restoration and corrupt-backup refusal were tested in a scratch directory.

The focused real-art browser test is `tests/orrery-slime-art.cjs`; run with `scripts/test-touch-bounded.sh` and the standard browser, Node and private binary environment. It checks production loading, portraits, clip timings, frame bounds, eight distinct attacks and deaths, wind-up and strike motion, grounding and health-bar tops. `scripts/orrery_slime_review.py review|verify|upload` creates and verifies the review package and verifies the pre-deployment live art. No encounter or balance testing was run.
