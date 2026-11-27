# Caster mana return and warrior rage (1.15.12)

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
