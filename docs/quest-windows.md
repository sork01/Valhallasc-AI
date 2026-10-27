# Quest rewards and acceptance

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
automatic quest becomes available at its giver and acceptance clears that flag.
Current escorts and gauntlets end on abandonment; quest-bound hires leave via
the usual contract update. Partial memory/hold/bell state is cleared.

Conversations no longer include a Goodbye button. The header X (`npc-x`) is
the default focus and outside-dismiss target; Escape and grouped merchant/bag
closing still use the normal City close action.

Focused checks: `cargo test quest_journal_` and the bounded
`tests/quest-journal-ui.cjs` at the phone and tablet sizes. No encounter tests.

Validation: five focused quest-journal server tests, nine existing Eldmarr story checks, and 44 bounded browser checks at 844×390 and 1024×768 pass. Peak browser-scope memory: 664 MiB. Release build, Clippy with warnings denied, formatting, source syntax, generator byte stability, release notes and locale runtime checks pass. The Swedish catalog checker retains the same three pre-existing proper-name failures as the unchanged main checkout.

Beta 1.27.0 deployed 2026-10-27 with nobody online. Rollback backup: `deploy/backups/quest-journal-20261027T081549Z`. Public/bridge health, the running binary hash, all nine changed client asset hashes, SQLite `quick_check`, unchanged character/guest counts, test-flag exclusion and a warning-free service journal pass. No zone IDs changed or saved characters needed migration. Release binary SHA-256: `a342981a132870a2925f85ee486541788571093259e3a0ac1eb4ebb5f4fe1dfb`.
