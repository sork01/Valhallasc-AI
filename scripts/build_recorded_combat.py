#!/usr/bin/env python3
"""Build the bundled CC0 recordings. Download the three archives in docs/combat-feedback.md first."""
import argparse
import array
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKS = {
    'rpg': ('3ae398ad63e293f9c450bda22d5d81c3af69c74df66fc1400f33c012c0bbc231', 'Kenney', 'https://opengameart.org/content/50-rpg-sound-effects'),
    'creature': ('5d4002eea42f278e76543bb36e8ddd2cb978588a13271984191d8228f5d26768', 'rubberduck', 'https://opengameart.org/content/80-cc0-creature-sfx'),
    'human': ('e9100a4e3b9dcd146993089970dc6097dcf9935fa4683b196040012bad65d67a', 'HaelDB', 'https://opengameart.org/content/male-gruntyelling-sounds'),
}
CLIPS = {
    'sword': ('rpg', 'OGG/knifeSlice.ogg'),
    'dagger': ('rpg', 'OGG/knifeSlice2.ogg'),
    'mace': ('rpg', 'OGG/cloth1.ogg'),
    'staff': ('rpg', 'OGG/drawKnife1.ogg'),
    'bow': ('rpg', 'OGG/creak1.ogg'),
    'arrow': ('rpg', 'OGG/cloth2.ogg'),
    'impact': ('rpg', 'OGG/chop.ogg'),
    'metal': ('rpg', 'OGG/metalPot1.ogg'),
    'wood': ('rpg', 'OGG/creak2.ogg'),
    'beast-attack': ('creature', 'roar_01.ogg'),
    'beast-hurt': ('creature', 'hurt_01.ogg'),
    'beast-death': ('creature', 'monster_01.ogg'),
    'insect-attack': ('creature', 'bug_01.ogg'),
    'insect-hurt': ('creature', 'bug_03.ogg'),
    'insect-death': ('creature', 'bug_02.ogg'),
    'undead-attack': ('creature', 'monster_03.ogg'),
    'undead-hurt': ('creature', 'hurt_03.ogg'),
    'undead-death': ('creature', 'scream_01.ogg'),
    'plant-attack': ('creature', 'grunt_01.ogg'),
    'plant-hurt': ('creature', 'hurt_02.ogg'),
    'plant-death': ('creature', 'monster_05.ogg'),
    'water-attack': ('creature', 'burble_01.ogg'),
    'water-hurt': ('creature', 'spit_01.ogg'),
    'water-death': ('creature', 'burble_02.ogg'),
    'ranged-attack': ('creature', 'alien_01.ogg'),
    'ranged-hurt': ('creature', 'hurt_04.ogg'),
    'ranged-death': ('creature', 'alien_02.ogg'),
    'player-hurt': ('human', 'yelling sounds/3grunt4.wav'),
    'player-death': ('human', 'yelling sounds/2yell1.wav'),
}


def build(cache):
    packs = {}
    for name, (digest, _, _) in PACKS.items():
        data = (cache / (name + '.zip')).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, f'{name}: source archive changed'
        packs[name] = zipfile.ZipFile(cache / (name + '.zip'))
    out = ROOT / 'client/assets/combat'
    out.mkdir(parents=True, exist_ok=True)
    manifest = {'license': 'CC0-1.0', 'licenseUrl': 'https://creativecommons.org/publicdomain/zero/1.0/', 'clips': {}}
    for cue, (pack, member) in CLIPS.items():
        # Decode to mono, remove leading/trailing silence, cap long takes and fade the edges.
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-ac', '1', '-ar', '44100', '-f', 'f32le', 'pipe:1'], input=packs[pack].read(member), capture_output=True, check=True).stdout
        samples = array.array('f', raw)
        peak = max(abs(v) for v in samples)
        active = [i for i, v in enumerate(samples) if abs(v) > peak * .008]
        assert peak > .001 and active, cue
        start, end = max(0, active[0] - 220), min(len(samples), active[-1] + 442)
        samples = samples[start:min(end, start + int(44100 * 1.4))]
        gain = .70 / max(abs(v) for v in samples)
        for i in range(len(samples)):
            samples[i] *= gain * min(1, i / 220, (len(samples) - 1 - i) / 882)
        target = out / (cue + '.mp3')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', '44100', '-ac', '1', '-i', 'pipe:0', '-map_metadata', '-1', '-c:a', 'libmp3lame', '-b:a', '96k', str(target)], input=samples.tobytes(), check=True)
        digest, author, url = PACKS[pack]
        manifest['clips'][cue] = {'file': target.name, 'author': author, 'source': url, 'member': member, 'archiveSha256': digest, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'duration': round(len(samples) / 44100, 4)}
    (out / 'sources.txt').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    (out / 'LICENSE.txt').write_text('Recorded combat effects — CC0 1.0 Universal\nhttps://creativecommons.org/publicdomain/zero/1.0/\n\nKenney: RPG Sounds (weapon and impact foley).\nrubberduck: 80 CC0 creature SFX (recorded mouth performances with filters).\nHaelDB: Male Grunt/Yelling sounds (recorded human vocals; CC0 option).\n\nSee sources.txt for each source URL, original filename and checksum.\nEdits: mono 44.1 kHz, silence trimming, maximum 1.4 seconds, peak normalization, edge fades and MP3 encoding.\n\nOriginal Kenney license notice:\n' + packs['rpg'].read('license.txt').decode('utf-8-sig').replace('\r\n', '\n'))
    print(f'Built {len(CLIPS)} recordings ({sum(p.stat().st_size for p in out.glob("*.mp3")):,} bytes)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path, help='directory containing rpg.zip, creature.zip and human.zip')
    build(parser.parse_args().cache)
