"""Bring saved orange copies under the level gate (TODO ORANGE-LEVEL-GATE).

Run while valhalla.service is stopped, before starting the binary that knows the new required levels.
Every saved orange GearInstance is re-rolled inside the ranges of world/orange_rules.txt (the old level 1 rolls
were far above any piece's level) with a roll seeded by character and copy, so a rerun cannot change it again, and a
piece worn by a character below its required level goes back to the bag. Rolls are recorded per copy.
"""

import argparse
import hashlib
import json
import random
import sqlite3
from pathlib import Path

MIGRATION = 'orange_level_gate_20261020'
ROOT = Path(__file__).resolve().parents[1]
PIECES = {p['id']: p for p in json.loads((ROOT / 'world/orange_rules.txt').read_text())['pieces']}


def reroll(character_id, copy):
    piece = PIECES[copy['item']]
    seed = hashlib.sha256(f"{MIGRATION}:{character_id}:{copy['id']}".encode()).digest()
    rng = random.Random(seed)
    rolls = piece['rolls']
    copy['attack'] = float(rng.randint(*rolls['attack']))
    copy['defense'] = float(rng.randint(*rolls['defense']))
    for stat in ('stamina', 'accuracy', 'dexterity'):
        copy['bonusStats'][stat] = rng.randint(*rolls[stat])


def migrate(character_id, state, marked):
    """Returns (copies re-rolled, pieces taken off) and edits `state` in place."""
    copies = [c for c in state.get('gearInstances') or []
              if c['item'] in PIECES and (character_id, c['id']) not in marked]
    taken = 0
    for copy in copies:
        reroll(character_id, copy)
    level = state.get('level', 1)
    equipment = state.get('equipment', {})
    for slot, item in list(equipment.items()):
        if item in PIECES and PIECES[item]['requiredLevel'] > level:
            del equipment[slot]
            taken += 1
    return copies, taken


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
            db.execute('''CREATE TABLE IF NOT EXISTS orange_migrations (
                migration TEXT NOT NULL, character_id TEXT NOT NULL, copy_id INTEGER NOT NULL,
                PRIMARY KEY (migration, character_id, copy_id))''')
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='orange_migrations'").fetchone()
        marked = set(db.execute('SELECT character_id, copy_id FROM orange_migrations WHERE migration=?',
                                (MIGRATION,))) if exists else set()
        characters = rerolled = taken = 0
        for character_id, raw in list(db.execute('SELECT id, state FROM characters')):
            state = json.loads(raw)
            copies, off = migrate(character_id, state, marked)
            if not copies and not off:
                continue
            characters += 1
            rerolled += len(copies)
            taken += off
            if apply:
                for copy in copies:
                    db.execute('INSERT INTO orange_migrations VALUES (?, ?, ?)', (MIGRATION, character_id, copy['id']))
                db.execute('UPDATE characters SET state=? WHERE id=?',
                           (json.dumps(state, separators=(',', ':')), character_id))
        if apply:
            db.commit()
        return characters, rerolled, taken
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
    characters, rerolled, taken = run(args.db, args.apply, args.backup)
    print(f'{characters} characters, {rerolled} copies re-rolled, {taken} worn pieces returned to the bag'
          + (' applied' if args.apply else ' pending'))
