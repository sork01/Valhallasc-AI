// Execute the production client with a deterministic clock/DOM/canvas. No browser or live connection.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const items = JSON.parse(read('world/items.txt')), map = JSON.parse(read('world/map.txt'));
const candidates = JSON.parse(read('world/fishing-spots.txt'));
let checks = 0;
function check(value, message) { checks++; assert(value, message); }
class Element {
  constructor(tag = 'div') { this.tagName = tag.toUpperCase(); this.children = []; this.events = {}; this.hidden = true; this.value = ''; this.dataset = {}; this.style = {setProperty(k,v) {this[k] = v;}}; const classes = new Set(); this.classList = {toggle(k,on) {if(on) classes.add(k); else classes.delete(k);},remove(k){classes.delete(k);},contains:k => classes.has(k)}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; this._text = ''; }
  addEventListener(name, fn) { this.events[name] = fn; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text || this.children.map(n => typeof n === 'string' ? n : n.textContent).join(' '); }
  focus() { this.focused = true; }
  getBoundingClientRect() { return {width:260,height:80}; }
  setAttribute(k,v) { this[k] = v; }
}
function fixture() {
  const els = new Map(), events = {}, cues = [], sent = [], errors = [], ops = [];
  let time = 0, reduced = false;
  const el = id => { if (!els.has(id)) els.set(id, new Element()); return els.get(id); };
  const ctx = {performance:{now:() => time},Date:class extends Date {static now(){return 100000 + time;}},
    document:{getElementById:el,createElement:tag => new Element(tag),addEventListener(name,fn){events[name]=fn;}},
    WORLD_ITEMS:items, Prefs:{keys:{}}, navigator:{},
    Locale:{language:'en',translate:t=>t},matchMedia:()=>({get matches(){return reduced;}}),
    addEventListener(name,fn){events[name]=fn;},MutationObserver:class{observe(){}},
    Inventory:{definition:id=>items.find(i=>i.id===id),icon:i=>i ? `<i data-icon="${i.id}"></i>` : ''},
    Field:{canAct:true,hero:null,clearInput(){this.clears=(this.clears||0)+1;},setPaused(on){this.paused=on; this.canAct=!on;}},
    Online:{connected:true,send:p=>{sent.push(p);return true;}},Cutscene:{active:false},
    Announce:{show:(...args)=>errors.push(args)}, setTimeout,clearTimeout,
  };
  ctx.window=ctx;vm.createContext(ctx);
  vm.runInContext(read('client/keymap.js'),ctx);
  check(ctx.Keys.holders('KeyR','fish').length===0, 'default fishing key is free');
  let src=read('client/fishing.js');
  if(process.env.MUTATE==='hint')src=src.replace(".replace(/‹fish›/g, tr(Keys.label('fish', false)))",'');
  // Deliberately break behaviour in memory; these remain effective after the implementation is committed.
  if(process.env.MUTATE==='input')src=src.replace("Online.send({ type: 'fish' })", "Online.send({ type: 'attack' })");
  if(process.env.MUTATE==='spots')src=src.replace('(packet.fishingSpots || [])','(map.fishingSpots || [])');
  if(process.env.MUTATE==='records')src=src.replace('log = hero.fishingLog || {}','log = {}');
  if(process.env.MUTATE==='deadline')src=src.replace(' / 1200)', ' / 120000)');
  if(process.env.MUTATE==='privacy')src=src.replace("if (e.actor !== self || !e.kind?.startsWith('fish_'))", "if (!e.kind?.startsWith('fish_'))");
  if(process.env.MUTATE==='cleanup')src=src.replace('lines.clear(); $(\'fishing-panel\')', '$(\'fishing-panel\')');
  if(process.env.MUTATE==='cardX')src=src.replace('((box.width || 240) / 2 + 8) / (stage.clientWidth || width) * width','120');
  if(process.env.MUTATE==='cardY')src=src.replace('((box.height || 80) + 8) / (stage.clientHeight || height) * height','100');
  vm.runInContext(src,ctx);
  const g = new Proxy({globalAlpha:1}, {get(t,k){return k in t?t[k]:(...a)=>ops.push([k,...a]);},set(t,k,v){t[k]=v;return true;}});
  const project=(x,y)=>[x*10,y*10];
  const draw=(ground=false)=>ctx.Fishing.drawFishing(g,project,1600,900,ground,reduced);
  const sync=(hero,spots=[],z=map,others=[])=>{ctx.Field.hero={...hero};ctx.Fishing.sync({players:[hero,...others],fishingSpots:spots,fishingTime:(100000+time)/1000},hero,z,c=>cues.push(c));};
  return {ctx,el,events,cues,sent,errors,ops,g,draw,sync,setTime:t=>{time=t;},reduce:on=>{reduced=on;}};
}
const f=fixture(), {ctx,el,cues,sent,errors}=f, fishing=ctx.Fishing;
const twig=items.find(i=>i.kind==='rod'&&!i.fishing.lava), lava=items.find(i=>i.kind==='rod'&&i.fishing.lava), allRods=items.filter(i=>i.kind==='rod').map(i=>({item:i.id,quantity:1}));
const hero={id:'self',x:map.dock.start.x,y:map.dock.start.y,zone:0,level:99,fx:1,fy:0,inventory:allRods};
check(el('fishing-hint').textContent.includes('press R to cast')&&!el('fishing-hint').textContent.includes('‹fish›'),'log hint resolves the initial fishing key');
check(ctx.Keys.is({code:'KeyR',key:'r'},'fish'),'default physical fishing key works');
ctx.Prefs.keys.fish=['KeyV'];check(!ctx.Keys.is({code:'KeyR',key:'r'},'fish')&&ctx.Keys.is({code:'KeyV',key:'v'},'fish'),'rebound key replaces the shipped binding');
check(ctx.Keys.label('fish')==='V','bite hint follows rebind');f.events['keymap-change']();check(el('fishing-hint').textContent.includes('press V to cast'),'log hint follows rebound fishing key');delete ctx.Prefs.keys.fish;

