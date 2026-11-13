# Spark Travel

A hero who has talked to a travel master can fly from that station to any other discovered station, at three times
walking speed, for 20 gold per leg. In the air the hero cannot be attacked, attack or pick anything up.

## The network (`scripts/spark_routes.py`)

Every station is an NPC with `travelStop` (its name) and `travelLinks` (the stations one leg away). The links are
not written by hand any more: `spark_routes.py` runs last in `sync-world` and replaces every list with one rule.

- Two stations in the same zone are linked. The leg is a straight flight over the zone.
- For every two-way crossing between two zones (seam, vault, gate or walked path, never an `after_clear` door),
  every station of either zone is linked to the station nearest the crossing on the other side, and the two zones'
  main hubs (the station inside the zone's `city`) are linked to each other.

A leg between two zones is flown station, crossing, station, so every link has a crossing by construction. Zone
generators and designs may still write `travelLinks`; whatever they write is replaced at the end.

- `python3 scripts/spark_routes.py` rewrites `world/map.txt`; `--check` fails when the map is stale.
- `--report` prints the size of the network and how direct its routes are, measured against a network where every
  pair of stations in neighbouring zones is linked. On 2026-11-13: 94 stations, 478 links, the
  median route within 1% of that yardstick, 95% of routes within 8%. Against the network before Beta 1.50.0 the
  average flight is about a quarter shorter and takes fewer legs (3.4 against 4.2), so it also costs less.

## Routes (`server/src/world/travel.rs`)

`spark_routes(from)` finds the fastest route to every station: the least flight in tiles, where one more stop has to
save `LEG_HANDICAP` (20 tiles, about a second and a half) to be worth making. A leg between two zones uses the
crossing that makes the shortest flight (`spark_leg`). The fare is 20 gold per leg of that route, and every stop on
it must be discovered. Before Beta 1.50.0 the server took the first route with the fewest legs it found, which for
about a quarter of all pairs was more than 15% longer than the best one over the same links.

Tests: `cargo test spark_` (the routes are checked against an all-pairs search written another way; the links
against the crossings in the map).

## Choosing a destination (`client/worldmap.js`, Beta 1.50.0)

The travel master's conversation has one row, Spark Travel. It closes the conversation and opens the world map in
travel mode (`WorldMap.showTravel(npc, offers, discoveredStops)`): zones cannot be opened, and every station is a
marker placed with `atlasPosition`.

- Gold: the station the hero stands at. Bright: can be flown to now. Grey: discovered, but a stop on the way is not,
  or the purse is short. Small dark dot: not discovered; shown only where the hero has charted the ground.
- Hovering or focusing a station shows a card with its name, the stops on the way, and the fare or the reason it
  cannot be reached, and draws the route through its stations. All of that comes from the server's `travel` offers.
- A mouse click or Enter on a bright station starts the flight. A finger first pins the card, which then has a Fly
  button.
- A refused flight reopens the conversation with the server's reason.

Test: `bash scripts/test-touch-bounded.sh tests/spark-travel-ui.cjs` (`MUTATE=fare` and `MUTATE=touch` must fail).
