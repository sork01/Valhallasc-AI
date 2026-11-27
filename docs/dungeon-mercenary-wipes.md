# Dungeon mercenary contracts survive deaths and wipes

Owner correction, 2026-11-27: dungeon hires should stay until the final boss is
defeated or the hirer leaves the dungeon. A death or full party wipe must permit
a retry with the existing hires, without paying again.

The reported behavior came from the older outdoor hirer-death penalty in
`World::update_mercenaries`: it assigned every hire an irreversible deadline
12–30 seconds after the hirer died. Until that deadline it slowed attacks,
suppressed healing/potions and disabled the boss-mechanic brain, then killed and
removed the hire. Reviving the hirer did not clear the deadline. That rule also
ran on dungeon contracts, overriding their existing recovery lifecycle.

Only hires without `merc_instance` can now acquire `merc_doom`. Dungeon and raid
hires therefore keep their ordinary combat behavior and existing contract
through owner deaths, their own deaths and wipes. Survivors keep fighting;
fallen hires still follow the existing pack/boss fallen and respawn timers.
Final-boss completion, leaving the copy, explicit dismissal, party departure and
logout still end contracts. Outdoor contracts retain their existing rules.
No save schema, world data, damage, gear, pricing or respawn timer changes.

The new native regressions cover owner death/return past the old deadline and
completion/exit cleanup in every one of the 83 runtime instance copies, plus
actual lethal-hit full-wipe recovery in ordinary/raid templates and private
copies. Existing Nornroot progress/exit, outdoor doom, seven pack recovery and
boss fallen checks also pass: 13 distinct native checks in total.

`tests/dungeon-mercenary-wipes.cjs` exercises the real private protocol: hire
four classes from the Undervault smith, die, revive and observe the same four
living hires for 35 simulation seconds without another hire payment; kill the
final boss through the authoritative kill path and verify contracts end. It
also checks Nornroot death/revival and leaving the instance. The frozen live
executable fails the survival assertion, reproducing the reported defect.
Run with an explicit `VALHALLA_BINARY`; it never connects to the public game or
edits a database.

The optimized candidate passes all 10 private protocol checks. The same four
hires remain alive through 351 snapshots spanning 35 simulation seconds after
the death; revival, no further payment, final-boss cleanup and exit cleanup all
pass. Report: `test-results/driver-xkENHt/report.json`. The normal release gates
(notes, Swedish, all client JavaScript syntax) pass. The 55 MiB optimized
executable is frozen with the backups below for activation after approval.

Candidate: 1.15.8 on `fix/dungeon-mercenary-wipes` in
`/media/raid/valhallasc-data/firefox-scrolling`. Builds and private databases use
isolated paths under that checkout; the main checkout's pending artwork and the
separate staged loot/melee work are excluded. An optimized executable and a
matching client must be activated together after fresh owner restart approval.
The public game remains 1.15.7 until that approval and deployment.

Before-build backup (frozen live executable and consistent running SQLite
backup):
`/media/raid/valhallasc-data/backups/valhalla-dungeon-mercs-20261127T075626Z-r_cnlxut/`.
Refresh the SQLite backup immediately before an approved restart. Previous
client: `1.15.7-0098d3a7`.
