#!/usr/bin/env python3
"""Render complete sprite sheets of all 5 hero classes in full worn gear."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT_DIR = ROOT / 'test-results/hero-sheets'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

CLASSES = [
    ('warrior', 'Warrior', 'warrior_layered', '#d8aa68', '#3a2a1a', [
        ('head', 'Bridgeward Keystone Helm', 'head_regearspan'),
        ('shoulders', 'Bridgeward Keystone Pauldrons', 'shoulders_regearspan'),
        ('armor', 'Bridgeward Keystone Cuirass', 'armor_regearspan'),
        ('gloves', 'Bridgeward Keystone Gauntlets', 'gloves_regearspan'),
        ('pants', 'Bridgeward Keystone Greaves', 'pants_regearspan'),
        ('weapon', 'Bridgeward Crystal Blade', 'weapon_regearspan'),
    ]),
    ('mage', 'Mage', 'mage', '#79b9e4', '#162838', [
        ('head', 'Bridgeward Archon Spire Crown', 'head_regearspan'),
        ('shoulders', 'Bridgeward Archon Mantle', 'shoulders_regearspan'),
        ('armor', 'Bridgeward Archon Robes', 'armor_regearspan'),
        ('gloves', 'Bridgeward Archon Wraps', 'gloves_regearspan'),
        ('pants', 'Bridgeward Archon Trousers', 'pants_regearspan'),
        ('weapon', 'Bridgeward Archon Spire Staff', 'weapon_regearspan'),
    ]),
    ('assassin', 'Assassin', 'assassin', '#b7a0d9', '#271c38', [
        ('head', 'Bridgeward Glass Mask', 'head_regearspan'),
        ('shoulders', 'Bridgeward Glass Spaulders', 'shoulders_regearspan'),
        ('armor', 'Bridgeward Glass Tunic', 'armor_regearspan'),
        ('gloves', 'Bridgeward Glass Claws', 'gloves_regearspan'),
        ('pants', 'Bridgeward Glass Breeches', 'pants_regearspan'),
        ('weapon', 'Bridgeward Prism Daggers', 'weapon_regearspan'),
    ]),
    ('priest', 'Priest', 'priest', '#e2d59d', '#332e18', [
        ('head', 'Bridgeward Radiant Halo', 'head_regearspan'),
        ('shoulders', 'Bridgeward Radiant Epaulets', 'shoulders_regearspan'),
        ('armor', 'Bridgeward Radiant Vestments', 'armor_regearspan'),
        ('gloves', 'Bridgeward Radiant Mitts', 'gloves_regearspan'),
        ('pants', 'Bridgeward Radiant Skirt', 'pants_regearspan'),
        ('weapon', 'Bridgeward Radiant Sun Mace', 'weapon_regearspan'),
    ]),
    ('hunter', 'Hunter', 'hunter', '#9ac78f', '#1c2e1c', [
        ('head', 'Bridgeward Horizon Crest', 'head_regearspan'),
        ('shoulders', 'Bridgeward Horizon Mantle', 'shoulders_regearspan'),
        ('armor', 'Bridgeward Horizon Jerkin', 'armor_regearspan'),
        ('gloves', 'Bridgeward Horizon Bracers', 'gloves_regearspan'),
        ('pants', 'Bridgeward Horizon Leggings', 'pants_regearspan'),
        ('weapon', 'Bridgeward Prismatic Glass Bow', 'weapon_regearspan'),
    ]),
]

def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

def composite_frame(stem, parts, row, col):
    fw, fh = 160, 160
    meta = json.loads((ASSETS / f'{stem}_sprites.txt').read_text())
    b_files = meta['parts']['body']
    box = (col * fw, row * fh, (col + 1) * fw, (row + 1) * fh)
    
    with Image.open(ASSETS / b_files['png']) as img:
        color = np.asarray(img.crop(box).convert('RGBA')).copy()
    with Image.open(ASSETS / b_files['depth']) as img:
        d_rgb = np.asarray(img.crop(box).convert('RGB')).astype(np.uint16)
        nearest = d_rgb[:, :, 0] * 256 + d_rgb[:, :, 1]
    nearest = np.where(color[:, :, 3] > 0, nearest, 65535).copy()

    for p in parts:
        f = meta['parts'][p]
        with Image.open(ASSETS / f['png']) as img:
            p_col = np.asarray(img.crop(box).convert('RGBA')).copy()
        with Image.open(ASSETS / f['depth']) as img:
            p_drgb = np.asarray(img.crop(box).convert('RGB')).astype(np.uint16)
            p_dep = p_drgb[:, :, 0] * 256 + p_drgb[:, :, 1]
        nearer = (p_col[:, :, 3] > 0) & (p_dep <= nearest)
        color[nearer] = p_col[nearer]
        nearest[nearer] = p_dep[nearer]
    
    return Image.fromarray(color, 'RGBA')

def render_showcase():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    width = 1620
    row_h = 320
    header_h = 130
    footer_h = 70
    height = header_h + len(CLASSES) * row_h + footer_h
    
    canvas = Image.new('RGB', (width, height), '#0e141e')
    draw = ImageDraw.Draw(canvas)
    
    # Header
    draw.text((36, 26), 'VALHALLA', font=font(40, True), fill='#f1d395')
    draw.text((38, 76), 'HERO EQUIPMENT & ANIMATIONS  •  BRIDGEWARD SETS', font=font(20, True), fill='#d9e5ea')
    draw.text((38, 102), 'Authoritative layered cel-shaded compositing  ·  Armor, Helm, Shoulders, Gloves, Pants & Weapons  ·  All 5 Classes',
              font=font(14), fill='#8fa4b3')
    
    for idx, (cls_id, cls_name, stem, accent, bg_dark, gear_list) in enumerate(CLASSES):
        y = header_h + idx * row_h
        draw.rounded_rectangle((24, y + 8, width - 24, y + row_h - 12), radius=16, fill=bg_dark, outline=accent, width=2)
        
        # Class title & tag
        draw.text((44, y + 22), cls_name.upper(), font=font(24, True), fill=accent)
        draw.text((44, y + 54), 'Level 30 Bridgeward Set', font=font(14, True), fill='#bfcfd6')
        
        # Gear list
        part_keys = [item[2] for item in gear_list]
        for g_idx, (slot, item_title, _) in enumerate(gear_list):
            gy = y + 84 + g_idx * 28
            draw.text((44, gy), f'{slot.capitalize()}:', font=font(12, True), fill='#9ab0be')
            draw.text((124, gy), item_title, font=font(12), fill='#ffffff')
        
        # Hero Idle Portrait (Large)
        idle_full = composite_frame(stem, part_keys, row=0, col=0)
        # Crop character area (around 120x130)
        idle_crop = idle_full.crop((30, 8, 130, 138))
        idle_scaled = idle_crop.resize((150, 195), Image.Resampling.NEAREST)
        draw.rounded_rectangle((320, y + 26, 490, y + 280), radius=12, fill='#00000055', outline=accent, width=1)
        canvas.paste(idle_scaled, (330, y + 46), idle_scaled)
        draw.text((365, y + 250), 'IDLE POSE', font=font(12, True), fill=accent)
        
        # Action animation frames
        anim_frames = [
            ('WALK A', 8, 0),
            ('WALK B', 8, 2),
            ('WALK C', 8, 4),
            ('ATTACK WINDUP', 16, 2),
            ('ATTACK IMPACT', 16, 4),
            ('ATTACK RECOVERY', 16, 6),
            ('HURT', 24, 1),
            ('FALLEN / DIE', 32, 6),
        ]
        
        start_x = 520
        frame_w = 130
        for a_idx, (label, f_row, f_col) in enumerate(anim_frames):
            fx = start_x + a_idx * frame_w
            frame_img = composite_frame(stem, part_keys, row=f_row, col=f_col)
            frame_crop = frame_img.crop((20, 4, 140, 134))
            frame_thumb = frame_crop.resize((120, 130), Image.Resampling.NEAREST)
            
            draw.rounded_rectangle((fx, y + 26, fx + frame_w - 10, y + 280), radius=10, fill='#00000044', outline='#ffffff22', width=1)
            canvas.paste(frame_thumb, (fx, y + 60), frame_thumb)
            draw.text((fx + 8, y + 248), label, font=font(10, True), fill='#c9d6df')
            
        print(f'Rendered showcase row {idx+1}/{len(CLASSES)}: {cls_name}')
        
    draw.text((36, height - 42), 'Composite depth buffer: character body + pants + chest armor + pauldrons + gloves + helm + weapon.',
              font=font(13), fill='#7a8f9c')
    
    out_file = OUT_DIR / 'Valhalla_Heroes_Gear_Sprite_Sheet.png'
    canvas.save(out_file, optimize=True)
    print('Saved showcase to', out_file, canvas.size)
    return out_file

def render_equipped_atlas():
    """Render a clean 5-hero action sheet with all facings and key cycles."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cols = 8
    rows = 4 * len(CLASSES) # 4 facings/animations per class
    cell = 160
    sheet = Image.new('RGBA', (cols * cell, rows * cell), (0, 0, 0, 0))
    
    for c_idx, (_, _, stem, _, _, gear_list) in enumerate(CLASSES):
        part_keys = [item[2] for item in gear_list]
        # 4 key rows for each class:
        # 0: Idle down (facing south)
        # 1: Walk down
        # 2: Attack down
        # 3: Die down
        for local_row, src_row in enumerate([0, 8, 16, 32]):
            target_row = c_idx * 4 + local_row
            for col in range(cols):
                frame = composite_frame(stem, part_keys, row=src_row, col=col)
                sheet.paste(frame, (col * cell, target_row * cell), frame)
        print(f'Rendered atlas block {c_idx+1}/{len(CLASSES)}')
        
    out_file = OUT_DIR / 'Valhalla_Equipped_Heroes_Atlas.png'
    sheet.save(out_file, optimize=True)
    print('Saved atlas to', out_file, sheet.size)
    return out_file

if __name__ == '__main__':
    render_showcase()
    render_equipped_atlas()
