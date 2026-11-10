# Aggro range follows the level gap (`AGGRO-LEVEL`, Beta 1.40.3)

Owner, 2026-11-10: monsters above your level notice you from further away, monsters below your level from nearer.

## Rule

`aggro_radius(awareness, monster_level, hero_level)` in `server/src/world.rs`, used by the nearest-hero scan in `World::update_slime`:

- Scale = `1 + 0.12 * (monster level - hero level)`, limited to **x2.0** above and **x0.35** below (reached at +8.3 and -5.4 levels).
- Floor: never under 3 tiles (or the kind's whole radius if that is smaller), so a gray monster still attacks a hero who walks right up to it.
- `awareness` is the fourth number of `Slime::attack_profile` (or the Cathedral catalog profile), unchanged.
- It is measured **per hero**: the check runs for every player in the zone against that player's own level, then the nearest one in reach is chosen.
- A monster that is already chasing (`was_chasing`, `s.target`, the 9-tile follow rule and the leash) is unchanged.

## Scope

Every open-world monster, **elites and bosses included**. Dungeon and raid instances (`instance_at(zone)` is some) keep the fixed radius, so the dungeon and raid calibration is untouched. Enemy levels still roll +-2 (`VALHALLA_LEVEL_SPREAD`), so two monsters of one kind differ by a few percent.

## Consequences to remember

- The elite placement rule ("awareness + 3 tiles from every road, place and person", checked in each zone's `design()` and tests) uses the **base** radius. An elite above a hero now reaches up to twice that, so a road that was clear for an on-level hero can pull an under-levelled one. Elites are fixed-level, so this only matters for heroes below the elite.
- Cairnspine's Behemoth (12.6 tiles from the Frostwake seam, awareness 17) and Storm Condor (20.1, awareness 19) are the known close ones.
- Hired mercenaries and ambient adventurers are players for this scan and count by their own level.

Checks: `cargo test aggro_level` (formula and the in-world lock-on at both radii).
