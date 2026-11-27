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


Deployment: source `437d61b5` is pushed to main and silently released as
`1.2.0-437d61b5`, then retained in latest client `1.2.0-f8031984`. All three
changed public files (account, game, Swedish) matched the clean release checkout;
public health passed and server PID/executable `1250668` stayed unchanged.
Receipt: `www/Valhalla/guest-choice-release-receipt.json`. Previous client
`1.2.0-cc1c12fa` remains available for rollback. No public guest was created.
Wiki: `10_projects:valhallasc_guest_character_choice_20261120`.

## Playable Mothkin (1.8.0)

Choose Human or Mothkin in the creator. Mothkin come from the Moonspore
Canopy and have dusk skin, pale cheek markings and feathered antennae.
Both bodies and all five classes are available. They start with the usual
class equipment and Greenmeadow arrival. The server saves the race with
the character's appearance. Earlier guest and account saves default to Human.

The game uses the existing head pose for each frame to place the antennae
and markings. Headgear covers the antennae. The artwork lives in the
two-layer PixelFlow sprite `a3cadd60feee1497`. Run
`python3 scripts/make_mothkin_art.py export` to export editor changes and use
`verify` to compare the committed atlas with PixelFlow.

## Playable Tidekin (1.9.0)

Tidekin come from Rán's Deep. They have four sea-green skin shades, finned
ears and pearlescent gill markings. They can use either body and any class,
with ordinary equipment, movement, skills and stats. The fin ears fit the
existing head poses and disappear under headgear. The two-layer PixelFlow
source is `80a958a4a7378e1d`. Run `python3 scripts/make_tidekin_art.py export`
to export editor changes or use `verify` to compare the atlas with PixelFlow.

## Playable Gnomes (1.10.0)

Gnomes from the Obsidian Orrery have brass clockwork fittings and a compact
frame. The game draws the dressed sprite at 76% width and 67% height around
its foot anchor. Both bodies and all five classes use the usual class
equipment, skills, stats and collision. On a mount, the compositor resamples
the rider's color and depth around the saddle before layering the rider over
the mount. The Assassin's Shadowstep afterimage uses the same foot-relative
scale. Headgear covers the brasswork.

The PixelFlow source for the brasswork is `47c3c9871c597c7a`. Use
`python3 scripts/make_gnome_art.py export` or `verify`.

## Racial passives (1.11.0)

The creator shows the selected race's passive. The Character pane shows
the saved character's passive. Races keep the normal class skills and combat stats.

| Race | Passive | Effect |
| --- | --- | --- |
| Human | Resourcefulness | 5 percentage points more quest coin, added to the Rebirth coin bonus. The quest offer and journal show the calculated payout. |
| Mothkin | Moonlit Forager | Flower gathering runs at 115% speed if started from 20:00 through 04:59 on the world clock. The speed is set when the pick starts and applies to the pick's duration. |
| Tidekin | Water Sense | Waiting for a bite in water takes 90% of the usual time. It multiplies the existing bite-rate modifiers and leaves the casting and bite windows, loot, and lava timing at their normal values. |
| Gnome | Haggler | 10% off NPC stock, equipment repairs, and Spark Travel. NPC stock includes bulk orders, fitted bags and mounts sold at shops. Spark fares apply Haggler after Rebirth. |

Coin bonuses and discounts round to the nearest copper. A positive price
costs at least one copper. Stock discounts are applied per unit and repairs
per physical copy, so the bulk totals match the displayed prices. Vendor
offers and shop replies quote the same discounted amount used by the
purchase action. Buyback charges the exact original sale amount.

## Race checks

`tests/playable-race-art.cjs` checks the races in the real compositor and
writes their front-and-back renders. Its `--gnome`, `--tidekin` and `--mothkin` options
check one race, and `--preview-only` selects the body and class used in that
race's preview. The Gnome check covers the dressed sprite on foot and on
horse and seahorse. `tests/playable-race-creation-ui.cjs` checks selection, drafts
and reconnect in desktop English and touch Swedish. Run both through
`scripts/test-touch-bounded.sh`.
