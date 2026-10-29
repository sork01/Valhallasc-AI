#!/usr/bin/env python3
"""Build the bundled CC0 sound files from the pinned downloads in docs/combat-feedback.md."""
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

# A fourth archive plus individual voice/spell files; raw downloads carry their original filename.
PACKS.update({
    'fantasy': ('1c2f06ff4e8563b5b8b745b23cf213c1474142a69bb82bd8f5e10d9b3f7a7bbd', 'rubberduck', 'https://opengameart.org/content/80-cc0-rpg-sfx'),
    'female': ('80a9fb09203bb8feb065ba15197609b118cbe167c9a2264670a31ee22c384adb', 'AuraVoice (Nocturnal_Vanguard)', 'https://opengameart.org/content/female-hurt-grunts-groans', 'female.ogg'),
})
MAGIC_HASHES = [
    '119f9061a566c72c1c58444b03f8685b833079ef268dda02fe742eb34d3bc68f',
    '84a70f63f3f21e5ba4a48285b760a663d422ad3feddba2f3cbadd94b76cdc52e',
    '9fac648a1de869cf9ca2f4b3f1cd47f1766a3ee9d2fdec45831234401d7b2392',
    'b7862d109b4013dfb2a389a10f8917203beb0efc458444bc5a1b8ada605cc118',
    '69aaaaed729cacb518005a5d24074196db3c5fffc0ed2cd01ad864fbed4a62be',
    '0a18ee3460cf3fd79c3771bbf94c20c26d34b65ab60d0b0e15694ffcad815955',
    '2817da4f5df69ff993baffd6594a2f2a069f85ee2a02019f97db2246e350a76b',
]
for n, digest in enumerate(MAGIC_HASHES, 1):
    PACKS[f'magic-{n}'] = (digest, 'JaggedStone', 'https://opengameart.org/content/magic-spell-sfx', f'magic-{n}.ogg')

CLIPS.update({
    'sword-2': ('fantasy', 'blade_01.ogg'),
    'sword-3': ('fantasy', 'blade_02.ogg'),
    'dagger-2': ('fantasy', 'blade_03.ogg'),
    'dagger-3': ('rpg', 'OGG/drawKnife2.ogg'),
    'mace-2': ('rpg', 'OGG/cloth3.ogg'),
    'mace-3': ('rpg', 'OGG/cloth4.ogg'),
    'staff-2': ('rpg', 'OGG/drawKnife3.ogg'),
    'bow-2': ('rpg', 'OGG/creak3.ogg'),
    'arrow-2': ('rpg', 'OGG/clothBelt.ogg'),
    'impact-2': ('fantasy', 'metal_01.ogg'),
    'impact-3': ('fantasy', 'item_wood_01.ogg'),
    'metal-2': ('rpg', 'OGG/metalPot2.ogg'),
    'wood-2': ('fantasy', 'wood_01.ogg'),
    'player-hurt-2': ('human', 'yelling sounds/3grunt3.wav'),
    'player-hurt-3': ('human', 'yelling sounds/3grunt5.wav'),
    'player-death-2': ('human', 'yelling sounds/2yell2.wav'),
    'player-death-3': ('human', 'yelling sounds/2yell3.wav'),
    # Offsets isolate separate performances in AuraVoice's seven-take recording.
    'player-female-hurt': ('female', 'female_hurt_grunts_groans_1.ogg', .30, .90),
    'player-female-hurt-2': ('female', 'female_hurt_grunts_groans_1.ogg', 2.06, .75),
    'player-female-hurt-3': ('female', 'female_hurt_grunts_groans_1.ogg', 7.30, .95),
    'player-female-death': ('female', 'female_hurt_grunts_groans_1.ogg', 4.88, 1.30),
    'player-female-death-2': ('female', 'female_hurt_grunts_groans_1.ogg', 9.28, 1.15),
    'player-female-death-3': ('female', 'female_hurt_grunts_groans_1.ogg', 11.65, 1.10),
    'skill-fire': ('fantasy', 'spell_fire_01.ogg'),
    'skill-fire-2': ('fantasy', 'spell_fire_02.ogg'),
    'skill-blast': ('fantasy', 'spell_fire_05.ogg'),
    'skill-earth': ('fantasy', 'stones_01.ogg'),
    'skill-shadow': ('fantasy', 'spell_02.ogg'),
    'skill-arcane': ('fantasy', 'spell_01.ogg'),
    'skill-lightning': ('fantasy', 'spell_fire_07.ogg'),
    'skill-ice': ('magic-2', 'magical_2.ogg'),
    'skill-heal': ('magic-1', 'magical_1_0.ogg', 0, 1.70),
    'skill-holy': ('magic-3', 'magical_3.ogg', 0, 1.90),
    'skill-shield': ('magic-5', 'magical_5.ogg', 0, 1.50),
    'skill-focus': ('magic-6', 'magical_6_0.ogg'),
    'skill-rush': ('rpg', 'OGG/clothBelt2.ogg'),
    'skill-whirl': ('fantasy', 'blade_03.ogg'),
    'achievement': ('magic-7', 'magical_7_0.ogg', 0, 1.60),
    'levelup': ('magic-4', 'magical_4.ogg', 0, 2.50),
})


