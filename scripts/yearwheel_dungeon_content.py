"""Level-99 autumn and winter dungeon encounters and material catalogs."""
import json
from pathlib import Path

CAST = {
    'amber_archive': [
        ('amber_page', 'Living Page', 'page', '#dfb875', [1110000, 13900, 3.4, 1.3], [.5, 1.3, 10, 13], None, 0, 0, False),
        ('amber_moth', 'Script Moth', 'moth', '#d59a59', [960000, 13500, 3.3, 1.5], [.7, 1.9, 0, 14], [16, 11, '#f9dfa6', 1, 2, .25], 0, 0, False),
        ('amber_sentinel', 'Archive Sentinel', 'sentinel', '#9c7554', [1280000, 16300, 2.5, 1.9], [1, 1.6, 9, 13], None, 4.0, 0, False),
        ('amber_curator', 'The Curator', 'curator', '#ad7445', [5500000, 35300, 2.5, 2.5], [.9, 1.8, 10, 15], None, 5.0, 4.7, True),
        ('amber_chronicle', 'The Living Chronicle', 'chronicle', '#eac782', [5100000, 33800, 2.8, 2.4], [.8, 2, 0, 15], [18, 11, '#ffedbc', 1.25, 4, .29], 0, 0, True),
        ('amber_memory', 'The Last Memory', 'memory', '#f1cc75', [8100000, 45000, 2.1, 3.1], [1.2, 2.3, 10, 18], [19, 12, '#fff0bf', 1.5, 5, .33], 6.0, 6.0, True),
    ],
    'silent_solstice': [
        ('solstice_flurry', 'Whispering Flurry', 'flurry', '#aed2dd', [1110000, 13900, 3.4, 1.3], [.5, 1.3, 10, 13], None, 0, 0, False),
        ('solstice_owl', 'Night Owl', 'owl', '#9fb9d1', [960000, 13500, 3.3, 1.5], [.7, 1.9, 0, 14], [16, 11, '#dbeeff', 1, 2, .25], 0, 0, False),
        ('solstice_guard', 'Rime Guard', 'guard', '#718aa1', [1280000, 16300, 2.5, 1.9], [1, 1.6, 9, 13], None, 4.0, 0, False),
        ('solstice_watcher', 'The Frost Watcher', 'watcher', '#7397b7', [5500000, 35300, 2.5, 2.5], [.9, 1.8, 10, 15], None, 5.0, 4.7, True),
        ('solstice_harbinger', 'Harbinger of Night', 'harbinger', '#b6cee0', [5100000, 33800, 2.8, 2.4], [.8, 2, 0, 15], [18, 11, '#edf6ff', 1.25, 4, .29], 0, 0, True),
        ('solstice_heart', 'Heart of the Longest Night', 'heart', '#d5e4ed', [8100000, 45000, 2.1, 3.1], [1.2, 2.3, 10, 18], [19, 12, '#f2faff', 1.5, 5, .33], 6.0, 6.0, True),
    ],
}

def enemies(theme):
    result = []
    for kind, name, art, color, stats, profile, ranged, slam, melee, boss in CAST[theme]:
        result.append(dict(kind=kind, name=name, art=art, color=color, stats=stats,
                           profile=profile, ranged=ranged, slam=slam, melee=melee,
                           boss=boss, level=99, gold=23000 if boss else 5500,
                           material=kind+'_relic', lootSource=theme if boss else None))
    return result

def bosses(theme):
    return [e['kind'] for e in enemies(theme) if e['boss']]

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    path = root/'world/items.txt'; items = json.loads(path.read_text()); ids = {i['id'] for i in items}
    for theme in CAST:
        cast = enemies(theme)
        (root/f'world/{theme}.txt').write_text(json.dumps(cast, indent=2)+'\n')
        for e in cast:
            if e['material'] not in ids:
                items.append(dict(id=e['material'], name=e['name']+' Relic', kind='material', rarity='common', sell=11000 if e['boss'] else 4700))
    path.write_text(json.dumps(items, indent=2)+'\n')
