# Key map (UI-KEYMAP, 2026-10-21)

Client only (`client/keymap.js`, the Keyboard screen in `settings.js`, check `tests/keymap-ui.cjs`). No server change.

## Model
- One table `ACTIONS` in `keymap.js`: group, action id, label, shipped keys. 33 actions: four moves, mount, talk, attack, dash (Assassin Shadow Step), twelve skill slots, three quick slots, ten windows and menu keys, chat, sound.
- Up to **two keys per action** (the shipped bindings already needed it: WASD + arrows, Space + J, B + I, M + N for sound).
- Keys are stored as **`event.code`** (the physical key), Left/Right Shift as one `Shift`. A code survives Shift, an IME (`event.key` is `Process`) and other layouts; labels come from `navigator.keyboard.getLayoutMap()` where the browser has it (Chromium), else the code's own name. A synthetic event with no `code` falls back to its character.
- `Prefs.keys` holds **overrides only** (`{action: [code, code]}`, saved in `valhallasc.save.v1` as `keys`). The shipped keys are merged under them at read time, so old saves work and a new action gets its key. An empty slot is `null`.
- The two shipped skill keys `-` and `=` still answer by character while those slots are unchanged (on a Swedish layout the physical Minus key prints `+`).

## `window.Keys`
`is(event, action)` (false for Ctrl/Alt/Meta and while a capture runs), `which(event, [actions])`, `actionsFor(code)`, `codeOf`, `typing(event)` (INPUT/TEXTAREA/SELECT/contenteditable), `label(action, all)`, `name(code)`, `slots(action)`, `isDefault(action)`, `bind`, `clear`, `reset`, `resetAll`, `capture(cb)`, `skillRange()`. Every handler asks `Keys.is`; none compares `event.key` any more except the fixed keys below.

## Fixed (not rebindable)
Esc always closes/opens like before (the `menu` action only adds a key), Tab and the focus traps, Enter/Esc/arrows inside dialogs and the Edit UI nudging and grip keys. Never bindable: Tab, Ctrl/Alt/Meta, CapsLock, F5/F11/F12, Backspace/Delete (they clear a box), Escape (cancels the capture), Enter except for chat.

## Keyboard screen
Settings → Keyboard: one row per action, two key boxes, a per-row Reset, Reset all keys. Click a box, press the key. A key another action holds is **swapped**: the other action gets the key this slot had, unless it may not have it (Escape, Enter outside chat) and then it loses the key; a key held by several actions (M is the map and a sound key) leaves all of them. The message names the first one. Esc cancels, Backspace clears.

## Hints that follow the keys
Dynamic: tracker/party/mount/skill-slot/quick-slot labels and titles, the welcome line, level-up hint, bags tooltip, sound toast, pvp and mount help, rebirth notice, and (in `keymap.js` `applyHints`) the static `index.html` aria-labels, titles and kbd tags. `applyHints` rewrites a hint only once its action was changed, so the shipped text and its Swedish stay untouched for everyone else. Standalone-loaded scripts (test fixtures) fall back to the shipped keys.
Swedish: hand-written templates in `sv-template-translations.txt` with `{n:t}` on key slots (key names such as Space/Shift are translated); `keymap` is in `CLIENT_FILES` of `build_swedish.py`; key codes are in `sv-ignore.txt`. The key name for Enter is `↵ Enter` because the plain word is the dungeon button's "Gå in".

## Server and world texts: ‹action› placeholders
Text the server or the world data writes cannot know the player's keys, so it names an action instead of a letter: `‹mount›`, `‹quests›`, `‹bags›`, `‹dash›` (any action id; the first key is used). `keymap.js` runs a MutationObserver over the page and replaces the placeholder in text nodes and in `title`/`aria-label`/`placeholder` where the text lands. It runs after Locale's observer (locale.js loads first), so Swedish templates keep the placeholder (`Tryck på ‹mount› för att sitta upp`) and the key name is translated afterwards (Space becomes Mellanslag). Text already on the page keeps the key it was written with. Used by: the mount and quest notices in `world.rs` and `consumables.rs`, two NPC lines in `map.txt`, and the class blurb in `game.js` (re-applied on `keymap-change`).
**Release note:** the Rust change is in HEAD but only reaches players with the next server release; until then the live binary sends the default letters, which read correctly. The dialogue lines are live now (client/world.js).
New server text that names a key: write `‹action›`, never a letter.
