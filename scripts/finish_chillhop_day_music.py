#!/usr/bin/env python3
"""Fold the Chillhop Axiom8 rerenders into the eight active daytime loops."""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000
# zone, title, quarter-note beats per bar, tempo, bars
SCORES = [
    ('meadow', 'Greenmeadow Wander', 3, 132, 32),
    ('crags', 'Ashfall Run', 4, 140, 32),
    ('rime', 'Rimeveil Spiral', 4, 100, 32),
    ('fen', 'Lanternmere Dusk', 3, 99, 40),
    ('city', 'Skaldholm Square', 4, 76, 32),
    ('wyrd', 'Wyrdwood Wanderings', 3, 96, 32),
    ('sky', 'Bifrost Reach - Above the Storm', 4, 84, 32),
    ('asterion', 'Seven Rings of Light', 4, 112, 32),
]


def export(zone, title, beats, bpm, bars):
    rate, audio = wavfile.read(f'/tmp/valhallasc-{zone}-day-dybase2.wav')
    assert rate == RATE and audio.ndim == 2 and audio.shape[1] == 2
    audio = sosfiltfilt(butter(2, 25, fs=RATE, btype='highpass', output='sos'),
                       audio.astype(np.float64), axis=0)
    frames = round(RATE * bars * beats * 60 / bpm)
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
    # Encoding the 128 kbps game MP3 lowers mono RMS by about 0.45 dB.
    target_rms = 10 ** (-23.55 / 20)
    low, high = 0.0, target_rms / math.sqrt(float(np.mean(loop.mean(axis=1) ** 2))) * 2
    for _ in range(20):
        gain = (low + high) / 2
        trial = np.clip(loop * gain, -.9, .9)
        if math.sqrt(float(np.mean(trial.mean(axis=1) ** 2))) < target_rms:
            low = gain
        else:
            high = gain
    loop = np.clip(loop * (low + high) / 2, -.9, .9)
    wav = Path(f'/tmp/valhallasc-{zone}-day-loop.wav')
    wavfile.write(wav, RATE, loop.astype(np.float32))
    target = ROOT / f'client/assets/music_{zone}.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav),
                    '-codec:a', 'libmp3lame', '-b:a', '128k',
                    '-metadata', f'title={title}', '-metadata', 'artist=Valhalla',
                    str(target)], check=True)
    rms = 20 * math.log10(math.sqrt(float(np.mean(loop.mean(axis=1) ** 2))))
    peak = 20 * math.log10(float(np.max(np.abs(loop))))
    seam = float(np.max(np.abs(loop[0] - loop[-1])))
    print(f'{zone}: {frames/RATE:.3f}s, mono RMS {rms:.2f} dB, '
          f'peak {peak:.2f} dB, seam {seam:.6f}', flush=True)


if __name__ == '__main__':
    wanted = set(sys.argv[1:])
    for score in SCORES:
        if not wanted or score[0] in wanted:
            export(*score)
