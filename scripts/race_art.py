"""Save and export the eight-facing head attachments used by playable races."""

import argparse
from pathlib import Path
import sys

import numpy as np
from PIL import Image

SIZE = 48
ANCHOR = (24, 36)
ASSETS = Path(__file__).resolve().parents[1] / 'client/assets'


def export_race_atlas(race, name, palette, artwork):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'export', 'verify'])
    args = parser.parse_args()
    sys.path.insert(0, str(Path.home() / '.claude/skills/makesprites'))
    import pf

    sprite_id = pf.ids(name).get(name)
    if args.action == 'build' and sprite_id is None:
        operations = [
            dict(op='grid', frame=direction, layer=layer, x=0, y=0,
                 rows=np.asarray(image).tolist())
            for direction in range(8)
            for layer, image in enumerate(artwork(direction))
        ]
        sprite_id = pf.create(name, SIZE, SIZE, 8, palette, layers=2, layer_ops=operations)
    if sprite_id is None:
        parser.error(f'Run build first to create {name}.')
    sprite, frames = pf.load(sprite_id)
    assert (sprite['width'], sprite['height'], len(frames)) == (SIZE, SIZE, 8)
    atlas = Image.new('RGBA', (SIZE * 8, SIZE * 2))
    for direction, layers in enumerate(frames):
        assert len(layers) == 2 and np.any(layers[0]), direction
        for layer, grid in enumerate(layers):
            image = Image.fromarray(pf.to_rgba(grid, sprite['palette']))
            atlas.paste(image, (direction * SIZE, layer * SIZE))
    path = ASSETS / (race + '.png')
    if args.action == 'verify':
        with Image.open(path) as exported:
            assert np.array_equal(np.asarray(atlas), np.asarray(exported.convert('RGBA')))
    else:
        atlas.save(path, optimize=True)
    print(f'{args.action}: {sprite_id}, eight facings and two layers')
