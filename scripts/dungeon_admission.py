#!/usr/bin/env python3
"""Idempotent exterior admission quests; run before exporting world/client data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Parent, dungeon, door, quest, giver, level. Existing Foundry/Forge keys are preserved.
GATES = [
    (6, 41, 'wyrd_nornroot', 'entry_norn', 'barrow_guide', 25),
    (17, 18, 'asterion_moonwell_stairs', 'entry_moon', 'asterion_bellkeeper', 60),
    (25, 34, 'lapis_astrolabe_gate', 'entry_astro', 'lapis_seer', 85),
    (28, 39, 'year_solstice_descent', 'entry_solstice', 'yr_wi_lead', 99),
]
DIALOGUE = {
    'barrow_scribe': ' The forgotten names are Alva, who tended the cradle; Tor, who kept his oath; '
                    'and Sif, who stayed for the farewell. Tell Runa: remembered, released, returned.',
    'lapis_cartographer': ' For Laleh\'s horizon lens, use the lowest star in the Mirrored Oasis\'s '
                          'reflection as your bearing. The Astrolabe must be shown the sky below, not the sky above.',
    'yr_wi_heal': ' If Ysra is smuggling a sunrise, take a spark from my hearth. Shelter it in your '
                  'shadow at the Dawn Vigil. Even the longest winter cannot forbid a borrowed flame.',
}


def objective(kind, target, label, count=1):
    return dict(kind=kind, target=target, label=label, count=count)


def install(world):
    zones = [world] + world.get('zones', [])
    levels = json.loads((ROOT / 'world/levels.txt').read_text())
    while len(levels) < 99:
        levels.append(levels[-1] + 2300)
    content = [
        ('Three Names for the Dead',
         'Nornroot admits mourners, not treasure hunters. Visit the Cradle Stone, '
         'the Oath Stone and the Farewell Stone along the Norn Stones approach to remember a life, '
         'a promise and a parting. Ask Egil Spindlekeeper for the missing names, then return to Runa '
         'Threadreader. She will weave your funeral verse into the door. This opens Nornroot Barrow '
         'permanently for you.',
         [objective('visit', 'admit_cradle', 'Remember a life at the Cradle Stone'),
          objective('visit', 'admit_oath', 'Remember a promise at the Oath Stone'),
          objective('visit', 'admit_farewell', 'Remember a parting at the Farewell Stone'),
          objective('talk', 'barrow_scribe', 'Ask Egil for the forgotten names')]),
        ('A Bell for Your Reflection',
         'Your reflection reached the Moonwell before you, and Voss will not let another stranger '
         'follow it. Walk into the circles of the Waking Bell, the Dreaming Bell and the Returning Bell '
         'in Asterion. Each rings for 25 seconds: get all three ringing together, in any order, '
         'so your echo learns the way home. Return to Mora Thirteenbells to have your true name '
         'entered in the descent ledger. This opens the Moonwell permanently for you.',
         [objective('chime', 'admit_moon', 'Ring all three reflection bells together', 3)]),
        ('The Sky Beneath the Sand',
         'The Sunken Astrolabe has forgotten which way is up. Bring three Glass Scorpion Shards '
         'for a new horizon lens, ask Ivo Starfold at Azure Wells for the lost star bearing, and '
         'visit the Mirrored Oasis to catch the sky beneath your feet. Return to Laleh of the Lens; '
         'she will set the bearing and teach the door to recognise you. The shards are used to '
         'make the lens. This opens the Sunken Astrolabe permanently for you.',
         [objective('bring', 'scorpion_glass', 'Bring Glass Scorpion Shards for the horizon lens', 3),
          objective('talk', 'lapis_cartographer', 'Ask Ivo for the lost star bearing'),
          objective('visit', 'lapis_mirror', 'Catch the reflected sky at the Mirrored Oasis')]),
        ('Smuggle a Little Sunrise',
         'The Silent Solstice has outlawed dawn. Defeat three Snow Stoats that steal the village '
         'kindling, and ask Tilda Warmmitt in Rimehold for a spark from her hearth. Stand for '
         '12 seconds inside the Dawn Vigil circle beside the Solstice entrance to shelter that '
         'spark with your shadow. Leaving the circle pauses the vigil; falling resets unfinished '
         'progress. Return to Ysra Snowglass and she will hide the sunrise in your name. '
         'This opens the Silent Solstice permanently for you.',
         [objective('kill', 'snowstoat', 'Drive away the kindling thieves', 3),
          objective('talk', 'yr_wi_heal', 'Ask Tilda for a hearth spark'),
          objective('hold', 'admit_dawn', 'Shelter the sunrise at the Dawn Vigil', 12)]),
    ]
    sites = {
        6: [('admit_cradle', 'The Cradle Stone', 96, 58, 'spire'),
            ('admit_oath', 'The Oath Stone', 96, 65, 'spire'),
            ('admit_farewell', 'The Farewell Stone', 88, 71, 'spire')],
        17: [('admit_waking', 'The Waking Bell', 92, 68, 'tidebell'),
             ('admit_dreaming', 'The Dreaming Bell', 100, 88, 'tidebell'),
             ('admit_returning', 'The Returning Bell', 116, 88, 'tidebell')],
        28: [('admit_dawn', 'The Dawn Vigil', 57, 153, 'wardstone')],
    }
    for (parent, target, door, qid, giver, level), (title, description, objectives) in zip(GATES, content):
        if target >= len(zones):
            continue
        zone = zones[parent]
        for npc in zone['npcs']:
            if npc['id'] in DIALOGUE:
                extra = DIALOGUE[npc['id']]
                npc['dialogue'] = npc['dialogue'].removesuffix(extra) + extra
        portal = next(p for p in zone['portals'] if p['id'] == door)
        portal['needs_quest'] = qid
        quest = dict(id=qid, title=title, description=description, npc=giver, level=level,
                     minLevel=level, requires=None, repeatable=False, rewardXp=levels[level-1]//10,
                     rewardGold=0, objectives=objectives)
        zone['quests'] = [q for q in zone['quests'] if q['id'] != qid] + [quest]
        for key in ('places', 'objects'):
            zone[key] = [p for p in zone.get(key, [])
                         if not p.get('id', p.get('place', '')).startswith('admit_')]
        for pid, name, x, y, kind in sites.get(parent, []):
            place = dict(id=pid, name=name, x=x, y=y, r=1.8)
            if kind == 'tidebell':
                place.update(chain='admit_moon', burn=25)
            zone['places'].append(place)
            zone['objects'].append(dict(kind=kind, x=x, y=y, r=0, v=0, place=pid, label=name))
    return world


def install_file():
    path = ROOT / 'world/map.txt'
    world = install(json.loads(path.read_text()))
    path.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    install_file()
