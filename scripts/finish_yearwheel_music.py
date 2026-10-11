#!/usr/bin/env python3
"""Fold dybase2's reverb tail into a seamless Yearwheel game loop."""
import argparse
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('source',nargs='?',type=Path,default=Path('/tmp/valhallasc-yearwheel-four-horizons.wav'))
parser.add_argument('--bars',type=int,default=64)
parser.add_argument('--bpm',type=float,default=100)
parser.add_argument('--title',default='Four Horizons')
args=parser.parse_args()
SOURCE=args.source
RATE,audio=wavfile.read(SOURCE)
assert RATE==48000 and audio.ndim==2 and audio.shape[1]==2
# The Sork-60 Mellow Pad render has a measurable DC offset. Remove it before
# folding the tail and setting level, as in the other repaired zone songs.
audio=sosfiltfilt(butter(2,25,fs=RATE,btype='highpass',output='sos'),audio.astype(np.float64),axis=0)
frames=round(RATE*args.bars*4*60/args.bpm)
assert frames+RATE<len(audio)<frames+RATE*3
loop=audio[:frames].copy()
# Some synths emit a one-time start transient in the offline render. Ease into
# the first phrase before measuring loudness; the folded tail fills this space.
warm=round(RATE*.08)
loop[:warm]*=np.sin(np.linspace(0,np.pi/2,warm))[:,None]**2
tail=audio[frames:]
loop[:len(tail)]+=tail*(1-np.arange(len(tail))/len(tail))[:,None]
n=round(RATE*.025);mid=(loop[0]+loop[-1])/2
for channel in range(2):
    loop[:n,channel]+=(mid[channel]-loop[0,channel])*(1-np.arange(n)/n)
    loop[-n:,channel]+=(mid[channel]-loop[-1,channel])*(np.arange(n)/n)
loop[0]=mid;loop[-1]=mid
rms=math.sqrt(float(np.mean(loop.mean(axis=1)**2)))
peak=float(np.max(np.abs(loop)))
loop*=min(10**(-27/20)/rms,.90/peak)
assert np.max(np.abs(loop))<=.901
folded=Path('/tmp/valhallasc-yearwheel-loop.wav')
wavfile.write(folded,RATE,loop.astype(np.float32))
target=ROOT/'client/assets/music_yearwheel.mp3'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(folded),'-codec:a','libmp3lame','-b:a','192k',
                '-metadata',f'title={args.title}','-metadata','artist=Valhalla',str(target)],check=True)
print(f'{target}: {frames/RATE:.3f}s, mono RMS {20*math.log10(math.sqrt(float(np.mean(loop.mean(axis=1)**2)))):.2f} dB, '
      f'peak {20*math.log10(float(np.max(np.abs(loop)))):.2f} dB, seam {np.max(np.abs(loop[0]-loop[-1])):.6f}')
