# City and Halloween changes — Beta 1.33.0

Four owner-reported city/travel tasks are implemented. The separately requested
`PLAYER-NAME-UNIQUENESS` remains open in TODO.md.

- Rust `seasonal`: six passed (five new calendar/quest/save/access checks and one existing seasonal catalog check).
- Rust `compact_atlas`: seven passed, including the new arch/alcove test and all 96 actual walking crossings.
- Bounded `tests/cities-seasonal-ui.cjs`: 47 passed, no browser errors. Real talk/visit progress and exact rewards in all four cities; annual duplicate refusal/reset; expiry and same-character reconnect with saved reward history; production NPC artwork/accessories; city views at 1280×800 and 844×390; aperture pixels and real dungeon entry/return; Bifrost bypass, physical touch selection and safe return; final glyph pixels/font sizes across five terrains, day/night and both viewport sizes. Final artifacts: `/media/raid/valhallasc-data/cities-halloween-work/test-results/driver-C9uM3M/`.
- Stair regression control removes the aperture clip and fails the first pixel check as expected.
- Two complete sync-world runs are byte-stable: map SHA-256 `fa035226832ffd9449799f5fc89f7e9635d73a87d54b9d596006488f650314aa`; client/world.js `791aa1c7d9f1fc8ee29b2614d0b7475b37181d738d6dbc2dc5f9ad42a9885248`.
- All-target Clippy with warnings denied passes. Swedish generation freshness and 23 locale checks, release-notes guard, JavaScript/Python syntax, formatting and whitespace checks pass. The broader Swedish catalog flags three English words inside existing proper names; the same three failures exist in HEAD’s catalog. No full suite, combat timing or balance sweep was run.

A pixel assertion caught sea weather tinting the exit signs after drawing.
Plaques now draw after all weather, before travel messages/guidance. A shallow
isometric arch initially resembled a plank; the final stone vault has enough
rise and separate front/intrados/extruded faces. Use authoritative movement
progress in bounded tests, actual portal coordinates for return, and clear
plaza coordinates away from fountains. Preserve saved client state across a
reload when testing reconnecting the same character.

Rules and regeneration: `docs/seasonal-events.md`, `docs/zone-travel.md`.
No new zones or changed private-copy IDs; old saves use default empty annual
maps. The release needs no database migration or backfill.

Release state: **deployed and verified 2026-11-02** with nobody online.
Source `d4cb7f1` is byte-identical to the privately reviewed
candidate `9e6e03e`. The optimized release passed a separate
private calendar/quest-expiry/descent/return probe before publication.

Backup: `cities-halloween-1.33.0-20261102T100447Z` under `deploy/backups/` (previous executable,
changed client files, consistent online SQLite and stopped DB/WAL/shm).
Public and bridge health pass; all ten changed public client hashes match;
`cmp` and SHA-256 prove the running executable matches the reviewed binary.
SQLite quick_check is OK; **36 characters / 22 guests** are unchanged. No test
flags, public test guests or post-restart journal warnings were introduced.
No copy-ID migration or backfill was needed.

Release and public-hash receipts: `test-results/cities-halloween-release.json`
and `test-results/cities-halloween-public-hashes.json` in the main checkout.
