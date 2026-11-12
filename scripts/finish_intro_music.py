#!/usr/bin/env python3
"""Export the finite, natural-ending dybase2 intro performance for game playback."""
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('INTRO_SCORE_OUT', ROOT / 'test-results/intro-strings'))
RATE, SECONDS = 48000, 62
score = np.zeros((RATE * SECONDS, 2), dtype=np.float64)
for group in ['low', 'high']:
    rate, stem = wavfile.read(OUT / f'strings-{group}.wav')
    assert rate == RATE and stem.ndim == 2 and stem.shape[1] == 2
    assert abs(len(stem) / RATE - SECONDS) < .01
    score += stem.astype(np.float64)
# Keep the release at each join; this song ends rather than looping.
score = sosfilt(butter(2, 25, fs=RATE, btype='highpass', output='sos'), score, axis=0)
fade_in, fade_out = round(.65 * RATE), round(2.4 * RATE)
score[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
score[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
rms = math.sqrt(float(np.mean(score.mean(axis=1) ** 2)))
gain = 10 ** (-23.55 / 20) / rms
assert float(np.max(abs(score))) * gain < .89, 'Repair the dybase mix before normalizing'
score *= gain
natural = OUT / 'beyond-the-nine-chains.wav'
wavfile.write(natural, RATE, score.astype(np.float32))
game = ROOT / 'client/assets/music_intro.mp3'
preview = OUT / 'Beyond-the-Nine-Chains.mp3'
for dest, bitrate in [(game, '128k'), (preview, '192k')]:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(natural),
                    '-c:a', 'libmp3lame', '-b:a', bitrate,
                    '-metadata', 'title=Beyond the Nine Chains',
                    '-metadata', 'artist=Veyrheim / dybase2', str(dest)], check=True)
decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(game), '-f', 'f32le',
                          '-af', 'pan=mono|c0=0.5*c0+0.5*c1', '-ar', str(RATE), '-'], check=True, capture_output=True)
audio = np.frombuffer(decoded.stdout, dtype=np.float32)
mono_rms = 20 * math.log10(math.sqrt(float(np.mean(audio ** 2))))
assert abs(mono_rms + 24) < .3
assert len(audio) == SECONDS * RATE
assert np.max(abs(audio)) < .9
assert np.max(abs(audio[-RATE // 20:])) < .001, 'The final release must fade to silence'
report = dict(title='Beyond the Nine Chains', project_id='2930e63d0705e3be',
              project_url='https://gunning.se/dybase2/?project=2930e63d0705e3be',
              seconds=SECONDS, bpm=96, bars=24, key='D minor, ending in D major',
              mono_rms_db=round(mono_rms, 3), mono_peak_db=round(20*math.log10(float(np.max(abs(audio)))), 3),
              gain_db=round(20*math.log10(gain), 3),
              asset='client/assets/music_intro.mp3', sha256=hashlib.sha256(game.read_bytes()).hexdigest(),
              size=game.stat().st_size, renderer="dybase2 offline string stems",
              listening='Musical and rendered measurements checked; direct listening unavailable.')
(OUT / 'export.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
