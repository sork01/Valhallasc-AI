#!/usr/bin/env python3
"""Fold the dybase2 render's tail into a seamless Seed Vault - The First Heartbeat game loop."""
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/tmp/valhallasc-seed-vault-dybase2.wav')
rate, audio = wavfile.read(SOURCE)
assert rate == 48000 and audio.ndim == 2 and audio.shape[1] == 2
frames = round(rate * 32 * 4 * 60 / 84)
assert frames + rate < len(audio) < frames + rate * 3
loop = audio[:frames].astype(np.float64)
tail = audio[frames:].astype(np.float64)
loop[:len(tail)] += tail * (1 - np.arange(len(tail)) / len(tail))[:, None]
n = round(rate * .025)
mid = (loop[0] + loop[-1]) / 2
for channel in range(2):
    loop[:n, channel] += (mid[channel] - loop[0, channel]) * (1 - np.arange(n) / n)
    loop[-n:, channel] += (mid[channel] - loop[-1, channel]) * np.arange(n) / n
loop[0] = mid
loop[-1] = mid
rms = math.sqrt(float(np.mean(loop.mean(axis=1)**2)))
peak = float(np.max(np.abs(loop)))
loop *= min(10**(-24 / 20) / rms, .90 / peak)
assert np.max(np.abs(loop)) <= .901
folded = Path('/tmp/valhallasc-seed-vault-loop.wav')
wavfile.write(folded, rate, loop.astype(np.float32))
target = ROOT / 'client/assets/music_seed_vault.mp3'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(folded), '-codec:a', 'libmp3lame', '-b:a', '128k',
                '-metadata', 'title=The First Heartbeat', '-metadata', 'artist=Valhalla', str(target)], check=True)
print(f'{target}: {frames/rate:.3f}s, mono RMS {20*math.log10(math.sqrt(float(np.mean(loop.mean(axis=1)**2)))):.2f} dB, '
      f'peak {20*math.log10(float(np.max(np.abs(loop)))):.2f} dB, seam {np.max(np.abs(loop[0]-loop[-1])):.6f}')
