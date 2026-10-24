# Green weapons from vendors

Regular merchants (`buys: true`) and armorers sell existing uncommon class
weapons at levels 10, 20, 30, 40, 50, 60, 70, 80 and 90. The current world has
28 eligible NPCs. Five class families cover 45 existing weapons; their IDs,
stats, artwork, drop eligibility and resale values stay unchanged.

Each vendor carries a tiered offer for every class. The client shows the buyer's
own class and the highest decade their current level permits, including level,
price, weapon icon and a normal equipment tooltip. Below level 10 it shows the
first weapon disabled. Level 99 continues to use the level-90 tier. Purchase
is one item, never automatic and never auto-equips it.

| Required level | Gold |
| --- | ---: |
| 10 | 1,000 |
| 20 | 4,000 |
| 30 | 9,000 |
| 40 | 16,000 |
| 50 | 25,000 |
| 60 | 36,000 |
| 70 | 49,000 |
| 80 | 64,000 |
| 90 | 81,000 |

Prices are `10 × level²`, identical for all classes. This provides a gold cost
that rises with progression while existing green drops remain useful. Prices
exceed resale values at every tier. No other economy values change.

The server independently resolves the tier and price, checks class and level,
then uses the existing funds, bag-space, interaction range and persistence
path. A refused purchase does not spend gold or award a weapon.

`scripts/vendor_weapons.py` annotates only the selected existing items and adds
or refreshes the five vendor offers. `scripts/sync-world.cjs` runs it after the
other catalog/world overlays so regeneration preserves stock. Run sync-world
after gear or zone generation, then rebuild Rust; item/map data is embedded.
Canonical JSON layout is preserved, and repeated sync-world runs are byte-stable.
English and hand-written Swedish cover the purchase labels and refusals.

Focused validation: `vendor_weapon_` Rust tests and
`tests/vendor-weapons-ui.cjs`. The browser uses a private server and real
purchases. `MUTATE=1` removes class filtering and should fail the stock check.
No public test logins or purchases are needed.

Validation (2026-10-24): four focused Rust tests pass, including all 45 real
purchases and saved gold/items, every usable level boundary through 99, vendor
coverage, class/level/funds/bag/range refusals. All 197 private browser checks
pass against the immutable release candidate: real dialogue/purchases for all
five classes, English/Swedish, disabled levels, correct prices, green labels
and working equipment tooltips. Artifact:
`.tools/vendor-weapons-worktree/test-results/driver-2KxdDF`. Clippy with warnings
denied, fmt, changed JS/Python syntax, byte-stable generation, Swedish catalog
and 21 locale checks pass. Semantic data comparison confirms no new item IDs
or changes to stats, resale values, drop sources, map geometry, zones or quests.

The private `MUTATE=1` control removes class filtering and correctly fails
the first own-class stock assertion; production files are never mutated.

Deployed 2026-10-24 with nobody online (source `a01d59d`). Backup:
`deploy/backups/vendor-weapons-20261024T113025Z/` contains the old running
binary before building, previous four client files, consistent pre-build and
stopped SQLite snapshots, and the immutable tested candidate. Public/bridge
health and all four public client hashes pass. The running binary matches the
private candidate; no test flags or warning/error journal entries. SQLite
`quick_check` passes; counts remain 25 characters / 14 guests. No new zones,
item IDs or database migration. Release SHA-256:
`2a9e32ab009353cc90714c5f0546c248c7aebf08719f97f44b9fdbb03fcf6fcc`.

Finish/version follow-up (2026-10-24): the owner now requires patch bumps for
small additions and minor bumps for bigger features. This feature is marked
**Beta 1.1.1** in the visible client label; its untranslated keep-list changes
with it. The game server and protocol remain the already verified release.
