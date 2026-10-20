#!/usr/bin/env python3
"""Export the Frostwake night dybase2 render for game playback and FileDrop."""
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000
SECONDS = 32 * 4 * 60 / 84
source = Path('/tmp/valhallasc-frostwake-night-dybase2.wav')
rate, raw = wavfile.read(source)
assert rate == RATE and raw.ndim == 2 and raw.shape[1] == 2
audio = sosfiltfilt(butter(2, 25, fs=RATE, btype='highpass', output='sos'),
                   raw.astype(np.float64), axis=0)
frames = round(RATE * SECONDS)
assert frames + RATE < len(audio) < frames + RATE * 3
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

# The 128 kbps encode lowers mono RMS by approximately 0.45 dB.
wanted = 10 ** (-23.55 / 20)
wanted_gain = wanted / math.sqrt(float(np.mean(loop.mean(axis=1) ** 2)))
peak_gain = .89 / max(float(np.max(np.abs(loop))), float(np.max(np.abs(full))))
gain = min(wanted_gain, peak_gain)
if gain < wanted_gain * .97:
    raise ValueError('Frostwake peaks prevent -24 dB game level; repair the dybase2 mix')
loop *= gain
full *= gain
assert max(float(np.max(np.abs(loop))), float(np.max(np.abs(full)))) < .9
assert np.max(np.abs(loop[0] - loop[-1])) < .00001
folded = Path('/tmp/valhallasc-frostwake-night-loop.wav')
natural = Path('/tmp/valhallasc-frostwake-night-full.wav')
wavfile.write(folded, RATE, loop.astype(np.float32))
wavfile.write(natural, RATE, full.astype(np.float32))
game = ROOT / 'client/assets/music_frostwake_night.mp3'
filedrop = Path('/tmp/valhallasc-frostwake-night-filedrop/music_frostwake_night.mp3')
filedrop.parent.mkdir(parents=True, exist_ok=True)
for src, target, bitrate in ((folded, game, '128k'), (natural, filedrop, '192k')):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src),
                    '-codec:a', 'libmp3lame', '-b:a', bitrate,
                    '-metadata', 'title=Aurora Beneath the Ice', '-metadata', 'artist=Valhalla', str(target)], check=True)
print(f'Frostwake: loop {frames/RATE:.3f}s, mono RMS {20*math.log10(math.sqrt(float(np.mean(loop.mean(axis=1)**2)))):.2f} dB, '
      f'peak {20*math.log10(float(np.max(np.abs(loop)))):.2f} dB, '
      f'seam {np.max(np.abs(loop[0]-loop[-1])):.6f}; full {len(full)/RATE:.3f}s')
