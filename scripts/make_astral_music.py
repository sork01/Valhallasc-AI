#!/usr/bin/env python3
"""Render The Falling Garden: original 5/4, F# minor, 108 BPM, 32 bars.

Four eight-bar movements take a five-note motif from glass to bowed lead,
through a brighter bridge, and home. Circular releases keep the loop seamless.
"""
import math
import subprocess
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RATE, BPM, BARS, METER = 22050, 108, 32, 5
BEAT = 60 / BPM
COUNT = round(RATE * BARS * METER * BEAT)


def render():
    mix = np.zeros((COUNT, 2), dtype=np.float64)

    def add(midi, at, duration, volume, voice, pan=0):
        release = {'glass': 1.2, 'wood': .9, 'strings': 2.2, 'horn': 1.15, 'bass': .9}[voice]
        t = np.arange(round((duration * BEAT + release) * RATE), dtype=np.float64) / RATE
        phase = 2 * math.pi * 440 * 2 ** ((midi - 69) / 12) * t
        if voice == 'glass':
            tone = np.sin(phase) + .38*np.sin(phase*2.007)*np.exp(-t/1.2) + .17*np.sin(phase*3.97)*np.exp(-t/.42)
            env = (1-np.exp(-t/.008))*np.exp(-t/1.15)
        elif voice == 'wood':
            tone = np.sin(phase)+.28*np.sin(phase*2)*np.exp(-t/.45)+.08*np.sin(phase*3)*np.exp(-t/.3)
            env = (1-np.exp(-t/.006))*np.exp(-t/.65)
        elif voice == 'strings':
            tone = (np.sin(phase)+.32*np.sin(phase*2)+.13*np.sin(phase*3)+.05*np.sin(phase*4))*(1+.08*np.sin(2*math.pi*4.7*t))
            env = np.minimum(t/.52,1)
        elif voice == 'horn':
            tone = (np.sin(phase)+.35*np.sin(phase*2)+.14*np.sin(phase*3))*(1+.025*np.sin(2*math.pi*5.1*t))
            env = np.minimum(t/.09,1)
        else:
            tone = np.sin(phase)+.15*np.sin(phase*2)*np.exp(-t/1.2)
            env = np.minimum(t/.018,1)*np.exp(-t/2.5)
        sound = tone*env*np.clip((duration*BEAT+release-t)/release,0,1)*volume
        start = round(at*BEAT*RATE)%COUNT
        first = min(len(sound),COUNT-start)
        for channel,gain in enumerate((math.sqrt((1-pan)/2),math.sqrt((1+pan)/2))):
            mix[start:start+first,channel] += sound[:first]*gain
            if first<len(sound):mix[:len(sound)-first,channel] += sound[first:]*gain

    chords = [
        [42,49,57,61,68], [38,45,54,57,61], [47,54,59,61,66], [40,47,56,59,64],
        [37,44,54,59,64], [42,49,57,61,66], [45,52,57,61,64], [37,44,53,59,64],
    ]
    melody = [
        [(73,0,.9),(76,1,1),(78,2,1.8),(76,4,.8)],
        [(74,0,1.7),(73,2,.9),(71,3,1.8)],
        [(71,.5,.8),(73,1.5,.9),(78,2.5,1.3),(76,4,.8)],
        [(68,0,1.7),(71,2,1),(73,3,1.5)],
        [(73,0,1),(71,1,1),(68,2,1),(66,3,1.7)],
        [(69,0,1.8),(73,2,.9),(76,3,1.8)],
        [(73,.5,1),(76,2,1),(78,3,1.7)],
        [(76,0,1),(73,1,1),(68,2,1),(66,3,1.8)],
    ]
    for bar in range(BARS):
        b=bar*METER; chord=chords[bar%8]; section=bar//8
        for k,pitch in enumerate(chord[1:]):add(pitch,b,4.9,.009 if section==0 else .012,'strings',(k-1.5)*.22)
        for offset,pitch in [(0,chord[0]),(3,chord[0]+12)]:add(pitch,b+offset,1.8,.036 if section in (1,2) else .026,'bass',-.08)
        pattern=[1,3,None,2,4] if section!=2 else [3,None,2,4,1]
        for j,k in enumerate(pattern):
            if k is not None:add(chord[k]+12,b+j,.48,.012 if section==0 else .016,'wood',.33 if j%2 else -.33)
        if bar>=4:
            for pitch,offset,length in melody[bar%8]:
                pitch += 12 if section==2 and offset==2 else 0
                voice='glass' if section in (0,3) else 'horn'
                add(pitch,b+offset,length,.040 if voice=='glass' else .028,voice,-.15)
        if 12<=bar<28 and bar%2==0:
            add(chord[2]+12,b+1.5,1.25,.023,'glass',.42)
            add(chord[3]+12,b+3.5,1.25,.018,'glass',.42)
    dry=mix.copy()
    for delay,level in [(.18,.09),(.43,.075),(.79,.05),(.15+BEAT*.5,.035)]:
        mix+=np.roll(dry[:,::-1],round(delay*RATE),axis=0)*level
    mix-=mix.mean(axis=0)
    mix*=.058/np.sqrt(np.mean(mix**2))
    assert np.max(np.abs(mix))<.8
    return mix


def main():
    sound=render(); wav=Path('/tmp/valhallasc-the-falling-garden.wav')
    with wave.open(str(wav),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE)
        f.writeframes((sound*32767).astype('<i2').tobytes())
    dest=ROOT/'client/assets/music_astral.mp3'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-af','highpass=f=25',
                    '-codec:a','libmp3lame','-b:a','128k','-metadata','title=The Falling Garden',
                    '-metadata','artist=Valhalla',str(dest)],check=True)
    print(f'{dest}: {COUNT/RATE:.2f}s, RMS {20*np.log10(np.sqrt(np.mean(sound**2))):.2f} dB, peak {20*np.log10(np.max(np.abs(sound))):.2f} dB')


if __name__=='__main__':main()
