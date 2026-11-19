#!/usr/bin/env python3
"""Export the saved dybase2 cue render as short mono MP3s, matching boss SFX."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CUES={'cast':.65,'plop':.5,'bite':.7,'reel':.7,'catch':1.0,'legendary':2.0,'lava':1.0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wav',type=Path,default=Path('/tmp/valhalla-fishing-cues.wav'))
    p.add_argument('--project',type=Path,default=Path('/tmp/valhalla-fishing-sound-project.json'))
    a=p.parse_args(); project=json.loads(a.project.read_text())['project_id']
    meta={'project':project,'bpm':120,'meter':'4/4','source':'dybase2 MCP; scripts/create_fishing_sounds.sh','clips':{}}
    for n,(cue,duration) in enumerate(CUES.items()):
        # Each cue begins at its marker, every two 120 BPM 4/4 bars (4 seconds).
        # Normalise each independently so the quiet noise cues remain audible.
        import numpy as np
        raw=subprocess.run(['ffmpeg','-v','error','-i',str(a.wav),'-ss',str(n*4),'-t',str(duration),'-ac','1','-ar','44100','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
        samples=np.frombuffer(raw,dtype='<f4').copy()
        assert np.isfinite(samples).all() and np.max(np.abs(samples))>.0001,cue
        samples*=.65/np.max(np.abs(samples))
        target=ROOT/'client/assets'/f'sfx_fish_{cue}.mp3'
        subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar','44100','-ac','1','-i','pipe:0','-af',f'highpass=f=25,afade=t=in:d=0.005,afade=t=out:st={duration-.06}:d=0.06','-map_metadata','-1','-c:a','libmp3lame','-b:a','96k',str(target)],input=samples.tobytes(),check=True)
        meta['clips'][cue]={'file':target.name,'bar':n*2+1,'duration':duration,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    (ROOT/'client/assets/fishing-sounds.txt').write_text(json.dumps(meta,indent=2)+'\n')
    print('Exported seven fishing cues from dybase2 project',project)


if __name__=='__main__':main()