def build(cache, out):
    packs = {}
    for name, (digest, _, _, *filename) in PACKS.items():
        path = cache / (filename[0] if filename else name + '.zip')
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, f'{name}: source download changed'
        packs[name] = data if filename else zipfile.ZipFile(path)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {'license': 'CC0-1.0', 'licenseUrl': 'https://creativecommons.org/publicdomain/zero/1.0/', 'clips': {}}
    for cue, (pack, member, *trim) in CLIPS.items():
        # Decode to mono, remove leading/trailing silence, cap long takes and fade the edges.
        source = packs[pack] if isinstance(packs[pack], bytes) else packs[pack].read(member)
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-threads', '1', '-i', 'pipe:0', '-ac', '1', '-ar', '44100', '-f', 'f32le', 'pipe:1'], input=source, capture_output=True, check=True).stdout
        samples = array.array('f', raw)
        offset, limit = trim or (0, 1.4)
        if trim:
            samples = samples[int(offset * 44100):int((offset + limit) * 44100)]
        peak = max(abs(v) for v in samples)
        active = [i for i, v in enumerate(samples) if abs(v) > peak * .008]
        assert peak > .001 and active, cue
        start, end = max(0, active[0] - 220), min(len(samples), active[-1] + 442)
        samples = samples[start:min(end, start + int(44100 * limit))]
        gain = .70 / max(abs(v) for v in samples)
        for i in range(len(samples)):
            samples[i] *= gain * min(1, i / 220, (len(samples) - 1 - i) / 882)
        target = out / (cue + '.mp3')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', '44100', '-ac', '1', '-i', 'pipe:0', '-map_metadata', '-1', '-c:a', 'libmp3lame', '-b:a', '96k', str(target)], input=samples.tobytes(), check=True)
        digest, author, url, *filename = PACKS[pack]
        entry = {'file': target.name, 'author': author, 'source': url, 'member': member, 'sourceSha256' if filename else 'archiveSha256': digest, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'duration': round(len(samples) / 44100, 4)}
        if trim:
            entry['sourceOffset'] = offset
            entry['sourceWindow'] = limit
        manifest['clips'][cue] = entry
    (out / 'sources.txt').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    (out / 'LICENSE.txt').write_text('Bundled game effects — CC0 1.0 Universal\nhttps://creativecommons.org/publicdomain/zero/1.0/\n\nKenney: RPG Sounds (weapon and impact foley).\nrubberduck: 80 CC0 creature SFX (mouth performances with filters) and 80 CC0 RPG SFX (weapons, stones and spells).\nHaelDB: Male Grunt/Yelling sounds (human vocals; CC0 option).\nAuraVoice / Nocturnal_Vanguard: Female Hurt Grunts & Groans (original female voice performances).\nJaggedStone: Magic Spell SFX (authored spell and celebration sounds).\n\nSee sources.txt for each source URL, original filename, checksum and voice-take offsets.\nEdits: mono 44.1 kHz, take selection, silence trimming, up to 2.5 seconds, peak normalization, edge fades and MP3 encoding.\nPlayback applies subtle random pitch, volume and low-pass variation; alternate takes avoid immediate repeats.\n\nOriginal Kenney license notice:\n' + packs['rpg'].read('license.txt').decode('utf-8-sig').replace('\r\n', '\n'))
    print(f'Built {len(CLIPS)} recordings ({sum(p.stat().st_size for p in out.glob("*.mp3")):,} bytes)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path, help='directory containing the pinned source downloads')
    parser.add_argument('--output', type=Path, default=ROOT / 'client/assets/combat')
    args = parser.parse_args()
    build(args.cache, args.output)