// Exercise Field's real key routing and action dispatcher, including typing/repeat guards.
const field=read('client/field.js');
ctx.running=true;ctx.paused=false;ctx.hero={...hero};ctx.heldDirection=()=>null;
ctx.Field.action=vm.runInContext('(function(action) {'+field.split('    action(action) {')[1].split('\n    clearInput()')[0].replace(/},\s*$/, '}')+')',ctx);
vm.runInContext('function onKeyDown(e) {'+field.split('  function onKeyDown(e) {')[1].split('\n  function onKeyUp')[0],ctx);
const key=(code,extra={})=>ctx.onKeyDown({code,key:code.slice(-1).toLowerCase(),preventDefault(){},...extra});
f.sync(hero);f.setTime(50);key('KeyR',{target:{tagName:'INPUT'}});key('KeyR',{repeat:true});
check(sent.length===0,'typing and held-key repeat never cast');
ctx.Prefs.keys.fish=['KeyV'];key('KeyR');check(sent.length===0,'old binding cannot cast through Field');
key('KeyV');check(sent.length===1&&sent[0].type==='fish','Field routes a rebound fishing key into the real action');
delete ctx.Prefs.keys.fish;sent.length=0;f.setTime(500);

// The real touch button uses pointerdown for a quick hook and suppresses its synthetic click.
const touch=read('client/touch.js');ctx.arc=new Element();ctx.tr=text=>ctx.Locale.translate(text);
ctx.Keys.register('fish',()=>ctx.Field.action('fish'));
vm.runInContext('function button('+touch.split('  function button(')[1].split("\n  Keys.register('attack'")[0]+"\nthis.touchFish=button('Cast','fish',arc);",ctx);
ctx.touchFish.events.pointerdown({pointerType:'touch',preventDefault(){}});
ctx.touchFish.events.click({detail:1});
check(sent.length===1,'one touch produces one fishing input');sent.length=0;f.setTime(1000);
ctx.coarse={matches:true};ctx.fish=ctx.touchFish;
vm.runInContext('function fishTouchUpdate() {'+touch.split('  function update() {')[1].split('    const ids = assignments()')[0]+'}',ctx);
ctx.fishTouchUpdate();check(!ctx.fish.hidden&&ctx.fish.textContent==='Cast','contextual touch Cast button uses real update path');
check(fishing.shore(hero,map),'Saltby sea mask is fishable');
check(!fishing.shore({...hero,inventory:[]},map),'no rod hides shore control');
check(fishing.shore({...hero,inventory:[{item:lava.id,quantity:1}]},map),'Platinum line also fishes ordinary water');
check(!fishing.shore({...hero,x:10000},map),'far from shores');
for(const p of candidates) {
 const z=p.zone===0?map:map.zones[p.zone-1], h={...hero,zone:p.zone,x:p.shore.x,y:p.shore.y,fx:p.facing.x,fy:p.facing.y};
 check(fishing.shore(h,z),`context button accepts authored shore ${p.id}`);
}
const lavaSpot=candidates.find(p=>p.zone===45), lavaMap=map.zones[44];
check(!fishing.shore({...hero,zone:45,...lavaSpot.shore,fx:lavaSpot.facing.x,fy:lavaSpot.facing.y,inventory:[{item:twig.id,quantity:1}]},lavaMap),'water rod cannot fish lava');
f.sync(hero);check(fishing.available(),'context control visible at shore with rod');
f.sync({...hero,inCombat:true});check(!fishing.available(),'context control hidden in combat');f.sync(hero);
check(fishing.press(),'press sends request');check(sent.length===1&&sent[0].type==='fish'&&Object.keys(sent[0]).length===1,'request contains no catch, point or timestamp');
check(!fishing.press()&&sent.length===1,'double pointer/key activation is suppressed');
f.setTime(1200);ctx.Cutscene.active=true;check(!fishing.press(),'cutscenes block fishing');ctx.Cutscene.active=false;
ctx.Field.canAct=false;check(!fishing.press(),'paused/disconnected field blocks fishing');ctx.Field.canAct=true;
f.setTime(1500);check(fishing.press()&&sent.length===2,'fresh press works');

