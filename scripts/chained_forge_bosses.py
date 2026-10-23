"""Chained Forge Wardens. Data is shared by the deterministic zone generator and art maker."""
import math
ENEMIES = [dict(kind=kind,name=name,level=99,stats=[1000000,11000,2.0,1.8],
    profile=[1.05,2.4,12,22],boss=True,elite=True,outdoor=False,gold=150000,
    material=kind+'_relic',ranged=None,slam=0,melee=0,color=color)
    for kind,name,color in [('cf_kettil','Kettil Linkbearer','#bd9c68'),
                            ('cf_ysolt','Ysolt Bellowsmaid','#7ccbd3'),
                            ('cf_hallgrim','Hallgrim Anvilhand','#ed9c65'),
                            ('cf_sigrun','Sigrun Slagmother','#eab068'),
                            ('cf_dagfinn','Dagfinn Tongsbearer','#d5a76d'),
                            ('cf_thorbjorg','Thorbjörg Quenchwife','#e98661'),
                            ('cf_ragnhild','Ragnhild Cinderfoot','#ce78be'),
                            ('cf_orm','Orm Ashwalker','#70c5ce'),
                            ('cf_hildr','Hildr Lastlink','#dbdfef')]]
# The fixed throwing target must still reach carriers at the wells.
next(e for e in ENEMIES if e['kind']=='cf_orm')['ranged']=[18,11,'#ffac72',1,3,.24]
ENEMIES.append(dict(kind='cf_ingot',name='Numbered Ingot',level=99,stats=[1000000,0,0,1.1],
    profile=[0,1,0,0],boss=False,elite=False,outdoor=False,add=True,gold=0,
    material='',ranged=None,slam=0,melee=0,color='#ffbe78'))

def install(zone):
    kinds={e['kind'] for e in ENEMIES}
    zone['slimes']=[s for s in zone['slimes'] if s['kind'] not in kinds]
    for hall in zone['forgeHalls'][:9]:
        zone['slimes'].append(dict(kind=hall['boss'],x=hall['x'],y=hall['y']))
    h=zone['forgeHalls'][3]
    for i in range(6):
        angle=i*math.tau/6
        zone['slimes'].append(dict(kind='cf_ingot',x=round(h['x']+7*math.cos(angle),3),
            y=round(h['y']+7*math.sin(angle),3),ambush='cf_sigrun_ingot'))
    # A locked lift is usable only after Dagfinn falls in this private copy.
    zone['portals'] += [dict(id='cf_lift_out',name='Crucible Lift',x=64,y=287,r=1.2,to=46,tx=45,ty=214,look='chained_forge',needs_boss='cf_dagfinn'),
                        dict(id='cf_lift_back',name='Entrance Lift',x=42,y=214,r=1.2,to=46,tx=67,ty=287,look='chained_forge',needs_boss='cf_dagfinn')]
    # Clear the authored mechanic courts of solid decorative props. Preserve
    # the actual volcanic floor and every route/bridge; the posts are floor
    # markers, so a fighter can stand within their shelter radius.
    courts=[(h['x']-16,h['y']-15,h['x']+16,h['y']+15) for h in zone['forgeHalls'][:9]]
    zone['objects']=[o for o in zone['objects'] if not (o['kind'].startswith('cf_') and any(a-2<=o['x']<=c+2 and b-2<=o['y']<=d+2 for a,b,c,d in courts))]


