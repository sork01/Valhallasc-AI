# Christmas, seasonal titles and mount speed validation — Beta 1.35.0

Implemented as private commit `2a5e52e`, merged/deployed on main as `04e8ecd`.
Private source branch `feat/christmas-and-seasonal-rewards`, based on `bb7ba78`,
at `/media/raid/valhallasc-data/skaldholm-archways-work`. No new zones,
private-copy IDs, save fields or database schema/migration are needed.

- Seven focused Christmas Rust checks cover exact calendar boundaries, five
  fighters/hires, mixed levels 5/10/15/20/26 selecting 26, frozen membership and
  scaling, nonleader quest-holder summoning, outsiders, wipe/reset/expiry,
  daily rollover, independent controlled 5% outcomes and exact threshold,
  duplicate attempt/ownership protection, full bags and shared city claims.
- Six existing Halloween encounter checks pass after the shared engine refactor.
- Seven seasonal/history checks pass, including partial/full set completion,
  legacy seasonal claim reconciliation across years, save persistence and exact
  suffix rewards. The catalog check passes at 104 achievements / 2,250 points.
- Actual movement checks cover all seven mounts and five classes at precisely
  1.6 times walking speed. The existing horse purchase/level, combat and dungeon
  dismount/persistence check also passes. Input must be refreshed each tick in a
  direct movement fixture; walking gates require outward intent.
- Release-binary private MCP `christmas`: ten checks, real hired summon/kill,
  personal daily attempt, cross-city claim, server restart, off-season cleanup
  and forged summon refusal. Artifact `test-results/driver-pJ5fRi/report.json`.
- Thirty distinct browser checks across the focused city/hunt/title portions:
  actual errands in all four cities (`driver-b1SPJQ`), hired level-99 summon,
  daily kill/roll/cross-city claim and exact Merry suffix (`driver-dJurtF`),
  expiry/reconnect, exact Hallowed suffix and Swedish client (`driver-x1lwWA`).
  Initial runs exposed test-fixture issues (uninitialized packet, an open
  achievement overlay, and resetting the creation settings on reload); these
  were corrected, then only unfinished portions were run. No product failure
  remained and no passed encounter/errand sequence was needlessly repeated.
- Bounded real-art `tests/christmas-art-ui.cjs`: **57 checks**, ten class/body
  rigs, eight facings and both gaits, saved sources and protected rider pixels,
  five clear-edged Grinch clips, all four costumed cities and no camp dressing.
  Artifact `test-results/driver-BzwhxT`; native city pictures derive from it.
- All-target Clippy with warnings denied, Rust formatting, changed JS/Python
  syntax, release-note guard, Swedish freshness and 23 Locale checks pass.
  The broader Swedish catalog has only its three prior proper-name false
  positives (Laleh/Asha/Veya); no new missing translation.
- Two final sync-world runs are byte-stable. Map SHA-256:
  `a96cc159a87cf479ef99c1c3d95f7045cebe141650f81e14028fc9dd1a642c6b`;
  client world:
  `0225a1d3eed7dfa4f66389db024982fbedc6f2e63acf6d2286f8c1b7cac08e0f`.
  Semantic comparison preserves all 47 file zones, prior ordinary spawns,
  portals, roads, city entrances/bounds and arrivals. Only ten Rimeveil scenery props
  (six trees, two rocks, two bushes) retire for the new ritual clearing.

All sprites were created through PixelFlow. Grinch source
`7b06061b960f7f72`, five clips, 96×96 / anchor (48,90); sixteen reindeer source
IDs are retained in `client/assets/mounts_sprites.txt`. Existing mount IDs and
artwork are unchanged. The reindeer uses the established horse seat/depth
contract and a forward-running source gait. Grinch native exports crop rather
than shrink the full frame, with death motion contained within each frame.

No full suites, grinding, encounter timing or balance sweeps were run. The
owner retains timing/win-rate evaluation; elite health/enrage are provisional.

## Requested pictures

