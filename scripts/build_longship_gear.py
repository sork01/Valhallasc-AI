"""Resumable 28-piece PixelFlow build/export for the original Keelbound set."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
tasks=[t for t in json.loads((ROOT/'docs/instance-gear-state.txt').read_text())['tasks'] if t['group']=='keel'];assert len(tasks)==28
for n,task in enumerate(tasks,1):
 records=json.loads((ROOT/'world/gear-art.txt').read_text());record=records.get(task['id'])
 if not record or not record.get('files'):
  subprocess.run([sys.executable,'scripts/make_progression_gear.py','build',task['id']],cwd=ROOT,check=True)
 print(f'Keelbound {n}/28: {task["id"]} exported',flush=True)
subprocess.run([sys.executable,'scripts/gear_art_catalog.py'],cwd=ROOT,check=True)
print('All Keelbound pieces saved in PixelFlow and exported. Run focused browser and colour/shape review before marking complete.',flush=True)
