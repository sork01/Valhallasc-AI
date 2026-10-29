# Merchant selling

Beta 1.19.0: every NPC shop shows **Buys items** or **Does not buy items** below
the NPC's name. NPCs who sell supplies without buying loot previously rejected
every bag tap with the misleading item-specific message. Their message now
says **This person does not buy items. Sell to a merchant or smith.** The
detailed map's people directory labels buying merchants explicitly.
The server's buying rules and item protections are unchanged.

Choosing **Buy** opens a **Merchant** frame on the left and the existing inventory
bags on the right. Both windows have independent scale/corner-grip entries;
phone/tablet targets retain their 44 px floors. Stock uses two columns of five
slots, with ten items per page, bag artwork, names, gold prices and tooltips.
The header uses the NPC renderer to crop a circular portrait, not new artwork.
**Quests / services** returns to the NPC's ordinary gossip/services.

Beta 1.32.2 (same-version owner follow-up): every vendor opens at quests/services
with a **Buy** option. All stock is inside that shop: items, every bag tier and
mount purchases. Individual goods and the separate bag category are removed
from the greeting. Healing, repairs, crafting and other services stay beside
Buy. This supersedes the earlier automatic-shop behavior for NPCs without
quests. Purchases and sales keep an already-open shop in place. Own-class weapon
filtering, usable consumable tiers, bag-size restrictions and authoritative
purchase actions remain. Mounts use the existing catalog levels, ownership and
required-item checks.

Click a loose bag item or drag it onto the merchant to sell its stack/copy.
The server's available list selects the exact next loose copy, excluding worn
copies, starter/GM gear, quest items and bound licences. The bag tooltip shows
the exact server-quoted proceeds, including rebirth rounding. **Sell all junk**
sends one batch of common (gray) gear and materials, preserving green and up.
The old You give/You receive basket is replaced by direct sales.

Any epic or legendary sale still opens the confirmation naming those items in
rarity colors and the exact total. Cancel/Escape preserves ownership; an orange
item gives Cancel initial focus. Smiths have anvil controls for one-piece repair
and **Repair All Items**, using existing server quotes. The coin pouch sells
junk. The single buyback square shows the last sold item and opens **Buyback**;
the folder tabs switch between stock and the retained last twelve entries.

Closing restores the same bag DOM to its ordinary character/bags workspace.
Purchases, sales, repairs and buyback remain existing server actions; no Rust,
world data, database schema, pricing or balance change is part of this release.

## Protocol and prices

- `shop_open {npc}` returns current sellable copies/stacks and buy-back rows.
- `sell_batch {npc, items:[{item,copy?,quantity}]}` sells 1–256 entries atomically.
  The picker addresses gear copies by id, one copy per line; non-gear uses a
  stack quantity. Omitting the gear id retains first-loose-copy selection.
- `buy_back {npc,id}` returns one retained row (one gear copy or sold material/
  consumable stack) for exactly what the merchant paid.
- `shop` replies include `ok`, `notice`, exact `paid`/`spent`, the current bag
  state, `available`, `goldPercent`, and `buyBack`. `changed` distinguishes a
  committed transaction from opening or refusing one. An invalid merchant,
  distance, defeated hero or travelling hero closes the view.

Sale values remain the existing `Item.sell` rule: a rare catalog copy merged
to epic sells for twice the base; other rarities retain their catalog price.
Wear and refinement do not lower or raise the price. The existing rebirth gold
bonus applies per selected entry with the same nearest-integer rounding as
`sell_item`. Server quotes provide each copy's base and the gold percentage;
the basket displays that exact calculation. A stale selection is revalidated.

The server checks the current NPC, zone, moving NPC position, 2.8-tile reach,
health, quantities, copy ownership, equipped allocation, duplicates and gold
arithmetic. It stages the complete character and buy-back changes, writes the
character with a SQLite transaction, then publishes the result. Refused batches
and failed saves change neither bags, gold nor buy-back. Service mutations
retain the 0.5-second cooldown. The WebSocket frame limit is 32 KiB so a full
256-entry basket fits. No client-supplied price or gold total is accepted.

Legacy `sell:<item>:<quantity>` and `sell:materials` interactions remain usable
and populate the same buy-back list.

## Buy-back lifetime

Each connected player retains the last 12 sold entries **per merchant** in
server memory. Gear has one entry per physical copy; a stack keeps its sold
quantity and total price. Older entries are evicted first. Closing the window,
travelling or visiting another merchant preserves the list; logout or server
restart clears it. Other players and other merchants cannot retrieve it.

Gear returns with its original id, rarity, rolled stats, rank, wear and
`tradeUntil`/`tradeWith` fields. Its old trade expiry remains absolute. Returned
copies append after existing copies, preserving equipped allocations. Funds,
bag room, stack overflow and duplicate-copy checks run before restoring it.

## Validation

Focused Rust filter `shop_` covers batch payment/persistence, merged epic and
rebirth pricing, exact copy restoration, rollback/protected items, duplicate
requests, arithmetic limits, merchant isolation, twelve-row eviction, logout,
legacy interactions, insufficient funds, full bags and injected save failures.
`tests/shop-sell-ui.cjs` runs real English/Swedish merchant interactions in a
private Chromium world. `MUTATE=1` bypasses the valuable-item confirmation and
must fail. Release version: **Beta 1.14.33**.

