# Phone and tablet play

Status: owner approved the control layout on 2026-10-24 in this session.
Implementation is built and the indexed combined check passed 198 assertions at both target sizes. The owner has
not yet tested the Safari zoom fix or played this release on real devices.
Keep `BUG-IOS-SAFARI-ZOOM` and `TOUCH-CHECK` open until that happens.

Browser checks on this shared host must use `bash scripts/test-touch-bounded.sh`:
1.5 GiB RAM for the complete process tree, no swap, one CPU and a ten-minute
limit. The helper refuses uncapped execution. Each viewport gets a fresh
browser; layout checks use one physical pixel per CSS pixel, with two used by
the backing-scale check. Test audio decoding is disabled. Never raise limits
or retry a resource failure without investigating it.

On 2026-10-24 an uncapped audit exhausted host RAM and the owner rebooted the
host. The new taller tablet viewport revealed a ground-cache defect: it drew
33–35 chunks while the old cache retained 31, continually replacing visible
canvases. In a capped reproduction, idle anonymous memory grew from 973 MiB to
1123 MiB in about one second, before Settings opened. Ground-cache capacity
now follows the viewport working set and evicted canvases release their backing
buffers. The same bounded six-second probe stayed around 526–565 MiB total,
with a 579 MiB peak. `touch-cache-ui.cjs` asserts that stationary play creates
no replacement canvases; restoring the 31-entry limit produces 99 canvases in
half a second and fails the assertion. The original host's privileged kernel
logs were unavailable; this reproduction establishes the browser defect.

## Approved layout

Landscape only, target sizes 844 × 390 and 1024 × 768 CSS pixels. The game uses the
available landscape area within the safe-area insets; portrait shows the rotate
screen above every window. On a tablet, the world can keep its aspect ratio but
controls and windows must fit the actual stage. Controls appear only when
`matchMedia('(pointer: coarse)')` matches, including a touch laptop whose primary
pointer is coarse. A mouse desktop gets its existing controls.

```text
┌──────────────────────────────────────────────────────────────┐
│ Hero / party                    Quest tracker   Map / menu    │
│                                                              │
│                       Game world                             │
│                                           Skill 3            │
│  Floating joystick                  Skill 2       Skill 4     │
│  (left thumb)                         Skill 1   ATTACK        │
│                    Food / potions     Talk / target actions   │
│                    Other skills tray                         │
└──────────────────────────────────────────────────────────────┘
```

The joystick starts where the first finger touches the lower-left movement
area, outside existing controls. Diameter: 112 px; travel radius:
40 px; dead zone: 8 px; resting opacity: 45%, held opacity: 80%. Four assignable
skill buttons surround a 70 px attack button at the bottom right. Every button
has a final visible width and height of at least 44 px after UI scaling. The
other skill slots remain available through a tray. Food, health and resource
potions sit beside that tray. Talk/read, cross interaction and mount use the
same actions as their keyboard bindings; selected-target actions remain
available through the target portrait menu.

## Movement and simultaneous touches

`Field.keyboardDirection()` already converts screen directions into isometric
world directions; `Field.update()` sends an authoritative action request
`{type: 'input', dx, dy}` every 50 ms while moving and every 250 ms while idle.
The stick supplies an independent screen-direction vector to this same input
path. It does not synthesize keyboard events or send positions, speed, damage
or any player state. Normalize combined keyboard and stick input once.

Beginning stick movement cancels the pending ground route and selected attack
target in the same way as held movement keys. Releasing it clears only the
stick vector. Ordinary ground taps retain the existing route and enemy taps
retain the existing selection/autoattack behavior. Skill use does not change
autoattack rules (`docs/autoattack.md`).

In Beta 1.17.1, the touch Attack button chooses the nearest living monster
in the current zone using snapshot positions and sends the existing `target`
action. It ignores corpses and dormant ambushers, clears held movement and
routes, and lets the server walk into range and repeat basic attacks. Selection
works during an attack cooldown; the server still enforces that cooldown.
After the target dies, tap Attack again to choose another. Explicitly selected
PvP targets keep their existing attack behavior; keyboard Attack is unchanged.
`tests/touch-attack-ui.cjs` checks selection, joystick release and repeated
server-authored attacks, including a mutation restoring the old one-shot action.