Six PNGs uploaded to [FileDrop](https://gunning.se/filedrop/), with matching
source/destination SHA-256. Cities are direct native game-canvas captures,
without HUD overlays; portraits use the saved exported game artwork.

| Stored filename | SHA-256 prefix |
| --- | --- |
| `valhallasc-christmas-alderhaven.png` | `dd7d5b13da7d599a` |
| `valhallasc-christmas-skaldholm.png` | `482f1c9cfb46a554` |
| `valhallasc-christmas-nacrehold.png` | `5a696d42fe6ace99` |
| `valhallasc-christmas-asterion.png` | `e52dc097739bbecb` |
| `valhallasc-christmas-grinch.png` | `4fd20d3dc42f30ad` |
| `valhallasc-christmas-reindeer.png` | `1fe3920aa936f4ee` |

## Deployment

**Beta 1.35.0 is deployed and verified**, 2026-11-02 at 18:43 UTC, with nobody
online. Source `04e8ecd`; backup
`deploy/backups/christmas-1.35.0-20261102T183014Z`, containing the previous live
executable saved before building, consistent online/stopped SQLite snapshots,
previous changed client files and saved JSON hashes. No migration was needed.

Public and bridge health pass. The running executable exactly matches the
optimized release, SHA-256
`d8dadaf95b2a1dfec874928e1b93fe2ac1aa02323df2ddbb70fa0327785e15e9`.
All **17 changed public client files/assets** match local hashes. SQLite
quick_check is `ok`; **37 characters / 23 guests** and every saved character JSON
hash are unchanged. Test flags and journal warnings/errors are absent; no
public test guest was created. The additional legitimate guest since the
previous release was included in this release’s pre-build backup/audit.
Receipt: `test-results/christmas-release-20261102T184323Z.json`.

Christmas activates automatically on December 15 and retires at December 29
midnight (Stockholm). Today’s Halloween remains active through November 9;
permanent Hallowed/Merry rewards and the 160% mount speed are installed now.

## Attachment correction — Beta 1.35.1

Owner reported floating NPC hats and incorrectly oriented house ornaments.
The former crown height used `NpcArt.top`, the full silhouette including flags,
lanterns, staffs and other props. Christmas now uses a cached, frame-specific
head socket derived from the actual exported skin/headwear pixels. It follows
individual scale and mirrored walking/talking poses; scarves attach below the
face, and nameplates clear the hat. No art or gameplay data was regenerated.

Elevated wreaths/garlands now use the +Y house-front wall projection (1:2 slope),
with separate cache variants for mounted/free-standing drawings. Ground props
stay upright. Authoritative world geometry, quests and calendar remain intact.

Bounded `tests/christmas-attachments-ui.cjs`: **14 checks**, **103 NPCs / 2,884
poses**, actual brim/body pixel contact, idle/talk/both walking directions, all
four cities, wall foliage slope and warmed cache separation. The old placement
floats in **108** sampled poses. Contact sheets and in-game views inspected; no
browser errors. Artifact `test-results/driver-nf21rF`. Focused client-only fix;
no server restart, database work or encounter tests needed.


Beta 1.35.1 is live from source `b6a138e` (private `b7663a0`). All **six changed
public client hashes** match; public/bridge health pass, with the existing
Beta 1.35.0 server/PID untouched. Receipt:
`test-results/christmas-attachments-release-20261102T185833Z.json`.

At the owner’s request, the four city pictures in FileDrop were refreshed to
show the corrected hats and wall ornaments (current hashes in the table above).
Two additional close-ups were uploaded and SHA-256 verified:

| Stored filename | SHA-256 prefix |
| --- | --- |
| `valhallasc-christmas-npc-hats-fixed.png` | `dbb31b46cf677a2b` |
| `valhallasc-christmas-wall-ornaments-fixed.png` | `c5c4d898d2c8f5c7` |

Fresh city/house captures: private `test-results/driver-HvNieR`; NPC contact
sheet: `test-results/driver-nf21rF`. Grinch and reindeer art is unchanged.

Beta 1.35.2 projects building doors/windows onto their actual walls. The four
city and wall-detail FileDrop pictures were refreshed again (current hashes
above); the original Grinch/reindeer and hat sheet stay unchanged.
See [building-facades.md](building-facades.md) for the complete rendering audit.

Beta 1.35.3 refreshes the city/wall pictures with corrected Nacrehold shell
roofs/pillars and Alderhaven ledges; current hashes are above. Additional gallery
`valhallasc-nacre-shells-pillars-fixed.png`; see [nacre-roof-geometry.md](nacre-roof-geometry.md).

Beta 1.35.4 removes residential address plaques and floats named service/shop
signs over roofs. City/detail/building galleries in FileDrop were refreshed
again; current city/detail hashes are above. See [building-facades.md](building-facades.md).
