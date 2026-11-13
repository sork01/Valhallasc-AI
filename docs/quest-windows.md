# Quest rewards and acceptance

## One-column conversations (Beta 1.48.0)

Owner references in FileDrop (2026-11-13): `questgiver.webp` for the quest
giver's page and `npc_dialogue1.png` for the greeting. They show the layout to
follow; the frame, parchment, fonts and icons are the game's own drawing.

Every conversation is now one tall parchment in a dark iron frame, at every
screen size. The journal keeps its two-pane frame; conversations no longer
borrow it (no `quest-panel` / `journal-*` classes, no sidebar, no phone
**Quest list / Details** tabs on `#npc-dialogue`).

- **Header:** the speaker's face in a round frame on the top-left corner
  (`#npc-portrait`, drawn by `portrait()` in `city.js` with `drawNpc(..., true)`;
  hidden in merchant mode, which has its own), the name on a plate, a red close
  square.
- **Greeting (`view.kind === 'gossip'`):** the greeting text, then the quests as
  rows (`#npc-quest-list .journal-quest[data-quest|data-status]`, now inside the
  parchment and styled as gossip rows: mark, title, level), then services.
  Footer: purse on the left, **Goodbye** (`#npc-quest-close`) on the right.
- **Quest page:** title, state line, story, **Quest Objectives**, **Rewards**.
  Each reward icon sits on a plate with the item's name beside it
  (`.quest-reward-cell`, two per row; `rewards(..., named)` in `quests.js`; the
  journal keeps bare icons). Footer: **Accept** / **Complete Quest** on the left,
  **Decline** / **Back** on the right (returns to the greeting). The shell has
  class `quest-view`; the quest rows stay in the DOM but hidden.
- **Touch:** `touch.css` sizes the window from the stage and divides text and
  targets by `--window-k`; both grid tracks of `#npc-dialogue` are
  `minmax(0, 1fr)` so the unscaled box centres instead of overflowing downwards.
- Merchant, merge, refine, repair and stat-reset views are unchanged in
  behaviour; the non-merchant ones sit in the new frame.

Checks (bounded runner): `tests/quest-window-ui.cjs` 21 at touch 844×390 and 21
at desktop 1440×900 (`QUEST_DESKTOP=1 TOUCH_SIZE=1440x900`);
`tests/quest-mobile-ui.cjs` 34 at 667×375. Screenshots
`test-results/touch/npc-gossip-*`, `quest-accept-classic-*`, `quest-window-*`.
Not rerun: the older zone suites that click `#npc-quest-list` rows
(`zones-ui`, `skaldholm-ui`, `gloamfen-ui`, `rimeveil-ui`, `progression-ui`,
`dungeon-admission-ui`, `quest-ui`, `todo-bags-chime-ui`); the row selectors and
footer `data-action` buttons they use are kept, but a step that presses a quest
row while a quest page is open, or `#npc-quest-close` on a quest page, needs
Decline/Back first. The sections below describe earlier layouts.

## Mobile quest windows (Beta 1.47.3)

On narrow or short touch screens (width at most 900 px or height at most
500 px), the journal and NPC quest windows show a full-width quest list or a
full-width parchment, selected with **Quest list / Details** buttons. Tapping a
quest opens its details and moves focus to the visible parchment. Details also
reaches an NPC's greeting and services. Larger tablets and mouse desktops keep
both panes visible.

The action footer and header stay fixed while the list and parchment scroll
by touch. Navigation/buttons keep 44 physical pixel targets after the user's
window scale is applied. List and reading positions survive pane changes and
live quest updates; returning to the list clears item tooltips. Long quest
names wrap in the phone list. Accept, turn-in, confirmed abandonment, tracking
and Close retain the authoritative actions. A fresh opening starts on the list.
The game's existing landscape-only policy is unchanged.

Focused `tests/quest-mobile-ui.cjs` runs use the unchanged bounded wrapper:

