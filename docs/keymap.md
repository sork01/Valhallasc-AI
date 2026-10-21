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

## Not dynamic (open)
Texts the server sends name keys: "Press H to mount" (`world.rs` mount notices, `consumables.rs`) and "journal (Q)" (quest accepted/found). The Assassin class blurb on the title screen says "Shift". They would need a placeholder the client fills in.
