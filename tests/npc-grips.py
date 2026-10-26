#!/usr/bin/env python3
"""Inspect visible hands and handles in the shipped animation pixels, not the generator."""
import json, math, subprocess, sys
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
meta = json.loads((ROOT / 'client/assets/npc.txt').read_text())
baseline = '--baseline' in sys.argv
# Anatomical wrist positions, plus a point six pixels along the held shaft.
fixtures = {
    'sentinel': (24, 25, 0, 'leather'),
    'smith': (26, 20, -1, 'leather'),
    'merchant': (27, 21, 0, 'gold'),
    'pilgrim': (20, 22, 0, 'leather'),
    'elder': (20, 22, 0, 'leather'),
    'lamplighter': (17, 30, 0, 'leather'),
}
gestures = (0, 2, 5, 7, 4, 1)
checks = 0
for key, (hx, hy, offset, material) in fixtures.items():
    if baseline:
        sheet = Image.open(BytesIO(subprocess.check_output(['git', 'show', f'HEAD:client/assets/npc_{key}.png'], cwd=ROOT)))
    else:
        sheet = Image.open(ROOT / f'client/assets/npc_{key}.png')
    pixels = np.array(sheet.convert('RGBA'))
    skin = {tuple(bytes.fromhex(c[1:])) for k, c in meta['designs'][key]['materials'].items() if k.startswith('skin')}
    # Tool ramps are stable across NPC identities and distinct from skin/cloth.
    handle = {'leather': {(59,45,53), (105,80,82), (161,123,99)},
              'gold': {(132,96,57), (216,173,89), (255,226,161)}}[material]
    for clip, info in meta['clips'].items():
        for n in range(info['n']):
            y = hy - math.sin(n * math.tau / 8) * 4 if clip == 'walk' else hy + (gestures[n] if clip == 'talk' else 0)
            frame = pixels[info['row']*96:(info['row']+1)*96, n*96:(n+1)*96]
            xpix, ypix = round(48+hx), round(90-y)
            palm = frame[ypix-1:ypix+2, xpix-1:xpix+2]
            assert any(tuple(p[:3]) in skin and p[3] for row in palm for p in row), (key,clip,n,'missing gripping hand')
            shaft = frame[ypix+5:ypix+8, xpix+offset-1:xpix+offset+2]
            assert any(tuple(p[:3]) in handle and p[3] for row in shaft for p in row), (key,clip,n,'handle detached from hand')
            checks += 1
print(f'NPC grips: {checks} shipped poses have visible hands with attached handles')