- 667×375 English phone: **36 checks**.
- 844×390 Swedish phone: **37 checks**, including the new hand-written labels.
- 1024×768 touch tablet: **31 checks**, both panes visible.
- 1440×900 mouse desktop: **27 checks**, original two-pane layout.

These checks use genuine touch swipes, real server acceptance and item-reward
turn-in, fixed and visible footers, readable parchment, physical target sizes,
focus/reading retention and cancelled abandonment. Screenshots of the small
English journal and Swedish NPC turn-in were visually reviewed. Peak memory
stayed below 900 MiB under the 1.5 GiB/no-swap/one-CPU cap. Updated older journal
and quest-window checks navigate the phone pane buttons before selecting a
hidden list entry. No general suite, encounter simulation or server change.

Candidate: `/media/raid/valhallasc-data/quest-mobile-work`, branch
`fix/quest-mobile`. Logs: `/media/raid/valhallasc-data/quest-mobile-*.log`;
screenshots: candidate `test-results/touch/quest-mobile-*`. Client-only release;
all seven changed public client hashes match the checked files, public health
passes, and server PID `339798` is unchanged. Receipt: candidate
`test-results/quest-mobile-release.json`. Original client backup:
`/media/raid/valhallasc-data/quest-mobile-original-20261112T190933Z`. Changes
are included in the combined Beta 1.47.4 client release. Owner invoked finish
and deploy; all 17 combined public client hashes and both health endpoints pass,
with the server PID/executable unchanged. Finish receipt: candidate
`test-results/mobile-intro-finish-release.json`; session record: wiki
`10_projects:valhallasc_veyrheim_mobile_intro_20261112`.

## Matching quest-giver windows (Beta 1.47.1)

Quest-giver greetings, acceptance and turn-ins now reuse the journal's frame,
dark quest sidebar, parchment, book emblem and red bottom controls. Selecting
a title keeps the NPC's other offered quests available in the sidebar. Accept,
Complete Quest and Decline/Back live in the footer beside Close, outside the
scrolling details. Class-choice reward icons remain on the parchment with their
existing hover/touch behavior. Acceptance still waits for the server and closes
only on success; refused turn-ins retain the selected details and reason.

The conversation's normal parchment is wrapped in a `display: contents`
container outside quest mode. Merchant/services views remove the quest frame
classes and retain their existing stock/bag layout. Client-only presentation. Bag-space errors and dungeon-roll mail were
subsequently released in Beta 1.47.2; see `docs/todo-feedback-hats.md`.

Focused `tests/quest-window-ui.cjs` checks pass: 15 on touch 844×390 and 19 on
desktop 1440×900, including matching layout, reward tooltips, Enter acceptance,
the real fixed-item turn-in, class filtering, server refusals, a successful
chosen reward and return to merchant services. Screenshots of acceptance and
turn-in were reviewed. Logs/images: `test-results/touch/quest-conversation-*`
and `quest-{accept,turnin}-classic-*`. No broad suites or encounter tests.
All eleven changed public client hashes match, public/bridge health is healthy,
and server PID 183593 is unchanged. Swedish freshness, release notes, changed
JavaScript syntax and whitespace checks pass.

## Classic quest journal (Beta 1.47.0)

The owner's FileDrop reference `pvw69993.png` replaces the earlier accordion
journal with a dark, gold-trimmed frame and two independently scrolling panes.
Unfinished quests are grouped by region in the left pane. Ready turn-ins follow
them, then abandoned automatic quests and the folded completed history at the
bottom. Region groups can be folded. Clicking a quest (or using the arrow keys
on its row) selects the single parchment page on the right.

The page shows the description, authoritative objective counts, giver/location,
party progress, recovered memories, and the existing reward icons/tooltips.
Reading rewards never claims them remotely. Abandon, Track, Show Map and Close
sit along the bottom; the header X and outside dismissal use normal closing.
Abandon still requires confirmation and sends the existing server command;
Empty Seat quests remain protected. Recoverable automatic quests expose Restore
quest. Completed history disables active-quest actions. No Share button is
added because the game has no quest-sharing action.

