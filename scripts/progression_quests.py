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
