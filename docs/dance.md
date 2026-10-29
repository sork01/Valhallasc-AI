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
