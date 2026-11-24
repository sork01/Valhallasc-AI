# Alchemy

Learn Alchemy from Maera Petalbrook in Alderhaven. Alchemists in Alderhaven, Skaldholm, Nacrehold, Asterion and Veyrroot Heartwood have brewing counters, sell Empty Vials for 25 copper and Empty Flasks for 1 silver, and teach the staple recipes. The workshop lists flower locations, skill requirements, known recipes, available ingredients and buff effects.

Click or tap a nearby flower patch and stay still for 1.5 seconds. Moving, taking damage or losing reach interrupts the pick. Each shared patch yields 1–2 flowers per pick and moves after 3–5 successful picks. Flowers and any skill gain must save before a charge is spent. Three patches are active per adventure zone. Wyrdwood has two outer patches and one inner patch. Alderhaven has its own garden in addition to Greenmeadow's outdoor patches. The four service cities each have one garden patch.

Alchemy starts at skill 1 and caps at 600. The next flower band opens 15 points before the preceding band's cap, and both bands can train during the overlap. Brewing unlocks at the recipe's printed skill requirement. Each eligible pick or brew can award one point, and two eligible misses guarantee the next gain. The workshop shows gathering requirements and available training bands. Flowers from the same band can be mixed in a recipe, including Heartvine Bloom with Dune Lotus and Hourglass Blossom with Ashen Dahlia. A potion needs two flowers and a vial. A staple flask needs four flowers, one from the preceding band and a flask.

Cairnspine elites roll 5% for Trailwind's formula. The final bosses of Black Hour Foundry, The Chained Forge and The Silent Solstice each roll 20% for their respective capstone flask formula at level 99. Study a formula from the bags or the workshop to learn it permanently. Unused formulas, flowers and finished brews can be traded. The drinker's character level gates each brew.

## Buffs

A character can have one 15-second potion and one 45-minute flask in PvE. Drinking a brew replaces or refreshes its slot. The stronger Alchemy bonus applies when both slots affect the same stat. Cooked food keeps its own slot. All short potions use the shared 60-second health and resource potion cooldown. Flasks require being out of combat and use wall-clock expiry. A flask survives death and reconnect. Short potions clear on death or logout.

Alchemy effects are suppressed in duels, Arena matches, the Arena gauntlet and while flagged for world PvP. An unexpired flask resumes in PvE. Maximum-health flasks raise the cap without directly healing the drinker. Replacing, expiring or suppressing the effect clamps health to the new cap.

## Data and verification

- `world/alchemy.txt` defines flowers, effects and recipes. `scripts/alchemy_catalog.py` runs after shaping and mining placement in `scripts/sync-world.cjs`. It installs workshop offers and creates `world/flower-patches.txt` from the reachable finished terrain.
- `cargo test alchemy_` checks authoritative approaches, shared depletion, interruption, atomic saves, training, formula drops and buff eligibility. `python3 tests/alchemy-data.py` checks coverage, alternate candidates, catalog parity, repeatable generation and asset integrity.
- `node tests/alchemy-protocol.cjs` plays through the live protocol with two private guests and a disposable database. `node tests/alchemy-client.cjs` exercises the actual client module in Swedish. On an approved browser host, use the bounded runner with `tests/alchemy-ui.cjs` for desktop and set `TOUCH=1` for Swedish touch.
- Editable PixelFlow projects are listed in `client/assets/alchemy-art.txt`. Run `python3 scripts/make_alchemy_art.py export` to rebuild the sprite atlas. The three dybase2 cues can be rendered again with `bash scripts/create_alchemy_sounds.sh`.

## Public release

Alchemy went live on 2026-11-22 as `1.6.0-8fe38684`. Implementation `8205d277` is on main. The public build came from `8fe38684` on `release/alchemy-1.6.0` and keeps the 120-achievement catalog at 2,555 points.

The release executable passed the private two-player gathering, brewing and restart test. Production returned to bridge health in 2.97 seconds. Verification matched the running executable and all 20 changed client files, checked public and legacy health and the service journal, and confirmed that SQLite preserved all five characters. The desktop and touch browser suites still await host approval.

The previous client release is `1.5.0-a72767c5`. See `www/Valhalla/alchemy-release-receipt.json` and `deploy/backups/alchemy-release-20261122-ArVtgm/` for the release record and rollback backups.
