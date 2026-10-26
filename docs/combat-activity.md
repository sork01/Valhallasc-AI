# Pack recovery, DPS meter and GM activity

Beta 1.20.0.

## Dungeon pack recovery

Ordinary dungeon and raid pulls remember their engaged enemies, fighters and
fallen fighters. A human killed by a pack returns to the entrance, including
when the raid has an earlier boss rally. Surviving hired fighters keep their
targets and remain in the fight; fallen hires wait until that pull ends.
A respawned human counts as fallen for that pull until deliberately returning
within enemy awareness, preventing a wipe from chasing that human to the door.
A human can rejoin by targeting a pull enemy or moving back into the fight.

When every fighter falls or leaves, living engaged enemies reset to their
authored homes, with health, status and target restored and projectiles cleared.
Already killed enemies stay dead. Other pulls/copies are untouched. A finished
pull releases fallen hires to their normal respawn and regroup behavior.
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

The client displays trusted `damageMeter` snapshot data. The panel can be moved
and scaled in Settings and hidden/restored using World Menu > DPS meter. Its hide
preference persists. No client-provided damage or time is accepted.

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
