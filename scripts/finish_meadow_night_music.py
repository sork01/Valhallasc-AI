#!/usr/bin/env python3
"""Filter and loop-fold Greenmeadow's 32-bar 6/8 night remix."""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/valhallasc-meadow-night-dybase2.wav')
RATE, audio = wavfile.read(SOURCE)
assert RATE == 48000 and audio.ndim == 2 and audio.shape[1] == 2
audio = sosfiltfilt(butter(2, 25, fs=RATE, btype='highpass', output='sos'), audio.astype(np.float64), axis=0)
frames = round(RATE * 32 * 3 * 60 / 100)
assert frames + RATE < len(audio) < frames + RATE * 3
loop = audio[:frames].copy()
tail = audio[frames:]
loop[:len(tail)] += tail * (1 - np.arange(len(tail)) / len(tail))[:, None]
n = round(RATE * .025)
loop[:n] *= (np.arange(n) / n)[:, None]
mid = (loop[0] + loop[-1]) / 2
for channel in range(2):
    loop[:n, channel] += (mid[channel] - loop[0, channel]) * (1 - np.arange(n) / n)
    loop[-n:, channel] += (mid[channel] - loop[-1, channel]) * (np.arange(n) / n)
loop[0] = mid
loop[-1] = mid
# Keep transients below the peak ceiling without flattening their tops.
def soft_limit(samples):
    magnitude = np.abs(samples)
    excess = np.maximum(magnitude - .75, 0)
    curved = .75 + .15 * (1 - np.exp(-excess / .15))
    return np.sign(samples) * np.where(magnitude > .75, curved, magnitude)


# The 128 kbps encode drops about 0.45 dB; target -24 dB after decoding.
target_rms = 10 ** (-23.55 / 20)
low, high = 0.0, target_rms / math.sqrt(float(np.mean(loop.mean(axis=1) ** 2))) * 2
for _ in range(20):
    gain = (low + high) / 2
    trial = soft_limit(loop * gain)
    if math.sqrt(float(np.mean(trial.mean(axis=1) ** 2))) < target_rms:
        low = gain
    else:
        high = gain
gain = (low + high) / 2
loop = soft_limit(loop * gain)
audio = soft_limit(audio * gain)
assert np.max(np.abs(loop)) <= .901
folded = Path('/tmp/valhallasc-meadow-night-loop.wav')
wavfile.write(folded, RATE, loop.astype(np.float32))
full = Path('/tmp/valhallasc-meadow-night-full.wav')
wavfile.write(full, RATE, audio.astype(np.float32))
target = ROOT / 'client/assets/music_meadow_night.mp3'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(folded), '-codec:a', 'libmp3lame', '-b:a', '128k',
                '-metadata', 'title=Fireflies on the Path', '-metadata', 'artist=Valhalla', str(target)], check=True)
filedrop = Path('/tmp/valhallasc-meadow-night-filedrop/music_meadow_night.mp3')
filedrop.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(full), '-codec:a', 'libmp3lame', '-b:a', '192k',
                '-metadata', 'title=Fireflies on the Path', '-metadata', 'artist=Valhalla', str(filedrop)], check=True)
print(f'{target}: {frames/RATE:.3f}s, mono RMS {20*math.log10(math.sqrt(float(np.mean(loop.mean(axis=1)**2)))):.2f} dB, '
      f'peak {20*math.log10(float(np.max(np.abs(loop)))):.2f} dB, seam {np.max(np.abs(loop[0]-loop[-1])):.6f}')
print(f'{filedrop}: {len(audio)/RATE:.3f}s, full-length natural ending')