// Candidate map coordinates never draw as rich spots. Only active snapshot coordinates may render.
f.sync(hero,[],{...map,fishingSpots:[{x:777,y:777}]});f.ops.length=0;f.draw(true);
check(f.ops.filter(o=>o[0]==='ellipse').length===0,'candidate pool is not rendered');
f.sync(hero,[{x:4,y:8}],{...map,fishingSpots:[{x:777,y:777}]});f.ops.length=0;f.reduce(true);f.draw(true);
check(f.ops.filter(o=>o[0]==='ellipse').length===1&&f.ops.find(o=>o[0]==='ellipse')[1]===40,'only active rich point renders, reduced motion uses one ring');
f.sync(hero,[]);f.ops.length=0;f.draw(true);check(!f.ops.some(o=>o[0]==='ellipse'),'depleted point disappears on next snapshot');

// Cast -> landing -> waiting -> bite -> reel -> card. Snapshot repetition must not restart cues.
const line={x:21,y:29,state:'cast',lava:false};
f.setTime(1000);fishing.event({actor:'self',kind:'fish_cast',x:line.x,y:line.y},'self',c=>cues.push(c));f.sync({...hero,fishing:line});
f.draw();check(cues.join(',')==='cast','cast cue before landing');
f.setTime(1500);f.draw();f.draw();check(cues.join(',')==='cast,plop','plop once at landing');
const remote={id:'other',x:24,y:30,zone:0,fishing:{...line,x:28,state:'waiting'}};
f.sync({...hero,fishing:{...line,state:'waiting'}},[],map,[remote]);f.ops.length=0;f.draw();
check(f.ops.filter(o=>o[0]==='quadraticCurveTo').length===4,'own and other player each draw rod and line');
fishing.event({actor:'other',kind:'fish_catch',item:'fish_pier_sprat'},'self');check(cues.length===2,'remote events cannot show private catch UI or sound');
f.setTime(2000);f.sync({...hero,fishing:{...line,state:'bite'},fishDeadline:103.2},[],map,[remote]);
fishing.event({actor:'self',kind:'fish_bite',deadline:103.2},'self');check(fishing.phase==='bite'&&cues.at(-1)==='bite','bite phase and cue');
ctx.fishTouchUpdate();check(ctx.fish.textContent==='Hook!'&&ctx.fish.dataset.bite==='true','touch button becomes Hook on bite');
f.draw();f.ops.length=0;f.setTime(2600);f.draw();
const arc=f.ops.find(o=>o[0]==='arc');check(arc&&Math.abs(arc[5]-Math.PI/2)<.001,'deadline ring drains using server clock');
const fish=items.find(i=>i.kind==='fish'&&i.rarity==='legendary');
fishing.event({actor:'self',kind:'fish_catch',item:fish.id,rarity:fish.rarity,kg:22,quantity:3},'self');
f.sync({...hero,fishingLog:{total:1,legendary:1,longestStreak:1,species:{[fish.id]:{count:1,bestKg:22}}}});
f.draw();check(el('fishing-catch').hidden&&cues.at(-1)==='reel','reel precedes catch card');
f.setTime(3200);f.draw();check(!el('fishing-catch').hidden&&el('fishing-catch').textContent.includes(fish.name)&&el('fishing-catch').textContent.includes('22'),'card shows authoritative fish and weight');
check(cues.at(-1)==='legendary'&&!cues.includes('catch'),'one legendary celebration replaces ordinary catch');
el('stage').clientWidth=600;el('stage').clientHeight=390;ctx.Field.hero={x:1,y:1};f.draw();
check(parseFloat(el('fishing-catch').style.left)*6>=138,'phone catch card stays inside the left edge');
check(parseFloat(el('fishing-catch').style.top)*3.9+.001>=88,'phone catch card stays below the top edge (subpixel rounding tolerance)');
el('stage').clientWidth=1600;el('stage').clientHeight=900;ctx.Field.hero={...hero};
check(!el('stage').classList.contains('fishing-legendary'),'reduced motion suppresses screen glow');
f.draw();check(cues.filter(c=>c==='legendary').length===1,'no celebration replay on next frame');
f.reduce(false);f.draw();check(el('stage').classList.contains('fishing-legendary'),'legendary has edge glow with motion enabled');
f.setTime(6200);f.draw();check(el('fishing-catch').hidden&&!el('stage').classList.contains('fishing-legendary'),'card and glow expire');

