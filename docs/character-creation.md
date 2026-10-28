# Character creation

Beta 1.31.1, 2026-10-28, kept in the same release at the owner's request.

The preview has left/right buttons for all eight sprite facings. Turning ends
the current preview attack and redraws immediately, including with reduced
motion. Facing is shared when switching class or body, and does not change
gameplay facing or saved appearance. Buttons support keyboard activation and
44-pixel touch targets. Direction labels and controls support Swedish.

Armor and weapon lists offer their empty options as well as starter equipment.
**No gear** clears all worn preview layers. The owner confirmed that this should
also start the character unequipped, keeping all starter items in the bag.
Individual empty armor/weapon choices leave the other starter piece equipped.

The server still issues and owns starter inventory. `Online.newCharacter`
receives the chosen empty slots, and the first welcome sends the existing
authoritative `equip` action with `none` for those slots. The pending request is
stored in the character's guest/account layout slot until a snapshot confirms
it, so reconnects can finish an interrupted request. Confirmation checks armor
and weapons through class-specific look fields: these two slots are not in the
extra-slot `equipment` map. After confirmation the request is removed; later
equipment choices survive reconnects. No Rust or protocol changes are needed.

`bash scripts/test-touch-bounded.sh tests/creation-preview-ui.cjs` passes 399
focused checks across all five classes and both bodies at 1280 × 800 English and
844 × 390 Swedish. Covers all eight rendered facings, wrap/reverse/keyboard,
empty layers and selectors, touch targets, authoritative empty starts, every
starter item remaining in the bag, guest reconnect after re-equipping, and
account creation with an individual empty slot. The account branch can be run
alone with `--account-only`. Screenshots are in `test-results/creation-preview/`.
Real artwork was also reviewed at both sizes, including the female Priest's
front-left view without gear. Syntax, Swedish coverage, release notes and diff
checks pass. Public hashes match all six changed client files. The existing
server handles the equip action, so no rebuild or restart was needed.
