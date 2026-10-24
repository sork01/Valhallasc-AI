# Merchant selling

Every NPC with `buys` has a **Sell** gossip row. The conversation's resizable
window contains a trade-style basket: pick loose bag items and quantities,
review **You give** and **You receive: N gold**, then confirm once. Rarity chips
filter the picker. **Sell all junk** adds common/uncommon gear and materials;
it never adds blue, purple or orange items. Items can be removed before payment.
Equipped copies, starter/GM gear, quest materials (`material`, `sell: 0`) and
bound mount licences cannot be sold. Fitted expansion bags are outside inventory.

Any epic or legendary copy in the basket opens a second dialog naming those
items in their rarity colors. **Yes, sell** performs the batch; Cancel/Escape
returns to the basket. If any item is orange, Cancel receives initial focus.
The popup is dismissed when ownership or the merchant view changes.

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
