#!/usr/bin/env python3
"""Fold dybase2's two-second reverb tail into Asterion's exact 32-bar loop and encode the game MP3."""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/valhallasc-asterion-dybase2.wav')
RATE, audio=wavfile.read(SOURCE)
assert RATE==48000 and audio.ndim==2 and audio.shape[1]==2
frames=round(RATE*32*4*60/112)
assert len(audio)>frames+RATE and len(audio)<frames+RATE*3
loop=audio[:frames].astype(np.float64)
tail=audio[frames:].astype(np.float64)
blend=(1-np.arange(len(tail))/len(tail))[:,None]
loop[:len(tail)]+=tail*blend
# Align the very last and first sample with a short, inaudible boundary correction.
n=round(RATE*.025)
mid=(loop[0]+loop[-1])/2
for channel in range(2):
    loop[:n,channel]+=(mid[channel]-loop[0,channel])*(1-np.arange(n)/n)
    loop[-n:,channel]+=(mid[channel]-loop[-1,channel])*(np.arange(n)/n)
loop[0]=mid;loop[-1]=mid
mono=loop.mean(axis=1)
rms=math.sqrt(float(np.mean(mono**2)))
gain=10**(-24/20)/rms
loop*=gain
assert np.max(np.abs(loop))<.95
folded=Path('/tmp/valhallasc-asterion-loop.wav')
wavfile.write(folded,RATE,loop.astype(np.float32))
target=ROOT/'client/assets/music_asterion.mp3'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(folded),'-codec:a','libmp3lame','-b:a','128k',
                '-metadata','title=Seven Rings of Light','-metadata','artist=Valhalla',str(target)],check=True)
print(f'{target}: {frames/RATE:.3f}s, mono RMS {20*math.log10(math.sqrt(float(np.mean(loop.mean(axis=1)**2)))):.2f} dB, '
      f'peak {20*math.log10(float(np.max(np.abs(loop)))):.2f} dB, seam {np.max(np.abs(loop[0]-loop[-1])):.6f}')
