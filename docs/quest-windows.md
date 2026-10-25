# Quest rewards and acceptance

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
