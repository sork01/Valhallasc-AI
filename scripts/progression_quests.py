#!/usr/bin/env python3
"""The progression quests: one arrives by itself every five levels and sends you on to the next area.

Each one lives in the quests of the zone it sends you to, so its giver (the captain of that zone's camp)
is where it is handed in, and carries `autoLevel`: the server accepts it for the character once they
reach that level (nobody offers it). Its one objective is `reach`: it completes when the character stands
in, or has already explored, the zone named by `target`.

The generators import `for_zone(name)` and append the result to their quest list, so a regenerated zone
keeps its progression quest. Run this file on its own to patch the quests into world/map.txt without
regenerating any terrain; it replaces earlier copies, so it is safe to repeat. Then run
node scripts/sync-world.cjs and rebuild Rust.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
LEVEL_XP = json.loads((ROOT / 'world/levels.txt').read_text())  # XP to next level; a quest pays a tenth

# zone name -> (id, title, giver, level, gold, description, objective label)
PROGRESSION = {
    'Emberfall Crags': (
        'crags_onward', 'Onward to the Crags', 'crags_captain', 5, 100,
        'You have outgrown the meadow. Captain Rowan is sending you north: leave Alderhaven by the Emberfall Gate at the end of the north road, cross into the Emberfall Crags and report to Captain Sera at Cinderwatch Camp.',
        'Travel to the Emberfall Crags'),
    'Rimeveil Glacier': (
        'rime_onward', 'Up the Frozen Stair', 'rime_warden', 10, 200,
        'The Crags have little left to teach you. Past the last lava ford a gate leads up onto the Rimeveil Glacier: climb it, find Rimeward Camp and report to Warden Halvard.',
        'Travel to the Rimeveil Glacier'),
    'Gloamfen': (
        'fen_onward', 'Lights in the Gloam', 'fen_reeve', 15, 300,
        'Something has started to glow at the heart of the glacier. Cross the summit bowl to the fen gate, step down into Gloamfen and report to Reeve Osric in Lanternmere.',
        'Travel to Gloamfen'),
    'Skaldholm': (
        'city_onward', 'The Capital Awaits', 'city_captain', 20, 400,
        'You are ready for the greatest city in the north. Take the city gate beside the Rimeveil summit and walk the long road into Skaldholm, then report to Captain Ingrid Stormwatch at the Great Gate.',
        'Travel to Skaldholm'),
    'Wyrdwood': (
        'wyrd_onward', 'The Road East', 'wyrd_warden', 22, 500,
        'Skaldholm is not the end of the road. Leave the city by the East Gate at the end of the Trade Road and walk into the Wyrdwood, where the forest has begun to go wrong. Find Hollowmoot beneath the Elder Ash and report to Moot-Warden Bjorn Oakhand.',
        'Travel to the Wyrdwood'),
    'Bifrost Reach': (
        'sky_onward', 'Up Through the Rift', 'sky_warden', 30, 600,
        'The Highmoor has taught you all it can. In the north-west corner of the summit court, beyond the second ridge, lightning has begun to rise instead of fall: walk into the Stormrift, climb into the sky and report to Shieldmaiden Sigrun Cloudwatcher at Heimdall\'s Perch.',
        'Travel to Bifrost Reach'),
    "R\u00e1n's Deep": (
        'deep_onward', 'Down the Maelstrom', 'deep_warden', 35, 700,
        "Bifrost Reach has no sky left to climb. On the Roc's Eyrie, at the north-east edge of the last island, a waterspout stands up out of the storm: step into the Maelstrom, fall through the sea and report to Skipper Ylva Saltbeard in Keelhaven.",
        "Travel to R\u00e1n's Deep"),
    'Astralhollow': ('astral_onward', 'Beyond the Pearl Road', 'astral_steward', 40, 1200,
        'Leave Nacrehold for Astralhollow and report to Seren Starwatcher.', 'Travel to Astralhollow'),
    'The Prismwaste': ('prism_onward', 'Into the Prismwaste', 'prism_keeper', 45, 1800,
        'Cross the Astralhollow border into the Prismwaste and report to Mara Vey.', 'Travel to the Prismwaste'),
    'The Obsidian Orrery': ('orrery_onward', 'The Turning Machine', 'orrery_keeper', 50, 2500,
        'Follow the glass road to the Obsidian Orrery and report to Ilyra Cogsong.', 'Travel to the Obsidian Orrery'),
    'The Moonspore Canopy': ('moonspore_onward', 'Under the Moonspores', 'moonspore_warden', 55, 3500,
        'Leave the Orrery by its forest gate and report to Eira Lanternkeeper.', 'Travel to the Moonspore Canopy'),
    'The Stormglass Shore': ('stormglass_onward', 'To the Stormglass Shore', 'stormglass_warden', 60, 5000,
        'Cross from Asterion to the Stormglass Shore and report to Captain Thora Vale.', 'Travel to the Stormglass Shore'),
    'Sunward Vale': ('sun_onward', 'The Sunward Road', 'sun_miller', 65, 6500,
        'Take the eastern shore gate into Sunward Vale and report to Ada Bell.', 'Travel to Sunward Vale'),
    'The Ribbonwild': ('ribbon_onward', 'Through the Ribbons', 'ribbon_host', 70, 8000,
        'Follow the vale road into the Ribbonwild and meet Mira Vell.', 'Travel to the Ribbonwild'),
    'The Tanglecrown': ('tangle_onward', 'Beneath the Rain Crown', 'tangle_warden', 75, 10000,
        'Pass through the Ribbonwild gate and report to Asha Banyan.', 'Travel to the Tanglecrown'),
    'The Lapis Erg': ('lapis_onward', 'The Lapis Road', 'lapis_keeper', 80, 12500,
        'Leave Veyrroot for the Lapis Erg and report to Sahra Bluewell.', 'Travel to the Lapis Erg'),
    'Frostwake Shelf': ('frostwake_onward', 'Across Frostwake', 'frostwake_captain', 85, 15000,
        'Cross the Erg to Frostwake Shelf and report to Captain Svala Northlight.', 'Travel to Frostwake Shelf'),
    'The Cairnspine': ('cairn_onward', 'Climb the Cairnspine', 'cairn_warden', 90, 18000,
        'Climb from Frostwake into the Cairnspine and report to Warden Mira Cairn.', 'Travel to the Cairnspine'),
    'The Yearwheel': ('yr_onward', 'The Fourfold Road', 'yr_sp_lead', 95, 22000,
        'Take the summit gate to the Yearwheel and report to Ilya Greenwake in Springmere.', 'Travel to the Yearwheel'),
}


def for_zone(name):
    """The progression quest sending players to the zone `name`, as a list of zero or one quests."""
    if name not in PROGRESSION:
        return []
    id, title, giver, level, gold, description, label = PROGRESSION[name]
    return [dict(id=id, title=title, npc=giver, description=description,
                 objectives=[dict(kind='reach', target=name, label=label, count=1)],
                 level=level, rewardXp=LEVEL_XP[level - 1] // 10, rewardGold=gold,
                 requires=None, repeatable=False, autoLevel=level)]


def keep_released_rewards_and_route_quest(previous, rebuilt):
    """Keep later quest rewards when a terrain generator rebuilds its zone."""
    old = {q['id']: q for q in previous.get('quests', [])}
    for quest in rebuilt['quests']:
        for field in ('rewardItem', 'rewardChoices'):
            if field in old.get(quest['id'], {}):
                quest[field] = old[quest['id']][field]
    new_ids = {q['id'] for q in rebuilt['quests']}
    rebuilt['quests'].extend(q for q in for_zone(rebuilt['name']) if q['id'] not in new_ids)
    import mount_sources
    mount_sources.patch_zone(rebuilt)


def main():
    raw = PATH.read_text()
    world = json.loads(raw)
    assert json.dumps(world, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    ids = {entry[0] for entry in PROGRESSION.values()}
    for zone in world['zones']:
        zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids] + for_zone(zone['name'])
        got = [q['id'] for q in zone['quests'] if q['id'] in ids]
        print(f"{zone['name']}: {len(zone['quests'])} quests, progression {got}")
    PATH.write_text(json.dumps(world, indent=2) + '\n')


if __name__ == '__main__':
    main()