Selection, group folds, reading position and list scroll survive progress
updates. Opening the journal selects the tracked quest or the first current
quest and folds completed/recovery history. Only the selected detail is built,
so long histories do not create hundreds of reward tooltips. The existing
window size control remains available. All new headings/controls are translated.

Focused private checks: `tests/quest-journal-ui.cjs` through
`scripts/test-touch-bounded.sh`, at tablet and phone sizes. Earlier tests below
describe the superseded accordion layout.

Validation: 21 focused checks each at desktop 1440×900 and touch 844×390
pass, including actual progress updates, reward tooltips, Track/Show Map,
confirmed abandonment, recovery, read-only repeatable history, keyboard
selection and outside dismissal. Swedish headings and controls also passed in
the private tablet client. Desktop and phone screenshots were reviewed against
the reference. Logs and images are in `test-results/touch/quest-journal-*`.
Peak scope memory was 917 MiB under the unchanged 1.5 GiB cap. Release notes,
Swedish freshness, changed-source syntax and whitespace checks pass. All ten
changed public client hashes match; both health endpoints are healthy and
server PID 183593 is unchanged. This is a client-only release.

**Beta 1.46.1:** unfinished quests precede ready-to-turn-in quests in both the
journal and the left-side tracker, even when a ready quest is tracked. Completed history stays last and includes claimed
repeatable quests. Named objective-completion toasts are described in
`docs/quest-feedback.md`.

Beta 1.19.0: pressing a window's backdrop invokes its normal close action.
The shared handler in `settings.js` also covers equipment, skills, social,
map, bank, settings, keyboard bindings, inspect, trade, rebirth, boss signs,
release notes and the GM test menu. Resize grips remain usable. Merchant
stock and borrowed bags form one group: pressing inside either keeps both
open; pressing outside closes the conversation and restores the bag DOM.
Pressing outside a valuable-sale confirmation cancels that confirmation.
Connection recovery remains an explicit choice. The pointer is consumed so
closing a window does not also move or attack in the world.

Beta 1.17.4 replaces fixed and class-choice item reward text with the same bag
icons in both NPC detail and journal. Only the hero's class choices appear.
The normal Inventory tooltip shows catalog stats/rarity/level/set information;
reward tooltips do not accidentally describe an upgraded copy already owned.
Touch targets match the bag's 44 px squares. First touch previews a reward;
second touch claims a ready choice at the NPC through the existing server
quest action. Full bags still pay nothing and leave the quest ready.

Beta 1.17.5 sends acceptance from the same click/Enter action and closes after
the authoritative dialogue confirms the quest is accepted. It waits for that
answer so a refusal can stay visible, retaining the quest detail/reason. A
pending request clears on close or timeout. Claim/turn-in and Decline retain
their existing behavior. Enter in an open modal activates its focused button
instead of opening chat; outside modals the existing chat key behavior remains.

Focused `tests/quest-window-ui.cjs` runs against the real private server under
`scripts/test-touch-bounded.sh`, with no grinding or balance simulations. It
checks physical reward sizes/artwork, hover and touch tooltips, Enter acceptance
and journal update, an actual server level refusal, class filtering, full bag
refusal, and a subsequent successful chosen reward. Mutations restore text
rewards or leave accepted conversations open.

Indexed verification: 26 assertions across the two touch target sizes, with
688 MiB peak under the unchanged cap. Both reward-text and accept-close
mutations fail as intended. Proof: `test-results/touch/quest-window-index.log`,
`quest-window-mutation-{icons,accept}.log` and the indexed export screenshots.

## Journal and conversations (Beta 1.27.0)

Every journal quest starts folded when the journal opens. Its native `details` /
`summary` row shows only `!` and the title; pressing it (or Enter/Space while
focused) opens the description, objectives, rewards and actions. Live progress
updates preserve open entries until the journal is closed. Completed quests use
the same rows inside the completed section, including recovered story memories.

