#!/usr/bin/env python3
"""Upload the owner's requested Emberwake review bundle, with verified hashes.

Run only when an upload is explicitly requested. Takes the successful UI
artifact directory as its one argument. The existing FileDrop helper writes
the metadata sidecars as www-data and verifies each uploaded file.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from emberwake_content import ENEMIES
ROOT=Path(__file__).resolve().parents[1]

def main():
    ui=Path(sys.argv[1]).resolve();out=ROOT/'test-results/emberwake'
    pictures=[('asterion','Asterion - The Warm North Road'),('arrival','Emberwake - Arrival'),
        ('causeway','Emberwake - Basalt Causeway'),('lava','Emberwake - Molten River'),('shackle','Emberwake - Eastern Shackle'),
        ('bellows','Emberwake - Bellows Basin'),('door-day','Emberwake - Nine-Chain Door by Day'),
        ('door-night','Emberwake - Nine-Chain Door at Night'),('door-mobile','Emberwake - Mobile View')]
    files=[(ui/f'emberwake-{key}-real.png',title+'.png','image/png') for key,title in pictures]
    files += [(ui/'emberwake-map.png','Emberwake Caldera - Zone Map.png','image/png'),
        (out/'emberwake-enemy-cast.png','Emberwake Caldera - Enemy Cast.png','image/png')]
    files += [(out/f"emberwake-sheet-{e['kind']}.png",'Emberwake - '+e['name']+' - Full Sprite Sheet.png','image/png') for e in ENEMIES]
    files += [(out/(title+'.mp3'),'Emberwake - '+title+'.mp3','audio/mpeg') for title in ['Heat Beneath the Stones','The Chains Dream']]
    for source,_,_ in files:assert source.is_file(),source
    report=[]
    for source,title,mime in files:
        subprocess.run(['bash',str(ROOT/'scripts/filedrop_put.sh'),str(source),title,mime],check=True)
        report.append(dict(source=str(source),original_name=title,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),bytes=source.stat().st_size))
    (out/'filedrop-upload.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Uploaded and verified {len(files)} Emberwake review files')
if __name__=='__main__':main()
