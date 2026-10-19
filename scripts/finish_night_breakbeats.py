#!/usr/bin/env python3
"""Fold dybase2's night-breakbeat renders into level-matched game loops."""
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000
# zone, title, quarter-note beats per bar, tempo
SCORES = [
    ('meadow', 'Fireflies on the Path', 3, 100),
    ('crags', 'Embers Beneath the Ridge', 4, 92),
    ('rime', 'Stars Beneath the Ice', 3, 88),
    ('fen', 'Lights Across the Mere', 4, 90),
    ('city', 'The Last Lantern', 3, 90),
    ('wyrd', 'Lanterns Under the Ash', 3, 82),
    ('sky', 'Stars Above the Rift', 4, 76),
    ('nacre', 'Pearls Beneath the Moon', 3, 90),
    ('astral', 'Garden of Distant Stars', 5, 96),
    ('prism', 'Saltglass Afterglow', 4, 84),
]


def export(zone, title, beats, bpm):
    rate, audio = wavfile.read(f'/tmp/valhallasc-{zone}-night-dybase2.wav')
    assert rate == RATE and audio.ndim == 2 and audio.shape[1] == 2
    audio = sosfiltfilt(butter(2, 25, fs=RATE, btype='highpass', output='sos'),
                       audio.astype(np.float64), axis=0)
    frames = round(RATE * 32 * beats * 60 / bpm)
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
    # 128 kbps MP3 encoding lowers these loops' mono RMS by about 0.45 dB.
    target_rms = 10 ** (-23.55 / 20)
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
    game = ROOT / f'client/assets/music_{zone}_night.mp3'
    full = Path(f'/tmp/valhallasc-{zone}-night-filedrop/music_{zone}_night.mp3')
    full.parent.mkdir(parents=True, exist_ok=True)
    for target, wav, bitrate in [
        (game, loop, '128k'),
        (full, audio, '192k'),
    ]:
        source = Path(f'/tmp/valhallasc-{zone}-night-{bitrate}.wav')
        wavfile.write(source, RATE, wav.astype(np.float32))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source),
                        '-codec:a', 'libmp3lame', '-b:a', bitrate,
                        '-metadata', f'title={title}', '-metadata', 'artist=Valhalla',
                        str(target)], check=True)
    rms = 20 * math.log10(math.sqrt(float(np.mean(loop.mean(axis=1) ** 2))))
    peak = 20 * math.log10(float(np.max(np.abs(loop))))
    seam = float(np.max(np.abs(loop[0] - loop[-1])))
    print(f'{zone}: {frames/RATE:.3f}s loop, mono RMS {rms:.2f} dB, '
          f'peak {peak:.2f} dB, seam {seam:.6f}; natural ending {len(audio)/RATE:.3f}s')


if __name__ == '__main__':
    import sys
    requested = set(sys.argv[1:])
    for score in SCORES:
        if not requested or score[0] in requested:
            export(*score)
