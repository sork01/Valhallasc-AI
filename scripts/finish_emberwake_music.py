#!/usr/bin/env python3
"""Fold both 32-bar 4/4 dybase2 render, remove DC, and match decoded MP3 mono RMS to -24 dB.

Keeps a natural-ending full MP3 in test-results/emberwake; FileDrop is only on request.
"""
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/emberwake'


def encode(source, target, bitrate, title):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-codec:a', 'libmp3lame', '-b:a', bitrate,
                    '-metadata', f'title={title}', '-metadata', 'artist=Valhalla', str(target)], check=True)


def finish(night=False):
    key = "night" if night else "day"
    bpm = 96 if night else 110
    title = "The Chains Dream" if night else "Heat Beneath the Stones"
    OUT.mkdir(parents=True, exist_ok=True)
    proj = json.loads((OUT / f'music-{key}-project.json').read_text())
    rate, audio = wavfile.read(f'/tmp/valhallasc-emberwake-{key}.wav')
    if np.issubdtype(audio.dtype, np.integer):
        audio = audio.astype(float) / np.iinfo(audio.dtype).max
    else:
        audio = audio.astype(float)
    frames = round(rate * 32 * 4 * 60 / bpm)
    assert frames < len(audio) < frames + rate * 5
    assert np.isfinite(audio).all()
    loop = audio[:frames].copy()
    tail = audio[frames:].copy()
    tail *= np.linspace(1, 0, len(tail))[:, None]
    loop[:len(tail)] += tail
    sos = butter(2, 25, fs=rate, btype='highpass', output='sos')
    # Filter from the same cyclic history so the high-pass introduces no seam transient.
    _, state = sosfilt(sos, loop, axis=0, zi=np.zeros((len(sos), 2, 2)))
    loop, _ = sosfilt(sos, loop, axis=0, zi=state)
    n = max(2, round(rate * .003))
    mid = (loop[0] + loop[-1]) / 2
    loop[:n] += (mid - loop[0])[None, :] * np.linspace(1, 0, n)[:, None]
    loop[-n:] += (mid - loop[-1])[None, :] * np.linspace(0, 1, n)[:, None]
    raw_rms = np.sqrt(np.mean(loop.mean(axis=1) ** 2))
    gain = min(10 ** (-23.55 / 20) / raw_rms, .9 / np.abs(loop).max())
    loop *= gain
    path = OUT / f'music-{key}-loop.wav'
    wavfile.write(path, rate, loop.astype(np.float32))
    game = ROOT / ('client/assets/music_emberwake_night.mp3' if night else 'client/assets/music_emberwake.mp3')
    encode(path, game, '128k', title)
    full = sosfilt(sos, audio, axis=0)
    full[-rate * 3:] *= np.linspace(1, 0, rate * 3)[:, None]
    full *= min(gain, .9 / np.abs(full).max())
    natural = OUT / f'{title}.wav'
    wavfile.write(natural, rate, full.astype(np.float32))
    encode(natural, OUT / f'{title}.mp3', '192k', title)
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(game), '-f', 'f32le', '-ac', '2', 'pipe:1'])
    stereo = np.frombuffer(raw, dtype='<f4').reshape(-1, 2)
    decoded = stereo.mean(axis=1)
    info = dict(project_id=proj['project_id'], bars=32, meter='4/4', bpm=bpm, seconds=len(decoded) / rate,
                mono_rms_db=20 * math.log10(np.sqrt(np.mean(decoded ** 2))), peak_db=20 * math.log10(np.max(np.abs(stereo))),
                seam_delta=float(np.max(np.abs(loop[0] - loop[-1]))), auditioned=False)
    assert abs(info['seconds'] - frames / rate) < .04
    assert -24.6 < info['mono_rms_db'] < -23.4, info
    assert info['peak_db'] < -1
    (OUT / f'music-{key}-report.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    finish(False)
    finish(True)
