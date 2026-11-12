#!/usr/bin/env python3
"""Export pose-matched head attachment axes; preserve every saved sprite and atlas.

Requires VALHALLA_TOOLS pointing at the archived shared rig tools.
"""
import json
from pathlib import Path
import gear_shapes as gear
import cel_common as cc

ROOT = Path(__file__).resolve().parents[1]
TURNS = {'mage': .6, 'warrior': .5, 'priest': .3, 'hunter': .3, 'assassin': 1.}


def main():
    for cls in TURNS:
        for gender in ('male', 'female'):
            stem = ('warrior_layered' if cls == 'warrior' else cls) + ('_f' if gender == 'female' else '')
            path = ROOT / 'client/assets' / (stem + '_sprites.txt')
            meta = json.loads(path.read_text())
            poses = {}
            for clip, spec in meta['clips'].items():
                for direction, facing in enumerate(meta['dirs']):
                    for frame in range(spec['n']):
                        module, ink, p, rotation, xf, joints, head = gear.pose(cls, gender, clip, facing, frame)
                        head = cc.head_frame(ink, xf, cc.rig.psi_for(facing), p, turn=TURNS[cls])
                        origin = head['H'](0, 0)
                        right = head['H'](1, 0) - origin
                        poses[f'{clip}/{direction}/{frame}'] = [round(float(v), 5) for v in (*origin, *right, head['front'], head['side'])]
            meta.pop('headFrames', None)
            text = json.dumps(meta, indent=2)[:-2]
            rows = ',\n'.join('    ' + json.dumps(k) + ': ' + json.dumps(v) for k, v in poses.items())
            path.write_text(text + ',\n  \"headFrames\": {\n' + rows + '\n  }\n}\n')
            print(stem, len(poses))


if __name__ == '__main__':
    main()
