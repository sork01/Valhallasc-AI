#!/usr/bin/env python3
"""Install the pinned FileDrop recordings without altering arrangements.

Decode the exact FileDrop MP3. Fold any exported reverb bar into the pinned
musical loop, then apply the game's DC/level treatment and encode at 128 kbps. Earlier
imports and recordings without a replacement are hash-checked and retained. Default invocation checks provenance only.
"""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'scripts/soundtrack-filedrop.txt'
RATE = 44100


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(path):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-threads', '1', '-i', str(path),
                                   '-f', 'f32le', '-ac', '2', '-ar', str(RATE), 'pipe:1'])
    audio = np.frombuffer(raw, dtype='<f4').reshape(-1, 2)
    assert len(audio) > RATE * 20 and np.isfinite(audio).all(), path
    return audio


def measure(audio):
    mono = audio.mean(axis=1)
    return dict(seconds=round(len(audio) / RATE, 6),
                mono_rms_db=round(20 * math.log10(float(np.sqrt(np.mean(mono ** 2)))), 4),
                peak_db=round(20 * math.log10(float(np.max(np.abs(audio)))), 4),
                seam_delta=round(float(np.max(np.abs(audio[0] - audio[-1]))), 6))


def install(source, target, title, scratch, loop_seconds):
    audio = decode(source).astype(np.float64)
    frames = round(loop_seconds * RATE)
    assert frames <= len(audio) + 1 and len(audio) - frames < RATE * 4
    tail = audio[frames:].copy()
    audio = audio[:frames].copy()
    if len(tail):
        audio[:len(tail)] += tail * np.linspace(1, 0, len(tail))[:, None]
    seconds = len(audio) / RATE
    sos = butter(2, 25, fs=RATE, btype='highpass', output='sos')
    # Seed the filter from cyclic history instead of introducing a startup transient.
    _, history = sosfilt(sos, audio, axis=0, zi=np.zeros((len(sos), 2, 2)))
    audio, _ = sosfilt(sos, audio, axis=0, zi=history)
    n = round(RATE * .003)
    midpoint = (audio[0] + audio[-1]) / 2
    audio[:n] += (midpoint - audio[0])[None, :] * np.linspace(1, 0, n)[:, None]
    audio[-n:] += (midpoint - audio[-1])[None, :] * np.linspace(0, 1, n)[:, None]
    rms = float(np.sqrt(np.mean(audio.mean(axis=1) ** 2)))
    audio *= min(10 ** (-23.55 / 20) / rms, .89 / float(np.max(np.abs(audio))))
    wav = scratch / 'loop.wav'
    wavfile.write(wav, RATE, audio.astype(np.float32))
    output = scratch / 'loop.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-threads', '1', '-i', str(wav),
                    '-c:a', 'libmp3lame', '-b:a', '128k', '-metadata', 'title=' + title,
                    '-metadata', 'artist=Valhalla Saga', str(output)], check=True)
    metrics = measure(decode(output))
    assert abs(metrics['seconds'] - seconds) < .002, metrics
    assert -24.8 < metrics['mono_rms_db'] < -23.2 and metrics['peak_db'] < -.5, metrics
    target.write_bytes(output.read_bytes())
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--filedrop', type=Path,
                        default=Path('/home/serveperry/webserver/www/filedrop/data/Sork/files'))
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    assets = ROOT / 'client/assets'
    for name, expected in manifest['preserved'].items():
        assert sha(assets / name) == expected, 'Preserved recording changed: ' + name
    scratch_root = ROOT / 'test-results/soundtrack-import'
    if args.apply:
        scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch_root if args.apply else None) as temp:
        for track in manifest['tracks']:
            source = args.filedrop / track['source']
            assert sha(source) == track['source_sha256'], 'FileDrop source changed: ' + track['source']
            target = assets / ('music_' + track['slot'] + '.mp3')
            if track.get('game_sha256'):
                assert sha(target) == track['game_sha256'], 'Installed recording changed: ' + str(target)
                if args.apply and 'seconds' not in track:
                    track.update(measure(decode(target)))
            elif args.apply:
                track.update(install(source, target, track['title'], Path(temp), track['loop_seconds']))
                track['game_sha256'] = sha(target)
                # Keep a resumable receipt after each successful conversion.
                MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
                print(f"Installed {track['slot']}: {track['seconds']:.3f}s, {track['mono_rms_db']:.2f} dB RMS", flush=True)
        if args.apply:
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f"Verified {len(manifest['tracks'])} source recordings and {len(manifest['preserved'])} preserved tracks", flush=True)


if __name__ == '__main__':
    main()
