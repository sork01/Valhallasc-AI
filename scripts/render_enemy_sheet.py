#!/usr/bin/env python3
"""One share sheet of a zone's exported enemy atlases: python3 scripts/render_enemy_sheet.py <zone number> [...].

Writes test-results/enemy-sheets/Valhalla_<Zone>_Enemy_Sprites.png (zones 1-8 of the cel-shaded redraw)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/enemy-sheets'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
ZONES = {
    1: ('crags', 'Emberfall Crags', 'Zone 1 · levels 5-10', '#3a2a2e', '#251a1d', '#ffb066', [
        ('wisp', 'Cinder Wisp', 0), ('spider', 'Magma Spider', 0), ('wraith', 'Ash Wraith', 0),
        ('golem', 'Basalt Golem', 0), ('cinderlord', 'The Cinderlord', 1)]),
    2: ('rime', 'Rimeveil Glacier', 'Zone 2 · levels 10-15', '#243a4c', '#16232f', '#9fe0ff', [
        ('crab', 'Rime Crab', 0), ('wolf', 'Frostfang Wolf', 0), ('yeti', 'Glacier Yeti', 0), ('wyrm', 'Rime Wyrm', 0)]),
    3: ('fen', 'Gloamfen', 'Zone 3 · levels 15-20', '#2a3a2e', '#18241d', '#b6e86a', [
        ('toad', 'Fen Toad', 0), ('croc', 'Mire Crocodile', 0), ('knight', 'Drowned Knight', 0),
        ('hydra', 'Mire Hydra', 0), ('gloomroot', 'Gloomroot Colossus', 1)]),
    5: ('vault', 'The Undervault', 'Zone 5 · dungeon, level 20', '#2e2e3e', '#1c1c28', '#c9b8ff', [
        ('thrall', 'Vault Thrall', 0), ('archer', 'Bone Archer', 0), ('acolyte', 'Hollow Acolyte', 0),
        ('gatewarden', 'Hrolf Bonegate', 1), ('choir', 'Valka, the Hollow Choir', 1),
        ('colossus', 'Ironwake, the Vault Colossus', 1), ('hollowking', 'Haldor, the Hollow King', 1)]),
    6: ('wyrd', 'Wyrdwood', 'Zone 6 · levels 20-30', '#2c3a2c', '#1a241a', '#ffd25a', [
        ('boar', 'Rotfang Boar', 0), ('crow', 'Gallowcrow', 0), ('troll', 'Mosshide Troll', 0), ('weaver', 'Wyrdweaver', 0),
        ('ram', 'Stormram', 0), ('oakhorn', 'Oakhorn', 1), ('hrungnir', 'Hrungnir', 1)]),
    7: ('sky', 'Bifrost Reach', 'Zone 7 · levels 30-35', '#2c3050', '#191c33', '#a8f0ff', [
        ('galehound', 'Galehound', 0), ('prismgolem', 'Prism Golem', 0), ('skyray', 'Skyray', 0),
        ('einherjar', 'Hollow Einherjar', 0), ('thunderroc', 'Thunderroc', 0)]),
    8: ('deep', "Rán's Deep", 'Zone 8 · levels 35-40', '#1c3a4a', '#10242e', '#9ffff0', [
        ('draugr', 'Drowned Draugr', 0), ('angler', 'Lantern Angler', 0), ('moray', 'Gnashing Moray', 0),
        ('siren', 'Siren', 0), ('shellback', 'Shellback', 0), ('kraken', 'The Kraken', 1),
        ('hvitserk', 'Hvitserk the Drowned', 1), ('ghostmaw', 'Ghostmaw', 1)]),
    22: ('tanglecrown', 'The Tanglecrown', 'Zone 22 · levels 75-80', '#1c3a2c', '#10251a', '#b8ff9a', [
        ('orchidmantis', 'Orchid Mantis', 0), ('canopyglider', 'Canopy Glider', 0), ('poolcaiman', 'Blackwater Caiman', 0),
        ('drumgorilla', 'Drum Gorilla', 0), ('jadeanaconda', 'The Jade Anaconda', 1), ('crownjaguar', 'The Crown Jaguar', 1)]),
    25: ('lapis', 'The Lapis Erg', 'Zone 25 · levels 80-85', '#3a3426', '#251f16', '#8ae4ff', [
        ('sandhopper', 'Sandhopper', 0), ('dunefennec', 'Dune Fennec', 0), ('glassscorpion', 'Glass Scorpion', 0),
        ('sunvulture', 'Sun Vulture', 0), ('dunecolossus', 'The Dune Colossus', 1), ('mirageroc', 'The Mirage Roc', 1)]),
    26: ('frostwake', 'Frostwake Shelf', 'Zone 26 · levels 85-90', '#1c3450', '#101f33', '#c8f4ff', [
        ('snowhare', 'Snow Hare', 0), ('iceotter', 'Ice Otter', 0), ('frostheron', 'Frost Heron', 0),
        ('glaciercrab', 'Glacier Crab', 0), ('bellmammoth', 'The Bell Mammoth', 1), ('auroramanta', 'The Aurora Manta', 1),
        ('crevasseleviathan', 'The Crevasse Leviathan', 1)]),
    27: ('cairn', 'The Cairnspine', 'Zone 27 · levels 90-95', '#34343c', '#202026', '#e8e4ff', [
        ('screeferret', 'Scree Ferret', 0), ('stoneibex', 'Stone Ibex', 0), ('slateraven', 'Slate Raven', 0),
        ('ridgeadder', 'Ridge Adder', 0), ('cairnbehemoth', 'The Cairn Behemoth', 1),
        ('whitebarktitan', 'The Whitebark Titan', 1), ('stormcondor', 'The Storm Condor', 1)]),
    28: ('yearwheel', 'The Yearwheel', 'Zone 28 · levels 95-99', '#2c3a3a', '#1a2424', '#ffe49a', [
        ('brooknewt', 'Brook Newt', 0), ('sundarter', 'Sun Darter', 0), ('acornmimic', 'Acorn Mimic', 0),
        ('snowstoat', 'Snow Stoat', 0), ('bloomtortoise', 'Bloom Tortoise', 1), ('petalchimera', 'Petal Chimera', 1),
        ('rainseraph', 'Rain Seraph', 1), ('glasslion', 'Glass Lion', 1), ('sunwheel', 'Sunwheel', 1),
        ('firephoenix', 'Fire Phoenix', 1), ('lanternowl', 'Lantern Owl', 1), ('harvestreaper', 'Harvest Reaper', 1),
        ('ambermantis', 'Amber Mantis', 1), ('rimesaber', 'Rime Saber', 1), ('snowgiant', 'Snow Giant', 1),
        ('longnightwyrm', 'Longnight Wyrm', 1)]),
}

def _dungeon(zone, title, level, bg, band, accent, cast):
    """Zones 29-39 are sealed-template dungeons whose atlases live in the shared cathedral set (cathedral_<kind>.png)."""
    ZONES[zone] = ('cathedral', title, f'Zone {zone} · dungeon, level {level}', bg, band, accent,
                   [(k, n, 1 if boss else 0) for k, n, boss in cast])


_dungeon(29, 'The Eye Below', 65, '#1c3a48', '#10242e', '#9ff0e8', [
    ('eye_drifter', 'Silt Drifter', 0), ('eye_lurker', 'Glassjaw Lurker', 0), ('eye_adept', 'Veil Adept', 0),
    ('eye_lenswarden', 'The Lenswarden', 1), ('eye_undertide', 'The Undertide Sibyl', 1),
    ('eye_unblinking', 'The Unblinking Eye', 1)])
_dungeon(30, 'The Elder Hollow', 70, '#2c3a2a', '#18241a', '#c8f08a', [
    ('elder_thornling', 'Thornling', 0), ('elder_moth', 'Lantern Moth', 0), ('elder_barkguard', 'Barkguard', 0),
    ('elder_gatekeeper', 'The Knotted Gatekeeper', 1), ('elder_matron', 'The Pollen Matron', 1),
    ('elder_heart', 'Heart of the Elder', 1)])
_dungeon(31, 'The Thousandfold Pavilion', 75, '#3a2c3c', '#241a26', '#ffd0e8', [
    ('pavilion_foldling', 'Paper Foldling', 0), ('pavilion_inkmoth', 'Inkwing Moth', 0), ('pavilion_silkguard', 'Silkguard', 0),
    ('pavilion_mirror', 'The Mirror Dancer', 1), ('pavilion_weaver', 'The Thousandfold Weaver', 1),
    ('pavilion_sovereign', 'Sovereign of the Last Fold', 1)])
_dungeon(32, 'Temple of the Rain Crown', 80, '#1c3a44', '#102228', '#a8f0ff', [
    ('rain_crown_droplet', 'Crowned Droplet', 0), ('rain_crown_oracle', 'Jade Rain Oracle', 0),
    ('rain_crown_guard', 'Monsoon Guard', 0), ('rain_crown_gatekeeper', 'Keeper of the Floodgate', 1),
    ('rain_crown_sibyl', 'Sibyl of the Rain', 1), ('rain_crown_sovereign', 'The Rain Crown', 1)])
_dungeon(33, 'The Seed Vault', 80, '#3a3220', '#241e12', '#ffe08a', [
    ('seed_mote', 'Awakened Seedling', 0), ('seed_amberwing', 'Amberwing Moth', 0), ('seed_rootguard', 'Heartroot Guard', 0),
    ('seed_warden', 'Warden of Rings', 1), ('seed_germinator', 'The Germinator', 1),
    ('seed_worldseed', 'Heart of the Worldseed', 1)])
_dungeon(34, 'The Sunken Astrolabe', 85, '#1c2c4a', '#0f1a2e', '#ffe9a0', [
    ('astro_gearling', 'Brass Gearling', 0), ('astro_starling', 'Fallen Starling', 0), ('astro_sentinel', 'Orrery Sentinel', 0),
    ('astro_warden', 'Meridian Warden', 1), ('astro_navigator', 'The Lost Navigator', 1),
    ('astro_axis', 'Axis of the Buried Sky', 1)])
_dungeon(35, 'The Thunderheart Gate', 95, '#2a2c4a', '#171830', '#fff09a', [
    ('thunder_spark', 'Forked Spark', 0), ('thunder_ray', 'Stormglass Ray', 0), ('thunder_guard', 'Slatebound Guard', 0),
    ('thunder_conductor', 'Storm Conductor', 1), ('thunder_bastion', 'The Thunder Bastion', 1),
    ('thunder_heart', 'Heart of the Stormgate', 1)])
_dungeon(36, 'The Blooming Labyrinth', 97, '#3a2a3a', '#241624', '#ffb8e0', [
    ('bloom_spore', 'Glasspetal Spore', 0), ('bloom_moth', 'Prismwing Moth', 0), ('bloom_guard', 'Vineglass Guardian', 0),
    ('bloom_thornkeeper', 'Thornkeeper', 1), ('bloom_mirror', 'Petal Mirror', 1),
    ('bloom_heart', 'Heart of the Labyrinth', 1)])
_dungeon(37, 'The Solar Crucible', 98, '#4a2c1c', '#2e180e', '#ffc860', [
    ('solar_emberling', 'Cinderling', 0), ('solar_sunmoth', 'Sunmoth', 0), ('solar_crucible_guard', 'Crucible Guard', 0),
    ('solar_ashwarden', 'Ashwarden', 1), ('solar_heliomancer', 'The Heliomancer', 1),
    ('solar_heart', 'Heart of the Crucible', 1)])
_dungeon(38, 'The Amber Archive', 99, '#443220', '#2a1e10', '#ffd478', [
    ('amber_page', 'Living Page', 0), ('amber_moth', 'Script Moth', 0), ('amber_sentinel', 'Archive Sentinel', 0),
    ('amber_curator', 'The Curator', 1), ('amber_chronicle', 'The Living Chronicle', 1),
    ('amber_memory', 'The Last Memory', 1)])
_dungeon(39, 'The Silent Solstice', 99, '#26344a', '#141e2e', '#d0eaff', [
    ('solstice_flurry', 'Whispering Flurry', 0), ('solstice_owl', 'Night Owl', 0), ('solstice_guard', 'Rime Guard', 0),
    ('solstice_watcher', 'The Frost Watcher', 1), ('solstice_harbinger', 'Harbinger of Night', 1),
    ('solstice_heart', 'Heart of the Longest Night', 1)])
_dungeon(41, 'Nornroot Barrow', 25, '#3a2c44', '#22182a', '#ffd88a', [
    ('barrow_scarab', 'Graveamber Scarab', 0), ('barrow_hound', 'Threadbound Hound', 0), ('barrow_spinner', 'Spindle Shade', 0),
    ('barrow_doorward', 'Arn, the Amber Doorward', 1), ('barrow_threadkeeper', 'Vessa, Keeper of Threads', 1),
    ('barrow_fatebound', 'The Unwritten King', 1)])
_dungeon(42, 'The Shattered Span', 30, '#1c2844', '#10172c', '#8fe8ff', [
    ('span_lynx', 'Glassfang Lynx', 0), ('span_sentinel', 'Bifrost Sentinel', 0), ('span_caster', 'Prismatic Caster', 0),
    ('span_warden', 'Torstein, Keeper of the Toll', 1), ('span_weaver', 'Sunniva, the Spectrum Weaver', 1),
    ('span_archon', 'Vaelor, Bifrost Archon', 1)])


CARD_W, CARD_H, GAP = 408, 506, 18


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def frame(atlas, row, col, scale):
    tile = atlas.crop((col * 96, row * 96, (col + 1) * 96, (row + 1) * 96))
    return tile.resize((96 * scale, 96 * scale), Image.Resampling.NEAREST)


def sheet(zone):
    tag, title, sub, card_bg, band_bg, accent, cast = ZONES[zone]
    cols = 3 if len(cast) == 6 else min(len(cast), 4) if len(cast) in (4, 8) else min(len(cast), 5) if len(cast) <= 5 else 4
    rows = (len(cast) + cols - 1) // cols
    width = cols * CARD_W + (cols + 1) * GAP
    head = 110
    height = head + rows * (CARD_H + GAP) + 50
    canvas = Image.new('RGB', (width, height), band_bg)
    d = ImageDraw.Draw(canvas)
    d.text((GAP * 2, 18), title.upper(), font=font(40, True), fill=accent)
    d.text((GAP * 2 + 2, 70), f'{sub} · {len(cast)} enemies · cel-shaded · idle, walk, attack, hurt and die',
           font=font(19), fill='#d6d2e8')
    for i, (kind, name, boss) in enumerate(cast):
        x = GAP + (i % cols) * (CARD_W + GAP)
        top = head + (i // cols) * (CARD_H + GAP)
        d.rounded_rectangle((x, top, x + CARD_W, top + CARD_H), radius=18, fill=card_bg, outline=accent, width=3)
        d.text((x + 18, top + 14), name, font=font(22 if len(name) < 24 else 18, True), fill='#f7f5ff')
        d.text((x + 19, top + 46), 'BOSS / ELITE' if boss else 'ORDINARY', font=font(15, True),
               fill=accent if boss else '#a9a6c4')
        atlas = Image.open(ROOT / f'client/assets/{tag}_{kind}.png').convert('RGBA')
        big = frame(atlas, 0, 0, 3)
        canvas.paste(big, (x + (CARD_W - 288) // 2, top + 68), big)
        d.line((x + 18, top + 366, x + CARD_W - 18, top + 366), fill=accent, width=2)
        for j, (label, clip, col) in enumerate((('WALK', 1, 2), ('ATTACK', 2, 4), ('HURT', 3, 1), ('DIE', 4, 3))):
            px = x + 12 + j * 96
            pose = frame(atlas, clip, col, 1)
            canvas.paste(pose, (px, top + 376), pose)
            d.text((px + 6, top + 476), label, font=font(13, True), fill='#c9c6e2')
    d.text((GAP * 2, height - 34), '96 × 96 source frames · shared foot anchor · 34 frames per enemy',
           font=font(16), fill='#8c88a8')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"Valhalla_{title.replace(' ', '_').replace(chr(39), '').replace('á', 'a')}_Enemy_Sprites.png"
    canvas.save(path, optimize=True)
    print(path, canvas.size)


if __name__ == '__main__':
    for z in sys.argv[1:] or ZONES:
        sheet(int(z))
