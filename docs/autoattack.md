# Autoattack after skills

Selecting a living monster sends `target` to the server. `World::update_player`
walks into basic-attack range and calls `start_attack` while that target remains
valid. Skills briefly interrupt the basic attack; they should not cancel this
selection. A new movement command or `stop` still cancels autoattack.

The Hunter idle report of 2026-10-23 reproduced after Roll Away: `use_skill`'s
shared `Effect::Dash` branch called `Player::stop`, which cleared `target` along
with movement. The client kept its selected enemy, so the target portrait and
ring remained visible while the server had no target to attack.

Movement skills now clear keyboard input and the walking destination while
keeping the selected monster. This applies to Roll Away, Blink, Charge and
Lunge. Assassin's separate Shadowstep command now follows the same rule.
Target validation still discards dead monsters and monsters in another
zone. A roll with no selected monster starts no attack. No balance values,
cooldowns, resource costs or damage calculations change.

Focused checks:

- `autoattack_resumes_after_every_class_skill`: repeated basic attacks resume
  after all 50 learned skills across all five classes, including a skill cast
  during a basic attack. Healing skills run with the caster injured.
- `assassin_shadowstep_resumes_autoattack`: the Assassin's separate dash command
  also resumes repeated basic attacks.
- `movement_skills_keep_autoattack_target_until_manually_cancelled`: all five
  movement skills retain the target; Stop, keyboard movement and click-to-move
  cancel it.
- `hunter_rollaway_never_acquires_an_unselected_or_dead_target`: no automatic
  target acquisition, and no attacks on a dead target.
- `tests/autoattack-ui.cjs`: clicks every class's skills in a private browser
  and counts repeated server-authored basic-attack events and hits afterward,
  without another action. At close range, arrows can spawn and hit between
  snapshots, so counting only visible bolts is unreliable.
  `AUTOATTACK_CLASSES=hunter AUTOATTACK_SKILL_ONLY=rollaway` isolates the original reproduction, which fails
  against the pre-fix server with zero basic shots. The matching Assassin /
  `shadowstep` filter also reproduced zero basic attacks before its fix.

This is a server change and requires a rebuilt binary and restart to become live.

Validated 2026-10-23: all five focused Rust tests pass, including every learned
skill and manual cancellation after each movement skill. The private browser
passes all 51 abilities (Warrior 10, Mage 10, Assassin 11, Priest 10, Hunter 10),
with repeated basic attacks and confirmed hits/misses after each cast. Priest
needed no combat change. Clippy with `--all-targets -- -D warnings`, formatting
and JavaScript syntax checks pass. Browser results are saved locally in
`test-results/autoattack-all-classes.log`.

Both Roll Away and Shadowstep were reproduced with zero attacks on their
unfixed servers. No public restart was performed.
