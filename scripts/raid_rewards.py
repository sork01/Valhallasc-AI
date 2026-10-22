"""Generate boss-only Chainforged orange copies, loot rules and artwork jobs.

Preserves the world-drop orange pool and every existing item. Run before
gear_art_catalog, set_bonuses, sync-world and the private server build.
"""
import json
from pathlib import Path
import orange_rules as orange

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
CLASS_SLOTS = ('armor', 'headgear', 'shoulders', 'gloves', 'weapon')
SHARED = ('pants', 'necklace', 'accessory', 'cloak')
WEAPONS = dict(warrior='Chainsplitter', mage='Cinderwake Staff', assassin='Twin Embertongs',
               priest='Bellows Censer', hunter='Chainbow')
REPLACEMENTS = dict(warrior=('earthshatter', 'Slagshatter'), mage=('arcaneward', 'Cinder Ward'),
                    assassin=('knifering', 'Ember Ring'), priest=('mend', 'Bellows Mend'),
                    hunter=('arrowstorm', 'Chain Storm'))
SUFFIX = dict(armor='Furnace Harness', headgear='Vent Crown', shoulders='Anvil Pauldrons',
              gloves='Ratchet Gauntlets', pants='Shackle Greaves', necklace='Broken Link',
              accessory='Crucible Seal', cloak='Nine-chain Cloak')
# Two DISTINCT slots from each row, chosen without replacement, then class independently.
# The eight non-weapon kinds all occur; only Eldmarr ever yields a weapon.
BOSSES = (
    ('cf_kettil', ('armor', 'headgear', 'cloak')),
    ('cf_ysolt', ('shoulders', 'gloves', 'pants')),
    ('cf_hallgrim', ('necklace', 'accessory', 'armor')),
    ('cf_sigrun', ('headgear', 'cloak', 'shoulders')),
    ('cf_dagfinn', ('gloves', 'pants', 'necklace')),
    ('cf_thorbjorg', ('accessory', 'armor', 'headgear')),
    ('cf_ragnhild', ('cloak', 'shoulders', 'gloves')),
    ('cf_orm', ('pants', 'necklace', 'accessory')),
    ('cf_hildr', ('armor', 'headgear', 'shoulders')),
    ('cf_eldmarr', ('gloves', 'pants', 'cloak')),
)

def item_id(cls, kind):
    return 'chainforged_' + (cls + '_' if cls else '') + kind

def build():
    pieces = []
    for cls, kinds in [(c, CLASS_SLOTS) for c in CLASSES] + [(None, SHARED)]:
        for kind in kinds:
            ranges = orange.rolls(kind, 99)
            # At least +10% nominal; whole-number rounding must still leave the
            # lowest roll above Worldheart's best, except capped hit/dodge.
            for stat in ('attack', 'defense', 'stamina'):
                if ranges[stat][1] == 0:
                    continue
                low, high = ranges[stat]
                ranges[stat] = [max(high + 1, round(low * 1.10)), max(high + 2, round(high * 1.10))]
            if kind in ('necklace', 'accessory'):
                # These are offensive trinkets in gear_levels, unlike a head/glove.
                # The older five-slot orange helper treats all unknown slots as
                # defense=1; do not reuse that fallback for the newly filled slots.
                base = 2.0 if kind == 'necklace' else 1.5
                total = base * orange.level_factor(99) * 1.25 * 1.175 ** 2 * 1.175 * 1.10
                ranges['attack'] = orange.span(total * .8)
                ranges['defense'] = orange.span(total * .2)
            pieces.append(dict(id=item_id(cls, kind), name=WEAPONS[cls] if kind == 'weapon' else
                               ('Chainforged Assassin Cinder Hood' if cls=='assassin' and kind=='headgear' else
                                'Chainforged ' + (cls.capitalize() + ' ' if cls else '') + SUFFIX[kind]),
                               slot=kind, requiredLevel=99, **{'class': cls}, rolls=ranges))
    previous = {p['slot']: p for p in orange.build()['pieces'] if p['requiredLevel'] == 99}
    for p in pieces:
        for stat, (lo, hi) in p['rolls'].items():
            assert 0 <= lo <= hi, (p['id'], stat)
            if p['slot'] in previous and stat in ('attack', 'defense', 'stamina') and hi:
                assert lo > previous[p['slot']]['rolls'][stat][1], (p['id'], stat)
        assert p['rolls']['accuracy'][1] <= orange.ACCURACY_CAP
        assert p['rolls']['dexterity'][1] <= orange.DEXTERITY_CAP
    return dict(version=1, source='chained_forge', pieces=pieces,
                bosses=[dict(kind=kind, slots=list(slots), drops=2,
                             weapons=2 if kind == 'cf_eldmarr' else 0) for kind, slots in BOSSES],
                weapons=[dict(item=item_id(cls, 'weapon'), **{'class':cls},
                              replaces=REPLACEMENTS[cls][0], name=REPLACEMENTS[cls][1]) for cls in CLASSES])

def apply():
    rules = build()
    (ROOT / 'world/raid-rewards.txt').write_text(json.dumps(rules, indent=2, ensure_ascii=False) + '\n')
    path = ROOT / 'world/items.txt'
    items = [i for i in json.loads(path.read_text()) if i.get('source') != 'chained_forge']
    tasks = []
    for p in rules['pieces']:
        kind, cls = p['slot'], p['class']
        items.append(dict(id=p['id'], name=p['name'], kind=kind, rarity='legendary', requiredLevel=99,
                          sell=9152, attack=p['rolls']['attack'][0], defense=p['rolls']['defense'][0],
                          bonusStats={k:p['rolls'][k][0] for k in ('stamina','accuracy','dexterity')},
                          **{'class':cls}, variant=p['id'], art='regearchainforged', source='chained_forge'))
        tasks.append(dict(id='chainforged-' + (cls or 'shared') + '-' + kind, group='chainforged',
                          className=cls, kind=kind, item=p['id'], name=p['name'], done=False))
    assert len(tasks) == 29 and len({i['id'] for i in items}) == len(items)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    state = ROOT / 'docs/raid-reward-gear-state.txt'
    if not state.exists():
        state.write_text(json.dumps(dict(tasks=tasks), indent=2) + '\n')
    print('29 Chainforged items; 10 boss tables; 5 signature weapons')

if __name__ == '__main__':
    apply()
