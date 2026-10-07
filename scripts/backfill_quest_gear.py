"""Grant gear added to already claimed quests before the reward server went live.

Run while valhalla.service is stopped, before starting the reward-aware binary.
The migration records each character/quest grant so a rerun cannot grant twice.
"""

import argparse
import json
import sqlite3
from pathlib import Path

from quest_gear_rewards import REWARDS

MIGRATION = 'quest_gear_rewards_20261007'
ITEMS = {item['id']: item for item in json.loads((Path(__file__).resolve().parents[1] / 'world/items.txt').read_text())}


def owed(state):
    return [(progress['id'], REWARDS[progress['id']])
            for progress in state.get('quests', [])
            if progress.get('claimed') and progress.get('id') in REWARDS]


def bag_overflow(state):
    """Match Character::bag_used: worn copies do not occupy backpack cells."""
    equipped = {item: list(state.get('equipment', {}).values()).count(item)
                for item in ITEMS}
    look = state.get('look', {})
    for item in ITEMS.values():
        kind = item.get('kind')
        if item.get('class') == look.get('class') and kind in ('armor', 'weapon'):
            field = look['class'] + ('Armor' if kind == 'armor' else 'Weapon')
            if look.get(field) == item.get('variant'):
                equipped[item['id']] += 1
    used = sum(stack['quantity'] > equipped.get(stack['item'], 0)
               for stack in state.get('inventory', []) if stack['item'] in ITEMS)
    capacity = 16 + sum(ITEMS[bag].get('bagSlots', 0) for bag in state.get('bags', []) if bag in ITEMS)
    return used - capacity


def fit_owed_bags(state):
    """Keep every compensated stack visible; use the existing legacy 16-cell pack."""
    bags = state.setdefault('bags', [])
    fitted = 0
    while bag_overflow(state) > 0:
        if len(bags) < 4:
            bags.append('traveler_pack')
        else:
            smallest = min(range(len(bags)), key=lambda i: ITEMS.get(bags[i], {}).get('bagSlots', 0))
            if ITEMS.get(bags[smallest], {}).get('bagSlots', 0) >= 16:
                raise ValueError('Quest reward compensation exceeds all four full expansion bags')
            bags[smallest] = 'traveler_pack'
        fitted += 1
    return fitted


def run(db_path, apply=False, backup=None):
    if apply and backup is None:
        raise ValueError('Applying the migration requires --backup PATH')
    db = sqlite3.connect(db_path)
    try:
        db.execute('PRAGMA busy_timeout=2000')
        if apply:
            backup = Path(backup)
            if backup.exists():
                raise FileExistsError(f'Backup already exists: {backup}')
            backup.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(backup) as saved:
                db.backup(saved)
            db.execute('BEGIN IMMEDIATE')
            db.execute('''CREATE TABLE IF NOT EXISTS quest_gear_migrations (
                migration TEXT NOT NULL, character_id TEXT NOT NULL, quest_id TEXT NOT NULL,
                PRIMARY KEY (migration, character_id, quest_id))''')
        table_exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='quest_gear_migrations'").fetchone()
        marked = set(db.execute('SELECT character_id, quest_id FROM quest_gear_migrations WHERE migration=?',
                                (MIGRATION,))) if table_exists else set()
        grants = 0
        characters = 0
        packs = 0
        for character_id, raw in db.execute('SELECT id, state FROM characters'):
            state = json.loads(raw)
            pending = [(quest, gear) for quest, gear in owed(state) if (character_id, quest) not in marked]
            if not pending and not any(owner == character_id for owner, _ in marked):
                continue
            if pending:
                characters += 1
                grants += len(pending)
            inventory = state.setdefault('inventory', [])
            for quest, gear in pending:
                stack = next((stack for stack in inventory if stack['item'] == gear), None)
                if stack is None:
                    inventory.append({'item': gear, 'quantity': 1})
                else:
                    stack['quantity'] += 1
                if apply:
                    db.execute('INSERT INTO quest_gear_migrations VALUES (?, ?, ?)',
                               (MIGRATION, character_id, quest))
            fitted = fit_owed_bags(state)
            packs += fitted
            if apply and (pending or fitted):
                db.execute('UPDATE characters SET state=? WHERE id=?',
                           (json.dumps(state, separators=(',', ':')), character_id))
        if apply:
            db.commit()
        return characters, grants, packs
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    characters, grants, packs = run(args.db, args.apply, args.backup)
    print(f'{characters} characters, {grants} quest gear grants, {packs} legacy packs' + (' applied' if args.apply else ' pending'))
