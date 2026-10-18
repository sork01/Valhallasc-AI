"""BANK-NPC: five bankers, one per big city and nowhere else, the client copy in step, and the Swedish text present.

Run: python3 tests/bank-npcs.py (after node scripts/sync-world.cjs)
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CITIES = {
    'Alderhaven': 'banker_alderhaven', 'Skaldholm': 'banker_skaldholm', 'Nacrehold': 'banker_nacrehold',
    'Astralhollow': 'banker_astralhollow', 'Asterion': 'banker_asterion',
}
NAMES = {'Brenna Coinwright', 'Hakon Vaultwarden', 'Perla Tidekeeper', 'Ilvane Stargaler', 'Archon Veyl'}

def zones(world):
    return [world, *world.get('zones', [])]

def main():
    text = (ROOT / 'world/map.txt').read_text()
    world = json.loads(text)
    seen = {}
    for zone in zones(world):
        city = (zone.get('city') or {}).get('name')
        bankers = [n for n in zone.get('npcs', []) if any(o['id'] == 'bank' for o in n['offers']) or n['id'].startswith('banker_')]
        if city in CITIES:
            assert [n['id'] for n in bankers] == [CITIES[city]], f'{city}: {[n["id"] for n in bankers]}'
            seen[city] = bankers[0]
        else:
            assert not bankers, f'{zone.get("name")} must have no banker'
    assert set(seen) == set(CITIES), set(CITIES) - set(seen)
    # No two bankers share a name or a line, and every line says what the quest rule is.
    assert len({n['name'] for n in seen.values()}) == 5 and len({n['dialogue'] for n in seen.values()}) == 5
    assert {n['name'] for n in seen.values()} == NAMES
    assert all('quest counts only what you carry' in n['dialogue'] for n in seen.values())
    # The sync script leaves a correct map alone (idempotent) and the client copy matches the source.
    subprocess.run(['python3', str(ROOT / 'scripts/bank_npcs.py')], check=True, capture_output=True)
    assert (ROOT / 'world/map.txt').read_text() == text, 'bank_npcs.py changed an already synced map'
    client = (ROOT / 'client/world.js').read_text()
    assert json.loads(client.split('window.WORLD_MAP = ', 1)[1].rsplit(';', 1)[0]) == world, 'client/world.js is stale'
    # Swedish: every new string exists, and everything but a proper name differs from the English.
    sv = (ROOT / 'client/sv-data.js').read_text()
    table = json.loads(re.match(r"'use strict';\nwindow\.SV_TEXT = (\{.*?\});\nwindow\.SV_TEMPLATES", sv, re.S)[1])
    keep = set(json.loads((ROOT / 'scripts/sv-keep.txt').read_text()))
    strings = {'Open the bank'}
    for n in seen.values():
        strings |= {n['name'], n['role'], n['dialogue']}
    for s in strings:
        assert s in table or s in keep, f'no Swedish for {s!r}'
        assert s in NAMES or s in keep or table[s] != s, f'{s!r} is not translated'
    print(f'bank NPC checks passed: {len(seen)} bankers, {len(strings)} strings')

if __name__ == '__main__':
    main()
