#!/usr/bin/env python3
"""Build the checked-in Swedish client catalog; run manually when English copy changes.

The translation service is used at build time only. No game text or player data is sent
from the browser. Existing translations are retained so reruns need only new strings.
"""
import concurrent.futures
import glob
import html.parser
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'scripts' / 'sv-translations.txt'
OUTPUT = ROOT / 'client' / 'sv-data.js'
TEMPLATE_CACHE = ROOT / 'scripts' / 'sv-template-translations.txt'
KEYS = {'name', 'title', 'description', 'label', 'dialogue', 'role'}
ITEM_WORDS = {
    'Health Potion':'hälsodryck', 'Mana Potion':'manadryck', 'Slime Gel':'slemgelé',
    "Apprentice's":'lärlingens', "Pilgrim's":'pilgrimens', "Scout's":'spejarens', "Hunter's":'jägarens', "Traveler's":'resenärens',
    'Ironhide':'järnhud', 'Moonveil':'månslöja', 'Nightweave':'nattsväv', 'Wildwarden':'vildväktare', 'Wayfarer':'vandrare',
    'Tempered':'härdad', 'Weathered':'väderbiten', 'Gilded':'förgylld', 'Battered':'sliten', 'Reinforced':'förstärkt',
    'Exalted':'upphöjd', 'Faded':'bleknad', 'Veteran':'veteran', 'Radiant':'strålande', 'Ancient':'uråldrig',
    'Runed':'runristad', 'Hardened':'härdad', 'Heroic':'hjältemodig', 'Mythic':'mytisk', 'Legendary':'legendarisk',
    'Divine':'gudomlig', 'Eternal':'evig', 'Grand':'stor', 'Supreme':'överlägsen', 'Greater':'större', 'Superior':'överlägsen',
    'Crimson':'karmosinröd', 'Azure':'azurblå', 'Blue':'blå', 'Pink':'rosa', 'Golden':'gyllene', 'Royal':'kunglig',
    'Shadow':'skugga', 'Moon':'måne', 'Sun':'sol', 'Iron':'järn', 'Steel':'stål', 'Oak':'ek', 'Ash':'aska',
    'Armor':'rustning', 'Robes':'rockar', 'Vestments':'skrudar', 'Jerkin':'väst', 'Coat':'rock', 'Cuirass':'bröstharnesk',
    'Pauldrons':'axelskydd', 'Spaulders':'axelskydd', 'Mantle':'mantel', 'Capelet':'kort kappa',
    'Gauntlets':'handskar', 'Gloves':'handskar', 'Mitts':'vantar', 'Claws':'klor', 'Grips':'grepp', 'Bracers':'armskydd',
    'Helm':'hjälm', 'Hat':'hatt', 'Hood':'huva', 'Headband':'pannband', 'Brow Band':'pannband',
    'Diadem':'diadem', 'Circlet':'diadem', 'Crown':'krona', 'Pants':'byxor', 'Necklace':'halsband', 'Ring':'ring',
    'Sword':'svärd', 'Staff':'stav', 'Mace':'stridsklubba', 'Daggers':'dolkar', 'Shortbow':'kortbåge', 'Longbow':'långbåge',
    'Bow':'båge', 'Shield':'sköld', 'Shell':'skal', 'Heart':'hjärta', 'Core':'kärna', 'Fang':'huggtand',
    'Scale':'fjäll', 'Pelt':'päls', 'Horn':'horn', 'Hide':'skinn', 'Gauntlet':'handske', 'Gel':'gelé',
    'Jelly':'gelé', 'Stew':'gryta', 'Feast':'festmåltid', 'Banquet':'bankett', 'Satchel':'väska', 'Pack':'packning',
    'Amber':'bärnsten', 'Moonstone':'månsten', 'Crystal':'kristall', 'Feathered':'fjäderprydd', 'Winged':'bevingad',
    'Plumed':'fjäderprydd', 'Simple':'enkel', 'Plain':'enkel', 'Drowned':'dränkt', 'Worn':'sliten',
    'Wolfhood':'varghuva', 'Bone':'ben', 'Fletching':'pilfjädring', 'Hollow':'ihålig', 'Chime':'klocka',
    'Tusk':'bete', 'Shard':'skärva', 'Wing':'vinge', 'Quill':'fjäderpenna', 'Lure':'lockbete',
    'Pearl':'pärla', 'Beak':'näbb', 'Greatsword':'storsvärd', 'Relic':'relik', 'Leggings':'benkläder',
    'Signet':'sigillring', 'Bark':'bark', 'Carapace':'ryggsköld', 'Pinions':'vingpennor', 'Lens':'lins',
    'Ember':'glöd', 'Seed':'frö', 'Echo':'eko', 'Dew':'dagg', 'Plume':'fjäder', 'Antler':'horn',
    'Claw':'klo', 'Comb':'kam', 'Tail':'svans', 'Bell':'klocka', 'Resin':'kåda', 'Fur':'päls',
    'Chip':'flisa', 'Feather':'fjäder', 'Heartstone':'hjärtsten', 'Cog':'kugghjul', 'Eye':'öga',
    'Filament':'tråd', 'Edge':'egg', 'Roc':'rok', 'Newt':'vattensalamander', 'Moth':'mal',
    'Guard':'väktare', 'Sovereign':'härskare', 'Oracle':'orakel', 'Sentinel':'väktare',
}


