#!/usr/bin/env python3
"""Stage the active Greenmeadow night render and listening copies (no upload)."""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'test-results/meadow-night-hiphop'
OUT.mkdir(parents=True, exist_ok=True)
SCORE = json.loads((OUT / 'score.json').read_text())
RENDER = json.loads((OUT / 'render.json').read_text())
PROJECT = SCORE['project']
RATE = 48000
BPM = float(PROJECT['tempo'].split()[0])
BARS = PROJECT['bars']
METER = PROJECT['meter']
numerator, denominator = map(int, METER.split('/'))
BEATS_PER_BAR = numerator * 4 / denominator
SECONDS = BARS * BEATS_PER_BAR * 60 / BPM
TITLE = PROJECT['name'].split(' - ', 1)[-1]
rate, raw = wavfile.read(RENDER['wav'])
assert rate == RATE and raw.ndim == 2 and raw.shape[1] == 2
assert raw.dtype.kind == 'f', 'Expected the DAW float WAV'
assert np.all(np.isfinite(raw)), 'Non-finite renderer output'
audio = sosfiltfilt(butter(2, 25, fs=RATE, btype='highpass', output='sos'),
                   raw.astype(np.float64), axis=0)
frames = round(RATE * SECONDS)
assert frames + RATE * 2 < len(audio) <= frames + RATE * 4
loop = audio[:frames].copy()
tail = audio[frames:]
# Preserve the complete rendered release across the loop, not a hard cut.
loop[:len(tail)] += tail
# A two-ms correction removes a sample discontinuity without a long intro fade.
edge = round(RATE * .002)
middle = (loop[0] + loop[-1]) / 2
ramp = np.linspace(0, 1, edge)
loop[:edge] += (middle - loop[0])[None, :] * (1 - ramp[:, None])
loop[-edge:] += (middle - loop[-1])[None, :] * ramp[:, None]
assert np.max(np.abs(loop[0] - loop[-1])) < 1e-10


def mono_db(samples):
    return 20 * math.log10(math.sqrt(float(np.mean(samples.mean(axis=1) ** 2))))


def soften_peaks(samples):
    # The established Meadow export uses a smooth curve on isolated transients,
    # rather than hard-clamping the waveform. Most samples pass unchanged.
    magnitude = np.abs(samples)
    curved = .75 + .14 * (1 - np.exp(-np.maximum(magnitude - .75, 0) / .14))
    return np.sign(samples) * np.where(magnitude > .75, curved, magnitude)


def encode(source, destination, bitrate):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source),
                    '-codec:a', 'libmp3lame', '-b:a', bitrate,
                    '-metadata', f'title={TITLE}',
                    '-metadata', 'artist=Valhalla', str(destination)], check=True)


def decode(source):
    result = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(source),
                             '-f', 'f32le', '-ac', '2', '-ar', str(RATE), '-'],
                            check=True, capture_output=True)
    return np.frombuffer(result.stdout, dtype='<f4').reshape(-1, 2)


gain = 10 ** ((-23.55 - mono_db(loop)) / 20)
game = OUT / 'music_meadow_night.mp3'
loop_wav = OUT / 'loop.wav'
for _ in range(3):
    affected = np.count_nonzero(np.abs(loop * gain) > .75) / loop.size
    if affected > .001:
        raise ValueError('Repair the dybase2 mix: more than 0.1% of samples need peak control')
    mastered = soften_peaks(loop * gain)
    wavfile.write(loop_wav, RATE, mastered.astype(np.float32))
    encode(loop_wav, game, '128k')
    decoded = decode(game)
    error = -24 - mono_db(decoded)
    if abs(error) < .03:
        break
    gain *= 10 ** (error / 20)
assert abs(mono_db(decoded) + 24) < .05
assert len(decoded) == frames, 'MP3 gapless duration differs from the musical loop'
assert np.max(np.abs(decoded)) < .95, 'Encoded transients are too high'
assert np.max(np.abs(decoded.mean(axis=0))) < .0001, 'DC remains after filtering'

natural = soften_peaks(audio * gain)
assert np.max(np.abs(natural)) < .89
full_wav = OUT / 'natural-ending.wav'
wavfile.write(full_wav, RATE, natural.astype(np.float32))
full = OUT / (re.sub(r'[^A-Za-z0-9._-]+', '_', TITLE) + '.mp3')
encode(full_wav, full, '192k')

# Full arrangement with a steady pulse for human timing review.
click = np.zeros(len(natural))
pulses = [0, 1.5] if METER == '6/8' else list(range(int(BEATS_PER_BAR)))
for bar in range(BARS):
    for beat in pulses:
        frequency, level = (1800, .11) if beat == 0 else (1200, .075)
        start = round((bar * BEATS_PER_BAR + beat) * 60 / BPM * RATE)
        t = np.arange(round(.022 * RATE)) / RATE
        click[start:start + len(t)] += np.sin(2 * np.pi * frequency * t) * np.exp(-190 * t) * level
click_mix = natural * .8 + click[:, None]
assert np.max(np.abs(click_mix)) < 1
click_wav = OUT / 'metronome.wav'
wavfile.write(click_wav, RATE, click_mix.astype(np.float32))
encode(click_wav, OUT / 'metronome.mp3', '192k')
seam = np.concatenate([decoded[-RATE * 4:], decoded[:RATE * 4]])
seam_wav = OUT / 'loop-seam.wav'
wavfile.write(seam_wav, RATE, seam)
encode(seam_wav, OUT / 'loop-seam.mp3', '192k')
levels = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(game),
                          '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True, check=True).stderr
lufs = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', levels)[-1])
peak = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', levels)[-1])
stats = {
    'project_id': SCORE['project_id'], 'title': TITLE,
    'bpm': BPM, 'meter': METER, 'bars': BARS, 'loop_seconds': len(decoded) / RATE,
    'full_seconds': len(natural) / RATE, 'bitrate_kbps': 128,
    'decoded_mono_rms_db': mono_db(decoded), 'integrated_lufs': lufs,
    'true_peak_dbfs': peak, 'decoded_sample_peak_dbfs': 20 * math.log10(float(np.max(np.abs(decoded)))),
    'decoded_dc': decoded.mean(axis=0).tolist(),
    'wav_seam_step': float(np.max(np.abs(mastered[0] - mastered[-1]))),
    'mp3_seam_step': float(np.max(np.abs(decoded[0] - decoded[-1]))),
    'max_internal_step': float(np.max(np.abs(np.diff(decoded, axis=0)))),
    'soft_peak_curve_sample_fraction': affected,
    'game_mp3': str(game), 'natural_ending_mp3': str(full),
    'listening_review': 'Pending: no auditory sign-off; metronome and loop-seam copies prepared',
}
(OUT / 'export.json').write_text(json.dumps(stats, indent=2) + '\n')
print(json.dumps(stats, indent=2))