Focused verification on 2026-10-24: six Rust tests, 49 real-sprite Chromium
assertions (English/Swedish), Clippy with warnings denied, formatting, changed
JavaScript syntax, the complete Swedish catalog and 21 locale assertions pass.
The mutation bypassed the valuable-item gate and failed waiting for its popup,
after nine assertions; it used a routed private-client script only. The final
client artifact is `.tools/shop-sell-worktree/test-results/driver-N0S9d2/`.

## Release

Deployed together on 2026-10-24 at 18:40 UTC, source `b60a333`,
**Beta 1.14.33**. Backup: `deploy/backups/shop-sell-20261024T183043Z`
(previous binary, previous client, consistent before/stopped SQLite snapshots
and installed candidate). No players were online during the restart.

The final release binary passed a private merchant open/sell/payment/buy-back
probe before installation. After restart, public and bridge health, all seven
changed public client hashes, the live executable hash, SQLite `quick_check`
and absence of test flags/warning journal entries pass. Counts remain
27 characters and 15 guests. No world data, copy IDs or DB schema changed.
Release proof: `test-results/shop-sell-release.json`; installed executable
SHA-256: `aab9e6aad01cd8fb3069700855a219c92cc07b12b529f560c4b7bfa949049914`.

## Merchant frame follow-up (Beta 1.18.0)

Owner specification: `TODO.md` `UI-MERCHANT-FRAME`. Focused capped private-client
suite: `tests/shop-sell-ui.cjs`; mutations restore the missing bag dock or bypass
valuable confirmation. The touch window audit now targets the merchant frame,
its adjacent bags, the valuable-sale popup and the repair view. Earlier results
above describe the retired basket release, not this frame's validation.

Final indexed merchant-frame run: 47 assertions at 844x390 and 1024x768,
including Swedish tabs, 44 px controls, tooltip quotes, two-window bounds at
UI scales 60%, 80% and 150%, exact rebirth-adjusted payment, equipped/quest/blue+
protection, orange Cancel focus, drag selling, exact gear-copy buyback, individual
and full repair, stock purchases, pagination and merchant isolation. Peak RAM:
670 MiB inside the unchanged 1536 MiB cap. Native pointer checks caught a
resize grip covering Goodbye; the footer now reserves space for that grip.

Fixture timing: a shop reply updates Inventory before the next hero snapshot.
Wait for the returned gear ID in the authoritative snapshot before comparing
all copy fields. The page buttons use arrow glyphs, not the key-hint token
opener: that opener can cause the old hint observer to rewrite unchanged text
in an endless mutation loop. The stalled private audit was stopped in its own
cgroup; no production process was stopped or restarted.

Proof: `test-results/touch/merchant-index.log`, merchant mutation logs, and
`merchant-*.png` in the indexed RAID export. Browser checks remain bounded by
`scripts/test-touch-bounded.sh`. No full suite or balance sweep was run.

The Merchant/Buyback folder tabs occupy the final footer row, below the purse
and conversation actions. The borrowed bag window registers independently only
while docked at the merchant; close unregisters its observer/grip and clears
its own scale before restoring it inside the normal equipment workspace.
This prevents a nested scale after a merchant visit. The dedicated layout
check covers both panes, footer/tabs, grip reachability and restored bag scale.

Final footer/restore layout check: 26 additional assertions at both sizes,
603 MiB peak. Both merchant mutations fail their intended assertions (collapsed
columns and bypassed valuable confirmation). All eleven public client files
match the git index; public and bridge health report OK. Hash list:
`deploy/merchant-assets.txt`; proof `merchant-public.txt` and
`merchant-layout-index.log` under `test-results/touch/`.


## Stable merchant receipts (Beta 1.18.1)

Sale confirmations previously added a row above the catalog, moving it, then
an empty shop refresh cleared the text. Merchant messages now use the existing
`#npc-notice` status below the controls, with 36 physical pixels reserved even
when empty. The latest nonempty result survives stock/inventory refreshes and
is replaced by the next meaningful result; closing/reopening clears it. City
leaves merchant status ownership to Shop so a dialogue redraw cannot erase it.
Long notices scroll inside the same fixed space. Gossip/quest notices keep
their existing behavior.

Focused indexed `tests/merchant-notice-ui.cjs` passes 18 assertions at 844x390
and 1024x768, including real sales, empty refreshes, frame-by-frame bounds of
stock/tools/tabs/status, and clearing on a new visit. Peak 606 MiB within the
unchanged 1536 MiB cap. All five changed public client hashes match the index;
both health endpoints report OK. Proof: `test-results/touch/merchant-notice-index.log`,
`merchant-notice-public.txt` and screenshots in the indexed RAID export.


## Gray-only junk (Beta 1.18.2)

Owner requested that Sell all junk keep green items. The shared `isJunk`
predicate now selects only common gear/materials, for both the batch and the
button's enabled state. Green, blue, purple and orange items remain in the
bags; individual green sales still use the ordinary merchant action.

The gray-only focused check passes seven assertions at the phone viewport,
including protected green/blue/purple/orange copies, equipped gray protection,
exact gray-only payment, one batch, disabled-empty-junk state and a manual green
sale. Peak 589 MiB under the unchanged cap. Receipt mutations fail on shifting
geometry and lost text; the junk mutation restores green inclusion and fails
preservation. Proof: `test-results/touch/merchant-junk-index.log`,
`merchant-junk-mutation.log` and `merchant-notice-mutation-{1,clear}.log`.

Focused follow-up validation: `bash scripts/test-touch-bounded.sh tests/client-followups-ui.cjs` checks Buy on potion, bag, crystal and mount vendors, complete paginated stock, actual potion/mount purchases, service access and no individual stock buttons on the greeting.
