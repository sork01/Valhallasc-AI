# Blacksmithing

Speak to Bram Emberforge in Alderhaven and choose the Blacksmithing workshop to learn the profession and receive a starter pick. Keep a pick in your bags. Click or tap an active vein to walk into reach and begin mining. Stay still for the pull. Learned miners see ore on the minimap by default. Settings can hide ore markers. On phones and tablets, **Mine ore** appears beside the skill buttons when a vein is within reach. Moving, taking damage, or losing access to the vein ends the action. Town smiths sell components and replacement starter picks through their Buy menu.

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
| 180–209 | Cobalt | Rán’s Deep | Silver |
| 210–239 | Mithril | Astralhollow | Cobalt |
| 240–269 | Mithril | The Prismwaste | Cobalt |
| 270–299 | Mithril | The Obsidian Orrery | Cobalt |

The workshop lists the mining areas that currently award skill. The region sets the training band even when two regions contain the same ore. A completed pull or equipment craft in the current band rolls once for one point. Two eligible misses guarantee the next gain. Earlier tiers still produce their ore and equipment. Smelting and pick upgrades use materials without increasing skill. Copper, Silver, Cobalt and Stormsilver pick upgrades unlock at skills 30, 90, 150 and 210. Each uses the previous pick, four current bars, two Hardwood and a fee of 1 silver, 3 silver 50 copper, 9 silver or 18 silver.

Smiths teach green recipes when their bands open. Level-appropriate monsters in shared adventure zones drop a blue blueprint at 1.5%, or 4.5% for elites and bosses. The final bosses of Black Hour Foundry, The Amber Archive, The Silent Solstice and The Chained Forge have a 20% chance to award one of eight level-99 epic plans. Unused plans can be traded. Study a plan from the bags or the workshop to learn it permanently. Five of the epic recipes require skill 300 and three master recipes require 600. Their stats use 90% of the equivalent level-99 epic budget.

### Expert training

From skill 300, mine in the region named in the workshop with its required pick, or forge equipment from the listed ore. A weaker pick that reaches the ore still gathers it. The mining result points you to the pick that can advance your skill. Skill, equipment and learned plans in existing saves carry over.

| Skill before gaining | Ore | Mining region | Minimum pick for skill gains | New equipment blueprint |
| --- | --- | --- | --- | --- |
| 300–329 | Stormsilver | The Moonspore Canopy | Moonspore | Moonspore Pendant (trainer) |
| 330–359 | Stormsilver | The Stormglass Flats | Moonspore | Stormglass Mantle (drop) |
| 360–389 | Stormsilver | Sunward Vale | Sunward | Sunward Trail Leggings (trainer) |
| 390–419 | Stormsilver | The Ribbonwild | Sunward | Jubilee Signet (drop) |
| 420–449 | Sunsteel | The Tanglecrown | Tanglecrown | Tanglecrown Mantle (trainer) |
| 450–479 | Sunsteel | Veyrroot Canopy or The Lapis Erg | Tanglecrown | Duneglass Longbow (drop) |
| 480–509 | Sunsteel | Frostwake Shelf | Frostwake | Frostwake Pauldrons (trainer) |
| 510–539 | Stariron | The Cairnspine | Frostwake | Slatewing Pendant (drop) |
| 540–569 | Stariron | The Yearwheel | Yearwheel | Yearwheel Band (trainer) |
| 570–599 | Stariron | Emberwake Caldera | Yearwheel | Caldera Veil (drop) |

Forge the expert picks at skills 300, 360, 420, 480, 540 and 600. Each upgrade uses the previous pick, four bars, two Hardwood and a fee. The first two recipes use Stormsilver, the next two use Sunsteel, and the last two use Stariron. The Masterwork Mining Pick yields one extra ore per completed pull at skill 600.

Each new blue plan shares its region's existing blueprint roll. The workshop names the region in the recipe row. At 600, smiths can forge Equinox Crown Ring, Unbroken Hour Pendant and Last Ember Mantle after studying their plans. Those three plans share the final-boss pool with the five earlier epics.

Mining trains through the current 30-point band. Forging can continue through consecutive bands using the same ore. Expert gains use the same 60% base chance as skill 300, with the existing recipe quality bonus and guaranteed gain after two eligible misses.

## Data and persistence

`world/blacksmithing.txt` defines the tier, pick, blueprint and ingredient lists. `scripts/blacksmithing_catalog.py` runs after shaping in `scripts/sync-world.cjs`. It adds smith offers and item definitions and generates `world/mining-veins.txt` from reachable finished terrain. It preserves other offers and world geometry. The client receives active vein IDs and coordinates in zone snapshots. Mining channels and active veins are session state, while the skill, miss streak, learned plans, materials and gear copies are saved with the character.

The recipe transaction checks the existing smith, available skill, learned plans and costs. It applies the change to a staged character and saves it before returning the result. A completed pull saves the ore and any skill gain before consuming a vein charge. Crafted gear creates an ordinary physical copy that works with existing equip, trade and enchantment rules.

The editable PixelFlow sources are listed in `client/assets/blacksmithing-art.txt`. The expert sheet was appended after the original icon cells. Export from those sources with `python3 scripts/make_blacksmithing_art.py export`. The three sound effects come from the dybase2 project stored in `client/assets/blacksmithing-sounds.txt` and can be rendered again using `bash scripts/create_blacksmithing_sounds.sh`.

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
