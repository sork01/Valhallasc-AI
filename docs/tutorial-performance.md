# Tutorial inventory performance (silent fix, 2026-11-20)

Owner report: FileDrop `Valhalla-tutorial-perf-fix.md`, profiling the Android
WebView client on an AYN Odin 3. It attributes 76% of CPU samples to tutorial step
selection, with an incomplete tutorial scanning 7,241 catalog items twice and
calling `Inventory.bagQuantity()` for each. Its linear definition lookup nested
inside that scan makes the work quadratic. The measured device symptoms were
about 13 fps and roughly 93 ms per tutorial render. Those device observations
come from the report; this change has not been re-profiled on that device.

`Inventory.definition()` now indexes IDs once and refreshes the cache on catalog
array replacement or length changes. The production catalog has no in-place ID
rewrites or equal-length object swaps; future callers making those changes must
replace the array. Ordinary item-property changes remain visible through the
cached object references. Duplicate IDs keep their original first-match behavior.

Quantity lookups use a Map rebuilt at every changed authoritative inventory
update, including `updateBags()` replies before a snapshot, in-place quantity
changes supplied to `update()`, item removal and character changes. There is only
one stack-assignment path. No cached quantity is inferred from a previous player.
Duplicate stack entries keep the old first-match behavior.

`Inventory.ownedItemIds()` exposes distinct positive stacks in original catalog
order. Only those IDs are visited by the tutorial's gear and consumable checks.
Catalog order matters: the first compatible item drives gear auto-completion;
using bag order would change behavior after sorting or moving items. Starter,
class, level, worn-quantity and food/potion filters are unchanged; raw fish do not
start the old consumables milestone. No throttling delays the arrows or controls.

Validation: `node tests/tutorial-inventory-performance.cjs` passes 27 checks of
the complete production Inventory/Tutorial scripts with a deterministic DOM.
Checks cover index invalidation, duplicate/missing IDs, bank replies, worn gear,
quantity updates/removals, character switching, eligibility/priority, equipment,
food/potions, stats, skills and the MORE spirit step. Warm lookups and repeated
incomplete tutorial renders assert zero catalog-entry or stack-entry scans; these
complexity checks do not depend on machine speed.

`node tests/tutorial-inventory-performance.cjs --mutations` catches seven faults:
linear item and quantity lookups, stale catalog append/replacement caches, stale
quantities, changed item order, and restoring full-catalog tutorial scans.
`--baseline` benchmarks the pinned pre-fix implementation at `437d61b5` rather
than a moving HEAD. With the same 7,241 items, 20 owned material stacks and four
completed milestones, its tutorial state is byte-equivalent to the fixed state
(no active tip, still enabled). Host VM measurements for 20 renders averaged
202.870 ms before and 0.095 ms after; a complete catalog bag-quantity loop measured
575.171 ms before and 17.190 ms after. These are non-browser host measurements,
not Android frame-rate claims or timing assertions. Raw reports are in
`test-results/tutorial-inventory-performance/`.

Existing non-browser inventory/fishing stacking, tooltip, rod, raw-meal, junk and
rare-sale checks pass, as do all 90 fishing progression client checks. Existing
`tests/tutorial-ui.cjs`, `tests/tutorial-more-ui.cjs`, `tests/inventory-ui.cjs` and
`tests/gear-cells-ui.cjs` remain browser checks awaiting an approved test host;
the production-host restriction remains in force. Android rAF/frame-rate
verification must be done on the actual device. No browser run is claimed.

No world data, server binary, save schema, label or release-note change. Release
the client only; the achievement binary remains staged at the owner's request.
