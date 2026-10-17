#!/usr/bin/env python3
"""How each extra mount is obtained (docs/mounts.md): the data half of MOUNT-SOURCES.

* Raptor: the four-step quest chain *The Banyan Run* from Mara Vines in the Tanglecrown; the last step escorts a
  hatchling's bearer back to her and carries `rewardMount`.
* Lizard: a Dune-wrangler in the Lapis Erg hub sells it (`mount` on the offer).
* Gryphon: Oren Highwind in the Cairnspine hatches a Gryphon Egg for gold (`mount` plus `needs` on the offer).
* Sabertooth and Gryphon: the two bound `mount_licence` items. Their drop rolls live in the server
  (`mount_licence_drop` in items.rs).

`patch_zone(zone)` is called by progression_quests.keep_released_rewards_and_route_quest, so a regenerated zone keeps
its mount content. Run this file on its own to patch world/map.txt and world/items.txt without regenerating any
terrain; it replaces earlier copies, so it is safe to repeat. Then run node scripts/sync-world.cjs and rebuild Rust.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
ITEMS = ROOT / 'world/items.txt'
LEVEL_XP = json.loads((ROOT / 'world/levels.txt').read_text())  # XP to next level; a quest pays a tenth

LICENCES = [
    dict(id='sabertooth_whistle', name='Sabertooth Whistle', kind='mount_licence', rarity='legendary',
         requiredLevel=95, sell=0, mount='sabertooth'),
    dict(id='gryphon_egg', name='Gryphon Egg', kind='mount_licence', rarity='legendary',
         requiredLevel=95, sell=0, mount='gryphon'),
]
RAPTOR_QUESTS = ['tangle_banyan_1', 'tangle_banyan_2', 'tangle_banyan_3', 'tangle_banyan_4']
HATCHLING = 'tangle_hatchling'
WRANGLER = 'lapis_wrangler'
HATCH = 'hatch_gryphon'


def _quest(key, title, description, objectives, level, gold, requires, **extra):
    return dict(id=f'tangle_banyan_{key}', title=title, npc='tangle_tracker', description=description,
                objectives=objectives, level=level, rewardXp=LEVEL_XP[level - 1] // 10, rewardGold=gold,
                requires=requires, repeatable=False, **extra)


def _kill(kind, n, label):
    return dict(kind='kill', target=kind, count=n, label=label)


def _bring(item, n, label):
    return dict(kind='bring', target=item, count=n, label=label)


def tangle_quests():
    return [
        _quest('1', 'The Banyan Run: Thinning the Canopy',
               'Mara Vines needs the raptor trails clear before she trusts anyone with a hatchling. Cull 25 of the canopy beasts: gliders, mantises, caimans and gorillas.',
               [_kill('canopyglider', 6, 'Defeat Canopy Gliders'), _kill('orchidmantis', 6, 'Defeat Orchid Mantises'),
                _kill('poolcaiman', 6, 'Defeat Pool Caimans'), _kill('drumgorilla', 7, 'Defeat Drum Gorillas')],
               75, 8500, 'tangle_welcome'),
        _quest('2', 'The Banyan Run: The Nest Offering',
               'Raptors take only fresh offerings. Bring Mara ten of the canopy\'s own trophies: petals, membrane, scales and drumskin.',
               [_bring('mantis_petals', 3, 'Bring Orchid Mantis Petals'), _bring('glider_membrane', 3, 'Bring Glider Membrane'),
                _bring('caiman_scale', 2, 'Bring Blackwater Caiman Scales'), _bring('gorilla_drumskin', 2, 'Bring Drum Gorilla Hide')],
               76, 9200, 'tangle_banyan_1'),
        _quest('3', 'The Banyan Run: The Basin Warden',
               'The old raptor path crosses the Jade Anaconda\'s basin. Three companions should break its coils before the nest can be reached.',
               [_kill('jadeanaconda', 1, 'Defeat the Jade Anaconda')],
               79, 16000, 'tangle_banyan_2', group=True, recommendedPlayers=3),
        _quest('4', 'The Banyan Run: Hatchling Home',
               'Tamsin Reedfoot is stranded with a raptor hatchling in a basket on the high boardwalk. Speak to her and walk her back to Mara Vines along the canopy road; if Tamsin falls, or you do, you must start again with her. The hatchling is yours to ride once it is safe.',
               [dict(kind='escort', target=HATCHLING, count=1, label='Escort Tamsin and the hatchling to Mara Vines')],
               79, 12000, 'tangle_banyan_3', rewardMount='raptor'),
    ]


def hatchling_npc():
    return dict(
        id=HATCHLING, name='Tamsin Reedfoot', role='Hatchling bearer, stranded', color='#d6f1a2',
        dialogue='Shh. She hatched an hour ago and she is hungry and loud. Mara said you would come: take us down the canopy road to the landing and keep the beasts off us, and I will follow at my own pace. She will remember who carried her.',
        offers=[], buys=False, x=75.0, y=68.0,
        look=dict(skin='#a96c4e', hair='#263d31', style='long', hat='hood', hatColor='#3d9d74'),
        escort=dict(quest='tangle_banyan_4', **{'class': 'hunter'}, female=True, hairColor=0, skin=1, level=75, speed=2.5,
                    route=[[61.0, 84.0], [52.0, 91.0], [43.0, 98.0]], ambush=[]))


def wrangler_npc():
    return dict(
        id=WRANGLER, name='Zahir Dunereins', role='Dune-wrangler', color='#e8c98a',
        dialogue='Sand lizards do not tire and do not sulk. A level-80 rider with 160,000 gold can have the best of my string; the rest can walk.',
        offers=[dict(id='buy_lizard', label='Buy a riding lizard · level 80 · 160,000 gold', cost=160000, mount='lizard')],
        buys=False, x=40.0, y=134.0,
        look=dict(skin='#b88b66', hair='#3b2a1c', style='short', hat='hood', hatColor='#c9a35a'))


def hatch_offer():
    return dict(id=HATCH, label='Hatch a Gryphon Egg · level 95 · 250,000 gold', cost=250000, mount='gryphon',
                needs='gryphon_egg')


def patch_zone(zone):
    """Add this zone's mount content (a no-op for every other zone); safe to repeat."""
    name = zone['name']
    if name == 'The Tanglecrown':
        zone['quests'] = [q for q in zone['quests'] if q['id'] not in RAPTOR_QUESTS] + tangle_quests()
        zone['npcs'] = [n for n in zone['npcs'] if n['id'] != HATCHLING] + [hatchling_npc()]
    elif name == 'The Lapis Erg':
        zone['npcs'] = [n for n in zone['npcs'] if n['id'] != WRANGLER] + [wrangler_npc()]
    elif name == 'The Cairnspine':
        for n in zone['npcs']:
            if n['id'] == 'cairn_windseer':
                n['offers'] = [o for o in n['offers'] if o['id'] != HATCH] + [hatch_offer()]
    elif name == 'Skaldholm':
        for n in zone['npcs']:
            for o in n['offers']:
                if o.get('mount') is True:
                    o['mount'] = 'horse'


def patch_items(items):
    ids = {i['id'] for i in LICENCES}
    return [i for i in items if i['id'] not in ids] + LICENCES


def main():
    raw = MAP.read_text()
    world = json.loads(raw)
    assert json.dumps(world, indent=2, ensure_ascii=False) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    for zone in world['zones']:
        patch_zone(zone)
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
    raw = ITEMS.read_text()
    items = json.loads(raw)
    assert json.dumps(items, indent=2, ensure_ascii=False) + '\n' == raw, 'items.txt is not in the canonical 2-space JSON layout'
    ITEMS.write_text(json.dumps(patch_items(items), indent=2, ensure_ascii=False) + '\n')
    print('mount sources patched: raptor chain, Dune-wrangler, Gryphon hatching, two licences')


if __name__ == '__main__':
    main()
