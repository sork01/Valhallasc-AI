# Pack recovery, DPS meter and GM activity

Beta 1.20.0.

## Dungeon pack recovery

Ordinary dungeon and raid pulls remember their engaged enemies, fighters and
fallen fighters. A human killed by a pack returns to the entrance, including
when the raid has an earlier boss rally. Surviving hired fighters keep their
targets and remain in the fight. Humans and hires both respawn on the ordinary
timer during pack combat (owner correction, 2026-10-26); only boss fights hold
fallen fighters down. A respawned fighter counts as fallen for that pull until deliberately returning
within enemy awareness, preventing a wipe from chasing that human to the door.
A fighter can rejoin by targeting a pull enemy or moving back into the fight.

When every fighter falls or leaves, living engaged enemies reset to their
authored homes, with health, status and target restored and projectiles cleared.
Already killed enemies stay dead. Other pulls/copies are untouched. Ending a
pull never restarts or delays a hire's respawn timer.
Boss mechanic fights retain their existing fallen and rally rules.

`world/packs.rs` runs before mercenary navigation and player respawn each tick.
`mercs.rs` suppresses catch-up during a tracked pull; ordinary catch-up requires
both owner and hire out of combat and a living owner. Enemy targeting drops dead,
missing and departed targets rather than pursuing a respawned human indefinitely.

## DPS meter

Actual PvE HP removed is recorded at `hit_slime`; overkill is capped at the
victim's remaining health. Each human and each hire gets a separate row, including
zero-damage current occupants. Ambient adventurers, escorts, gauntlet opponents
and hidden GMs are excluded. Totals are per runtime zone/copy and are never saved.
The meter uses the current encounter's elapsed time with a one-second minimum
divisor. It freezes after its enemies die or disengage, and a new damaging hit
starts the next fight. Instance reset or an empty area clears its history.
An active tracked pack or boss keeps the encounter open even after every enemy
damaged so far has died. Dead fighters retain their damage totals and their DPS
continues falling with the shared clock until that encounter ends.

The client displays trusted `damageMeter` snapshot data. The panel can be moved
and scaled in Settings and hidden/restored using World Menu > DPS meter. Its hide
preference persists. No client-provided damage or time is accepted.

## Floating combat numbers

Rapid hits stagger by 80 ms with a maximum 320 ms display delay. A party burst
must never accumulate seconds of queued text after combat ends. Floating text
ages by real frame time, independently of the 50 ms movement/interpolation cap,
so a slow or hidden view cannot replay expired hits on return.

Checks: `tests/damage-numbers.cjs` includes a same-target 300-hit burst; the
bounded `tests/damage-number-backlog-ui.cjs` advances the actual field frame
clock by ten seconds and verifies old text expires.

## Activity log

The GM's Activity button reads a persistent history of **all real players**.
Only a verified `Character.gm` can read `gm_activity`, even when test commands
are enabled. Activity data is absent from regular snapshots.

Events cover login/logout, level changes, travel between public zone templates,
death/respawn, completed trades (both sides, gold/items), GM actions and rejected
commands/trades. Authenticated malformed commands, repeat joins and message-rate
disconnections are recorded too. Refusals are warnings, not claims of cheating.
NPCs and hires are excluded. Passwords, tokens and raw packets/arguments are not
stored. Unauthorized command records contain only the operation name.

SQLite `activity_log` keeps the latest 5000 entries across restarts. Reads return
100 newest-first entries and an older-page cursor, with bound parameters for
player/event search, category and warnings-only filters. The open GM window
refreshes every five seconds when at the top; loading older entries pauses live
refresh until Refresh. Warning attempts in the world are throttled per connection
for five seconds; malformed-packet reporting is once per connection.

Checks: Rust `pack_recovery_tests`, `damage_meter_tests`, `activity_tests`;
private browser `tests/dps-meter-ui.cjs`, `tests/activity-ui.cjs`. DPS removal
mutation omits hired rows and must fail. No encounter timing/balance sweep.
