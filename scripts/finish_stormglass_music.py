#!/usr/bin/env python3
"""Fold the Stormglass score's tail into a seamless 32-bar game loop."""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/valhallasc-stormglass-dybase2.wav')
RATE, audio = wavfile.read(SOURCE)
assert RATE == 48000 and audio.ndim == 2 and audio.shape[1] == 2
audio = sosfiltfilt(butter(2, 25, fs=RATE, btype='highpass', output='sos'), audio.astype(np.float64), axis=0)
frames = round(RATE * 32 * 4 * 60 / 96)
assert frames + RATE < len(audio) < frames + RATE * 3
loop = audio[:frames].copy()
tail = audio[frames:]
loop[:len(tail)] += tail * (1 - np.arange(len(tail)) / len(tail))[:, None]
n = round(RATE * .025)
# The renderer emits a short startup spike on the first bell; taper it before
# matching loudness so that one sample does not set the whole loop's level.
loop[:n] *= (np.arange(n) / n)[:, None]
mid = (loop[0] + loop[-1]) / 2
for channel in range(2):
    loop[:n, channel] += (mid[channel] - loop[0, channel]) * (1 - np.arange(n) / n)
    loop[-n:, channel] += (mid[channel] - loop[-1, channel]) * (np.arange(n) / n)
loop[0] = mid
loop[-1] = mid
mono_rms = math.sqrt(float(np.mean(loop.mean(axis=1) ** 2)))
peak = float(np.max(np.abs(loop)))
loop *= min(10 ** (-24 / 20) / mono_rms, .90 / peak)
assert np.max(np.abs(loop)) <= .901
folded = Path('/tmp/valhallasc-stormglass-loop.wav')
wavfile.write(folded, RATE, loop.astype(np.float32))
target = ROOT / 'client/assets/music_stormglass.mp3'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(folded), '-codec:a', 'libmp3lame', '-b:a', '128k',
                '-metadata', 'title=Where the Breakers Sing', '-metadata', 'artist=Valhalla', str(target)], check=True)
print(f'{target}: {frames/RATE:.3f}s, mono RMS {20*math.log10(math.sqrt(float(np.mean(loop.mean(axis=1)**2)))):.2f} dB, '
      f'peak {20*math.log10(float(np.max(np.abs(loop)))):.2f} dB, seam {np.max(np.abs(loop[0]-loop[-1])):.6f}')

# A requested FileDrop copy keeps the natural reverb ending instead of folding it.
full = audio.copy()
full[:n] *= (np.arange(n) / n)[:, None]
full_rms = math.sqrt(float(np.mean(full[:frames].mean(axis=1) ** 2)))
full_peak = float(np.max(np.abs(full)))
full *= min(10 ** (-24 / 20) / full_rms, .90 / full_peak)
drop_dir = Path('/tmp/valhallasc-stormglass-filedrop')
drop_dir.mkdir(exist_ok=True)
full_wav = drop_dir / 'music_stormglass.wav'
wavfile.write(full_wav, RATE, full.astype(np.float32))
full_mp3 = drop_dir / 'music_stormglass.mp3'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(full_wav), '-codec:a', 'libmp3lame', '-b:a', '192k',
                '-metadata', 'title=Where the Breakers Sing', '-metadata', 'artist=Valhalla', str(full_mp3)], check=True)
print(f'{full_mp3}: {len(full)/RATE:.3f}s with natural ending, mono RMS '
      f'{20*math.log10(math.sqrt(float(np.mean(full[:frames].mean(axis=1)**2)))):.2f} dB')
