# Dance command

Beta 1.32.3 adds `/dance` in world chat for all five classes and both bodies.
It toggles a looping cosmetic emote: female step-touch/sway/twirl, male bouncing
heel-toe shuffle. The shared compositor choreographs existing fitted walk frames,
so equipped artwork, colors and depth stay intact. World positions never move.

The server consumes the command (case insensitive, normal chat rate limit),
dismounts and clears movement/autoattack. Snapshot `danceT` is elapsed seconds
or null; clients interpolate it for local and remote characters. It is transient
and never saved. Movement, fighting, damage, death, mounting and travel cancel
it. Combat, stun, root, freezing and Spark Travel prevent starting. Zero input
and Stop preserve it because opening chat sends Stop.

Focused validation: Rust `dance::tests`, bounded `tests/dance-ui.cjs` (command,
observer snapshots and real equipped renders on all ten rigs).

Deployed 2026-10-29 with nobody online. Three focused Rust tests, 33 bounded
browser checks (including 160 real dressed dance samples), the disabled-dance
mutation, Clippy, formatting, JavaScript syntax, Swedish and release notes pass.
The mutation correctly fails the first real-art check when choreography is removed.

Backup: `deploy/backups/dance-1.32.3-20261029T155347Z/` (previous running binary,
consistent online/stopped SQLite backups and previous client files). Its
`verification.txt` records the deployed binary hash and five public client hashes.
Public/bridge health, exact running binary, SQLite quick_check, unchanged 30 saved
characters, absence of test flags and absence of journal errors were verified.
No public guest was created. Reload the game to load the dance renderer.

## Guided festival circuits (private Beta 1.38.0)

The original stationary chat emote retains its behavior. Seasonal centerpiece
interactions reuse its choreography while server-owned legal movement completes
two full circles. No client lap claims are accepted. See seasonal-events.md and
festival-spirit-validation.md for interruptions, persistent two-hour rewards and
focused validation.

## Race dances in 1.11.1

All five classes use the same choreography for a given race and body. Nearby
players see it during `/dance` and guided festival dances.

| Race | Female | Male |
| --- | --- | --- |
| Human | Step-touch, sway and twirl | Bouncing heel-toe shuffle |
| Mothkin | A hovering spiral with a soft landing | Quick zigzag hops with midair turns |
| Tidekin | A side-to-side glide with a sweeping turn | Low, rolling lunges to either side |
| Gnome | Toe taps and a clockwork pirouette | Double hops and sharp heel clicks |

The shared compositor takes the race and body from the dressed sprite's look.
Older looks use the Human routines. The dance transforms are drawn around the
feet, so equipment and race features stay aligned and the emote stays in place.
`tests/dance-ui.cjs` compares dressed pose sequences across all eight dances
and all five classes. `MUTATE=race` forces Human choreography to check that the
test catches lost race selection.
