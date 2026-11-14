#!/usr/bin/env python3
"""Quest-only items for `bring` quests (QUEST-ITEM-DROPS). Idempotent; run by sync-world after every other overlay.

Every `bring` objective that asks for an ordinary, sellable monster material (slime gel, ember cores ...) is given its own unsellable quest
item instead: `qi_<quest id>` (a `_2`, `_3` ... for a second one in the same quest), kind material, sell 0, `questMaterial` = the material it
comes from (the monsters that drop the material are the ones that drop it, but only for a hero on that quest who still needs it). The objective
points at the new item and carries its own `dropChance` (0.30..0.80, seeded by the quest id so every run gives the same number; a value already
present is kept, so it can be tuned by hand later).

The ordinary material keeps dropping as sellable loot, so gold income is unchanged. The quest items that already existed (hour shards, ember
shards, keys: `sell` 0) are not touched.

Swedish names are composed from the hand-written Swedish of the material and of the quest title ("<material> (<quest>)") and appended to
scripts/sv-translations.txt when missing (`--swedish`, off by default so the pipeline never rewrites that file by itself).
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
ITEMS = ROOT / 'world/items.txt'
SV = ROOT / 'scripts/sv-translations.txt'
LOW, HIGH = 0.30, 0.80


def chance(quest_id: str, n: int) -> float:
    digest = hashlib.sha256(f'dropchance:{quest_id}:{n}'.encode()).digest()
    return round(LOW + (int.from_bytes(digest[:4], 'big') % 51) / 100, 2)


def main():
    world = json.loads(MAP.read_text())
    items = json.loads(ITEMS.read_text())
    by_id = {i['id']: i for i in items}
    areas = [world, *world['zones']]
    made = {}
    changed_map = False
    for area in areas:
        for quest in area.get('quests', []):
            seen = 0
            for index, objective in enumerate(quest['objectives']):
                if objective.get('kind') != 'bring':
                    continue
                target = by_id.get(objective['target'])
                if target is None:
                    raise SystemExit(f"{quest['id']}: unknown bring target {objective['target']}")
                if target.get('questMaterial'):
                    # Already remapped by an earlier run: keep it and the chance, and make sure the chance exists.
                    if 'dropChance' not in objective:
                        objective['dropChance'] = chance(quest['id'], seen)
                        changed_map = True
                    seen += 1
                    made[target['id']] = target
                    continue
                if target.get('sell', 0) <= 0 or target.get('kind') != 'material':
                    continue                      # an existing quest item (hour shard, ember shard, key): untouched
                item_id = f"qi_{quest['id']}" + ('' if seen == 0 else f'_{seen + 1}')
                new = by_id.get(item_id) or {
                    'id': item_id,
                    'name': f"{target['name']} ({quest['title']})",
                    'kind': 'material',
                    'rarity': 'common',
                    'sell': 0,
                    'questMaterial': target['id'],
                }
                by_id[item_id] = new
                made[item_id] = new
                objective['target'] = item_id
                objective.setdefault('dropChance', chance(quest['id'], seen))
                changed_map = True
                seen += 1
    new_items = [i for i in made.values() if i not in items]
    if new_items:
        items.extend(new_items)
        ITEMS.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    if changed_map:
        MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
    if '--swedish' in sys.argv:
        swedish()
    print(f'{len(made)} quest items, {len(new_items)} new')


def swedish():
    sv = json.loads(SV.read_text())
    items = json.loads(ITEMS.read_text())
    names = {i['id']: i['name'] for i in items}
    world = json.loads(MAP.read_text())
    titles = {q['id']: q['title'] for area in [world, *world['zones']] for q in area.get('quests', [])}
    body = SV.read_text().rstrip()
    end = body.rfind('}')
    body = body[:end].rstrip()
    added = 0
    for i in items:
        if not i.get('questMaterial') or i['name'] in sv:
            continue
        material_sv = sv.get(names.get(i['questMaterial']))
        # The quest title sits inside the English name's brackets.
        title = i['name'][len(names[i['questMaterial']]) + 2:-1]
        title_sv = sv.get(title)
        if not material_sv or not title_sv:
            print('no hand-written Swedish yet for', i['name'])
            continue
        body += ',\n  ' + json.dumps(i['name'], ensure_ascii=False) + ': ' + json.dumps(f'{material_sv} ({title_sv})', ensure_ascii=False)
        sv[i['name']] = 'x'
        added += 1
    SV.write_text(body + '\n}\n')
    json.loads(SV.read_text())
    print(f'{added} Swedish names appended')


if __name__ == '__main__':
    main()