def definitions(zone):
    first,second,third,fourth=zone['forgeHalls'][:4]
    def bounds(h):return [h['x']-16,h['y']-15,h['x']+16,h['y']+15]
    x,y=first['x'],first['y']
    anvils=[[round(x+6*math.cos(i*math.tau/5),3),round(y+6*math.sin(i*math.tau/5),3)] for i in range(5)]
    x,y=second['x'],second['y']
    posts=[[x+dx,y+dy] for dx,dy in [(-4.5,-4),(4.5,-4),(-4.5,4),(4.5,4)]]
    x,y=third['x'],third['y']
    soaks=[[x-4,y-1],[x+4,y-1],[x,y+4]]
    def mech(name,block,**kw):return dict(name=name,block=block,**kw)
    fifth,sixth,seventh,eighth,ninth=zone['forgeHalls'][4:9]
    wells=[[round(eighth['x']+7*math.cos(i*math.tau/10),3),round(eighth['y']+7*math.sin(i*math.tau/10),3)] for i in range(10)]
    return {
        'cf_dagfinn':dict(arena=bounds(fifth),mechanics=[mech('Two Valves','valves',at=[.7,.4],cast=10,duration=25,points=[[fifth['x']-6,fifth['y']],[fifth['x']+6,fifth['y']]],r=3,need=3,hold=20)]),
        'cf_thorbjorg':dict(arena=bounds(sixth),mechanics=[mech('Brand Relay','relay',cast=8,first=10,every=50,duration=32,count=3,fuse=8,immunity=6,touch=1.2,blast=5)]),
        'cf_ragnhild':dict(arena=bounds(seventh),mechanics=[mech('Four on the Floor','grid',cast=5,first=10,every=18,bpm=150,heavy=.9)]),
        'cf_orm':dict(arena=bounds(eighth),mechanics=[mech('Water Carriers','carry',points=wells,r=1,throw_r=3,need=6,window=5,quenched=15,speed=.6)]),
        'cf_hildr':dict(arena=bounds(ninth),mechanics=[mech('Mirror Plate','reflect',cast=5,first=15,every=40,duration=8,heavy=.9)]),
        'cf_sigrun':dict(arena=bounds(fourth),mechanics=[
            mech('Ingot Order','shield',ordered=dict(deadline=25,heavy=.9),
                steps=[dict(hp=1,tag='cf_sigrun_ingot',count=6,still=True),
                       dict(hp=.4,tag='cf_sigrun_ingot',count=6,still=True)])]),
        'cf_kettil':dict(arena=bounds(first),mechanics=[
            mech('Taut Chain','tether',cast=9,every=30,first=10,duration=12,leash=6,heavy=.45,points=anvils,r=2,hold=1.5,hp_min=.4),
            mech('Taut Chain','tether',cast=9,every=24,first=1,duration=12,leash=6,heavy=.45,points=anvils,r=2,hold=1.5,hp_max=.4)]),
        'cf_ysolt':dict(arena=bounds(second),mechanics=[
            mech('Gale of the Bellows','gust',cast=10,every=30,first=10,push=10,points=posts,r=1.5,capacity=3,rim=.8,hp_min=.4),
            mech('Gale of the Bellows','gust',cast=10,every=24,first=1,push=10,points=posts,r=1.5,capacity=3,rim=.8,hp_max=.4)]),
        'cf_hallgrim':dict(arena=bounds(third),mechanics=[
            mech('Hammerfall','soak',cast=8,every=28,first=10,points=soaks,r=3,need=3,heavy=.75,hp_min=.4),
            mech('Hammerfall','soak',cast=8,every=21,first=1,points=soaks,r=3,need=3,heavy=.75,hp_max=.4)]),
    }