Track the stick's pointer ID and capture that pointer. Another pointer may tap
a skill or potion without changing the stick origin or releasing movement.
`pointerup`, `pointercancel`, `lostpointercapture`, window blur, hidden document,
opening a modal and disconnect all clear the stick. A cancel sends zero input
through the existing scheduler immediately. Resuming requires a new touch.

## Assignments and preference migration

Use independent `ITEMS` entries `touch-stick`, `touch-skills`, `touch-actions`
and `touch-quickuse`. Each is a sibling of other scaled HUD pieces; never nest
them inside `skillbar` or another `ITEMS`/`EXTRA` entry. Edit UI moves these
pieces and displays four assignment pickers, one for each arc slot.

Store positions under the existing `Prefs.layout`/saved `ui` keys. Store four
skill IDs per class in `Prefs.touchSkills`, independently of keyboard slots so
changing one does not silently remap the other. Reject unknown classes, skills
from another class, non-arrays and malformed IDs. Missing values use the
defaults below; locked skills remain visible with their required level.
Existing saves without these keys retain their keyboard layout and get touch
defaults. `Settings.loadLayout()` must recognize the new `ITEMS` IDs before
reading offsets; unknown old offsets are still dropped.

| Class | Skill 1 | Skill 2 | Skill 3 | Skill 4 |
| --- | --- | --- | --- | --- |
| Warrior | Cleave | Battle Cry | Shield Wall | Charge |
| Mage | Fireball | Arcane Ward | Blink | Chain Lightning |
| Assassin | Shadowstep | Throwing Knives | Evasion | Lunge |
| Priest | Mend | Smite | Ward of Light | Holy Nova |
| Hunter | Power Shot | Multishot | Roll Away | Hunter's Mark |

Actions with keyboard equivalents use the shared `Keys`/`ACTIONS` behavior and
current binding labels. Every new label receives hand-written Swedish.

## Windows and installation

All windows must fit inside the stage using measured `getBoundingClientRect`
bounds, including at the owner's chosen `--ui` scale. Use responsive layout and
internal scrolling before scaling. Compensate touch control minimum sizes for
the actual window scale so a CSS 44 px button is not reduced to 35 px on screen.
Keep window grips and `WINDOWS` scale caps. Test bags/character, bank, buy/sell,
quests, world map, trade, inspect, skills, settings, release notes, raid,
gauntlet and NPC dialogue, including long content and the final scrolled row.

Use `env(safe-area-inset-*)` at stage/HUD edges, `overscroll-behavior: none`,
and the existing canvas `touch-action: none`. Text fields remain at least
16 px on coarse pointers. Safari gesture guards are already shipped in
Beta 1.16.1; do not claim a real-device fix until the owner confirms it.
The rotate screen must cover both gameplay and dialogs in portrait.

Add a same-origin `.webmanifest` with landscape orientation and standalone
display, existing artwork converted into install icons and an Apple touch
icon. No offline promise: playing still requires the multiplayer connection.
Show a fullscreen button only when the browser supports the Fullscreen API;
reflect enter/exit state and handle a refused request. Validate public MIME
type, status and every changed/new asset hash without creating public guests.

## Low graphics and measurement

An optional persisted Low graphics checkbox is suggested once on the first
touch visit, never forced. Cap world painting at 30 fps while keeping input,
snapshots and simulation updates on their existing cadence. Lower backing
scale to at most 1 (normal maximum 2), reduce cosmetic burst particles and
weather particles, and simplify day/night glows. Preserve boss telegraphs,
ground hazards, projectiles, loot and status cues. Disable backdrop filters
and decorative CSS animations in this mode.

Final before/after idle CPU measurements are recorded below. Use one private
world and the same stationary hero/viewport, sum Chromium descendant processes'
`utime+stime` over equal sampling windows, and count running document animations
and actual canvas paints. Headless uses software rendering: record ratios and
raw observations, not a predicted saving. Sources read: the parent AGENTS.md
render-cost rules and wiki `10_projects:webapp_render_cost_audit_20260904c`,
`30_resources:mobile_layout_measurement_traps` and the existing UI scale code.

## Acceptance

