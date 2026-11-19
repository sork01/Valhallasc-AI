// Actual fishing controller, using the existing controlled DOM/canvas fixture.
const assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path');
const root=path.resolve(__dirname,'..'), mode=process.env.FISH_RICH_MUTATION;
if(process.argv.includes('--mutations')) {
 const {spawnSync}=require('node:child_process');
 for(const [name,message] of Object.entries({hit:'active spot is hoverable',marker:'active spot has a fish marker',status:'a cast into the active spot is identified',stale:'depletion clears the rich-line indicator',tooltip:'hover opens a named rich-spot tooltip'})) {
  const r=spawnSync(process.execPath,[__filename],{cwd:root,encoding:'utf8',env:{...process.env,FISH_RICH_MUTATION:name}});
  assert(r.status!==0&&(r.stdout+r.stderr).includes(message),name+': '+r.stdout+r.stderr);
  console.log('Caught rich-spot mutation:',name);
 }
 process.exit(0);
}
const read=fs.readFileSync.bind(fs);
const controlled={...fs,readFileSync(file,...args){let s=read(file,...args);if(String(file).endsWith('/client/fishing.js')&&typeof s==='string'){
 if(mode==='hit')s=s.replace('function richSpotAt(mx, my, project) {','function richSpotAt(mx, my, project) { return null;');
 if(mode==='marker')s=s.replace('spotMarker(g, x, y);','');
 if(mode==='status')s=s.replace('get richActive() { return usingRichSpot(); }','get richActive() { return false; }');
 if(mode==='stale')s=s.replace('return !!point && spots.some(spot => Math.hypot(spot.x - point.x, spot.y - point.y) < .001);','return !!point;');
 if(mode==='tooltip')s=s.replace('function drawRichTooltip(project, width, height) {','function drawRichTooltip(project, width, height) { return;');
}return s;}};
const prefix=fs.readFileSync(path.join(__dirname,'fishing-client.cjs'),'utf8').split('const f=fixture(),')[0];
const fixture=new Function('require','__dirname',prefix+'\nreturn fixture;')(name=>name==='node:fs'?controlled:require(name),__dirname);
const f=fixture(),{ctx,el}=f, fish=ctx.Fishing;
ctx.document.body=el('body');ctx.innerWidth=1600;ctx.innerHeight=900;
el('fieldcv').getBoundingClientRect=()=>({left:0,top:0,width:1600,height:900});
const map=JSON.parse(read(path.join(root,'world/map.txt'))),items=JSON.parse(read(path.join(root,'world/items.txt')));
const hero={id:'self',zone:0,...map.dock.start,level:99,fx:1,fy:0,inventory:items.filter(i=>i.kind==='rod').map(i=>({item:i.id,quantity:1}))};
const spot={x:4,y:8},project=(x,y)=>[x*10,y*10];let checks=0;
const tooltip=()=>ctx.document.body.children.find(n=>n.id==='rich-fishing-tooltip')||{hidden:true,textContent:''};
const check=(ok,message)=>{assert(ok,message);checks++;};
f.sync(hero,[spot]);
check(fish.richSpotAt(40,80,project)?.x===4,'active spot is hoverable');
check(!fish.richSpotAt(400,800,project),'ordinary scenery is not a rich hotspot');
f.reduce(true);f.ops.length=0;f.draw(true);
check(f.ops.some(o=>o[0]==='quadraticCurveTo'),'active spot has a fish marker');
check(f.ops.some(o=>o[0]==='fillText'&&o[1]==='Rich fishing spot'),'active spot is named on the water');
el('fieldcv').events.pointermove({pointerType:'mouse',clientX:40,clientY:80});f.draw();
check(!tooltip().hidden&&tooltip().textContent.includes('Rich fishing spot'),'hover opens a named rich-spot tooltip');
check(tooltip().textContent.includes('5–10 fish'),'tooltip explains shared fish depletion');
el('fieldcv').events.pointerleave();check(tooltip().hidden,'leaving the water clears the tooltip');

fish.event({actor:'self',kind:'fish_cast',...spot},'self');
const line={...spot,lava:false,state:'waiting'};f.sync({...hero,fishing:line},[spot]);
check(fish.richActive,'a cast into the active spot is identified');
f.ops.length=0;f.draw();check(f.ops.some(o=>o[0]==='fillText'&&o[1]==='Rich fishing spot'),'rich line is confirmed beside the hero');
f.sync({...hero,fishing:line},[]);
check(!fish.richActive,'depletion clears the rich-line indicator');
check(!fish.richSpotAt(40,80,project),'depleted point loses its hover hit area');
f.ops.length=0;f.draw(true);check(!f.ops.some(o=>o[0]==='fillText'&&o[1]==='Rich fishing spot'),'depleted point loses its visible label');

fish.reset();f.sync(hero,[]);fish.event({actor:'self',kind:'fish_cast',...spot},'self');
f.sync({...hero,fishing:line},[spot]);
check(!fish.richActive,'a later spawn cannot turn an ordinary cast into a rich cast');
f.ops.length=0;f.draw();check(f.ops.some(o=>o[0]==='fillText'&&o[1]==='Ordinary fishing water'),'ordinary cast is explicitly identified');
el('fieldcv').events.pointermove({pointerType:'mouse',clientX:40,clientY:80});f.draw();fish.reset();
check(tooltip().hidden,'disconnect/reset clears the rich tooltip');
console.log(`Rich fishing UI: ${checks} behaviour checks pass.`);