def catalog_strings():
    found = set()
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in KEYS and isinstance(child, str):
                    found.add(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for filename in glob.glob(str(ROOT / 'world' / '*.txt')):
        try:
            walk(json.loads(pathlib.Path(filename).read_text()))
        except json.JSONDecodeError:
            pass
    class Text(html.parser.HTMLParser):
        def handle_data(self, data):
            data = data.strip()
            if re.search(r'[A-Za-z]{3}', data) and len(data) < 250:
                found.add(data)
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key in ('title', 'placeholder', 'aria-label') and value and re.search(r'[A-Za-z]{3}', value):
                    found.add(value)
    Text().feed((ROOT / 'client' / 'index.html').read_text())
    # UI text created in JavaScript (network text is translated only after it enters the UI).
    for filename in ('game', 'account', 'city', 'quests', 'inventory', 'skillbar', 'quickuse', 'settings', 'online', 'social', 'syslog', 'attributes', 'weather', 'daynight'):
        source = (ROOT / 'client' / (filename + '.js')).read_text()
        for match in re.finditer(r"(?<![\\\w])(['\"])([^'\"\n]{3,180})\1", source):
            value = match[2]
            if re.search(r'[A-Za-z]{3}', value) and not re.search(r'[<>{}=\\/;+\$]', value) and not value.startswith(('#', '.', 'http')):
                found.add(value)
    # Literal server notices and refusal reasons are rendered by the client. Keep SQL,
    # authorization headers and internal diagnostics out of the public translation file.
    internal = ('INSERT ', 'ALTER ', 'PRAGMA ', 'SELECT ', 'CREATE ', 'UPDATE ', 'DELETE ', 'Bearer ', 'HTTP ', 'SIGTERM ', 'VALHALLA_')
    for filename in glob.glob(str(ROOT / 'server' / 'src' / '**' / '*.rs'), recursive=True):
        if '_tests.rs' in filename:
            continue
        source = pathlib.Path(filename).read_text().split('#[cfg(test)]')[0]
        for value in re.findall(r'"([^"\\\n]{4,180})"', source):
            if re.match(r'[A-Z][A-Za-z ]{3}', value) and ' ' in value and not re.search(r'[{}\\/<>:=]', value) and not value.startswith(internal):
                found.add(value)
    return sorted(v for v in found if v.strip() and not v.isascii() or v.strip() and re.search(r'[A-Za-z]{3}', v))


def translate_batch(batch):
    marker = '\n~|~\n'
    payload = marker.join(batch)
    url = 'https://translate.googleapis.com/translate_a/single?' + urllib.parse.urlencode({'client': 'gtx', 'sl': 'en', 'tl': 'sv', 'dt': 't', 'q': payload})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                translated = ''.join(segment[0] for segment in json.load(response)[0])
            parts = [part.strip() for part in translated.split('~|~')]
            if len(parts) == len(batch):
                return dict(zip(batch, parts))
        except Exception:
            time.sleep(1 + attempt * 2)
    # A changed separator must not shift translations onto the wrong source strings.
    return {}


def item_fallback(cache):
    for item in json.loads((ROOT / 'world' / 'items.txt').read_text()):
        name = item['name']
        if cache.get(name) != name:
            continue
        translated = name
        for english, swedish in sorted(ITEM_WORDS.items(), key=lambda entry: -len(entry[0])):
            translated = re.sub(r'(?<!\w)' + re.escape(english) + r'(?!\w)', swedish, translated)
        if translated != name:
            cache[name] = translated[0].upper() + translated[1:]


def template_strings():
    found = set()
    def add(value, pattern):
        if not re.search(r'[A-Za-z]{3}', value) or re.search(r'[<>=;/\\]', value):
            return
        parts = re.split(pattern, value)
        if len(parts) < 2 or sum(len(x) for x in parts if not re.fullmatch(pattern, x)) < 8:
            return
        index = iter(range(20))
        normalized = re.sub(pattern, lambda _: '{' + str(next(index)) + '}', value)
        if '${' in normalized or normalized.count('{') != normalized.count('}'):
            return
        if normalized.startswith(('login:', 'register:', 'sso:', 'quest:', 'refinement_')):
            return
        found.add(normalized)
    for filename in glob.glob(str(ROOT / 'server' / 'src' / '**' / '*.rs'), recursive=True):
        if '_tests.rs' in filename:
            continue
        source = pathlib.Path(filename).read_text().split('#[cfg(test)]')[0]
        for value in re.findall(r'"([^"\\\n]{4,220})"', source):
            add(value, r'\{[^{}]*\}')
    for filename in ('game', 'account', 'city', 'quests', 'inventory', 'skillbar', 'quickuse', 'settings', 'online', 'social', 'syslog', 'attributes', 'weather', 'daynight'):
        source = (ROOT / 'client' / (filename + '.js')).read_text()
        for value in re.findall(r'`([^`\n]{4,220})`', source):
            add(value, r'\$\{[^{}]*\}')
    return sorted(found)


def template_batch(batch):
    marked = [re.sub(r'\{(\d+)\}', lambda m: 'ZXQ' + m[1] + 'ZX', source) for source in batch]
    result = translate_batch(marked)
    return {source: re.sub(r'ZXQ(\d+)ZX', lambda m: '{' + m[1] + '}', result[text])
            for source, text in zip(batch, marked) if text in result and all('{' + str(i) + '}' in re.sub(r'ZXQ(\d+)ZX', lambda m: '{' + m[1] + '}', result[text]) for i in range(source.count('{')))}


def main():
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    sources = catalog_strings()
    cache = {source: target for source, target in cache.items() if source in sources}
    pending = [s for s in sources if s not in cache]
    batches = []
    current = []
    for s in pending:
        if len(current) >= 12 or sum(len(x) for x in current) + len(s) > 1400:
            batches.append(current); current = []
        current.append(s)
    if current:
        batches.append(current)
    print(f'{len(pending)} strings in {len(batches)} batches', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(translate_batch, batches):
            cache.update(result)
    item_fallback(cache)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + '\n')
    template_cache = json.loads(TEMPLATE_CACHE.read_text()) if TEMPLATE_CACHE.exists() else {}
    sources = template_strings()
    template_cache = {source: target for source, target in template_cache.items() if source in sources}
    pending_templates = [s for s in sources if s not in template_cache]
    groups = [pending_templates[i:i + 10] for i in range(0, len(pending_templates), 10)]
    print(f'{len(pending_templates)} new templates in {len(groups)} batches', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(template_batch, groups):
            template_cache.update(result)
    TEMPLATE_CACHE.write_text(json.dumps(template_cache, ensure_ascii=False, indent=2) + '\n')
    output = "'use strict';\nwindow.SV_TEXT = " + json.dumps(cache, ensure_ascii=False, separators=(',', ':')) + ';\n'
    output += 'window.SV_TEMPLATES = ' + json.dumps(sorted(template_cache.items(), key=lambda pair: -len(pair[0])), ensure_ascii=False, separators=(',', ':')) + ';\n'
    OUTPUT.write_text(output)
    print(f'wrote {len(cache)} translations; {len(pending) - len([s for s in pending if s in cache])} missing', flush=True)


if __name__ == '__main__':
    main()
