#!/usr/bin/env python3
"""Render Waterglass Lullaby: original F-major, 64 BPM, 32-bar underwater city loop.

Soft felt-key melody, slowly changing warm chords and a quiet rounded bass. No
percussion, noise or sharp bells. All releases and stereo echoes wrap around the
loop, so the seam preserves the tail. Needs numpy and ffmpeg, no music service.
"""
import subprocess
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RATE, BPM, BARS = 22050, 64, 32
BEAT = 60 / BPM
N = round(RATE * BARS * 4 * BEAT)


def render():
    out = np.zeros((N, 2), dtype=np.float64)

    def note(midi, beat, beats, amp, voice='keys', pan=0):
        duration = beats * BEAT
        release = 2.4 if voice == 'pad' else 1.6
        t = np.arange(round((duration + release) * RATE)) / RATE
        freq = 440 * 2 ** ((midi - 69) / 12)
        if voice == 'pad':
            env = np.minimum(t / 1.8, 1) * np.minimum(np.maximum((duration + release - t) / release, 0), 1)
            tone = np.sin(2 * np.pi * freq * t) + .13 * np.sin(2 * np.pi * freq * 2 * t) + .03 * np.sin(2 * np.pi * freq * 3 * t)
        elif voice == 'bass':
            env = np.minimum(t / .16, 1) * np.exp(-t / 3.8) * np.minimum(np.maximum((duration + release - t) / .8, 0), 1)
            tone = np.sin(2 * np.pi * freq * t) + .08 * np.sin(2 * np.pi * freq * 2 * t)
        else:
            env = (1 - np.exp(-t / .04)) * np.exp(-t / 1.7) * np.minimum(np.maximum((duration + release - t) / .8, 0), 1)
            tone = np.sin(2 * np.pi * freq * t) + .18 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t / .7) + .035 * np.sin(2 * np.pi * freq * 3 * t) * np.exp(-t / .3)
        samples = tone * env * amp
        ix = (round(beat * BEAT * RATE) + np.arange(len(t))) % N
        for ch, gain in enumerate([np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)]):
            np.add.at(out[:, ch], ix, samples * gain)

    chords = [[53, 57, 60, 64], [48, 55, 59, 62], [50, 57, 60, 65], [46, 53, 57, 60],
              [53, 57, 60, 64], [55, 58, 62, 65], [48, 55, 59, 62], [53, 57, 60, 67]]
    # An eight-bar melody: a rising question and a descending answer, with space between phrases.
    theme = [[(69, 0, 2), (72, 2.5, 1)], [(67, 0, 2), (64, 2.5, 1)],
             [(65, .5, 1.5), (69, 2.5, 1)], [(65, 0, 3)],
             [(69, 0, 1.5), (67, 2, 1)], [(65, .5, 2), (62, 3, .75)],
             [(64, 0, 2), (62, 2.5, 1)], [(60, 0, 3)]]
    for bar in range(BARS):
        chord = chords[(bar // 2) % 8]
        if bar % 2 == 0:
            for i, pitch in enumerate(chord):
                note(pitch, bar * 4, 7.3, .024, 'pad', (i - 1.5) * .2)
            note(chord[0] - 12, bar * 4, 5, .035, 'bass')
        # Quiet broken chords beneath the tune, never a fast or glittering ostinato.
        if 4 <= bar < 28:
            for i, pitch in enumerate(chord[1:]):
                note(pitch + 12, bar * 4 + .5 + i, 1.2, .013, pan=(-1 if i % 2 else 1) * .35)
        if 8 <= bar < 24 or bar >= 28:
            for pitch, offset, length in theme[bar % 8]:
                note(pitch, bar * 4 + offset, length, .047 if bar < 24 else .033, pan=-.1)
    # Gentle space with short, fixed-pitch stereo reflections. Circular shifts preserve the loop.
    dry = out.copy()
    for delay, level in [(0.23, .13), (.41, .1), (.67, .07), (1.11, .04)]:
        out += np.roll(dry[:, ::-1], round(delay * RATE), axis=0) * level
    out -= out.mean(axis=0)
    rms = np.sqrt(np.mean(out ** 2))
    out *= .060 / rms
    peak = float(np.max(np.abs(out)))
    assert peak < .6, peak
    return out


def main():
    out = render()
    wav = '/tmp/valhallasc-waterglass-lullaby.wav'
    with wave.open(wav, 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes((out * 32767).astype('<i2').tobytes())
    target = ROOT / 'client/assets/music_nacre.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-codec:a', 'libmp3lame', '-b:a', '128k',
                    '-metadata', 'title=Waterglass Lullaby', '-metadata', 'artist=Valhalla', str(target)], check=True)
    print(f'Wrote {target}: {N / RATE:.2f}s, RMS {20 * np.log10(np.sqrt(np.mean(out ** 2))):.2f}dB, peak {20 * np.log10(np.max(np.abs(out))):.2f}dB')


if __name__ == '__main__':
    main()
