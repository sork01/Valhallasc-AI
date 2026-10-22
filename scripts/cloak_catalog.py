"""Class-neutral cloak catalogue and generated sources; no cloak belongs to a set.

Ordinary cloaks have the necklace attribute budget from rare upward. The owner
added stamina to gray/green on 2026-10-22. No cloak adds attack or defence.
"""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEVELS=(*range(5,96,5),99)
RARITIES=('common','uncommon','rare','epic')
STYLES=('travel','hooded','mantle','clasp','ember')
# Each tuple is authored English / Swedish (mantel is en).
NAMES={
5: [('Weathered Travel Cloak','Sliten resemantel'),('Sturdy Travel Cloak','Stadig resemantel'),('Gilded Travel Cloak','Förgylld resemantel')],
10:[('Ashen Travel Cloak','Askgrå resemantel'),('Emberwoven Travel Cloak','Glödvävd resemantel'),('Runed Travel Cloak','Runristad resemantel'),('Sovereign Travel Cloak','Härskarens resemantel')],
15:[('Frostworn Travel Cloak','Frostsliten resemantel'),('Winterguard Travel Cloak','Vintervaktens resemantel'),('Icebound Travel Cloak','Isbunden resemantel')],
20:[('Bogworn Travel Cloak','Träsksliten resemantel'),('Mosswoven Travel Cloak','Mossvävd resemantel'),('Moonlit Travel Cloak','Månbelyst resemantel'),('Mythic Travel Cloak','Mytisk resemantel')],
25:[('Brambleworn Hooded Cloak','Törnsliten huvmantel'),('Thornwoven Hooded Cloak','Törnvävd huvmantel'),('Fatebound Hooded Cloak','Ödesbunden huvmantel')],
30:[('Windworn Hooded Cloak','Vindsliten huvmantel'),('Galesworn Hooded Cloak','Stormsvuren huvmantel'),('Prismatic Hooded Cloak','Prismatisk huvmantel'),('Stormcrowned Hooded Cloak','Stormkrönt huvmantel')],
35:[('Saltworn Hooded Cloak','Saltsliten huvmantel'),('Tidewoven Hooded Cloak','Tidvattenvävd huvmantel'),('Maelstrom Hooded Cloak','Malströmmens huvmantel')],
40:[('Drowned Hooded Cloak','Dränkt huvmantel'),('Pearlbound Hooded Cloak','Pärlbunden huvmantel'),('Nacreous Hooded Cloak','Pärlemorskimrande huvmantel'),('Tidesovereign Hooded Cloak','Tidvattenhärskarens huvmantel')],
45:[('Coralworn Long Cloak','Korallsliten långmantel'),('Reefguard Long Cloak','Revväktarens långmantel'),('Abyssal Long Cloak','Avgrundens långmantel')],
50:[('Timeworn Long Cloak','Tidssliten långmantel'),('Starwoven Long Cloak','Stjärnvävd långmantel'),('Empyrean Long Cloak','Himmelsk långmantel'),('Ascendant Long Cloak','Upphöjd långmantel')],
55:[('Clockworn Long Cloak','Ursliten långmantel'),('Hourwoven Long Cloak','Timvävd långmantel'),('Epochbound Long Cloak','Epokbunden långmantel')],
60:[('Sporeworn Long Cloak','Sporsliten långmantel'),('Moonwoven Long Cloak','Månvävd långmantel'),('Nightbloom Long Cloak','Nattblommans långmantel'),('Mooncrowned Long Cloak','Månkrönt långmantel')],
65:[('Brineworn Clasped Cloak','Saltnött spännmantel'),('Stormwoven Clasped Cloak','Stormvävd spännmantel'),('Eye-bound Clasped Cloak','Ögonbunden spännmantel')],
70:[('Fieldworn Clasped Cloak','Fältsliten spännmantel'),('Oakbound Clasped Cloak','Ekbunden spännmantel'),('Sunward Clasped Cloak','Solvänd spännmantel'),('Elder-crowned Clasped Cloak','Urkrönt spännmantel')],
75:[('Paradeworn Clasped Cloak','Paradsliten spännmantel'),('Ribbonbound Clasped Cloak','Bandbunden spännmantel'),('Jubilee Clasped Cloak','Jubileets spännmantel')],
80:[('Rootworn Clasped Cloak','Rotsliten spännmantel'),('Canopybound Clasped Cloak','Trädkronans spännmantel'),('Raincrowned Clasped Cloak','Regnkrönt spännmantel'),('Jade Sovereign Clasped Cloak','Jadehärskarens spännmantel')],
85:[('Sandworn Ember Cloak','Sandsliten glödmantel'),('Oasisbound Ember Cloak','Oasbunden glödmantel'),('Astrolabe Ember Cloak','Astrolabiets glödmantel')],
90:[('Snowworn Ember Cloak','Snösliten glödmantel'),('Riftwoven Ember Cloak','Revävd glödmantel'),('Aurorabound Ember Cloak','Norrskensbunden glödmantel'),('Glacier Sovereign Ember Cloak','Glaciärhärskarens glödmantel')],
95:[('Stoneworn Ember Cloak','Stensliten glödmantel'),('Cairnwoven Ember Cloak','Rösvävd glödmantel'),('Thunderbound Ember Cloak','Åskbunden glödmantel')],
99:[('Seasonworn Ember Cloak','Årstidssliten glödmantel'),('Yearwoven Ember Cloak','Årsvävd glödmantel'),('Everlasting Ember Cloak','Evig glödmantel'),('Worldcrowned Ember Cloak','Världskrönt glödmantel')],
}
DUNGEONS={
'undervault':('Choirbone Cloak','Körbenets mantel'),
'cathedral_cloister':('Stillwater Cloak','Stilla vattnets mantel'),
'cathedral_reliquary':('Pearl Widow Cloak','Pärlänkans mantel'),
'cathedral_nave':('Hierophant Cloak','Hierofantens mantel'),
'moonwell':('Lunar Tide Cloak','Måntidens mantel'),
'eye_below':('Watchful Cloak','Vaksam mantel'),
'elder_hollow':('Elderwood Cloak','Urträdets mantel'),
'thousandfold':('Thousandfold Cloak','Tusenfaldig mantel'),
'rain_crown':('Rain Crown Cloak','Regnkronans mantel'),
'seed_vault':('Seedkeeper Cloak','Fröväktarens mantel'),
'sunken_astrolabe':('Sunken Star Cloak','Sjunkna stjärnans mantel'),
'skybridge':('Spanbound Cloak','Brobunden mantel'),
'nornroot':('Fatewoven Cloak','Ödesvävd mantel'),
'longship':('Keelbound Cloak','Kölbunden mantel'),
'blackhour':('Nullforged Cloak','Nollsmidd mantel'),
'thunderheart_gate':('Stormbound Cloak','Stormbunden mantel'),
'blooming_labyrinth':('Glassbloom Cloak','Glasblommans mantel'),
'solar_crucible':('Sunforged Cloak','Solsmidd mantel'),
'amber_archive':('Archivist Cloak','Arkivariens mantel'),
'silent_solstice':('Nightglass Cloak','Nattglasets mantel'),
}
ORANGE_NAMES=[('Ember Sovereign Cloak','Glödhärskarens mantel'),('Verdant Crown Cloak','Gröna kronans mantel'),
('Storm Oracle Cloak','Stormoraklets mantel'),('Abyss Singer Cloak','Avgrundssångarens mantel'),
('Starforged Cloak','Stjärnsmidd mantel'),('Solar Regent Cloak','Solregentens mantel'),
('Ash Phoenix Cloak','Askfenixens mantel'),('Moonlit Sentinel Cloak','Månvaktens mantel'),
('Chronometer Cloak','Kronometerns mantel'),('Worldheart Cloak','Världshjärtats mantel')]

