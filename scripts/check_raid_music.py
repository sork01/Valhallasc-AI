#!/usr/bin/env python3
"""Audit the saved MCP note grids and actual isolated rendered attacks."""
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

OUT = Path(__file__).resolve().parents[1] / 'test-results/raid-music'
NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def midi(pitch):
    if isinstance(pitch, int):
        return pitch
    return (int(pitch[-1]) + 1) * 12 + NAMES[pitch[0]] + (1 if '#' in pitch else -1 if 'b' in pitch else 0)


def audit(key, bpm):
    score = json.loads((OUT / f'{key}-score.json').read_text())
    saved = json.loads((OUT / f'{key}-saved-grid.json').read_text())
    counts = {}
    for track, intended in score['parts'].items():
        actual = []
        for block in saved[track]:
            for n in block['notes']:
                actual.append((midi(n['pitch']), round(n['beat'] + (block['from_bar'] - 1) * 4, 6),
                               round(n['beats'], 6), n['velocity']))
        expected = [(n['pitch'], n['beat'], n['beats'], n['velocity']) for n in intended]
        assert sorted(actual) == sorted(expected), f'MCP grid differs: {key} / {track}'
        assert all(beat + beats <= 256 for _, beat, beats, _ in actual)
        counts[track] = len(actual)
    motif = score['parts']['Ratchet signal']
    assert all(a['beat'] + a['beats'] <= b['beat'] for a, b in zip(motif, motif[1:])), 'Motif overlaps itself'
    roots = {'F#m': [6, 9, 1], 'D': [2, 6, 9], 'E': [4, 8, 11]}
    for track in ['Pressure bass', 'Ratchet signal', 'Chain strikes', 'Heat behind iron']:
        for n in score['parts'][track]:
            chord = score['audit'][int(n['beat'] // 4)]['chord']
            assert n['pitch'] % 12 in roots[chord], f'Chord mismatch: {track}, {n}'
    kick = {n['beat'] for n in score['parts']['Furnace kick']}
    assert all(n['beat'] in kick for n in score['parts']['Pressure bass']), 'Bass and kick anchors disagree'
    assert {n['pitch'] for n in score['parts']['Vent hats']} <= {42, 46}, 'Unsupported/banned hat route'
    attacks = {}
    for track, beats, limit in [('Furnace kick', [0, 1, 2, 3], 20),
                                ('Iron backbeat', [1, 3], 20),
                                ('Vent hats', [.5, 1.5, 2.5, 3.5], 20),
                                ('Ratchet signal', [0, .75, 1.5, 2.5], 20),
                                ('Heat behind iron', [0], 65)]:
        rate, raw = wavfile.read(OUT / (key + '-probe-' + track.replace(' ', '-') + '.wav'))
        samples = sosfilt(butter(2, 25, fs=rate, btype='highpass', output='sos'), raw.astype(float), axis=0)
        signal = np.max(np.abs(samples), axis=1)
        timings = []
        for beat in beats:
            start = round(beat * 60 / bpm * rate)
            window = signal[start:start + round(.075 * rate)]
            peak = float(np.max(window))
            assert peak > .0001, f'Silent attack: {key}, {track}, beat {beat}'
            onset = int(np.flatnonzero(window > peak * .2)[0]) / rate * 1000
            assert onset < limit, f'Late rendered attack: {key}, {track}, {onset} ms'
            timings.append(dict(beat=beat, onset_ms=onset, peak_db=20 * float(np.log10(peak))))
        attacks[track] = timings
    return dict(song=key, passed=True, note_counts=counts, rendered_attacks=attacks, listened=False)


if __name__ == '__main__':
    report = [audit('forge', 152), audit('eldmarr', 160)]
    (OUT / 'score-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps([dict(song=r['song'], passed=r['passed'], notes=sum(r['note_counts'].values()),
                           max_attack_ms=max(t['onset_ms'] for v in r['rendered_attacks'].values() for t in v))
                      for r in report]))
