# Game master invisibility rules

These settle `GM-INVIS-RULES` in [TODO.md](../TODO.md). `GM-INVIS-SERVER`, `GM-INVIS-CLIENT` and `GM-INVIS-CHECK` implement and verify them. The commands and defaults are also in the README.

## Meaning of "hidden"

A hidden GM (`Player.hidden == true`, set only for a character with `gm == true`) is absent from everything another player can perceive or query.

| Surface | Other players | The GM |
| --- | --- | --- |
| Sprite, shadow, name, nameplate, effects of their own casts | Not sent in any snapshot | Drawn as a faint outline (about 35% opacity, gold) |
| Zone snapshot `players` list | Removed for every viewer except the GM | Included |
| Nearby-player list, minimap dots, world-map presence | Not listed | Sees themselves and others normally |
| Party list, friend list "online" state, `who` | Not listed; party invites and friend requests to the GM by name fail as if the name does not exist | Normal |
| Zone and world counts (`online`, `humansOnline`, the HUD count) | Not counted (the number a player sees excludes the GM) | Sees the count including themself |
| Chat | See below | Normal |
| Monsters | Never target or aggro the GM; area effects and bolts do nothing | God mode already stops all damage |
| Duels and arena matches | See Defaults | |

Per-viewer filtering matters: `snapshot_for(zone)` currently builds one list for the whole zone, so the server must build the player list **per recipient** (or remove the GM's entry from the shared list and add it back only into the GM's own copy). The GM's casts and hits are still real, but others see an attack only as the enemy's own reaction (a hurt flash), never a caster. `GM-INVIS-SERVER` must also strip the GM from `bolts`, `drops` that carry an owner name, and from every `event` that names the actor.

## Monsters

- A hidden GM is never selected by `World` aggro or `target` logic (`awareness` and `hunting` scans skip them), so enemies never chase.
- Enemies that are already chasing someone else keep their target; an area effect aimed at a point ignores the GM like any god-mode player.
- A hidden GM's hits damage the enemy but never give it a target, so nothing chases them. Kills, loot, XP and quest credit are unchanged.

## Chat

- **Chat while hidden shows the name and text, without a position and without any in-world bubble.** The chat line reads exactly like any other, so hidden GMs can still talk to players on request. A GM who wants to stay unseen simply does not chat.
- Whispers and party chat are not available while hidden (the GM is not a party member or a listed friend).

## Commands

Typed in the chat box (client/gm.js turns them into `debug` ops; the server checks `gm` again):

| Command | Effect |
| --- | --- |
| `/vis` | Show the current state. |
| `/vis on` , `/show` | Become **visible** to others. |
| `/vis off` , `/hide` | Become hidden. |
| `/vis toggle` | Flip. |

`/show` and `/hide` are aliases of `/vis on` and `/vis off`. The reply says "You are hidden." or "You are visible."; if the character is not a GM, the commands do not exist (same refusal as other debug ops).

## Defaults

- **Hidden on every login and every zone change** (not only the first login). A GM must type `/show` again after crossing a portal or teleporting if they want to be seen.
- Visibility is **not saved**. A restart, disconnect and reconnect all start hidden.
- **Private dungeon copies and arena matches:** hiding carries through (the same flag). A hidden GM entering a party's copy does not appear in the party's list or the copy's player count and does not count towards the party's size. An arena match always shows the GM: the arena refuses a hidden GM ("Show yourself before you can fight in the arena") because a hidden fighter has no valid team slot. Duels cannot start with a hidden GM (a duel request needs a visible target) and the GM cannot send one without first typing `/show`.

## Visible for the GM

- `GM-INVIS-CLIENT` shows a small "Hidden" or "Visible" badge next to the character name, plus the outline above.
- Other players are displayed normally, with names.

## README

Add under the existing game master commands: the table above and the default (hidden on login and zone change; not saved).

## What `GM-INVIS-CHECK` must prove

- A hidden GM is absent from a normal client's snapshots, nearby list, party list, counts and chat position, while the GM's own client has all of it.
- Monsters never target the GM, and no area effect, bolt or event names the actor to others.
- `/show` and `/hide` work for the GM only; a normal account gets no effect.
- The hidden state resets on login and on every zone change, is carried into a dungeon copy, and is refused in an arena.
