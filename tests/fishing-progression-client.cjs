// Run the actual inventory, fishing and workshop modules in deterministic DOM fixtures.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),mode=process.env.FISH_PROGRESSION_MUTATION;
if(process.argv.includes('--mutations')){
 for(const [name,message] of Object.entries({shore:'facing water does not draw a passive rod requirement',castError:'cast refusal appears in the red error stack',requirements:'Yearwheel names Worldwire',hover:'ordinary water hover names the required rod',food:'food description shows bonus strength',upgrade:'workshop explains replacement',ladder:'collection contains the complete upgrade ladder',buff:'food bonus chip shows the dish name'})){
  const p=spawnSync(process.execPath,[__filename],{env:{...process.env,FISH_PROGRESSION_MUTATION:name},encoding:'utf8'});
  assert(p.status!==0&&(p.stderr+p.stdout).includes(message),`${name}: ${p.stdout}${p.stderr}`);console.log('Caught fishing progression UI mutation:',name);
 }process.exit(0);
}
const read=fs.readFileSync.bind(fs),controlled={...fs,readFileSync(file,...args){let s=read(file,...args);if(typeof s==='string'){
 if(String(file).endsWith('/client/fishing.js')){
  if(mode==='shore')s=s.replace('if (cast && !cast.landed', "if (shoreHint && !own?.fishing) g.fillText(requirement(own.zone || 0), 0, 0);\n    if (cast && !cast.landed");
  if(mode==='requirements')s=s.replace("i.fishing?.zones?.includes(zone)",'false');
  if(mode==='hover')s=s.replace('function waterAt(mx, my, project) {','function waterAt(mx, my, project) { return false;');
  if(mode==='ladder')s=s.replace('ladder.append(row);','');
 }
 if(String(file).endsWith('/client/game.js')&&mode==='buff')s=s.replace("b.id.replace(/^meal:/, '')",'b.id');
 if(String(file).endsWith('/client/online.js')&&mode==='castError')s=s.replace('if (!packet.fatal) window.Field?.error(packet.text);','');
 if(String(file).endsWith('/client/inventory.js')&&mode==='food')s=s.replace("const b = i?.foodBonus; if (!b) return '';","return ''; const b = i?.foodBonus; if (!b) return '';");
 if(String(file).endsWith('/client/fisher-workshop.js')&&mode==='upgrade')s=s.replace("if(item.kind==='rod')for",'if(false)for');
}return s;}};
const getFixture=(file,split,tail)=>new Function('require','__dirname',read(path.join(__dirname,file),'utf8').split(split)[0]+tail)(name=>name==='node:fs'?controlled:require(name),__dirname);
const inv=getFixture('fishing-data-client.cjs','const {ctx,all,Element}=fixture();','\nreturn fixture();'),f=getFixture('fishing-client.cjs','const f=fixture(),','\nreturn fixture();');
const {ctx,el}=f,fish=ctx.Fishing,items=ctx.WORLD_ITEMS;
ctx.Inventory=inv.ctx.Inventory;ctx.Locale={translate:t=>t};ctx.document.body=el('body');ctx.innerWidth=1600;ctx.innerHeight=900;
el('fieldcv').getBoundingClientRect=()=>({left:0,top:0,width:1600,height:900});
const map=JSON.parse(read(path.join(root,'world/map.txt'))),hero={id:'self',zone:0,...map.dock.start,level:99,fx:1,fy:0,inventory:[]};let checks=0;
const check=(condition,message)=>{assert(condition,message);checks++;};
check(fish.requirement(28).includes('Worldwire Rod'),'Yearwheel names Worldwire');
for(const [zone,name] of [[0,'Twig Rod'],[1,'Platinum Rod'],[6,'Platinum Rod'],[7,'Reedglass Rod'],[13,'Silverline Rod'],[14,'Tempered Platinum Rod'],[19,'Silverline Rod'],[20,'Reedglass Rod'],[22,'Reedglass Rod'],[25,'Silverline Rod'],[26,'Starcatch Rod'],[45,'Tempered Platinum Rod'],[23,'Rootbraid Rod'],[24,'Rootbraid Rod'],[27,'Cairnsteel Rod']])check(fish.requirement(zone).includes(name),`required rod in zone ${zone}`);
check(fish.requirement(2,true).includes('Willow Rod')&&fish.requirement(2).includes('Twig Rod'),'rich cold water names its higher requirement');
const small={objects:[{kind:'water',x:5,y:5,r:2}]};f.sync({...hero,x:2,y:5},[],small);f.ops.length=0;f.draw();
// The former passive shoreline requirement was deliberately removed: cast errors own this feedback.
for(const inventory of [[],[{item:'rod_twig_rod',quantity:1}],[{item:'rod_worldwire_rod',quantity:1}]]){
 f.sync({...hero,x:2,y:5,inventory},[],small);f.ops.length=0;f.draw();
 check(!f.ops.some(o=>['fillText','strokeText'].includes(o[0])&&o[1].startsWith('Requires ')),'facing water does not draw a passive rod requirement');
 check(fish.available(),'shore Cast control remains available regardless of carried rod');
}
check(f.errors.length===0,'standing near water does not announce a rod error');
f.sync({...hero,x:2,y:5},[],small);
check(fish.press()&&f.sent.at(-1).type==='fish','shore cast reaches authoritative rod validation');
// Exercise the actual nonfatal error handler and shared error presenter without a browser/socket.
{
 const feedback=getFixture('fishing-client.cjs','const f=fixture(),','\nreturn fixture();'),c=feedback.ctx;
 c.Field.hero=hero;c.setTimeout=()=>0;
 for(const name of ['announce.js','worldfeedback.js'])vm.runInContext(read(path.join(root,'client',name),'utf8'),c);
 c.Field.error=text=>c.WorldFeedback.error(text);c.log=()=>{};
 const online=controlled.readFileSync(path.join(root,'client/online.js'),'utf8');
 const handler=online.slice(online.indexOf("        case 'error':"),online.indexOf('\n      }',online.indexOf("        case 'error':")));
 c.packet={type:'error',text:'This water requires Worldwire Rod (level 70).'};
 vm.runInContext('switch(packet.type){'+handler+'}',c);
 const lines=feedback.el('error-messages').children;
 check(lines.length===1&&lines[0].dataset.kind==='error'&&lines[0].textContent===c.packet.text,'cast refusal appears in the red error stack');
 check(feedback.el('announce').children.length===0,'cast refusal stays out of ordinary announcements');
}
el('fieldcv').events.pointermove({pointerType:'mouse',clientX:50,clientY:50});f.draw();
let tooltip=ctx.document.body.children.find(n=>n.id==='rich-fishing-tooltip');
check(tooltip&&!tooltip.hidden&&tooltip.textContent.includes('Ordinary fishing water')&&tooltip.textContent.includes('Twig Rod'),'ordinary water hover names the required rod');
// Verify inverse projection with actual isometric geometry, not only an axis-aligned mock.
const project=(x,y)=>[600+(x-y)*16,250+(x+y)*8],p=project(5,5);check(fish.waterAt(...p,project),'isometric water hit-test');check(!fish.waterAt(...project(20,20),project),'dry ground has no water tooltip');
f.sync({...hero,zone:45},[{x:5,y:5}],{objects:[{kind:'ew_lava',x:5,y:5,r:2}]});
el('fieldcv').events.pointermove({pointerType:'mouse',clientX:50,clientY:50});f.draw();
check(tooltip.textContent.includes('Tempered Platinum Rod')&&tooltip.textContent.includes('5–10 fish'),'rich lava hover has rod requirement and shared depletion');
for(const i of items.filter(i=>i.foodBonus)){
 const description=ctx.Inventory.foodBonus(i);check(description.includes(Math.round(i.foodBonus.amount*100)+'%')&&description.includes('10 min'),'food description shows bonus strength');
 check(description.includes('One food bonus at a time.'),'food description explains replacement');
 check(ctx.Inventory.effect(i).includes(description),'food tooltip combines restoration and bonus');
}
for(const i of items.filter(i=>i.kind==='rod')){
 const details=ctx.Inventory.rodDetails(i).join(' ');check(details.includes('consumes the previous rod')&&details.includes('Unlocks:'),'rod tooltip names unlocks and replacement');
 check(details.includes((i.fishing.tier-1)*6+'% shorter waits'),'rod preview matches cumulative wait reduction');
}
f.sync({...hero,zone:8},[],small);check(!fish.waterAt(50,50,(x,y)=>[x*10,y*10]),'underwater zones have no fishing tooltip');
f.sync(hero);fish.open();const ladder=el('fishing-species').children.find(n=>n.className==='fishing-progression');check(ladder.textContent.includes('Current rod: No rod yet')&&ladder.textContent.includes('Next upgrade: Twig Rod'),'collection shows current and next upgrade');check(ladder&&ladder.children.find(n=>n.tagName==='DETAILS')?.children.length===11,'collection contains the complete upgrade ladder');
vm.runInContext(controlled.readFileSync(path.join(root,'client/fisher-workshop.js'),'utf8'),ctx);
const holder=el('holder'),recipe=JSON.parse(read(path.join(root,'world/fishing-workshop.txt'))).find(r=>r.id==='rod:emberline');
ctx.Money={text:n=>n+' copper'};ctx.FisherWorkshop.render({id:'fisher_meadow_0'},{level:5,gold:999,inventory:[],fisherQuote:[recipe]},holder);
check(holder.textContent.includes('Upgrading consumes the previous rod.')&&holder.textContent.includes('Crags lava'),'workshop explains replacement');
// Execute the real buff renderer: the healing and ten-minute bonus are separate chips.
ctx.buffBar=el('buff-bar');ctx.buffTipState=null;ctx.WORLD_SKILLS=[];ctx.Skillbar={icon:()=>''};
ctx.el=(tag,attrs={})=>{const n=ctx.document.createElement(tag);for(const [key,value] of Object.entries(attrs)){
 if(key.startsWith('data-'))n.dataset[key.slice(5)]=value;else if(key==='text')n.textContent=value;else n[key]=value;
}n.querySelector=tag=>n.children.find(c=>c.tagName===tag.toUpperCase());return n;};
const game=controlled.readFileSync(path.join(root,'client/game.js'),'utf8');
vm.runInContext(game.slice(game.indexOf('  function renderBuffs(list) {'),game.indexOf('  function noiseBurst(')),ctx);
ctx.renderBuffs([{id:'dish_shore_grill',kind:'regen',left:8,time:8},{id:'meal:dish_shore_grill',kind:'haste',amount:.02,left:600,time:600}]);
const bonusChip=ctx.buffBar.children.find(c=>c.dataset.buff==='meal:dish_shore_grill');
check(bonusChip._buffMeta.name==='Shore Fish Grill','food bonus chip shows the dish name');
check(bonusChip._buffMeta.description.includes('2% attack speed')&&!bonusChip._buffMeta.description.includes('Restores'),'bonus chip explains the ongoing bonus');
check(bonusChip.querySelector('i').textContent==='10:00','food bonus timer uses minutes');
// Follow the established glossary: proper place names stay English except existing exceptions.
const body={nodeType:1,querySelectorAll:()=>[],hasAttribute:()=>false};
const sv={window:null,localStorage:{getItem:()=>JSON.stringify({lang:'sv'})},navigator:{language:'sv'},document:{documentElement:{},body,createTreeWalker:()=>({nextNode:()=>null})},Node:{TEXT_NODE:3,ELEMENT_NODE:1},NodeFilter:{SHOW_TEXT:4},MutationObserver:class{observe(){}}};sv.window=sv;vm.createContext(sv);
for(const name of ['sv-data.js','locale.js'])vm.runInContext(read(path.join(root,'client',name),'utf8'),sv);
check(sv.Locale.translate('Crags lava')==='Lava i Crags','Swedish retains proper place names');
check(sv.Locale.translate('Stormglass and Lapis Erg')==='Stormglass och Lapis Erg','Swedish retains both established names');
check(sv.Locale.translate('Emberwake lava')==='Lava i Glödvaket','Swedish uses the established Emberwake exception');
console.log(`Fishing progression client: ${checks} behavioural checks pass.`);
