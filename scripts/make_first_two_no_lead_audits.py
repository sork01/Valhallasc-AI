#!/usr/bin/env python3
"""Refresh the full-song click mixes after removing Greenmeadow and Crags leads."""
from pathlib import Path
import subprocess

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
AUDITS = ROOT / 'test-results/night-rhythm-audits'
RATE = 48000
for zone, bpm, beats_per_bar, click_beats in (
    ('meadow', 100, 3, (0, 1.5)),
    ('crags', 92, 4, (0, 1, 2, 3)),
):
    rate, music = wavfile.read(f'/tmp/valhallasc-{zone}-night-full.wav')
    assert rate == RATE and music.ndim == 2 and music.shape[1] == 2
    expected = 32 * beats_per_bar * 60 / bpm + 2
    assert abs(len(music) / RATE - expected) < .02
    click = np.zeros(len(music), dtype=np.float32)
    for bar in range(32):
        for beat in click_beats:
            start = round((bar * beats_per_bar + beat) * 60 / bpm * RATE)
            length = min(round(.022 * RATE), len(click) - start)
            t = np.arange(length) / RATE
            first = beat == 0
            tone = np.sin(2 * np.pi * (1800 if first else 1200) * t) * np.exp(-190 * t)
            click[start:start + length] += (.16 if first else .10) * tone
    mixed = music.astype(np.float32) * .8 + click[:, None]
    assert np.max(np.abs(mixed)) < 1
    wav = Path(f'/tmp/valhallasc-{zone}-night-metronome.wav')
    wavfile.write(wav, RATE, mixed)
    output = AUDITS / f'{zone}-metronome.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav),
                    '-codec:a', 'libmp3lame', '-b:a', '192k', str(output)], check=True)
    print(f'{output}: {len(music)/RATE:.3f}s, 32 bars plus ending')
