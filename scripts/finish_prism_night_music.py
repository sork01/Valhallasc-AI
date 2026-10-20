#!/usr/bin/env python3
"""Export Saltglass Afterglow as a game loop and a natural-ending full MP3."""
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000
SECONDS = 32 * 4 * 60 / 84
TITLE = 'Saltglass Afterglow'

rate, audio = wavfile.read('/tmp/valhallasc-prism-night-dybase2.wav')
assert rate == RATE and audio.ndim == 2 and audio.shape[1] == 2
audio = sosfiltfilt(butter(2, 25, fs=RATE, btype='highpass', output='sos'),
                   audio.astype(np.float64), axis=0)
frames = round(RATE * SECONDS)
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
target_rms = 10 ** (-23.55 / 20)  # MP3 loses roughly .45 dB of mono RMS.
low, high = 0.0, target_rms / math.sqrt(float(np.mean(loop.mean(axis=1) ** 2))) * 2
for _ in range(20):
    gain = (low + high) / 2
    trial = np.clip(loop * gain, -.9, .9)
    if math.sqrt(float(np.mean(trial.mean(axis=1) ** 2))) < target_rms:
        low = gain
    else:
        high = gain
gain = (low + high) / 2
loop = np.clip(loop * gain, -.9, .9)
audio = np.clip(audio * gain, -.9, .9)
folded = Path('/tmp/valhallasc-prism-night-loop.wav')
full = Path('/tmp/valhallasc-prism-night-full.wav')
wavfile.write(folded, RATE, loop.astype(np.float32))
wavfile.write(full, RATE, audio.astype(np.float32))
game = ROOT / 'client/assets/music_prism_night.mp3'
filedrop = Path('/tmp/valhallasc-prism-night-filedrop/music_prism_night.mp3')
filedrop.parent.mkdir(parents=True, exist_ok=True)
for source, target, bitrate in [(folded, game, '128k'), (full, filedrop, '192k')]:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source),
                    '-codec:a', 'libmp3lame', '-b:a', bitrate,
                    '-metadata', f'title={TITLE}', '-metadata', 'artist=Valhalla', str(target)], check=True)
rms = 20 * math.log10(math.sqrt(float(np.mean(loop.mean(axis=1) ** 2))))
peak = 20 * math.log10(float(np.max(np.abs(loop))))
print(f'prism: loop {frames/RATE:.3f}s, mono RMS {rms:.2f} dB, peak {peak:.2f} dB, '
      f'seam {np.max(np.abs(loop[0]-loop[-1])):.6f}; full {len(audio)/RATE:.3f}s')
