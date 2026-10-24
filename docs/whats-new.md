# What's new (UI-WHATS-NEW)

Beta 1.15.0 adds an English-only welcome and release-notes window. Client only; no server restart or save migration.

The first visit in a browser without a prior `valhallasc.save.v1` gets a short welcome about movement, fighting, Greenmeadow and Linden. Its controls come from `Keys.label` and update on rebinding. Existing browsers without an acknowledgement get the current release notes. After showing either window, `valhallasc.whats-new.v1` stores the displayed version, separate from game preferences, accounts and the original Valhalla. Settings → What's new always reopens the latest notes and its expandable Older updates section. Close, Escape and Enter close it; focus returns to the previous control. Tab stays in the window. Game keys are blocked while reading, held movement is cleared, and opening during gameplay sends Stop. The world keeps running.

The centered window is above the game's confirmations, registered in Settings `WINDOWS`, and follows global UI size and its own saved corner-grip scale. Header and Close stay visible while the text scrolls. Unrelated grips are hidden while reading. `translate="no"` is respected by Locale for both text and attributes. The notes, welcome and fixed labels stay English for every language; existing translations of words such as Close still work elsewhere. The new title and version are in `sv-keep.txt`. The intentionally English-only module and notes file are outside the Swedish text harvest.

If the notes cannot be loaded, the game remains usable and the version is not acknowledged. Opening from Settings retries the request. A blocked localStorage still allows reading and closing; a reload can show the update again when the browser cannot save its acknowledgement.

## Updating the notes

Every game version bump must update `client/index.html`, `scripts/sv-keep.txt` and `client/release-notes.txt` in the same change, followed by `python3 scripts/build_swedish.py`. Put the newest entry first, with its full displayed version, date, and `new`, `changed`, `removed` arrays. Use everyday English. Omit empty sections when rendering; keep all three arrays in the file. Every removal explains why. Describe balance changes as nearest whole percentages, never decimal factors or programming terms.

`node tests/whats-new-notes.cjs` rejects a missing current entry, duplicates, empty entries, programming language, decimal percentages and removals without reasons. It runs at the start of `npm test`, and `npm run test:whats-new` runs it with the private browser check. The displayed game version is independent of the Rust package and network protocol.

## Historical notes

The six entries preserve the actual displayed labels found with `git log -- client/index.html`; earlier changes did not consistently bump the label. They group the changes shipped under each label rather than inventing version numbers:

- Beta 1.15.0: this window and the welcome.
- Beta 1.14.33 (`b60a333`): selling basket, valuable-item confirmation, junk shortcut and buy-back.
- Beta 1.14.32 (`e8932db`): owner's new baseline, after the earlier updates below were already live.
- Beta 1.1.1 (`75b3d51`, `a01d59d`): green vendor weapons.
- Beta 1.0.1 (`2c401ab`): Ember Key (`bd16999`), movement-skill autoattack (`d3a8261`), login timer (`53e59e3`), mercenary following (`e679177`).
- Multiplayer alpha 0.985.1 (`0d3a63d` through the 2026-10-23 releases): raid and rewards, cloaks, death/repair, dungeon and arena easing, inspect/portrait menu, class gear binding, lava, Windows and Safari improvements. Opening details are in `docs/molten-raid.md`; easing values are in TODO and commit `fe99048`.

## Focused checks

Run only this feature, using the existing live binary in a private world:

```
node tests/whats-new-notes.cjs
REAL_SPRITES=1 VALHALLA_BINARY=/absolute/path/to/target/release/valhalla-server node tests/whats-new-ui.cjs
MUTATE=1 REAL_SPRITES=1 VALHALLA_BINARY=/absolute/path/to/target/release/valhalla-server node tests/whats-new-ui.cjs
MUTATE=missing node tests/whats-new-notes.cjs
python3 scripts/build_swedish.py --check
python3 tests/swedish-catalog.py
node tests/swedish-locale.cjs
```

The two mutation runs must fail. The UI test covers first and returning visits, current/rebound controls, once-per-version acknowledgement/reload, Settings, full history, English text with Swedish active, focus/keyboard behavior, UI/window/grip scale, phone scrolling, and a failed notes fetch followed by retry. It saves phone/history screenshots in its private driver's result folder. `tests/lib/playwright.cjs` acknowledges the current release for unrelated browser tests; this test sets `TEST_WHATS_NEW=1` to exercise the actual popup. No public guests, balance sweeps or server builds are needed.