Focused suites: `touch-input-ui.cjs`, `touch-skills-ui.cjs`,
`touch-windows-ui.cjs`, `touch-install-ui.cjs`, `touch-cache-ui.cjs`,
`low-gfx-ui.cjs`, plus existing `ios-zoom-ui.cjs`.
Use real Playwright touch contexts at both target sizes and viewport-only
screenshots (full-page screenshots can remove coarse-pointer emulation).
Each new behavior suite needs a meaningful mutation failure. Then run the
touch suites together once and record the owner's real-phone and tablet
findings. Do not tick the final check on browser emulation alone.

## Validation and measured cost (2026-10-25)

The combined indexed run passed 198 assertions at both target sizes, including
26 window views per size, all five class defaults and Swedish controls. The
whole run peaked at 1214 MiB inside its 1536 MiB cgroup limit. Safari guards
also pass eight focused Chromium checks; each of the seven served-copy
mutations fails on its intended behavior. JavaScript/Python/shell syntax,
release notes and the Swedish catalog pass. The 20 public client files match
staged SHA-256 hashes; the manifest is HTTP 200 with
`application/manifest+json`. The deployment list is `deploy/touch-assets.txt`.

| Viewport | Normal CPU, one core | Low CPU, one core | CPU saving | Normal / Low paints per second | Normal / Low canvas width |
| --- | --- | --- | --- | --- | --- |
| 844 × 390 | 75.2% | 68.0% | 10% | 19.3 / 29.3 | 1688 / 844 |
| 1024 × 768 | 78.0% | 76.6% | 2% | 11.0 / 26.3 | 2048 / 1024 |

These equal three-second stationary samples run with one CPU shared by Node,
the private server and Chromium, with stub actor sprites and audio disabled.
They show the whole Low graphics bundle, not isolated costs for each lever.
Both samples had zero running document animations. The cap constrains normal
rendering; these values do not predict real-phone CPU or GPU performance.

Proof: `test-results/touch/final-index.log`, per-window screenshots,
`cpu-844x390.txt`, `cpu-1024x768.txt`, seven mutation logs and
`public-assets.txt`. The verified index export is on the RAID, its path recorded
in `test-results/touch/export-path.txt`.

WebKit was downloaded on the RAID, but the host lacks its required shared
libraries. No system packages were installed. Real iPhone Safari zoom and real
phone/tablet play remain explicit owner acceptance checks; neither corresponding
TODO checkbox is marked complete.


Beta 1.17.1 focused indexed verification: 22 touch Attack assertions pass across
844x390 and 1024x768, with five/four basic attacks and four impacts after a
single touch. Peak memory was 589 MiB within the unchanged 1536 MiB cap.
Proof: `test-results/touch/attack-index.log` and `attack-public.txt` (all four
changed public client hashes and both health endpoints match).
The served-copy mutation restoring manual Attack fails the nearest-target
assertion as intended (`attack-mutation.log`, 556 MiB peak).


## Touch controls follow-up (Beta 1.17.2)

Owner chose to keep the action row and hide unavailable target actions. Target
menu appears for selected players/adventurers and toggles closed on a second
tap. Its trigger is exempt from the portrait menu's outside-pointer dismissal,
so that a second tap does not close on pointerdown and reopen on click.
Chat toggles open/closed, blurs typing on close, and preserves an unsent draft.
Enter retains its existing focus/send behavior. Both buttons expose expanded
state. Cooling arc skills show a white 24 px countdown over a dark full-icon
overlay, retaining full opacity while the disabled button blocks recasting.
The displayed seconds come from the existing authoritative cooldown state.
Focused test: `tests/touch-feedback-ui.cjs` under the required resource cap.

Indexed follow-up verification: 30 assertions pass at 844x390 and 1024x768,
with a 573 MiB peak inside the unchanged 1536 MiB cgroup cap. Screenshots show
the cooldown overlay; the private-world check observes its countdown, blocks
recasting and removes it when ready. Chat draft/focus/toggle and a selected real
player's target menu pass. Five changed public client hashes match; bridge and
public health report OK. Proof: `test-results/touch/feedback-index.log`,
`feedback-public.txt`, and the indexed export's `feedback-*.png` captures.
The three served-copy mutations fail the intended assertions for Chat closing,
contextual Target menu visibility and countdown legibility. Logs are
`feedback-mutation-{chat,target,cooldown}.log`.
