# Party resource bars (1.15.11)

Party and raid members show mana, energy or rage below their health in the always-visible frame and the Party panel. Both bars include current/max values. Mana is blue, energy yellow and rage orange, matching the owner's HUD. Compact raid rows stack the two bars beside the name; resource names remain in the tooltip and accessible label while the bar shows the values. Offline seats hide the resource bar; reconnecting restores authoritative values.

`World::party_value` sends `resource`, `maxResource` and `resourceType` through the existing party-only half-second updates and full social state. Values use the same Character accessors as the owner's snapshot, including equipment bonuses. This includes hired mercenaries and members in other zones. No new polling, messages, storage or gameplay rules. The client repaints existing rows as values change and safely hides resources when an older executable omits the fields.

Verified on 2026-11-27: the focused native regression and bounded desktop and touch checks pass. Browser tests close bot sockets directly because the driver's disconnect health counter assumes all humans are driver bots. The browser player's real party packets determine offline/reconnected state.

Focused checks:

- `cargo test party_resources_follow`: all five classes, a higher-level mana maximum, a distant member, periodic updates, disconnect/rejoin and no party packets to strangers.
- `bash scripts/test-touch-bounded.sh tests/party-resources-ui.cjs`: actual private party packets, all resource types/colours/fractions, updates without replacing rows, Party panel, disconnect/reconnect and ten-member raid fit. `MUTATE=1` hides the resource bars and must fail.
- Normal release notes, Swedish, JavaScript syntax and whitespace gates.

Built on the released 1.15.10 priest Mend change and the 1.15.9 dungeon reduction. Deployment requires the matching executable and client. Candidate staging and verification are recorded in the release receipt; the public game is unchanged until deployment.

The subsequent owner request adds another 25% HP reduction for ordinary-dungeon bosses only, with raid enemies and all damage unchanged. The combined candidate supersedes the standalone resource-bar executable; see `docs/dungeon-difficulty.md` and `dungeon-boss-hp-staged-receipt.json`.

Released with the dungeon-boss HP change as **1.15.11-78b2254d**, merged and pushed
to main after the owner requested deployment. Public files and exact executable
verified; PID 1480788, all ten saved characters unchanged, all health endpoints
and clean journal pass. Receipt: `www/Valhalla/dungeon-boss-hp-release-receipt.json`.
