'use strict';
// NPC controls and code-native isometric scenery for the private GM island.
(() => {
  const make = (tag, text, cls) => { const n=document.createElement(tag); if(text)n.textContent=text; if(cls)n.className=cls; return n; };
  const islandTowns=WORLD_MAP.zones.find(z=>z.gmOnly)?.gmIsland?.towns||[];
  const towns=()=>islandTowns;
  const nearest=(x,y)=>towns().reduce((a,b)=>Math.hypot(x-b.x,y-b.y)<Math.hypot(x-a.x,y-a.y)?b:a,towns()[0]);
  const colors={christmas:[201,25,83],newyear:[229,22,53],halloween:[29,44,38],solstice:[91,49,48],easter:[119,38,55],valentine:[338,31,62]};
  function ground(x,y,tone,dirt,alt) {
    if(x>=184&&x<=240&&y>=174&&y<=224) return (x===212||y===199)?'#bfa578':`hsl(225,12%,${41+tone*9+alt}%)`;
    if(x>=176&&x<=248&&y>=256&&y<=282)return `hsl(37,29%,${53+tone*8+alt}%)`;
    const c=colors[nearest(x,y)?.id]||[105,42,45];
    return dirt?`hsl(38,28%,${61+tone*6+alt}%)`:`hsl(${c[0]+tone*6},${c[1]}%,${c[2]+tone*7+alt}%)`;
  }
  function select(label, options, id) {
    const wrap=make('label',label), input=make('select'); input.id=id;
    for(const [value,text]of options){const opt=make('option',text);opt.value=value;input.append(opt);}
    wrap.append(input);return [wrap,input];
  }
  function controls(packet) {
    if(!packet.gmIsland||!packet.gm)return [];
    const npc=packet.npc, service=npc.offers.find(o=>o.id.startsWith('gmi:'))?.id.slice(4);
    const root=make('div',null,'gmi-controls'), status=make('p','Ready.','gmi-status');status.setAttribute('role','status');
    const action=(label,op,data=()=>({}))=>{
      const b=make('button',label,'btn ghost');b.type='button';b.dataset.gmi=op;
      b.addEventListener('click',async()=>{
        b.disabled=true;
        try {
          const values=data();
          if(values.level!=null&&(!Number.isInteger(values.level)||values.level<1||values.level>99))throw Error('Level must be 1-99.');
          if(values.count!=null&&(!Number.isInteger(values.count)||values.count<1||values.count>Number(count.max)))throw Error('Choose a valid count.');
          const r=await GM.request({op:'gm_island',action:op,npc:npc.id,...values});
          status.textContent=r.ok?(op==='setup'?`Level ${r.result.level} ${r.result.class} · ${r.result.equipped} pieces equipped.`:'Done.'):(r.error||'Refused.');
          if(r.ok&&op==='leave')City.close();
        } catch(error) { status.textContent=error.message || 'Refused.'; } finally { b.disabled=false; }
      });return b;
    };
    const [cl,klass]=select('Class',packet.gmIsland.classes.map(c=>[c,c[0].toUpperCase()+c.slice(1)]),'gmi-class');
    klass.value=Field.hero?.look?.class||'warrior';
    const lvlLabel=make('label','Level'), level=make('input');level.type='number';level.min='1';level.max='99';level.value=packet.level;level.id='gmi-level';lvlLabel.append(level);
    const quantity=make('label','Count'), count=make('input');count.type='number';count.min='1';count.max=service==='mercs'?'4':'24';count.value='1';count.id='gmi-count';quantity.append(count);
    if(service==='setup'){
      const [g,gear]=select('Equipment rarity',[['common','Common'],['uncommon','Green'],['rare','Blue'],['epic','Purple'],['legendary','Orange']],'gmi-gear');gear.value='uncommon';
      root.append(make('p','Choose a normal test loadout. Rebirth, potion effects and festival bonuses are cleared. Leaving restores your saved character.'),cl,lvlLabel,g,
        action('Apply test loadout','setup',()=>({class:klass.value,level:Number(level.value),gear:gear.value})));
    }else if(service==='summon'){
      const filter=make('input');filter.type='search';filter.placeholder='Find monster or boss';filter.setAttribute('aria-label','Find monster or boss');filter.id='gmi-search';
      const [w,enemy]=select('Opponent',[],'gmi-enemy');
      const fill=()=>{const q=filter.value.toLowerCase(),was=enemy.value;enemy.replaceChildren();for(const e of packet.gmIsland.enemies){const name=window.Field?.enemyName(e.kind)||e.kind;if(!`${name} ${e.kind}`.toLowerCase().includes(q))continue;const o=make('option',`${e.boss?'Boss / elite · ':''}${name} · L${e.level}`);o.value=e.kind;o.dataset.level=e.level;enemy.append(o);}if([...enemy.options].some(o=>o.value===was))enemy.value=was;};
      filter.addEventListener('input',fill);fill();enemy.addEventListener('change',()=>{level.value=enemy.selectedOptions[0]?.dataset.level||packet.level;});
      root.append(make('p','Summons appear in the arena. Up to 24 enemies; no rewards or automatic respawns.'),filter,w,lvlLabel,quantity,
        action('Summon opponent','summon',()=>({kind:enemy.value,level:Number(level.value),count:Number(count.value)})),action('Clear arena','clear'));
    }else if(service==='mercs'){
      root.append(make('p','Up to four companions. Apply your test loadout before recruiting; changing it dismisses the old companions.'),cl,lvlLabel,quantity,
        action('Summon mercenaries','mercs',()=>({class:klass.value,level:Number(level.value),count:Number(count.value)})),action('Dismiss companions','dismiss'));
    }else if(service==='training'){
      root.append(make('p','Six immortal, stationary dummies. Open the DPS meter from its HUD button. The meter stops after five seconds without a hit.'),
        action('Reset DPS meter','reset_dps'),action('Heal, refill and reset cooldowns','refresh'));
    }else if(service==='travel'){
      root.append(action('Leave and restore my character','leave'));
    }
    root.append(status);return [root];
  }
  const K=City.kit;
  City.art.gmi_rail={box:[230,140,115,90],draw(g,o){const w=o.width||.4,d=o.depth||.4;K.prism(g,w,d,45,'#c3b48c','#827759','#534f48');}};
  City.art.gmi_pillar={box:[180,260,90,210],draw(g){K.prism(g,1.1,1.1,150,'#bfb8a3','#888480','#62626b');K.prism(g,1.6,1.6,15,'#e5cc88','#ab915e','#776c55');K.ellipse(g,0,-160,18,10,'#e9d892');}};
  City.art.gmi_target_pad={box:[190,100,95,50],ground:true,draw(g){K.ellipse(g,0,0,67,29,'#918167','#d5bc82',3);}};
  function dummy(g,s,t){
    const sway=s.hurtT>0?Math.sin(t*35)*3:0;
    g.save();g.translate(sway,0);
    K.prism(g,1.1,.8,12,'#ac9771','#776649','#544838');
    K.line(g,[[0,0],[0,-105]],'#795b3e',14);
    K.line(g,[[-37,-68],[37,-68]],'#a48053',12);
    K.ellipse(g,0,-106,21,23,'#d7bc82','#775639',3);
    K.ellipse(g,0,-69,26,27,'#dbc68e','#856c49',3);
    K.ellipse(g,0,-69,18,18,'#b4584d');K.ellipse(g,0,-69,10,10,'#eeddb2');K.ellipse(g,0,-69,4,4,'#b4584d');
    K.line(g,[[-9,-108],[-3,-108]],'#584735',2);K.line(g,[[4,-108],[10,-108]],'#584735',2);
    g.restore();
  }
  window.GMIsland={controls,ground,dummy,enter:()=>GM.request({op:'gm_island',action:'enter'}).then(r=>{if(!r.ok)Online.log(r.error,null,'gm');})};
})();