check(fishing.open()&&ctx.Field.paused,'collection window pauses inputs');
check(el('fishing-species').children.filter(r=>r.dataset.item).length===items.filter(i=>i.kind==='fish').length,'log includes complete species catalogue');
check(el('fishing-records').textContent.includes('Caught: 1')&&el('fishing-records').textContent.includes('Legendary: 1'),'log uses saved counters');
const caughtRow=el('fishing-species').children.find(r=>r.dataset.item===fish.id), unknown=el('fishing-species').children.find(r=>r.dataset.item&&r.dataset.item!==fish.id);
check(caughtRow.textContent.includes('22')&&caughtRow.textContent.includes('1 caught'),'per-species saved weight and count');
check(unknown.textContent.includes('Undiscovered fish')&&unknown.children[0].classList.contains('silhouette'),'unseen species have silhouette and hidden name');
el('fishing-filter').value='Lava';el('fishing-filter').events.change();check(el('fishing-species').children.filter(r=>r.dataset.item).length===items.filter(i=>i.kind==='fish'&&i.fishing.habitat==='Lava').length,'habitat filter follows catalogue');
let stopped=false;f.events.keydown({code:'Escape',key:'Escape',preventDefault(){},stopPropagation(){stopped=true;}});check(stopped&&el('fishing-panel').hidden&&!ctx.Field.paused,'Escape closes log and resumes inputs without menu');

f.setTime(7000);f.sync({...hero,fishing:{...line,lava:true,state:'cast'}});fishing.event({actor:'self',kind:'fish_cast',x:21,y:29},'self');
f.sync({...hero,zone:1,fishing:{...line,lava:true,state:'cast'}},[],map.zones[0]); // zone transition discards old local effects
f.setTime(7500);f.draw();check(cues.at(-1)==='lava','lava cast has landing bubble');
fishing.event({actor:'self',kind:'fish_miss',text:'Too early.'},'self');check(errors.at(-1)[0]==='Too early.'&&errors.at(-1)[1]==='error','miss uses error stack');
f.sync({...hero,fishing:line});fishing.reset();f.ops.length=0;f.draw();check(!fishing.available()&&fishing.phase==='idle'&&!f.ops.some(o=>o[0]==='quadraticCurveTo'),'reset clears lines and availability');

// Run the real System tab formatter and preserve item-name rarity marking.
vm.runInContext(read('client/syslog.js'),ctx);
let rows=ctx.SystemLog.lines({actor:'self',kind:'fish_catch',item:fish.id,rarity:'legendary',kg:22,quantity:3},'self');
check(rows.length===1&&rows[0][0].includes('22 kg')&&rows[0][2].rarity==='legendary','one rarity-marked system line per catch');
check(ctx.SystemLog.lines({actor:'other',kind:'fish_catch',item:fish.id},'self').length===0,'other player catches are private');
rows=ctx.SystemLog.lines({actor:'self',kind:'fish_catch',item:'fishing_driftwood',quantity:1},'self');check(!rows[0][0].includes('kg'),'junk and treasure have no invented weight');

