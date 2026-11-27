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

Released as **1.15.8-c4059296** after the owner's explicit “deploy” approval.
Source is pushed on `fix/dungeon-mercenary-wipes` from
`/media/raid/valhallasc-data/firefox-scrolling`. The normal unit runs the exact
privately tested executable, PID `1325363`, SHA-256
`0871707af1d23e4d4e91c4d47b132253ba8a2172348080dc137c934343a33ffc`.
All ten saved character states are byte-equivalent before the stop, after the
stop and after startup. SQLite, public/legacy/bridge health, both changed public
files and the unchanged Firefox renderer pass verification. No test flags or
warning/error journal entries are present.

Builds and private databases use isolated paths under that checkout. The main
checkout's pending artwork and the separate staged loot/melee work are excluded.

Before-build backup (frozen live executable and consistent running SQLite
backup):
`/media/raid/valhallasc-data/backups/valhalla-dungeon-mercs-20261127T075626Z-r_cnlxut/`.
The backup includes fresh pre-restart and stopped SQLite copies, previous and
candidate executables, validation logs and `receipt.json`. Public receipt:
`www/Valhalla/dungeon-mercenary-wipes-release-receipt.json`.

Client rollback is `1.15.7-0098d3a7`; executable rollback uses
`previous-before-build` from that backup and requires fresh restart approval.
