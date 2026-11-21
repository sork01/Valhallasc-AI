# Blacksmithing

Speak to Bram Emberforge in Alderhaven and choose the Blacksmithing workshop to learn the profession and receive a starter pick. Keep a pick in your bags. Click or tap an active vein within reach, then stay still for the pull. Moving, taking damage, or losing access to the vein ends the action. Town smiths sell components and replacement starter picks through their Buy menu.

Three veins are active in each of 21 shared adventure zones. Each supports three to five pulls shared by everyone nearby. A successful pull places one or two ore in the miner's bag. If a bag cannot hold the ore, the pull remains available. After the last pull the vein relocates to an unoccupied candidate and receives a fresh ID. Town service maps, private instances and the Arena have no veins.

## Progression

| Skill to train | Ore | Primary zone | Pick that reaches this ore |
| --- | --- | --- | --- |
| 1–29 | Tin | Greenmeadow | Starter |
| 30–59 | Copper | Emberfall Crags | Starter |
| 60–89 | Iron | Rimeveil Glacier | Copper |
| 90–119 | Silver | Gloamfen | Copper |
| 120–149 | Gold | Wyrdwood | Silver |
| 150–179 | Cobalt | Bifrost Reach | Silver |
| 180–209 | Mithril | The Prismwaste | Cobalt |
| 210–239 | Stormsilver | The Stormglass Flats | Cobalt |
| 240–269 | Sunsteel | The Lapis Erg | Stormsilver |
| 270–299 | Stariron | The Yearwheel | Stormsilver |

The workshop lists the current tier's primary and alternate mining areas. A completed pull or equipment craft in the current band rolls once for one point. Two eligible misses guarantee the next gain. Earlier tiers still produce their ore and equipment. Smelting and pick upgrades use materials without increasing skill. Copper, Silver, Cobalt and Stormsilver pick upgrades unlock at skills 30, 90, 150 and 210. Each uses the previous pick, four current bars, two Hardwood and a fee of 1 silver, 3 silver 50 copper, 9 silver or 18 silver.

Smiths teach ten green recipes when their bands open. Level-appropriate monsters in shared adventure zones drop their tier's blue blueprint at 1.5%, or 4.5% for elites and bosses. The final bosses of Black Hour Foundry, The Amber Archive, The Silent Solstice and The Chained Forge have a 20% chance to award a blueprint from the five level-99 epic plans. Unused plans can be traded. Study a plan from the bags or the workshop to learn it permanently. The five epic recipes require skill 300. Their stats use 90% of the equivalent level-99 Foundry epic budget.

## Data and persistence

`world/blacksmithing.txt` defines the tier, pick, blueprint and ingredient lists. `scripts/blacksmithing_catalog.py` runs after shaping in `scripts/sync-world.cjs`. It adds smith offers and item definitions and generates `world/mining-veins.txt` from reachable finished terrain. It preserves other offers and world geometry. The client receives active vein IDs and coordinates in zone snapshots. Mining channels and active veins are session state, while the skill, miss streak, learned plans, materials and gear copies are saved with the character.

The recipe transaction checks the existing smith, available skill, learned plans and costs. It applies the change to a staged character and saves it before returning the result. A completed pull saves the ore and any skill gain before consuming a vein charge. Crafted gear creates an ordinary physical copy that works with existing equip, trade and enchantment rules.

The editable PixelFlow sources are listed in `client/assets/blacksmithing-art.txt`. Export from those sources with `python3 scripts/make_blacksmithing_art.py export`. The three sound effects come from the dybase2 project stored in `client/assets/blacksmithing-sounds.txt` and can be rendered again using `bash scripts/create_blacksmithing_sounds.sh`.

## Focused checks

- `cargo test blacksmithing_` checks candidate collision and approach, shared depletion, interruptions, full bags, tier eligibility, pick upgrades, loot, and saved crafting.
- `python3 tests/blacksmithing-data.py` checks the overlay, its generated world and item data, the ladder, the art and the decoded sound cues.
- `node tests/blacksmithing-client.cjs` checks workshop controls, Swedish text, canvas interactions and effects.
- `node tests/blacksmithing-protocol.cjs` uses two guests and a disposable private world to drive real mining, smith purchases, crafting, equipping and restart persistence.
- `bash scripts/test-touch-bounded.sh tests/blacksmithing-ui.cjs` checks desktop controls. `TOUCH=1` exercises touch in landscape and Swedish.

## Public release

Blacksmithing went live on 2026-11-21 as `1.5.0-a72767c5`. Implementation `3c435067` and catalog ordering fix `a3cff571` are on main. The exact public source is `a72767c5` on `release/blacksmithing-1.5.0`. It uses the public achievement catalog of 120 achievements and 2,555 points.

The release executable passed the private two-player protocol and restart test. Production returned to bridge health in 1.406 seconds. Verification matched the running executable and checksums of all 20 changed public files, checked both public routes and the service journal, and confirmed that SQLite preserved all five characters.

See `www/Valhalla/blacksmithing-release-receipt.json` and `deploy/backups/blacksmithing-release-20261121-j2iHMR/` for the release record and rollback backups. The previous client release is `1.4.0-f1f0fc25`.