// Real Swedish translation logic, including nested item names and player names that must stay unchanged.
const body={nodeType:1,querySelectorAll:()=>[],hasAttribute:()=>false};
const sv={window:null,localStorage:{getItem:()=>JSON.stringify({lang:'sv'})},navigator:{language:'sv'},document:{documentElement:{},body,createTreeWalker:()=>({nextNode:()=>null})},Node:{TEXT_NODE:3,ELEMENT_NODE:1},NodeFilter:{SHOW_TEXT:4},MutationObserver:class{observe(){}}};sv.window=sv;vm.createContext(sv);
for(const name of ['sv-data.js','locale.js'])vm.runInContext(read('client/'+name),sv);
ctx.Locale=sv.Locale;el('fishing-filter').value='';f.sync({...hero,fishingLog:{total:2,legendary:1,longestStreak:2,species:{[fish.id]:{count:2,bestKg:22}}}});fishing.open();
check(el('fishing-records').textContent.startsWith('Fångster: 2'),'Swedish collection records');
check(el('fishing-species').children.find(r=>r.dataset.item===fish.id).textContent.includes('Rekord: ca 22 kg'),'Swedish per-species record');
check(sv.Locale.translate(`Forest caught ${fish.name} (ca 22 kg)!`).startsWith('Forest fångade '),'legendary announcement preserves player name');
check(sv.Locale.translate(`You catch ${fish.name} (ca 22 kg) ×3.`).startsWith('Du fångar '),'Swedish catch line');
const html=read('client/index.html');
for(const habitat of new Set(items.filter(i=>i.kind==='fish').map(i=>i.fishing.habitat)))check(html.includes(`<option value="${habitat}">${habitat}</option>`),'habitat option value survives translated label: '+habitat);
check(html.indexOf('src="fishing.js"')<html.indexOf('src="settings.js"'),'fishing panel exists before window settings initialise');
check(read('client/settings.js').includes("['fishing-panel', '.fishing-window'"),'collection window participates in UI sizing');

// Execute the actual effects loader and verify bus, mute, cache, scene and latency behaviour.
(async()=>{
 let source=read('client/game.js').split('// FISHING-SOUND-BEGIN:')[1].split('// FISHING-SOUND-END')[0].split('\n').slice(1).join('\n');
 if(process.env.MUTATE==='sound')source=source.replace('source.connect(sfxOut(c))','source.connect(c.destination)');
 const connections=[],fetches=[],audioOps=[];let audioTime=0;
 const c={destination:{destination:true},decodeAudioData:async()=>({decoded:true}),createBufferSource:()=>({connect:n=>connections.push(n),start:()=>audioOps.push('start')})},bus={effects:true};
 const a={save:{sound:true},scene:'game',audio:()=>c,sfxOut:()=>bus,performance:{now:()=>audioTime},fetch:async url=>{fetches.push(url);return{ok:true,arrayBuffer:async()=>new ArrayBuffer(4)};}};
 vm.createContext(a);vm.runInContext(source+'\nthis.playFish=fishingSound;',a);
 a.playFish('bite');await new Promise(setImmediate);check(connections[0]===bus&&audioOps.length===1,'recorded cue connects to SFX bus');
 a.playFish('bite');await new Promise(setImmediate);check(fetches.length===1&&audioOps.length===2,'decoded cues are reused');
 a.save.sound=false;a.playFish('catch');await new Promise(setImmediate);check(fetches.length===1,'mute prevents fetch and playback');
 a.save.sound=true;a.playFish('reel');audioTime=2000;await new Promise(setImmediate);check(audioOps.length===2,'late decode does not play obsolete cue');
 a.playFish('cast');a.scene='splash';await new Promise(setImmediate);check(audioOps.length===2,'leaving game suppresses pending cue');
 console.log(`Fishing client: ${checks} behavioural checks pass (including ${candidates.length} authored shores).`);
})().catch(e=>{console.error(e);process.exitCode=1;});
