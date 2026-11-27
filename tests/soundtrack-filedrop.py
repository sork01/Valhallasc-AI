#!/usr/bin/env python3
"""Check the actual installed recordings against pinned FileDrop provenance."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from import_filedrop_soundtrack import decode, measure

manifest = json.loads((ROOT / 'scripts/soundtrack-filedrop.txt').read_text())
assets = ROOT / 'client/assets'
drop = Path('/home/serveperry/webserver/www/filedrop/data/Sork/files')
assert len(manifest['tracks']) == 73
assert sum(t['already_installed'] for t in manifest['tracks']) == 26
assert len({t['slot'] for t in manifest['tracks']}) == 73
parser = argparse.ArgumentParser()
parser.add_argument('--slots', help='Decode only the selected comma-separated slots; always verify all asset/source hashes')
args = parser.parse_args()
selected = set(args.slots.split(',')) if args.slots else None
if selected:
    assert selected <= {t['slot'] for t in manifest['tracks']}
report = []
for track in manifest['tracks']:
    target = assets / ('music_' + track['slot'] + '.mp3')
    source = drop / track['source']
    assert hashlib.sha256(target.read_bytes()).hexdigest() == track['game_sha256'], target
    assert hashlib.sha256(source.read_bytes()).hexdigest() == track['source_sha256'], source
    if selected is not None and track['slot'] not in selected:
        continue
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_streams', '-of', 'json', str(target)]))['streams'][0]
    assert info['codec_name'] == 'mp3' and info['channels'] == 2 and int(info['bit_rate']) == 128000, target
    audio = decode(target)
    metrics = measure(audio)
    assert -25 < metrics['mono_rms_db'] < -23 and metrics['peak_db'] < -.5, (target, metrics)
    assert abs(metrics['seconds'] - track['seconds']) < .002, target
    if not track['already_installed']:
        # Compare after an independently implemented high-pass: raw bass/DC
        # removal changes phase enough to lower correlation on bass-heavy tracks.
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-threads', '1', '-i', str(source), '-af', 'highpass=f=25:poles=2', '-f', 'f32le', '-ac', '2', '-ar', '44100', 'pipe:1'])
        original = np.frombuffer(raw, dtype='<f4').reshape(-1, 2)
        assert abs(len(audio) / 44100 - track['loop_seconds']) < .0001, target
        assert abs(len(original) / 44100 - track['source_seconds']) < .0001, source
        # Gain/DC/codec treatment may change sample values, but must retain the
        # original performance at its original speed and in its original order.
        # The exported reverb bar belongs over the intro, outside these samples.
        for position in [5 * 44100, len(audio) // 2, len(audio) - 5 * 44100]:
            a = audio[position:position + 5 * 44100:16].mean(axis=1).astype(float)
            b = original[position:position + 5 * 44100:16].mean(axis=1).astype(float)
            a -= a.mean(); b -= b.mean()
            similarity = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
            assert similarity > .94, (target, position, similarity)
        assert metrics['seam_delta'] < .06, (target, metrics)
    report.append(dict(slot=track['slot'], **metrics))
    print('Verified ' + track['slot'], flush=True)
for name, expected in manifest['preserved'].items():
    assert hashlib.sha256((assets / name).read_bytes()).hexdigest() == expected, name + ' must stay untouched'
assert not manifest['preserved'], 'All four previously missing recordings now have replacements'
assert {p.name for p in assets.glob('music*.mp3')} == {'music_' + t['slot'] + '.mp3' for t in manifest['tracks']}, 'Every game music asset has a pinned FileDrop source'
output = ROOT / ('test-results/soundtrack-import/audio-validation-selected.json' if selected else 'test-results/soundtrack-import/audio-validation.json')
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(dict(tracks=report, auditory_review=False, preserved=manifest['preserved']), indent=2) + '\n')
print(f'PASS soundtrack-filedrop: all 73 source/output hashes; {len(report)} decoded recordings pass codec/level/duration/seam and source-performance checks; no original music remains')
