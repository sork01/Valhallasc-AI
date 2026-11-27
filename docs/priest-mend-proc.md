# Priest: free Mend on normal hits (`PRIEST-MEND-PROC`, 1.15.10)

Owner, 2026-11-27: a level 25 priest in a hired party could not keep up on the Nornroot final boss. The fix had to
be an ability change, not different decisions by the computer priest.

## Rule
- Each normal swing of a priest that damages at least one monster has a **10% chance** to clear Mend's cooldown and
  make Mend cost no mana for **4 seconds**. One roll per swing, however many monsters it hits. Misses never roll.
- While the 4 seconds last, Mend is free every time it is ready (a second free cast is possible once its normal
  cooldown ends). A new proc restarts the 4 seconds. Only Mend is affected.
- Needs Mend (level 4). Applies to players, hired priests and ambient adventurers alike.
- Never in PvP: no roll while flagged, fighting a player, queued, duelling, in an arena match or gauntlet, and any
  time already held ends. Death ends it too.
- A free cast keeps a ready Spellweaver discount for the next cast that costs mana.

## Where it lives
- `server/src/world/mend_proc.rs`: chance, duration, `skill_price` (used by `use_skill` and `ai_combat_at`).
  The computer priest chooses exactly as before; it only knows a free Mend needs no mana.
- Snapshot field `mendFree` (seconds, owner only). `client/skillbar.js` `price()` / `free()`; the skill bar and the
  touch buttons glow and read "Free!".

## Evidence behind 10%
A replay of the owner's party (level 25 warrior in green gear with hired priest, mage, hunter and assassin) on the
final boss, 20 seeds each, with the harness playing the warrior (it dodges every mechanic, no potions):

| Proc chance, Mend | Kills | No deaths | Priest damage per second |
| --- | --- | --- | --- |
| none | 2 | 1 | 222 |
| 5% | 12 | 5 | 236 |
| 10% | 19 | 17 | 249 |
| 30% | 20 | 20 | 268 |

The cause of the wipes: the hired priest ran out of mana about 40 seconds into a fight of about 100. Priest damage
rises a little because mana not spent on Mend goes into damage spells; the owner accepted that.

Not checked: other bosses, and higher levels (at level 99 Mend already heals far more than monsters deal).

## Tests
`cargo test mend_proc` (7), `bash scripts/test-touch-bounded.sh tests/mend-proc-ui.cjs` (`MUTATE=1` must fail).
