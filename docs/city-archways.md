# Skaldholm wall archways — Beta 1.34.1

The west/left arch previously painted each wedge's roof, front and inner face
before the next wedge. Later roof faces cut dark triangles across completed
front faces, especially in the rotated wall. Its piers also showed a rear face.
The renderer now finishes each continuous surface before the front face and
uses complete world-axis piers, matching the adjoining limestone ramparts.

The southern opening was centred at x107.5, copied from the atlas crossing,
while Raven Row is centred at x112. The owning geography overlay now derives
the opening centre from the closest through-street, repairs the retired part
of the wall, and cuts the real aperture at (112,140). A foliage-clear connector
and highlighted paving link the street to the established crossing. The portal
(107.5,154.5), safe arrival and other city openings keep their positions.
No buildings, services, quest content, zones or private-copy IDs move.

Regenerate using `node scripts/sync-world.cjs`, then rebuild Rust for the changed
collision. Two consecutive generations are byte-stable. Focused checks:
`cargo test compact_atlas_city_archways_and_nacre_alcove_are_walkable` verifies
all four apertures and adjacent solid wall, the south street/connector, and the
restored retired opening. Bounded `tests/skaldholm-arches-ui.cjs` checks the
actual front-face pixels in both orientations, the paving centre line,
desktop/phone views and normal server-authoritative walking through both
reported openings. No full suite or unrelated gameplay checks are required.

The focused Rust check and all six browser checks pass, including both real
walk-throughs. All-target Clippy with warnings denied, formatting, changed
JavaScript/Python syntax, Swedish freshness and release-note checks pass.
Inspected desktop and phone views are in the private checkout at
`test-results/driver-OyUDlv/{left,bottom}-{desktop,phone}.png`; earlier views are
in `test-results/driver-9RQNJ8`. Generated map SHA-256:
`8de60e802139e841a92c29c9eca5ee32440b1adb8f29dcd98162e583badc8588`.

Deployed and verified 2026-11-02, source `aa09f59` (private source `fad42b6`).
The optimized release also crossed both openings via normal movement in a
private probe (`test-results/driver-hqXZUw/report.json` in the worktree).
Previous live executable, consistent SQLite
and changed client files are backed up before the release build at
`deploy/backups/skaldholm-arches-1.34.1-20261102T140954Z`.

Zero-player restart; public/bridge health, all four changed public client
hashes, exact running executable, SQLite quick_check, unchanged 36 characters /
22 guests and every saved character JSON hash verified. No test flags, journal
warnings/errors or public test guest. No zone/copy-ID or save migration.
Release receipt: `test-results/skaldholm-arches-release-20261102T141829Z.json`
and the backup's `verification.json`.

## Full city audit (Beta 1.34.2)

The later owner request aligns all major-city entrances with their streets.
It supersedes the Raven Row/retained-portal layout above: Skaldholm’s southern
entry now follows Grand Avenue (x80) and both side entries follow Trade Road
(y76). See [city-walkways.md](city-walkways.md) for all four cities.
