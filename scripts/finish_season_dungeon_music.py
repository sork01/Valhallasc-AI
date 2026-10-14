#!/usr/bin/env python3
"""Fold dybase2's render tail into one exact 16-bar loop."""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

theme = sys.argv[1]
scores = {'blooming_labyrinth': ('Petals Beyond the Door', 84),
          'solar_crucible': ('The Furnace of Noon', 112),
          'amber_archive': ('The Book of Falling Leaves', 90),
          'silent_solstice': ('The Longest Night', 72)}
title, bpm = scores[theme]
source = Path(f'/tmp/valhallasc-{theme}-dybase2.wav')
rate, audio = wavfile.read(source)
assert rate == 48000 and audio.ndim == 2 and audio.shape[1] == 2
frames = round(rate * 16 * 4 * 60 / bpm)
assert frames + rate < len(audio) < frames + rate * 4, (frames, len(audio))
loop = audio[:frames].astype(np.float64)
tail = audio[frames:].astype(np.float64)
loop[:len(tail)] += tail * (1 - np.arange(len(tail)) / len(tail))[:, None]
n = round(rate * .025)
mid = (loop[0] + loop[-1]) / 2
for channel in range(2):
    loop[:n, channel] += (mid[channel] - loop[0, channel]) * (1 - np.arange(n) / n)
    loop[-n:, channel] += (mid[channel] - loop[-1, channel]) * np.arange(n) / n
loop[0] = mid; loop[-1] = mid
rms = math.sqrt(float(np.mean(loop.mean(axis=1)**2)))
peak = float(np.max(np.abs(loop)))
loop *= min(10**(-24 / 20) / rms, .9 / peak)
folded = Path(f'/tmp/valhallasc-{theme}-loop.wav')
wavfile.write(folded, rate, loop.astype(np.float32))
target = Path(__file__).resolve().parents[1] / f'client/assets/music_{theme}.mp3'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(folded),'-codec:a','libmp3lame','-b:a','128k',
                '-metadata',f'title={title}','-metadata','artist=Valhalla',str(target)],check=True)
print(f'{target}: {frames/rate:.3f}s, {target.stat().st_size} bytes')
