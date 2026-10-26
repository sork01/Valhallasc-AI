#!/usr/bin/env python3
"""NPC art production plan and explicit identity inventory; gameplay data is read only."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# name, build, hair, headwear, occupational prop, coat, silhouette notes
ROWS=[
 ('sentinel','broad','crop','helm','spear','#547ba8','square shoulders, high greaves and long pennant spear'),
 ('physician','tall','braid','veil','bottle','#c2ddd5','long split coat, narrow shoulders and high medicinal flask'),
 ('smith','stocky','shaved','goggles','hammer','#b96e45','heavy apron, bare forearms and oversized smith hammer'),
 ('baker','round','curls','toque','bread','#e8c88d','round belly, towering soft chef hat and bread tray'),
 ('innkeeper','curvy','bun','ribbon','mug','#b86b88','full skirt, puff sleeves, apron and welcoming tankard'),
 ('merchant','round','beard','turban','scales','#9674bb','broad layered silk coat, wrapped hat and brass balance'),
 ('ranger','lean','ponytail','feather','bow','#64876a','long bow, fitted tunic and angled feather cap'),
 ('scholar','stooped','long','cap','book','#7079ad','bent shoulders, long robe, spectacles and open folio'),
 ('herald','tall','waves','beret','trumpet','#cc6b5a','angular tabard, jaunty beret and raised brass trumpet'),
 ('gardener','short','pigtails','straw','flowers','#91b772','wide straw hat, short overalls and overflowing flower basket'),
 ('fisher','broad','beard','beanie','fish','#629da4','oilskin cape, sea beard, creel and a silver fish'),
 ('weaver','curvy','braid','ribbon','spool','#b47eaf','asymmetric shawl, braids and spindle with threaded wool'),
 ('courier','lean','crop','scarf','satchel','#d0a261','short jacket, long trailing scarf and packed messenger satchel'),
 ('pilgrim','stooped','shaved','hood','staff','#9a8979','hunched cloak, high walking stick and tied bedroll'),
 ('bard','lean','waves','feather','lyre','#9776c1','fitted vest, swept hair and large curved lyre'),
 ('child','child','pigtails','ribbon','kite','#dc8a79','small limbs, oversized round face and diamond kite'),
 ('elder','stooped','beard','beanie','cane','#8297ac','low back, large beard, spectacles and crooked walking cane'),
 ('painter','short','curls','beret','palette','#ce9b69','painted smock, curled hair, broad palette and long brush'),
 ('carpenter','broad','ponytail','band','saw','#a97852','rolled sleeves, tool belt and long toothed hand saw'),
 ('alchemist','short','spikes','goggles','alembic','#71aaa0','short triangular coat, wild hair and glass distillation coil'),
 ('steward','tall','long','circlet','scroll','#977c98','straight formal mantle, thin crown and ribbon-bound scroll'),
 ('stablehand','stocky','braid','cap','reins','#ba925f','leather chaps, strong boots, braided hair and looped reins'),
 ('lamplighter','lean','crop','hood','lantern','#627a96','long rain cape, pointed hood and hanging amber lantern'),
 ('banker','round','bun','cap','chest','#7692a8','buttoned waistcoat, large coin chest and folded ledger'),
]
VARIANTS={name:dict(name=name,build=build,hair=hair,hat=hat,prop=prop,coat=coat,notes=notes,index=i)
          for i,(name,build,hair,hat,prop,coat,notes) in enumerate(ROWS)}
MATCH=[('banker','bank|vault warden|weights'),('physician','healer|physician|medic|apothecary|mender'),
 ('smith','smith|armorer|armourer|gearwright|bellows'),('baker','baker|miller'),('innkeeper','innkeeper|nautilus'),
 ('ranger','ranger|tracker|scout|forester|lookout|pathfinder|wrangler'),('scholar','scholar|archiv|loremaster|chronicler|cartograph|surveyor'),
 ('herald','herald|bellkeeper|bellwright'),('gardener','garden|botan|apiar|nectar|naturalist|beekeeper'),
 ('fisher','fish|ferryman|sailor|rigger|netmender'),('weaver','weaver|tailor|thread'),('courier','courier|spark travel|messenger'),
 ('bard','bard|singer|chorus|song|dancer'),('child','child'),('elder','retired|old '),('painter','painter'),
 ('carpenter','carpenter|wright|carver|builder'),('alchemist','alchemist'),('stablehand','stable'),
 ('lamplighter','lamp|beacon'),('merchant','merchant|trader|quartermaster|provision|outfitter|supplier|peddler|guildmaster'),
 ('sentinel','guard|watch|warden|captain|champion|keeper of the fallen'),('pilgrim','pilgrim|witness|stranded'),
 ('steward','steward|archon|reeve|matriarch|host|seer|oracle|keeper')]
# Bespoke zone materials and crown silhouettes; combined with each person's occupation.
THEMES={0:('meadow','leaf'),4:('city','braid'),6:('wyrd','antler'),7:('sky','wings'),8:('deep','rope'),9:('nacre','coral'),
 13:('astral','stars'),14:('prism','crystal'),15:('orrery','gears'),16:('moonspore','mushroom'),17:('asterion','rings'),
 19:('stormglass','shell'),20:('sunward','wheat'),21:('ribbon','ribbons'),22:('tangle','orchid'),23:('canopy','leaf'),
 24:('heartwood','branches'),25:('lapis','veil'),26:('frostwake','fur'),27:('cairn','slate'),28:('yearwheel','season'),
 41:('barrow','antler'),42:('span','wings'),43:('longship','rope'),44:('foundry','gears'),45:('emberwake','chains'),46:('forge','chains')}

# Individual silhouettes/occupational props for the earlier bespoke art catalog.
# These are production choices, independent of the world's gameplay records.
SPECIAL={
 'bank_alderhaven':('round','bun','cap','chest'), 'bank_skaldholm':('broad','beard','helm','chest'),
 'bank_nacrehold':('merfolk','long','circlet','pearl'), 'bank_astralhollow':('tall','braid','hood','scroll'),
 'bank_asterion':('stooped','waves','beret','scales'),
 'sun_miller':('stocky','bun','band','grain'), 'sun_keeper':('stooped','beard','straw','staff'),
 'sun_travel':('lean','crop','feather','satchel'), 'ribbon_host':('curvy','waves','ribbon','fan'),
 'ribbon_keeper':('tall','braid','circlet','key'), 'ribbon_travel':('short','pigtails','beret','kite'),
 'tangle_warden':('broad','braid','band','spear'), 'tangle_scholar':('stooped','shaved','cap','tablet'),
 'tangle_travel':('lean','ponytail','feather','satchel'),
 'heart_matriarch':('tall','long','crown','seed'), 'heart_archivist':('short','curls','cap','scroll'),
 'heart_oracle':('curvy','long','circlet','orb'), 'heart_travel':('lean','braid','scarf','satchel'),
 'lapis_keeper':('curvy','braid','veil','waterjug'), 'lapis_cartographer':('short','waves','turban','compass'),
 'lapis_warden':('broad','shaved','turban','spear'), 'lapis_seer':('tall','long','veil','orb'),
 'lapis_travel':('lean','crop','turban','satchel'),
 'frostwake_captain':('broad','braid','helm','spear'), 'frostwake_surveyor':('short','beard','beanie','compass'),
 'frostwake_bellkeeper':('stocky','braid','beanie','bell'), 'frostwake_skywatcher':('tall','long','hood','telescope'),
 'frostwake_ribkeeper':('stocky','beard','band','harpoon'), 'frostwake_travel':('lean','pigtails','scarf','satchel'),
 'cairn_warden':('broad','ponytail','helm','spear'), 'cairn_surveyor':('short','spikes','goggles','compass'),
 'cairn_stonesinger':('curvy','braid','band','bell'), 'cairn_grovekeeper':('stooped','long','hood','seed'),
 'cairn_windseer':('tall','beard','feather','fan'), 'cairn_travel':('lean','braid','scarf','satchel'),
 'year_sp_keeper':('short','waves','ribbon','flowers'), 'year_su_keeper':('broad','ponytail','circlet','grain'),
 'year_au_keeper':('round','beard','beret','mug'), 'year_wi_keeper':('tall','long','hood','orb'),
 'year_sp_travel':('short','pigtails','straw','satchel'), 'year_su_travel':('lean','spikes','band','satchel'),
 'year_au_travel':('curvy','bun','beret','satchel'), 'year_wi_travel':('broad','beard','beanie','satchel'),
}

def inventory():
 import re
 w=json.loads((ROOT/'world/map.txt').read_text());out=[];designs={k:dict(v,general=True) for k,v in VARIANTS.items()}
 for zi,z in enumerate([w]+w['zones']):
  for n in z.get('npcs',[]):
   if n.get('art') in ('stone','scenery'):continue
   text=(n['role']+' '+n['id']+' '+n['name']).lower()
   family=next((k for k,pattern in MATCH if re.search(pattern,text)), 'pilgrim')
   if n['id']=='city_grandfather':family='elder'
   if 'resident_' in n['id']:family=['gardener','weaver','courier','painter','innkeeper','scholar','merchant','bard'][int(n['id'].rsplit('_',1)[1])%8]
   bespoke=bool(n.get('art') or n.get('look',{}).get('species')=='merfolk' or zi in (7,13,14,15,16,17,24,41,42,43,44,45,46))
   if n['id'].startswith('dungeon_repair_'):family='smith';bespoke=False
   key='special_'+n['id'] if bespoke else family
   if bespoke:
    theme,ornament=THEMES.get(zi,('meadow','leaf'));spec=dict(VARIANTS[family]);spec.update(general=False,name=n['name'],theme=theme,ornament=ornament,npc=n['id'],zone=zi,identity=n.get('look',{}),coat=n.get('color',spec['coat']))
    if n.get('look',{}).get('species')=='merfolk':spec['build']='merfolk'
    if zi==28:
     spec['season']=next((i for i,k in enumerate(('sp','su','au','wi')) if '_'+k+'_' in n.get('art','')),0)
    if n.get('look',{}).get('prop')=='crown':spec['hat']='crown'
    designs[key]=spec
    if n.get('art') in SPECIAL:
     spec['build'],spec['hair'],spec['hat'],spec['prop']=SPECIAL[n['art']]
   identity=n.get('look') or dict(skin='#edc5a1',hair='#eae8df' if n['id']=='healer' else '#8a6550' if n['id']=='smith' else '#755841')
   out.append(dict(id=n['id'],name=n['name'],role=n['role'],zone=zi,zoneName=z['name'],art=key,previousArt=n.get('art'),moving=bool(n.get('route')),identity=identity,color=n.get('color','#8899aa')))
 return designs,out

def write_plan():
 designs,folk=inventory();plan=dict(frame=[96,96],anchor=[48,90],clips=dict(idle=dict(n=6,fps=6),walk=dict(n=8,fps=10),talk=dict(n=6,fps=6)),designs=designs,npcs=folk)
 (ROOT/'docs/npc-art-plan.txt').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n')
 print(len(VARIANTS),'general designs;',len(designs)-len(VARIANTS),'bespoke designs;',len(folk),'NPC assignments')
if __name__=='__main__':write_plan()
