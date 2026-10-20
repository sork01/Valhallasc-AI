"""Resumable Nullforged build: source -> PixelFlow -> all-pose worn/depth art and icons."""
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
tasks=[t for t in json.loads((ROOT/'docs/instance-gear-state.txt').read_text())['tasks'] if t['group']=='null']
assert len(tasks)==28
for n,t in enumerate(tasks,1):
    if '--preview' in sys.argv:
        subprocess.run([sys.executable,'scripts/make_progression_gear.py','preview',t['id']],cwd=ROOT,check=True)
        continue
    records=json.loads((ROOT/'world/gear-art.txt').read_text());record=records.get(t['id'])
    if not record or not record.get('files'):
        subprocess.run([sys.executable,'scripts/make_progression_gear.py','build',t['id']],cwd=ROOT,check=True)
    print(f'Nullforged {n}/28: {t["id"]} exported',flush=True)
if '--preview' not in sys.argv:subprocess.run([sys.executable,'scripts/gear_art_catalog.py'],cwd=ROOT,check=True)
