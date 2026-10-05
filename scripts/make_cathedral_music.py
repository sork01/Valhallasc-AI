#!/usr/bin/env python3
"""Three original, melodic Cathedral loops, with circular release/reverb tails.

Left: Stillwater Vespers, D Dorian, 66 BPM, 3/4, soft choir and felt keys.
Right: Pearls Behind Glass, G minor, 84 BPM, 6/8 (quarter BPM), harp and glass harmonics.
Main: Heart of the Drowned Tide, C minor, 60 BPM, 4/4, pipe organ and low choir.
Each has its own harmony, melody, rhythm, timbre, and exact 32-bar loop; no sharp hats/noise.
"""
import subprocess
import wave
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RATE=22050
SCORES=[
    dict(id='cloister',title='Stillwater Vespers',bpm=66,beats=3,voice='keys',
         chords=[[50,57,60,64],[53,57,60,65],[48,55,60,64],[55,59,62,65]],
         melody=[[69,72,71],[67,65,64],[65,69,67],[62,64,65],[69,67,65],[64,62,60],[62,65,64],[62,57,62]]),
    dict(id='reliquary',title='Pearls Behind Glass',bpm=84,beats=3,voice='harp',
         chords=[[55,58,62,67],[51,58,63,67],[53,57,60,65],[50,57,60,66]],
         melody=[[74,77,79],[77,74,70],[75,79,77],[74,72,70],[72,75,77],[75,72,69],[74,78,76],[74,70,67]]),
    dict(id='nave',title='Heart of the Drowned Tide',bpm=60,beats=4,voice='organ',
         chords=[[48,55,60,63],[44,51,56,60],[41,48,53,56],[43,50,55,59]],
         melody=[[67,63,62],[60,62,63],[68,67,65],[63,62,60],[65,68,67],[63,60,56],[62,65,59],[60,55,60]]),
]

def render(s):
    beat=60/s['bpm']; N=round(RATE*32*s['beats']*beat); out=np.zeros((N,2),np.float64)
    def note(midi,start,length,amp,voice,pan=0):
        dur=length*beat; release=3 if voice in ('choir','organ') else 1.8
        t=np.arange(round((dur+release)*RATE))/RATE; phase=2*np.pi*440*2**((midi-69)/12)*t
        if voice=='choir':
            tone=np.sin(phase)+.17*np.sin(phase*2)+.06*np.sin(phase*3)
            env=np.minimum(t/.7,1)*np.minimum(np.maximum((dur+release-t)/release,0),1)
        elif voice=='organ':
            tone=np.sin(phase)+.35*np.sin(phase*2)+.17*np.sin(phase*3)+.04*np.sin(phase*4)
            env=np.minimum(t/.18,1)*np.minimum(np.maximum((dur+release-t)/release,0),1)
        elif voice=='harp':
            tone=np.sin(phase)+.3*np.sin(phase*2)*np.exp(-t/.6)+.15*np.sin(phase*3)*np.exp(-t/.35)
            env=(1-np.exp(-t/.012))*np.exp(-t/1.05)*np.minimum(np.maximum((dur+release-t)/.8,0),1)
        elif voice=='bass':
            tone=np.sin(phase)+.1*np.sin(phase*2);env=np.minimum(t/.12,1)*np.exp(-t/4)*np.minimum(np.maximum((dur+release-t)/.8,0),1)
        else:
            tone=np.sin(phase)+.13*np.sin(phase*2)*np.exp(-t/.7);env=(1-np.exp(-t/.035))*np.exp(-t/2.1)*np.minimum(np.maximum((dur+release-t)/.8,0),1)
        ix=(round(start*beat*RATE)+np.arange(len(t)))%N
        for ch,gain in enumerate([np.sqrt((1-pan)/2),np.sqrt((1+pan)/2)]):np.add.at(out[:,ch],ix,tone*env*amp*gain)
    for bar in range(32):
        b=bar*s['beats']; chord=s['chords'][(bar//2)%4]
        if bar%2==0:
            for i,p in enumerate(chord):note(p,b,s['beats']*2-.25,.026,'organ' if s['id']=='nave' else 'choir',(i-1.5)*.22)
            note(chord[0]-12,b,s['beats']*1.5,.045,'bass')
        if s['id']=='reliquary':
            for k in range(6):note(chord[k%4]+12,b+k*.5,.4,.022,'harp',.4 if k%2 else -.4)
        elif s['id']=='cloister' and bar%2:
            note(chord[1]+12,b+.5,1.5,.022,'keys',.3)
        if 4<=bar<28 or bar>=30:
            melody=s['melody'][bar%8]; starts=[0,1.5,2.25] if s['beats']==3 else [0,2,3]
            for k,p in enumerate(melody):
                if bar%4==3 and k==2:continue
                note(p,b+starts[k],[1.4,.7,.6][k] if s['beats']==3 else [1.8,.8,.8][k],.054 if s['voice']!='organ' else .034,s['voice'],-.1)
    dry=out.copy()
    for delay,level in [(.19,.12),(.37,.1),(.63,.08),(1.1,.045),(1.7,.025)]:out+=np.roll(dry[:,::-1],round(delay*RATE),axis=0)*level
    out-=out.mean(axis=0);out*=.065/np.sqrt(np.mean(out**2))
    assert np.max(np.abs(out))<.8
    return out

def main():
    for s in SCORES:
        out=render(s); wav=Path('/tmp')/('cathedral-'+s['id']+'.wav')
        with wave.open(str(wav),'wb') as f:
            f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE);f.writeframes((out*32767).astype('<i2').tobytes())
        target=ROOT/'client/assets'/('music_cathedral_'+s['id']+'.mp3')
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-af','highpass=f=25','-codec:a','libmp3lame','-b:a','128k','-metadata','title='+s['title'],'-metadata','artist=Valhalla',str(target)],check=True)
        print(f"{s['title']}: {len(out)/RATE:.2f}s, RMS {20*np.log10(np.sqrt(np.mean(out**2))):.2f} dB, peak {20*np.log10(np.max(np.abs(out))):.2f} dB")
if __name__=='__main__':main()
