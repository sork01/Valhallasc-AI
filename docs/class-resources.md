# Class resources

## Hunter energy and class autoattacks (1.15.14)

Owner requests, 2026-11-27: faster Hunter energy recovery, 50% less Assassin autoattack damage, then 50% more Hunter and Priest autoattack damage. Hunter recovery rises from 10 to **15 energy per second**, in and out of combat; Assassin recovery remains 10. Both retain their 100-energy cap and stop recovering while dead. HUD tooltips describe the class-specific rate in English and Swedish.

Hunter and Priest basic attacks use a **1.5 damage multiplier**; Assassin basic attacks use a **0.5 damage multiplier** before the existing integer rounding and minimum-hit floor, in both PvE and PvP. Skills retain their authored damage, costs and cooldowns. Critical and hit chances, attack speed, equipment stats and independent set/enchantment signature damage remain unchanged. Hired/ambient actors use the same class paths. No save migration or world regeneration.

`World::roll_basic_damage` is shared by monster strikes and player basic attacks. Skill paths continue calling `roll_damage` directly. Focused native checks cover class isolation, misses/crits, buffed real PvE strikes, empty energy, PvP defences, and energy recovery in/out of combat, caps and death. `tests/hunter-assassin-balance-ui.cjs` checks both classes' English and Swedish energy tooltips. Released with the matching executable and client as **1.15.14-2be66591** after owner approval.

Validation: 20 resource checks and the focused PvP damage check cover all three changed classes; five existing autoattack checks pass. The companion Anchorfall fix passes the real Longship encounter regression in both phases and all 19 boss geometry/schema checks (46 focused native tests total). The actual client lane polygon passes 56 boundary checks. The optimized executable passes `tests/hunter-energy-probe.cjs`: over 40 simulation ticks, Hunter restores 30 energy and Assassin 20. The prior live executable fails the Hunter assertion (20 energy). Five bounded UI checks pass at 844 × 390, including both English/Swedish tooltips and no page errors (847 MiB peak). The HUD explicitly forwards the hero class and allows the initial reset before the hero look exists. Client release dry-run, Swedish coverage and JavaScript syntax checks pass.

Release verified: PID **1572995**, exact tested executable, all ten saved character states unchanged, SQLite, five public files, public/legacy/bridge health, no test flags and a clean journal. Source `2be66591` is on pushed main. Receipt `www/Valhalla/class-anchorfall-release-receipt.json`; backups `/media/raid/valhallasc-data/backups/valhalla-class-anchorfall-20261127-8d6s46qw/`. Client rollback `1.15.13-c32ee8bc`; executable `previous-before-build` there requires fresh restart approval.

## Caster mana return and warrior rage (1.15.12)

Owner request, 2026-11-27: priest and mage skills have a 10% chance to return 20% mana; warriors generate 50% less rage.

- Each accepted Mage or Priest skill cast rolls once for **20% of maximum mana**, after paying its cost and resolving its effects. Healing, buffs, utility and free casts qualify. The maximum uses the same level, intellect and equipment bonuses as the resource bar, and returns cap at that maximum. Failed casts, cooldown attempts, basic attacks, projectile hits and periodic effects do not roll. Applies in PvE and PvP, including hired/ambient casters through the normal skill path. No AI decision changes.
- Warrior combat rage now grants **0.25 per actual damage dealt** and **0.5 per actual damage taken**, down from 0.5 and 1 respectively. The same rates apply to monster and player combat, before the existing cap. Actual damage excludes shields, overkill and dead targets under the existing rules. Resource spending, maximum, out-of-combat decay, food, potions and explicit equipment restores keep their existing behavior.
- The existing priest normal-hit/free-Mend proc remains independent. A valid free Mend can also restore mana under the new per-cast rule.

`server/src/world/resources.rs` owns the chance/fraction and shared rage rates. `World::use_skill` calls `roll_cast_mana` exactly once at its successful end. A separate `resource_rng` stream avoids changing combat or enchantment random sequences. The existing skill event carries the **actual** `mana` restored, including zero when capped. No new packet or persistent field is needed.

The client shows positive returns with the existing blue mana floater and Healing/resources floating-text preference. Zero returns stay quiet. Mana/rage HUD tooltips describe the new rules in English and Swedish. Party resource bars already consume the resulting authoritative values.

Focused validation:

- `cargo test resource_tests`: accepted/rejected casts, all eligible classes, free Mend, caps and event values, fixed-seed proc frequency, actual AI casts, PvE/PvP rage, overkill, decay and existing resource/consumable lifecycle rules.
- Related price fixtures explicitly seed the new independent stream to isolate normal skill costs from procs: free Mend, enchanting discounts and raid set skill prices.
- `tests/class-resources-probe.cjs` uses the optimized executable in a private world, casts until both classes receive the proc, and checks the returned amount against maximum mana. The retained old executable must fail its missing-return assertion.
- `TOUCH_SIZE=844x390 bash scripts/test-touch-bounded.sh tests/class-resources-ui.cjs`: tooltips, actual field-event floating text, filtering, zero suppression, unchanged potion feedback and Swedish priest text. `MUTATE=1` serves the previous field renderer and must fail the missing skill-mana feedback.
- Existing `tests/floating-text.cjs` and normal release gates.

Built on live 1.15.11, retaining party resources and the dungeon-only boss-health reduction. No map generation or save migration. Deployment requires the matching executable and client; release state and frozen artifacts are recorded in the staging/deployment receipt.

Released after the owner requested “hurry and deploy”: **1.15.12-85b15f7e**, merged/pushed to main, PID **1503762**. All 21 focused native checks, seven bounded UI checks and the private mage/priest return probe pass; old executable and old renderer controls fail as expected. Exact executable, all ten character saves, SQLite, five public files, all health endpoints, absent test flags and clean journal verified. Receipt: `www/Valhalla/class-resources-release-receipt.json`. Backups: `/media/raid/valhallasc-data/backups/valhalla-class-resources-20261127-7dh6xq90/`. Client rollback `1.15.11-78b2254d`; executable `previous-before-build` there requires fresh restart approval.