def art_for(level):return STYLES[min(4,(level-5)//20)]

def ordinary_id(level,rarity):return f'cloak_l{level}_{rarity}'

def pieces(items):
    import gear_levels as gear
    result=[]
    for level in LEVELS:
        for tier,rarity in enumerate(RARITIES):
            if rarity=='epic' and level%10 and level!=99:continue
            amount=gear.ATTRIBUTE_BONUS.get(level,114)
            item=dict(id=ordinary_id(level,rarity),name=NAMES[level][tier][0],kind='cloak',rarity=rarity,
                      requiredLevel=level,sell=round(gear.SELL_BASE[rarity]*(.16*level+.8)),
                      attack=0,defense=0,**{'class':None},variant=ordinary_id(level,rarity),art=art_for(level),starter=False)
            if tier<2:
                item['bonusStats']={'stamina':max(1,round(amount/gear.TIER_STEP**(2-tier)))}
                item['family']='cloak_'+rarity;item['price']=item['sell']*4
            else:
                item['bonusStats']=gear.bonus_stats(item)
                if level==99:item['bonusStats']={stat:114 for stat in item['bonusStats']}
            # Unique tint for each rung; even the first recolours its base.
            item['tint']=dict(hue=(LEVELS.index(level)*47+tier*23+13)%360,saturate=(.45, .9,1.2,1.4)[tier],brightness=(.82,1,1.12,1.24)[tier])
            if tier==2:item['family']='cloak_rare';item['price']=item['sell']*4
            result.append(item)
    # Dungeon necklaces supply the same authored level and attribute budget.
    for source,(name,_) in DUNGEONS.items():
        necklace=next((i for i in items if i['kind']=='necklace' and i.get('source')==source),None)
        if not necklace:raise ValueError('Missing dungeon necklace: '+source)
        level=necklace['requiredLevel'];rarity=necklace['rarity'];id_='cloak_'+source
        item=dict(id=id_,name=name,kind='cloak',rarity=rarity,requiredLevel=level,sell=necklace['sell'],attack=0,defense=0,
                  **{'class':None},variant=id_,art=art_for(level),starter=False,source=source,
                  bonusStats=copy.deepcopy(necklace.get('bonusStats',{})))
        number=list(DUNGEONS).index(source)
        item['tint']=dict(hue=(number*37+19)%360,saturate=1.28,brightness=1.15+number*.003)
        result.append(item)
    return result

def apply(items):
    old={i['id']:n for n,i in enumerate(items)}
    result=[i for i in items if i['kind']!='cloak' or i.get('source')=='orange_pool']+pieces(items)
    result.sort(key=lambda i:old.get(i['id'],len(old)))
    return result

def choices(quest,items):
    """Add a cloak as a choice without changing an existing guaranteed reward."""
    by_id={i['id']:i for i in items};eligible=[i for i in items if i['kind']=='cloak' and i.get('source')!='orange_pool']
    levels={i['requiredLevel'] for i in eligible if not i.get('source')}
    rewards=quest.get('rewardChoices',{})
    references=[by_id[id_] for ids in rewards.values() for id_ in ids if id_ in by_id and by_id[id_]['kind'] in ('armor','weapon','headgear','shoulders','gloves','pants','necklace','accessory','cloak')]
    if not references or quest.get('level',1)<5:return quest
    source=next((i.get('source') for i in references if i.get('source') in DUNGEONS),None)
    if source and next(i for i in eligible if i.get('source')==source)['requiredLevel']<=quest['level']:cloak=next(i for i in eligible if i.get('source')==source)
    else:
        rarity='epic' if all(i['rarity']=='epic' for i in references) else 'rare'
        level=max((n for n in levels if n<=min(quest['level'],max(i.get('requiredLevel',1) for i in references))),default=5)
        id_=ordinary_id(level,rarity)
        cloak=next((i for i in eligible if i['id']==id_),next(i for i in eligible if i['id']==ordinary_id(level,'rare')))
    for cls in ('warrior','mage','assassin','priest','hunter'):
        slots=quest.setdefault('rewardChoices',{}).setdefault(cls,[])
        if cloak['id'] not in slots:slots.append(cloak['id'])
    return quest

def apply_world(world,items):
    by_id={i['id']:i for i in items}
    for area in [world,*world['zones']]:
        for npc in area.get('npcs',[]):
            offers=npc.get('offers',[])
            if not (npc.get('buys') or npc.get('role') == 'Armorer' or any(by_id.get(o.get('item'),{}).get('kind') in ('armor','headgear','shoulders','gloves','pants','necklace','accessory','weapon') for o in offers)):continue
            for rarity in RARITIES[:3]:
                id_='buy_cloak_'+rarity
                if not any(o['id']==id_ for o in offers):offers.append(dict(id=id_,label={'common':'Buy Travel Cloak','uncommon':'Buy Sturdy Cloak','rare':'Buy Rare Cloak'}[rarity],item=ordinary_id(5,rarity),tiered=True,cost=by_id[ordinary_id(5,rarity)]['price']))
        for q in area.get('quests',[]):choices(q,items)
    return world

if __name__=='__main__':
    items=json.loads((ROOT/'world/items.txt').read_text())
    path=ROOT/'world/map.txt';world=json.loads(path.read_text());apply_world(world,items)
    path.write_text(json.dumps(world,indent=2,ensure_ascii=False)+'\n')


def append_icons():
    """Append five editable cloak icons to the established inventory atlas, idempotently."""
    import math
    from PIL import Image
    assets=ROOT/'client/assets';path=assets/'items.txt';meta=json.loads(path.read_text())
    items=json.loads((ROOT/'world/items.txt').read_text());cloaks=[i for i in items if i['kind']=='cloak']
    if not all((assets/('gear_icon_cloak_'+style+'.png')).exists() for style in STYLES):return
    # Strip our old cells before appending; existing gear cells stay in place.
    at={k:v for k,v in meta['at'].items() if not k.startswith(('cloak_','orange_cloak_'))}
    size=meta['size'];cols=meta['cols'];start=max((y*cols+x for x,y in at.values()),default=-1)+1
    rows=math.ceil((start+len(STYLES))/cols);picture=Image.new('RGBA',(cols*size,rows*size));picture.paste(Image.open(assets/'items.png'),(0,0))
    for n,style in enumerate(STYLES,start):
        cell=[n%cols,n//cols];icon=Image.open(assets/('gear_icon_cloak_'+style+'.png')).convert('RGBA')
        picture.paste(icon,(cell[0]*size,cell[1]*size))
        for item in cloaks:
            if item['art']==style:at[item['id']]=cell
    meta.update(rows=rows,at=at);picture.save(assets/'items.png',optimize=True);path.write_text(json.dumps(meta,indent=1)+'\n')
    (ROOT/'client/itemicons.js').write_text("'use strict';\nwindow.ITEM_ICONS = "+json.dumps(dict(size=size,cols=cols,rows=rows,at=at),separators=(',',':'))+';\n')
