#!/usr/bin/env python3
"""Export dybase2 raid renders: cyclic DC removal, tail fold and decoded RMS.

The natural-ending MP3s stay in test-results/raid-music; FileDrop is on request.
Use --install to copy the checked game loops into client/assets.
"""
import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/raid-music'
SONGS = [('forge', 'Nine Chains Below', 152, 'chained_forge'),
         ('eldmarr', 'The Table He Was Promised', 160, 'eldmarr')]


def encode(source, target, bitrate, title):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-codec:a', 'libmp3lame',
                    '-b:a', bitrate, '-metadata', f'title={title}', '-metadata', 'artist=Valhalla',
                    str(target)], check=True)


def decode(path):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le',
                                   '-ar', '48000', '-ac', '2', 'pipe:1'])
    return np.frombuffer(raw, dtype='<f4').reshape(-1, 2)


def db(value):
    return 20 * math.log10(max(float(value), 1e-12))


def export(key, title, bpm, asset, install):
    project = json.loads((OUT / f'{key}-project.json').read_text())
    rate, raw = wavfile.read(OUT / f'{key}-render.wav')
    assert rate == 48000 and raw.ndim == 2 and raw.shape[1] == 2
    audio = raw.astype(np.float64)
    if np.issubdtype(raw.dtype, np.integer):
        audio /= np.iinfo(raw.dtype).max
    assert np.isfinite(audio).all()
    frames = round(rate * 64 * 4 * 60 / bpm)
    assert frames + rate * 3.9 <= len(audio) <= frames + rate * 4.1
    assert np.max(np.abs(audio)) < 1, 'Fix the source mix before exporting clipped audio'
    loop = audio[:frames].copy()
    tail = audio[frames:].copy()
    tail *= np.linspace(1, 0, len(tail))[:, None]
    loop[:len(tail)] += tail
    sos = butter(2, 25, fs=rate, btype='highpass', output='sos')
    # Prime from the previous cycle to avoid a high-pass startup transient.
    _, state = sosfilt(sos, loop, axis=0, zi=np.zeros((len(sos), 2, 2)))
    loop, _ = sosfilt(sos, loop, axis=0, zi=state)
    n = round(rate * .003)
    mid = (loop[0] + loop[-1]) / 2
    loop[:n] += (mid - loop[0]) * np.linspace(1, 0, n)[:, None]
    loop[-n:] += (mid - loop[-1]) * np.linspace(0, 1, n)[:, None]
    rms = np.sqrt(np.mean(loop.mean(axis=1) ** 2))
    gain_db = -23.55 - db(rms)
    wav = OUT / f'music_{asset}-loop.wav'
    mp3 = OUT / f'music_{asset}.mp3'
    # Verify the actual encoded/decoded file rather than assuming codec loss.
    for _ in range(3):
        mixed = loop * 10 ** (gain_db / 20)
        assert np.max(np.abs(mixed)) < .92
        wavfile.write(wav, rate, mixed.astype(np.float32))
        encode(wav, mp3, '128k', title)
        decoded = decode(mp3)
        decoded_rms = db(np.sqrt(np.mean(decoded.mean(axis=1) ** 2)))
        if abs(decoded_rms + 24) < .03:
            break
        gain_db += -24 - decoded_rms
    peak_db = db(np.max(np.abs(decoded)))
    assert abs(decoded_rms + 24) < .05 and peak_db < -1
    assert abs(len(decoded) / rate - frames / rate) < .04
    seam = float(np.max(np.abs(decoded[0] - decoded[-1])))
    assert seam < .03, f'Decoded seam needs attention: {seam}'
    full = sosfilt(sos, audio, axis=0)
    full[-rate * 4:] *= np.linspace(1, 0, rate * 4)[:, None]
    full *= 10 ** (gain_db / 20)
    assert np.max(np.abs(full)) < .95
    natural = OUT / (title + '.wav')
    wavfile.write(natural, rate, full.astype(np.float32))
    encode(natural, OUT / (title + '.mp3'), '192k', title)
    bars = [db(np.sqrt(np.mean(decoded[round(b * 4 * 60 / bpm * rate):
                                            round((b + 1) * 4 * 60 / bpm * rate)].mean(axis=1) ** 2)))
            for b in range(64)]
    assert min(bars) > -42, 'Unexpected silent bar'
    info = dict(project_id=project['project_id'], title=title, bpm=bpm, key='F# minor', meter='4/4',
                bars=64, seconds=len(decoded) / rate, bitrate=128000, mono_rms_db=decoded_rms,
                peak_db=peak_db, gain_db=gain_db, dc=np.mean(decoded, axis=0).tolist(),
                pcm_seam_delta=float(np.max(np.abs(mixed[0] - mixed[-1]))),
                decoded_seam_delta=seam, clipped_samples=int(np.sum(np.abs(decoded) >= 1)),
                bar_mono_rms_db=bars, auditioned=False, asset=f'assets/music_{asset}.mp3')
    (OUT / f'{key}-export.json').write_text(json.dumps(info, indent=2) + '\n')
    if install:
        shutil.copyfile(mp3, ROOT / 'client/assets' / mp3.name)
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    report = [export(*song, args.install) for song in SONGS]
    print(json.dumps([{k: r[k] for k in ['title', 'seconds', 'mono_rms_db', 'peak_db', 'decoded_seam_delta']}
                      for r in report], indent=2))
