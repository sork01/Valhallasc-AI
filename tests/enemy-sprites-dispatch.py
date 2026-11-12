#!/usr/bin/env python3
"""Combined native pipelines must keep both casts and the independent Firelord."""
import importlib
import json
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import dungeon_cel
import forge_slime_redraw as forge

for key in dungeon_cel.NATIVE_REDRAWS:
    calls = []
    native = types.SimpleNamespace(**{
        action: (lambda action=action: calls.append(action))
        for action in ('build', 'export', 'verify', 'preview')
    })
    with patch.object(dungeon_cel.importlib, 'import_module', return_value=native):
        dungeon_cel.build(key)
        dungeon_cel.preview(key)
    assert calls == ['build', 'export', 'verify', 'preview'], (key, calls)
    with patch.object(sys, 'argv', ['dungeon_cel.py', key, 'build', '--replace']):
        try:
            dungeon_cel.build(key)
        except SystemExit:
            pass
        else:
            raise AssertionError(f'{key}: destructive replacement accepted')
print(f'{len(dungeon_cel.NATIVE_REDRAWS)} native dungeon routes and replacement refusals pass')

for name, names in (
    ('make_astrolabe_sprites', ['astrolabe_slime_redraw', 'thunderheart_slime_redraw']),
    ('make_yearwheel_dungeon_sprites', ['amber_slime_redraw', 'solstice_slime_redraw']),
):
    maker = importlib.import_module(name)
    modules = [importlib.import_module(n) for n in names]
    for action in ('build', 'export', 'verify', 'preview'):
        calls = []
        with patch.object(modules[0], action, side_effect=lambda *args: calls.append(names[0])), \
                patch.object(modules[1], action, side_effect=lambda *args: calls.append(names[1])):
            getattr(maker, action)(maker.KINDS)
        assert calls == names, (name, action, calls)
    print(f'{name}: both native casts retained in every action')

# Exercise the real exporter alias merge without contacting or mutating PixelFlow.
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    meta = json.loads(forge.MANIFEST.read_text())
    firelord = {key: meta[key]['ember_firelord'] for key in ('sprites', 'tops', 'kindFrames', 'atlases')}
    meta['sprites']['es_foe_02'] = 'outdated-borrower'
    manifest = root / 'cathedral.txt'
    manifest.write_text(json.dumps(meta))
    with patch.object(forge, 'KINDS', []), patch.object(forge, 'registry', return_value={}), \
            patch.object(forge, 'MANIFEST', manifest), patch.object(forge, 'OUT', root), \
            patch.object(forge, 'ALIASES', {'ember_firelord': 'cf_eldmarr', 'es_foe_02': 'cf_kettil'}):
        forge.export()
    result = json.loads(manifest.read_text())
    assert {key: result[key]['ember_firelord'] for key in firelord} == firelord
    for key in ('sprites', 'tops', 'kindFrames'):
        assert result[key]['es_foe_02'] == result[key]['cf_kettil']
print('Forge export updates story borrowers while preserving independent Firelord art')