**Abandon quest** asks for confirmation inside the expanded journal entry.
`quest_abandon` sends only the quest ID; the server drops only the sender's
unclaimed progress, gives no rewards, and saves immediately. Retaking at the
original giver starts objectives again (bring objectives still reflect owned
items). Previously claimed rewards cannot be abandoned. Repeatable completion
counts are retained, so dropping a new bounty never revokes an earlier unlock.
`Character.abandoned_quests` defaults to empty for older saves and prevents
automatic quests from returning each tick or after reconnecting. A dismissed
automatic quest can be recovered in the journal (Beta 1.27.1, below); NPC acceptance also clears that flag.
Current escorts and gauntlets end on abandonment; quest-bound hires leave via
the usual contract update. Partial memory/hold/bell state is cleared.

Conversations no longer include a Goodbye button. The header X (`npc-x`) is
the default focus and outside-dismiss target; Escape and grouped merchant/bag
closing still use the normal City close action.

Focused checks: `cargo test quest_journal_` and the bounded
`tests/quest-journal-ui.cjs` at the phone and tablet sizes. No encounter tests.

Validation: five focused quest-journal server tests, nine existing Eldmarr story checks, and 44 bounded browser checks at 844×390 and 1024×768 pass. Peak browser-scope memory: 664 MiB. Release build, Clippy with warnings denied, formatting, source syntax, generator byte stability, release notes and locale runtime checks pass. The Swedish catalog checker retains the same three pre-existing proper-name failures as the unchanged main checkout.

Beta 1.27.0 deployed 2026-10-27 with nobody online. Rollback backup: `deploy/backups/quest-journal-20261027T081549Z`. Public/bridge health, the running binary hash, all nine changed client asset hashes, SQLite `quick_check`, unchanged character/guest counts, test-flag exclusion and a warning-free service journal pass. No zone IDs changed or saved characters needed migration. Release binary SHA-256: `a342981a132870a2925f85ee486541788571093259e3a0ac1eb4ebb5f4fe1dfb`.

## Recovering abandoned automatic quests (Beta 1.27.1)

Automatically granted travel quests and Eldmarr directions now remain findable
under **Abandoned automatic quests** in the journal. Expand the section, expand
the quest and press **Restore quest**. This works from any zone and for quests
abandoned before this fix. The section and entries start folded, like other
journal entries. Restored quests return to the active list; recovery grants no
XP, gold or items and does not move the hero. Automatic-quest abandonment
notices point to this recovery control. Normal quests are still retaken at
NPCs.

`quest_restore` accepts only a known automatic quest explicitly abandoned by
that character. The server checks its automatic/minimum level and prerequisites,
rejects already-started/completed quests and obsolete story handoffs, accepts
through the existing quest rule, synchronizes progression and saves immediately.
The existing saved `abandonedQuests` list needs no migration or manual backfill.
Focused checks: `cargo test quest_restore_` and the bounded
`tests/quest-recovery-ui.cjs` (ordinary automatic travel and the actual `es_go_02`
handoff from another zone, at phone/tablet sizes).

Validation: two focused restoration server tests and 28 bounded browser checks pass at 844×390 and 1024×768, including restoring `es_go_02` remotely and the Swedish controls. Peak scope memory: 788 MiB. Release build, Clippy with warnings denied, formatting, changed JavaScript syntax, Swedish generation/locale runtime and release-note checks pass. No broad suites or encounter tests were run.

Beta 1.27.1 deployed 2026-10-27 with nobody online. Backup: `deploy/backups/quest-recovery-20261027T085701Z`. Public/bridge health, running-binary hash, all five public asset hashes, SQLite `quick_check`, unchanged character/guest counts, test-flag exclusion and the warning-free journal pass. No saved-character edits were needed. Release SHA-256: `d5fc17bc830f427d9598e5d7eb3773e37c763ce3d6926c6b876c481e1e937355`.
