"""Wire individually exported progression artwork while preserving item IDs/stats and original icon cells."""
import json
from pathlib import Path
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'world/gear-art.txt'
STATE = ROOT / 'docs/gear-redesign-state.txt'
ASSETS = ROOT / 'client/assets'


def jobs():
    if not MANIFEST.exists(): return []
    manifest = json.loads(MANIFEST.read_text())
    state = {t['id']: t for t in json.loads(STATE.read_text())['tasks']}
    return [(state[key], record) for key, record in manifest.items() if record.get('files')]


def matches(item, task):
    if item['kind'] != task['kind'] or item.get('class') != task['className']: return False
    if task['group'].startswith('L'):
        return not item.get('source') and item.get('requiredLevel') == int(task['group'][1:])
    return item.get('source') == 'cathedral_' + task['group']


def apply(items):
    for task, record in jobs():
        for item in items:
            if matches(item, task): item['art'] = record['variant']
    # The new level-55 ladder uses the completed level-50 class silhouettes,
    # with its own tint, until a separate level-55 art pass is commissioned.
    level_50 = {(i.get('class'), i['kind']): i['art'] for i in items
                if i.get('requiredLevel') == 50 and not i.get('source') and i.get('art')}
    for item in items:
        if item.get('requiredLevel') == 55 and not item.get('source'):
            art = level_50.get((item.get('class'), item['kind']))
            if art: item['art'] = art
    return items


def append_icons(refresh_base=False):
    completed = jobs()
    if not completed: return
    base_image, base_meta = ASSETS / 'items_base.png', ASSETS / 'items_base.txt'
    if refresh_base or not base_image.exists():
        shutil.copyfile(ASSETS / 'items.png', base_image)
        shutil.copyfile(ASSETS / 'items.txt', base_meta)
    original = json.loads(base_meta.read_text()); n = original['cols'] * original['rows']; cols = original['cols']; size = original['size']
    rows = (n + len(completed) + cols - 1) // cols
    image = Image.new('RGBA', (cols * size, rows * size)); image.paste(Image.open(base_image), (0, 0))
    at = dict(original['at']); items = json.loads((ROOT / 'world/items.txt').read_text())
    for number, (task, record) in enumerate(completed, n):
        icon = Image.open(ASSETS / ('gear_icon_' + task['id'].lower() + '.png')).convert('RGBA')
        cell = [number % cols, number // cols]; image.paste(icon, (cell[0] * size, cell[1] * size))
        for item in items:
            if matches(item, task): at[item['id']] = cell
    for item in items:
        if item.get('requiredLevel') != 55 or item.get('source'):
            continue
        previous = next((old for old in items if old.get('requiredLevel') == 50
                         and not old.get('source') and old.get('class') == item.get('class')
                         and old['kind'] == item['kind'] and old['rarity'] == item['rarity']), None)
        if previous and previous['id'] in at:
            at[item['id']] = at[previous['id']]
    image.save(ASSETS / 'items.png', optimize=True)
    meta = {**original, 'rows': rows, 'at': at, 'progressionSprites': {task['id']: record['icon']['id'] for task, record in completed}}
    (ASSETS / 'items.txt').write_text(json.dumps(meta, indent=1) + '\n')
    (ROOT / 'client/itemicons.js').write_text("'use strict';\n// Original equipment icons plus individually exported progression gear.\nwindow.ITEM_ICONS = " + json.dumps(dict(size=size, cols=cols, rows=rows, at=at), separators=(',', ':')) + ';\n')


def wire():
    path = ROOT / 'world/items.txt'; items = json.loads(path.read_text()); apply(items)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    append_icons()


if __name__ == '__main__': wire()
