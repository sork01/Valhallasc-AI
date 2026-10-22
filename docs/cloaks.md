# Cloaks

`GEAR-CLOAK`, 2026-10-22. Prepared in `.tools/cloak-worktree` on
`feat/gear-cloak`. Do not release until `GEAR-CLOAK-RECAL` is complete.

The tenth equipment slot is `cloak`, with a matching `Look.cloak` field. All
100 cloaks are class-neutral and work on male and female Warriors, Mages,
Assassins, Priests and Hunters. There is no starter cloak and no save migration:
old looks default to `none`, and old equipment maps simply lack the slot.

The ordinary ladder is every five levels from 5 through 95, then 99. There are
60 gray/green/blue pieces, ten epic pieces (10..90 and 99), ten legendary
pieces, and twenty dungeon pieces. Cloaks add attributes only, with no attack
or defence. Blue and purple cloaks have the necklace's attribute budget at the
same level and rarity; dungeon cloaks copy their own source's necklace budget.
The 99 rung continues to 114 points per blue attribute. On 2026-10-22 the owner
also requested stamina on gray and green cloaks: the blue amount divided by
`1.175²` and `1.175`, respectively, rounded and at least one point.

`scripts/gear_levels.py` calls `cloak_catalog.apply`, which owns the ladder,
names and dungeon variants. Orange rules append ten cloak entries after the
fifty original pieces, preserving every original ID and roll range. There are
now sixty equally selected orange pieces; a cloak still has independent stat
rolls but its attack/defence ranges are `[0, 0]`.

Ordinary drops pick cloaks through the existing equipment pool. Dungeon cloaks
share the necklace boss pool, without adding a guaranteed roll. Their source
identifies the reward pool, but both the server and client explicitly exclude
cloaks from set bonuses. Existing hard-quest reward choices also offer a cloak;
a guaranteed `rewardItem` stays unchanged. The map overlay runs from
`sync-world.cjs`, so rerunning a zone generator does not permanently remove the
new choices. Armourers and provision merchants sell three tiered cloak
families through `best_tier`, at the buyer's level and each item's price.

Hired fighters receive the best ordinary green cloak from level five onward.
Upgrade comparison includes cloak attributes, so an empty slot and better
stamina pieces are useful even with zero attack/defence. Full progression and
gauntlet fixtures now explicitly fill ten slots, including both rings. At 99
the cloak uses its 99 rung; the other ordinary gear still uses 95. These are
fixture changes, not balance certification.

## Worn art

The `createarmors` and `makesprites` workflows are used. Five original cloth
constructions live in `scripts/cloak_shapes.py`: travel, folded hood, long
mantle, clasped cape and torn ember cloak. Each has its own silhouette and every
item has an explicit recolour. `make_cloak_sprites.py` fits all ten existing
character rigs, with eight facings and the original idle/walk/attack/hurt/die
frame counts. Shoulder seams follow the character's pose; lower rows have
phase-delayed sway, walking drag and ground correction on death. Panel depth
is interpolated over the projected plane rather than averaged.

Builds save both sexes and all clips to PixelFlow and export the cels back;
exports preserve editor changes. Existing completed sprites are never deleted.
The CLI locks its shared state file: supply multiple styles to one build command
or run separate commands sequentially.
The 250 animation sprites plus five icons have editable IDs in
`docs/cloak-gear-state.txt` and `world/gear-art.txt`. Runtime colour/depth atlases
are separate, lazy-loaded cloak parts. Exports recompute the affected bounds
using `sprite_bounds.part_bounds`. The inventory atlas gets five appended icon
cells; every cloak maps to one of those bases and its own tint.

Mounted riders retain the idle pose while cycling its breathing/cloth frames
when moving, so the cloak is animated on a running horse. Dashes use the same
pose selection as the existing character renderer.

```
python3 scripts/make_cloak_sprites.py preview [travel hooded mantle clasp ember]
python3 scripts/make_cloak_sprites.py build [styles...]
python3 scripts/make_cloak_sprites.py export [styles...]
python3 scripts/gear_levels.py
python3 scripts/orange_rules.py
python3 scripts/orange_items.py
node scripts/sync-world.cjs
python3 scripts/build_swedish.py
```

In a nested worktree set `VALHALLA_TOOLS` to the original Valhalla's read-only
`tools` directory. The private Cargo target is
`/media/raid/valhallasc-data/cloak-target`; the served main client is untouched.

## Focused validation

Use `cargo test cloak`, `tests/gear-cloak.py`, `tests/gear-cloak-ui.cjs` and
`tests/gear-cloak-world.cjs`. The sprite check uses real decoded atlases for all
ten rigs, five constructions, every facing and every animation frame, including
later armour that already has a cape. It also checks removing the cloak,
rarity recolours, a running horse and the ten-slot desktop/mobile window.
`--mutation-missing` removes the cloak layers from served test metadata and
must fail. The private-world check uses an isolated database, exercises equip
and vendor requests, and moves an actual equipped female Mage.

The older `tests/gear-generator.py` has two existing failures: extending an old
catalogue misses forty previously authored pieces, and the universal tint test
indexes `tint` on original non-recoloured art. `tests/quest-rewards.py` has six
existing failures for authored Foundry/Longship/Nornroot guaranteed rewards.
Both were compared with an unchanged `git archive HEAD` export. Cloak-specific
checks separately require deterministic catalogue rebuilds and all sources.


Validation completed 2026-10-22: 12 Rust checks, six focused Python checks,
14,400 real compositor poses, the private equip/vendor/movement flow, both
removal mutations, `cargo clippy --all-targets -- -D warnings`, formatting,
Python/JavaScript syntax and the Swedish check all pass. The portrait fixture
hides only the existing rotate-device curtain to inspect the 390x844 panel;
this feature does not enable portrait gameplay. Every original item is
unchanged. Removing the added offers/choices restores the original map exactly.
Receipts and reviewed images are in `test-results/cloaks/`.
