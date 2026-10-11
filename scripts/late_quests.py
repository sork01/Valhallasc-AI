#!/usr/bin/env python3
"""Apply late-game quest additions without regenerating terrain or moving enemy IDs.

Run after any zone generator, then sync-world.cjs. The operation replaces its own
quest IDs and reward choices, so repeating it is safe.
"""
import json
from pathlib import Path

from progression_quests import PROGRESSION, for_zone

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
ITEMS = {i['id']: i for i in json.loads((ROOT / 'world/items.txt').read_text())}
XP = json.loads((ROOT / 'world/levels.txt').read_text())
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
SLOTS = ('armor', 'weapon', 'headgear', 'shoulders', 'gloves')


def xp_need(level):
    return XP[level - 1] if level <= len(XP) else XP[-1] + (level - len(XP)) * 2300


def gear(level, kind, cls=None, rarity='rare'):
    candidates = [i for i in ITEMS.values() if i.get('kind') == kind and
                  i.get('class') == cls and i.get('rarity') == rarity and
                  i.get('requiredLevel', 1) <= level and not i.get('source') and
                  not i.get('starter')]
    if not candidates:
        raise ValueError((level, kind, cls, rarity))
    return max(candidates, key=lambda i: i['requiredLevel'])['id']


def quest(id, title, npc, text, objectives, level, gold, requires=None, reward=None, group=False):
    return dict(id=id, title=title, npc=npc, description=text, objectives=objectives,
                level=level, rewardXp=xp_need(level) // 10, rewardGold=gold,
                requires=requires, repeatable=False, rewardItem=reward,
                group=group, recommendedPlayers=5 if group else 0)


def kill(kind, label):
    return dict(kind='kill', target=kind, label=label, count=1)


def add_dungeon_quests(zones):
    city, nacre = zones[4], zones[9]
    city['quests'] = [q for q in city['quests'] if q['id'] not in ('city_vault_entry', 'city_vault_bosses')]
    city['quests'].extend([
        quest('city_vault_entry', 'Beneath the Meeting Stone', 'city_stonewarden',
              'The Undervault stairs stand beside the Meeting Stone. Gather five adventurers, descend, and return with a report from inside.',
              [dict(kind='reach', target='The Undervault', label='Enter the Undervault', count=1)],
              20, 1200, 'city_welcome', gear(20, 'necklace')),
        quest('city_vault_bosses', 'The Four Seals', 'city_stonewarden',
              'Break all four seals while exploring your party copy of the Undervault: Gatewarden, Choir, Colossus, and Hollow King.',
              [kill(k, f'Defeat {name}') for k, name in (
                  ('gatewarden', 'the Gatewarden'), ('choir', 'the Hollow Choir'),
                  ('colossus', 'Ironwake'), ('hollowking', 'the Hollow King'))],
              20, 3000, 'city_vault_entry', gear(20, 'accessory'), True),
    ])
    ids = {'nacre_cloister_clear', 'nacre_reliquary_clear', 'nacre_nave_clear'}
    nacre['quests'] = [q for q in nacre['quests'] if q['id'] not in ids]
    for wing, level, bosses, prerequisite, slot in [
        ('cloister', 40, ('bellkeeper', 'mournsister', 'rootabbot', 'choirmother'), 'nacre_cathedral', 'necklace'),
        ('reliquary', 45, ('pearlwidow', 'glasscantor', 'relicwarden', 'coralregent'), 'nacre_cloister_clear', 'pants'),
        ('nave', 50, ('chainmarshal', 'starseraph', 'tidejudicator', 'hierophant'), 'nacre_reliquary_clear', 'accessory'),
    ]:
        name = {'cloister': 'Flooded Cloister', 'reliquary': 'Coral Reliquary', 'nave': 'Grand Nave'}[wing]
        nacre['quests'].append(quest('nacre_' + wing + '_clear', 'Free the ' + name, 'nacre_warden',
            f'Take a party of five through the {name}, defeat its four wardens in your private copy, and report back to Captain Namar.',
            [kill(boss, 'Defeat ' + boss.replace('_', ' ').title()) for boss in bosses],
            level, level * 100, prerequisite, gear(level, slot), True))