def signs(zone):
    words=[
      ('Kettil Linkbearer','A chain joins you to a friend. When it pulls tight, stay close or it hurts you both.',
       'Follow your chain number to its blue anvil. Hold it together. Break chain 1, then 2, then 3, then 4, then 5.',
       'You have 9 seconds to get ready. Stay within 6 steps of your friend until your chain breaks.',['path','blue']),
      ('Ysolt Bellowsmaid','The arrow shows which way the wind will push you. The red edge is hot lava.',
       'Go to a blue iron post before the 10 seconds end. Only 3 friends fit at each post. Use all four posts.',
       'The wind changes direction each time. Read the arrow and the number at your post.',['path','blue','red']),
      ('Hallgrim Anvilhand','Three hammers fall on the blue anvils after 8 seconds. Each anvil needs at least 3 friends.',
       'Split into three groups. Put 3 or more friends at every blue anvil. A group that is too small falls.',
       'If one anvil is short, the shock hurts everyone. One friend can help whichever group needs them.',['blue','red']),
      ('Sigrun Slagmother','Six numbered ingots shield Sigrun. Only the lowest number still standing can be hurt.',
       'All ten friends hit ingot 1, then 2, up to 6. Each new number gives you 25 seconds. Too slow? It bursts and hurts the whole group.',
       'Break all six to hurt Sigrun. When she has 40% health left, she makes six more. The red ring shows the number to hit.',['red','path']),
      ('Dagfinn Tongsbearer','At 70% and 40% health, a red lava line divides the hall. You have 10 seconds to choose your side.',
       'Split five and five. Each blue valve needs at least 3 friends standing together for 20 full seconds. Leaving resets its progress.',
       'Stay off the red divide. If either valve is unfinished after 25 seconds, everyone falls. Beating Dagfinn opens the lift back to the entrance.',['red','blue']),
      ('Thorbjörg Quenchwife','Three friends carry burning brands. After the 8-second warning, each brand has an 8-second fuse.',
       'Carry your brand at least 2 steps, then touch a friend to pass it and refill its fuse. The giver cannot take another brand for 6 seconds.',
       'Keep passing for 32 seconds. If a fuse runs out, everyone within 5 steps of that brand falls.',['red','path']),
      ('Ragnhild Cinderfoot','The whole floor has numbered tiles. After a 5-second cue, tiles burst in order 1, 2, 3, 4 at 150 beats per minute.',
       'Wait on a tile marked 2 beside a tile marked 1. After beat 1, step onto that cleared tile before beat 2. Every new cue changes the numbers.',
       'The four beats are 0.4 seconds apart. Read the numbers, not just the colours. A red tile hurts on its own beat.',['red','blue']),
      ('Orm Ashwalker','Ten wells hold water. Walk to a blue well to take a flask. Carrying it slows you to 60% speed.',
       'Carry water into the ring at Orm’s feet to throw it. Six throws within 5 seconds quench him for 15 seconds. All ten friends can carry.',
       'Molten armour halves damage. Quenched armour takes double. Wells refill when he heats up; a missed window can be tried again.',['blue','path']),
      ('Hildr Lastlink','Mirror Plate gives a 5-second warning. Then Hildr glows white for 8 seconds and each hit makes its attacker suffer a heavy blow.',
       'Stop all attacks during the warning so flying spells can land before the glow. Hold fire while the white ring is lit.',
       'Attack again when the glow ends. The mirror returns every 40 seconds. Damage over time can also hurt its caster.',['path','red']),
    ]
    result={}
    for h,(title,what,todo,tip,colors) in zip(zone['forgeHalls'],words):
        cp=h['checkpoint']
        result[h['boss']]=dict(x=cp['x'],y=cp['y'],title=title,what=what,todo=todo,tip=tip,colors=colors)
    return result


def write_entries(path, owned):
    """Replace our top-level entries, preserving other encounters byte for byte."""
    import json
    raw=path.read_text();decoder=json.JSONDecoder();cursor=1;blocks=[]
    def skip(i):
        while i<len(raw) and raw[i].isspace():i+=1
        return i
    while True:
        cursor=skip(cursor)
        if raw[cursor]=='}':break
        start=cursor;key,cursor=decoder.raw_decode(raw,cursor)
        cursor=skip(cursor);assert raw[cursor]==':';cursor=skip(cursor+1)
        _,end=decoder.raw_decode(raw,cursor)
        if key not in owned:blocks.append(raw[start:end])
        cursor=skip(end)
        if raw[cursor]==',':cursor+=1
        else:assert raw[cursor]=='}'
    for key,value in owned.items():
        value=json.dumps(value,indent=2,ensure_ascii=False).replace('\n','\n  ')
        blocks.append(json.dumps(key)+': '+value)
    path.write_text('{\n  '+',\n  '.join(blocks)+'\n}\n')
