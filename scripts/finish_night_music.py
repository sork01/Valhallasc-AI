#!/usr/bin/env python3
"""Fold the dybase2 nocturne's reverb tail into its 80-second game loop."""
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
rate, audio = wavfile.read('/tmp/valhallasc-night-dybase2.wav')
assert rate == 48000 and audio.ndim == 2 and audio.shape[1] == 2
frames = round(rate * 24 * 4 * 60 / 72)
assert frames + rate < len(audio) < frames + rate * 3
loop = audio[:frames].astype(np.float64)
tail = audio[frames:].astype(np.float64)
loop[:len(tail)] += tail * (1 - np.arange(len(tail)) / len(tail))[:, None]
edge = round(rate * .025)
mid = (loop[0] + loop[-1]) / 2
for channel in range(2):
    loop[:edge, channel] += (mid[channel] - loop[0, channel]) * (1 - np.arange(edge) / edge)
    loop[-edge:, channel] += (mid[channel] - loop[-1, channel]) * np.arange(edge) / edge
loop[0] = mid
loop[-1] = mid
rms = math.sqrt(float(np.mean(loop.mean(axis=1)**2)))
peak = float(np.max(np.abs(loop)))
loop *= min(10**(-25 / 20) / rms, .90 / peak)
assert np.max(np.abs(loop)) <= .901
folded = Path('/tmp/valhallasc-night-loop.wav')
wavfile.write(folded, rate, loop.astype(np.float32))
target = ROOT / 'client/assets/music_night.mp3'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(folded), '-codec:a', 'libmp3lame', '-b:a', '128k',
                '-metadata', 'title=Lanterns After Sundown', '-metadata', 'artist=Valhalla', str(target)], check=True)
print(f'{target}: {frames/rate:.2f}s, mono RMS {20*math.log10(math.sqrt(float(np.mean(loop.mean(axis=1)**2)))):.2f} dB, '
      f'peak {20*math.log10(float(np.max(np.abs(loop)))):.2f} dB')
