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

## Guest choice and progression warning (silent update, 2026-11-20)

Selecting **Play as guest** first warns that access to guest progression depends
on this browser. Clearing its data or losing access to it can make the character
and progress inaccessible. The player can cancel or continue; an account is
recommended for access across devices. Guest characters really are saved on the
server, so the warning does not incorrectly describe their saves as local-only.
English and hand-written Swedish text are supported.

A fresh guest opens the job/body/appearance creator, even when an obsolete cached
look exists without any saved guest key. Returning guests see all characters
saved for this browser plus **New character**. Selecting a saved character uses
its existing key; creating another job preserves every previous guest and its
layouts. The picker does not refresh, change or delete a remembered account
session. Account limits, levels, deletion and GM controls retain their own rules.

`node tests/guest-character-choice.cjs` passes 44 non-browser checks of the real
Account/Online scripts, game sign-in and creation handlers, saved storage, chosen
join packets, warning text/cancel/Swedish, account isolation and reconnect helpers.
`MUTATE=auto|warning|picker|refresh` each fails its intended assertion. Unrelated
browser fixtures acknowledge only this exact warning; native dialogs remain
available with `TEST_GUEST_WARNING=1`, and unrelated confirmations are untouched.
41 reconnect fixtures (plus two direct-Playwright guest entry fixtures) now explicitly choose their saved current guest through
`tests/lib/guest.cjs`; the account integration test asserts the returning picker.
The new native-dialog/creation/reconnect suite is
`tests/guest-character-choice-ui.cjs`. Browser suites await an approved test host
under the existing production-host restriction. No browser run is claimed.

This is client-only and needs no server build or restart. Version 1.2.0 and its
release notes stay unchanged. The achievement server update remains staged at
the owner's explicit request; releasing this client does not activate it.
