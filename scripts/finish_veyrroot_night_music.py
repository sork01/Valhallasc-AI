#!/usr/bin/env python3
"""Fold the Veyrroot dybase2 night render into game loops and natural-ending MP3s."""
import math
import os
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000
SCORES = (
    ('veyrroot', 'When the Branches Sleep', 32 * 4 * 60 / 84),
)


def rms_db(audio):
    rms = math.sqrt(float(np.mean(audio.mean(axis=1) ** 2)))
    return 20 * math.log10(rms)


def export(zone, title, seconds):
    source = Path(f'/tmp/valhallasc-{zone}-night-dybase2.wav')
    rate, raw = wavfile.read(source)
    assert rate == RATE and raw.ndim == 2 and raw.shape[1] == 2, zone
    audio = sosfiltfilt(butter(2, 25, fs=RATE, btype='highpass', output='sos'),
                       raw.astype(np.float64), axis=0)
    frames = round(RATE * seconds)
    assert frames + RATE < len(audio) < frames + RATE * 3, zone
    loop = audio[:frames].copy()
    tail = audio[frames:]
    loop[:len(tail)] += tail * (1 - np.arange(len(tail)) / len(tail))[:, None]
    fade = round(RATE * .025)
    loop[:fade] *= (np.arange(fade) / fade)[:, None]
    mid = (loop[0] + loop[-1]) / 2
    for channel in range(2):
        loop[:fade, channel] += (mid[channel] - loop[0, channel]) * (1 - np.arange(fade) / fade)
        loop[-fade:, channel] += (mid[channel] - loop[-1, channel]) * (np.arange(fade) / fade)
    loop[0] = mid
    loop[-1] = mid

    full = audio.copy()
    full[:fade] *= (np.arange(fade) / fade)[:, None]

    # The encoder lowers mono RMS by roughly .45 dB at 128 kbps.
    wanted = 10 ** (-23.55 / 20)
    wanted_gain = wanted / math.sqrt(float(np.mean(loop.mean(axis=1) ** 2)))
    peak_gain = .89 / max(float(np.max(np.abs(loop))), float(np.max(np.abs(full))))
    gain = min(wanted_gain, peak_gain)
    if gain < wanted_gain * .97:
        raise ValueError(f'{zone}: peaks prevent -24 dB game level; fix the dybase2 mix')
    loop *= gain
    full *= gain
    assert max(float(np.max(np.abs(loop))), float(np.max(np.abs(full)))) < .9, zone
    assert np.max(np.abs(loop[0] - loop[-1])) < .00001, zone

    folded = Path(f'/tmp/valhallasc-{zone}-night-loop.wav')
    natural = Path(f'/tmp/valhallasc-{zone}-night-full.wav')
    wavfile.write(folded, RATE, loop.astype(np.float32))
    wavfile.write(natural, RATE, full.astype(np.float32))
    game = ROOT / f'client/assets/music_{zone}_night.mp3'
    filedrop = Path(f'/tmp/valhallasc-{zone}-night-filedrop/music_{zone}_night.mp3')
    filedrop.parent.mkdir(parents=True, exist_ok=True)
    for src, target, bitrate in ((folded, game, '128k'), (natural, filedrop, '192k')):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src),
                        '-codec:a', 'libmp3lame', '-b:a', bitrate,
                        '-metadata', f'title={title}', '-metadata', 'artist=Valhalla', str(target)], check=True)
    print(f'{zone}: loop {frames/RATE:.3f}s, mono RMS {rms_db(loop):.2f} dB, '
          f'peak {20*math.log10(float(np.max(np.abs(loop)))):.2f} dB, '
          f'seam {np.max(np.abs(loop[0]-loop[-1])):.6f}; full {len(full)/RATE:.3f}s')


for score in SCORES:
    if not os.environ.get('ZONES') or score[0] in os.environ['ZONES'].split(','):
        export(*score)
