# Street-aligned city entrances — Beta 1.34.2

All walking entrances to the four major cities are authored against the city
street layout. The atlas previously selected clear edge coordinates without
considering streets, then routed back to the default spawn. This produced
approaches around the perimeter and openings on grass beside paved streets.
The former one-off south Skaldholm correction is superseded by this full audit.

| City | Entrance | Street / crossing centre |
| --- | --- | --- |
| Alderhaven | North and south local gates | Existing central avenue, x36; both were already aligned |
| Skaldholm | Rimeveil, north | Lark Lane, x48 |
| Skaldholm | Greenmeadow, south | Grand Avenue, x80 |
| Skaldholm | Crags, east; Gloamfen, west | Trade Road, y76 |
| Nacrehold | Deep, north; Crags, south | Central avenue, x96 |
| Nacrehold | Astralhollow, east; Bifrost, west | East–west street, y48 |
| Nacrehold | Orrery, east | East–west street, y120 |
| Asterion | Stormglass, north | Central avenue, x90 |

Skaldholm's northern route uses its through-street because the Steward's Hall
closes the northern end of the Grand Avenue. Nacrehold's north approach enters
on the central avenue, follows the cathedral forecourt around the existing
building, and rejoins the avenue. Buildings and services keep their positions.

Skaldholm's old off-street openings are filled and new real collision openings
match the streets. The original south/east gateway towers support appropriately
wide arches; the west tower that blocked the Trade Road is removed. Invisible
old portal posts and foliage blocking the approach are cleared. Other walls
remain solid. Nacrehold's three obstructing coral/kelp props are cleared.
The actual paving extends through every approach. Alderhaven retains its
meadow adventure crossings and correctly centred local city gates.

`scripts/city_walkways.py` owns the authored entrances and prepares collision,
wall repair and paving before the atlas selects reciprocal portal landings.
`scripts/compact_atlas.py` uses those entrances for city endpoints and approach
paths. The source metadata is `cityEntrances`; original street rectangles remain
separate from paving added by this overlay (`cityEntry` marker on those roads).
This makes repeated sync-world runs deterministic and allows tests to compare
entrances with the pre-existing street network.

Run `node scripts/sync-world.cjs`, then rebuild Rust for collision and portal
changes. No file zones or private-copy IDs change. Reciprocal portals retain
their outgoing positions, but their city arrival coordinates update with the
new entrances. Arrival separation, all 96 walking crossings, key/sealed-door
rules and Spark Travel links remain covered by focused atlas checks.

Focused validation: Rust `compact_atlas` (eight distinct checks);
bounded `tests/city-walkways-ui.cjs` exercises all 12 approaches, each wall
opening and both directions of the ten inter-zone city crossings, with native
architecture screenshots at desktop/phone sizes. The narrower
`tests/skaldholm-arches-ui.cjs` uses the updated Grand Avenue/Trade Road locations.
The legacy atlas assertion that every path ends at the default spawn now checks
that authored city approaches end inside the city; movement/clearance and
original-street alignment checks still apply to every segment.

Eight focused Rust checks pass (the legacy spawn-tail assertion was updated for
street endpoints). All **39** bounded browser checks pass, including both sides
of every inter-zone crossing and actual movement through the two local gates.
Artifact: `test-results/driver-BcDgfC` in the private RAID worktree. Native
architecture views of all entrances were inspected at desktop/phone sizes.
All-target Clippy with warnings denied, formatting, changed syntax, Swedish
freshness, 23 locale checks and release-note validation pass. The private MCP
`city_entries` scenario is the focused optimized-release probe.

Two final generator runs are byte-stable: map SHA-256
`cd226aeca7e858673e670c4f049c8511bee57a36d7512abff29700b367ef8327`;
client world SHA-256
`67165b59ea8bcca39d6fcb3d6c45f76d1728c01a866b6cea5f1933a159d120eb`.
All NPCs, quests, monster spawns and file zone IDs are preserved. Outside the
four city zones, only reciprocal portal arrival coordinates change.

Release verification pending. Previous executable, consistent SQLite and prior
client files saved before building at
`deploy/backups/city-walkways-1.34.2-20261102T145210Z`.