def add_progression(zones):
    ids = {entry[0] for entry in PROGRESSION.values()}
    for zone in zones:
        zone['quests'] = [q for q in zone.get('quests', []) if q['id'] not in ids] + for_zone(zone['name'])


def update_legacy_rewards(zones):
    updates = {
        'sky_ward_vigil': 'accessory_amber_l30_blue',
        'sky_ward_last': 'pants_wayfarer_l35_blue',
        'deep_captain': 'accessory_amber_l35_blue',
        'deep_net': 'pants_wayfarer_l35_blue',
        'deep_rans': 'pants_wayfarer_l40_blue',
        'deep_kraken': 'necklace_moonstone_l40_purple',
    }
    found = set()
    for zone in zones:
        for q in zone.get('quests', []):
            if q['id'] in updates:
                q['rewardItem'] = updates[q['id']]
                found.add(q['id'])
                if q['id'] == 'sky_ward_last':
                    q['description'] = q['description'].replace('guaranteed epic pair of Mythic Wayfarer Pants', 'level-35 blue pair of Wayfarer Pants')
                if q['id'] == 'deep_captain':
                    q['description'] = q['description'].replace('guaranteed blue Celestial Amber Ring', 'level-35 blue Amber Ring')
                if q['id'] == 'deep_net':
                    q['description'] = q['description'].replace('guaranteed blue Verdigris Ring', 'level-35 blue pair of Wayfarer Pants')
                if q['id'] == 'deep_rans':
                    q['description'] = q['description'].replace('guaranteed pair of Vaultwalker Pants', 'level-40 blue pair of Wayfarer Pants')
    assert found == updates.keys(), updates.keys() - found


def add_class_choices(zones):
    prefixes = ('astral_', 'prism_', 'orrery_', 'moonspore_', 'stormglass_',
                'sun_', 'ribbon_', 'tangle_', 'lapis_', 'frostwake_', 'cairn_')
    for zone in zones:
        for q in zone.get('quests', []):
            if q['repeatable'] or q.get('autoLevel') or not q['id'].startswith(prefixes):
                continue
            rarity = 'rare' if q.get('group') else 'uncommon'
            q['rewardChoices'] = {cls: [gear(q['level'], slot, cls, rarity) for slot in SLOTS]
                                  for cls in CLASSES}


def add_year_rewards(zones):
    year = next(z for z in zones if z['name'] == 'The Yearwheel')
    for q in year['quests']:
        parts = q['id'].split('_')
        if len(parts) != 3 or parts[0] != 'yr' or parts[2] not in ('1', '2', '3'):
            continue
        season = ('sp', 'su', 'au', 'wi').index(parts[1])
        number = int(parts[2]) - 1
        reward_number = season * 3 + number
        slot = SLOTS[reward_number % len(SLOTS)]
        shared = ('pants', 'necklace', 'accessory')[reward_number // len(SLOTS)]
        q.pop('rewardItem', None)
        q['rewardChoices'] = {cls: [gear(95, slot, cls), gear(95, shared)] for cls in CLASSES}


def apply():
    raw = MAP.read_text()
    world = json.loads(raw)
    assert json.dumps(world, indent=2) + '\n' == raw, 'map.txt must use canonical layout'
    zones = [world, *world['zones']]
    add_dungeon_quests(zones)
    add_progression(zones)
    update_legacy_rewards(zones)
    add_class_choices(zones)
    add_year_rewards(zones)
    ids = set()
    for zone in zones:
        for q in zone.get('quests', []):
            assert q['id'] not in ids, q['id']
            ids.add(q['id'])
            assert q['rewardXp'] == xp_need(q['level']) // 10, q['id']
            assert any(n['id'] == q['npc'] for n in zone.get('npcs', [])), q['id']
            for cls, choices in q.get('rewardChoices', {}).items():
                assert cls in CLASSES and choices, q['id']
                for id in choices:
                    piece = ITEMS[id]
                    assert piece.get('class') in (cls, None) and piece['requiredLevel'] <= q['level'], (q['id'], id)
    MAP.write_text(json.dumps(world, indent=2) + '\n')
    print('Applied late quests and rewards:', len(ids), 'total quests')


if __name__ == '__main__':
    apply()
