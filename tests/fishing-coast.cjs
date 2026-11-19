// Real coastline casts and one catch; disposable server/database only.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const root=path.resolve(__dirname,'..'),world=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'))),species=JSON.parse(fs.readFileSync(path.join(root,'world/fish.txt')));
const w=new TestWorld(),bot='CoastAngler';w.startLevel=99;
const fixtureSource=fs.readFileSync(path.join(__dirname,'fishing-client.cjs'),'utf8').split('const f=fixture(),')[0];
const client=new Function('require','__dirname',fixtureSource+'\nreturn fixture;')(require,__dirname)();
const cell=(rows,x,y)=>x>=0&&y>=0?rows?.[Math.floor(y)]?.[Math.floor(x)]:undefined;
function witness(area) {
 const candidates=[];
 for(let y=1;y<area.shapeFloor.length-1;y++)for(let x=1;x<area.shapeFloor[y].length-1;x++) {
  if(cell(area.shapeFloor,x,y)===' ')continue;
  const p={x:x+.5,y:y+.5};if(area.dock&&p.x>=area.dock.x0&&p.x<=area.dock.x1&&p.y>=area.dock.y0&&p.y<=area.dock.y1)continue;
  for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
   if(cell(area.shapeEdge,p.x+dx,p.y+dy)!=='c'||cell(area.shapeFloor,p.x+dx,p.y+dy)!==' ')continue;
   if(![3,4,5,6].every(d=>cell(area.shapeEdge,p.x+dx*d,p.y+dy*d)==='c'&&cell(area.shapeFloor,p.x+dx*d,p.y+dy*d)===' '))continue;
   if(area.objects.some(o=>o.width>0&&o.depth>0?Math.abs(p.x-o.x)<o.width/2+.31&&Math.abs(p.y-o.y)<o.depth/2+.31:Math.hypot(p.x-o.x,p.y-o.y)<(o.r||0)+.31))continue;
   if(area.objects.some(o=>[.125,.25,.375].some(d=>{const q={x:p.x+dx*d,y:p.y+dy*d};return o.width>0&&o.depth>0?Math.abs(q.x-o.x)<o.width/2&&Math.abs(q.y-o.y)<o.depth/2:Math.hypot(q.x-o.x,q.y-o.y)<(o.r||0);})))continue;
   const clearance=Math.min(...area.slimes.filter(s=>!s.sleeping).map(s=>Math.hypot(p.x-s.x,p.y-s.y)));candidates.push({...p,dx,dy,clearance});
  }
 }
 return candidates.sort((a,b)=>b.clearance-a.clearance)[0];
}
(async()=>{
 await w.start();await w.connect({bot,class:'warrior'});await w.debug(bot,{op:'give_item',item:'rod_worldwire_rod',quantity:1});
 for(const zone of [0]) {
  const area=zone===0?world:world.zones[zone-1],p=witness(area);assert(p,'safe coastal shore witness');
  await w.debug(bot,{op:'teleport',zone,x:p.x,y:p.y});await w.action(bot,{type:'input',dx:p.dx,dy:p.dy});
  await w.waitFor(()=>Math.hypot(w.player(bot).fx-p.dx,w.player(bot).fy-p.dy)<.01);await w.action(bot,{type:'stop'});
  await w.debug(bot,{op:'teleport',zone,x:p.x,y:p.y});
  assert(client.ctx.Fishing.shore(w.player(bot),area),'actual coast enables the client casting hint');
  const before={...w.player(bot)},start=w.events.length;await w.action(bot,{type:'fish'});await w.waitFor(()=>w.player(bot).fishing,5000,'coastline cast');
  const line=w.player(bot).fishing;
  assert.equal(line.lava,false);assert.equal(cell(area.shapeEdge,line.x,line.y),'c');assert.equal(cell(area.shapeFloor,line.x,line.y),' ');
  assert(Math.hypot(w.player(bot).x-before.x,w.player(bot).y-before.y)<.01);
  console.log('Real coastal cast:',JSON.stringify({zone,shore:p,bobber:line}));
  if(zone===0){
   await w.waitFor(()=>w.player(bot).fishing?.state==='bite',15000);await w.action(bot,{type:'fish'});
   const caught=await w.waitFor(()=>w.events.slice(start).find(e=>e.kind==='fish_catch'));
   await w.waitFor(()=>w.player(bot).inventory.some(s=>s.item===caught.item&&s.quantity>=caught.quantity));
   const fish=species.find(s=>s.item===caught.item);if(fish)assert.equal(fish.habitat,'Shore');
   await w.disconnect(bot);await w.connect({bot,class:'warrior'});assert(w.player(bot).inventory.some(s=>s.item===caught.item&&s.quantity>=caught.quantity));
   console.log('Sea catch and reconnect persistence:',caught.item);
  }
 }
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>w.stop());
