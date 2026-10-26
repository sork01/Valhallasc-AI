# Dungeon admission quests

Four additional dungeons require a one-time quest turn-in per character. The
existing Black Hour Foundry (`null_keys`) and Chained Forge (`raid_key`) gates
remain. There are now five gated five-player dungeons out of twenty, plus the
Forge raid. The owner's correction was **four more dungeons**, superseding the
initial one-sixth target.

| Dungeon | Quest | Exterior giver | Objectives |
|---|---|---|---|
| Nornroot Barrow, 25 | Three Names for the Dead | Runa Threadreader, Wyrdwood | Visit three funeral stones and ask Egil for forgotten names. |
| The Moonwell, 60 | A Bell for Your Reflection | Mora Thirteenbells, Asterion | Ring three bells together before their 25-second echoes expire. Any order works. |
| The Sunken Astrolabe, 85 | The Sky Beneath the Sand | Laleh of the Lens, Lapis Erg | Bring three Glass Scorpion Shards, consult Ivo, visit the Mirrored Oasis. The shards are consumed on claim. |
| The Silent Solstice, 99 | Smuggle a Little Sunrise | Ysra Snowglass, Rimehold | Defeat three Snow Stoats, speak to Tilda, shelter a hearth spark in a 12-second vigil by the entrance. |

Each quest is independent of the zone's older quest chain, offered at the
dungeon's minimum level, with normal level-based quest XP and no item/gold reward.
Existing NPC identities/art are reused. All objectives and turn-ins are outside
the locked dungeon. The normal objective system does not impose an order.
The vigil pauses outside its circle; death resets unfinished progress. The bells
use personal chime state; each hero must complete their own run. Objectives,
tracked map markers, giver markers and quest windows use the existing systems.

Only `QuestProgress.completions > 0` opens a door. Accepting the quest or finishing
its objectives without turning it in is insufficient. Unlocks persist through
saves, and no item has to remain in the bag. Real party members need their own
unlock; hired fighters follow their hirer normally. Returns remain ungated.
Previously visiting a dungeon grants no exemption. Existing instance login
recovery returns saved occupants to their exterior entrance. No zones, copy IDs
or save fields change, and no save migration is needed.

`scripts/dungeon_admission.py` owns an idempotent overlay on `world/map.txt`.
`scripts/sync-world.cjs` always reapplies it before client export, so regenerating
a parent zone cannot lose the quests at the next sync. Never hand-edit generated
map or client data. Funeral stones reuse Wyrdwood `spire` art, bells reuse
`tidebell`, and the vigil reuses `wardstone` including its progress ring.
Props have a solid foot with an accessible objective circle around it.

Focused checks: `cargo test dungeon_admission` covers all four quest flows,
missing/active/ready refusals, claims, consumed materials, save round trips,
exit/reentry, level restrictions, bell expiry, vigil pause/death, existing keys
and collision/reachability. `MUTATE_DUNGEON_ADMISSION=1` removes the new gates
inside the refusal test and must fail. Fixtures inject kill credit through the
normal quest event rather than grinding or testing encounter balance.

## Validation and release

Released as **Beta 1.24.0** on 2026-10-26, with nobody online. Four admission
Rust checks pass, as do the five Nornroot checks (with the boss-loot fixture
updated for the additional ledger entry), the existing Moonwell stairs check,
and the deliberate gate-removal mutation. Clippy with warnings denied,
formatting, changed JavaScript/Python syntax, Swedish coverage, release-note
validation and overlay byte stability pass. No balance sweeps ran.

The bounded browser run passed 18 checks against the exact release executable:
all four exterior quest windows/acceptances, a live bell countdown, normal
bell-quest turn-in, Egil's actual forgotten names and normal funeral-quest
turn-in. Candidate and screenshot:
`/media/raid/valhallasc-data/dungeon-admission-bdowaotn/test-results/driver-IYx7wJ/`.

Rollback backup: `deploy/backups/dungeon-admission-20261026T185258Z/`, containing
the previous running executable, consistent pre-build SQLite, stopped database
and previous client files. Both health endpoints, the four public client hashes,
running executable hash, SQLite `quick_check`, all 31 saved characters, absence
of test flags and the clean startup journal were verified after release.
Release binary SHA256:
`64e1df6a31f455184f1c4e5d5992aa474d079013964bfe630235a222c5f9168c`.
