process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const{chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 w.startLevel=99;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});const p=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 if(process.env.MUTATE==='eggs')await p.route('**/easter.js',r=>r.fulfill({contentType:'application/javascript',body:fs.readFileSync(path.join(__dirname,'../client/easter.js'),'utf8').replace('drawNpc(g,n,t,top,talk=false){','drawNpc(g,n,t,top,talk=false){return;')}));
 await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:true,lowGraphicsSet:true,touchGraphicsSuggested:true}));});
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-mage').click();await p.locator('#gender-female').click();await p.locator('#name').fill('FestiveArt');await p.locator('#go').click({timeout:60000});await p.waitForFunction(()=>Online.connected&&Field.hero.hp>0,null,{timeout:60000});
 const list=process.env.MUTATE?[['easter',1806015600,'Easter']]:[['solstice',1813183200,'Solstice'],['valentine',1802214000,'Valentines'],['easter',1806015600,'Easter']];
 for(const[season,unix,module]of list){
  await p.evaluate(unix=>Online.send({type:'debug',command:{op:'season_time',unix}}),unix);await p.waitForFunction(id=>Seasonal.isActive(id),season);
  for(const[z,name]of[[0,'alderhaven'],[4,'skaldholm'],[9,'nacrehold'],[17,'asterion']]){
   const centre=await p.evaluate(([z,id])=>[WORLD_MAP,...WORLD_MAP.zones][z].npcs.find(n=>n.id===`festival_dance_${id}_${z}`),[z,season]);
   await p.evaluate(([z,x,y])=>{City.close();Field.clearInput();Online.send({type:'stop'});Online.send({type:'debug',command:{op:'teleport',zone:z,x,y}});Online.send({type:'debug',command:{op:'set_time',hour:12,freeze:true}});},[z,centre.x+1.8,centre.y]);
   await p.waitForFunction(z=>Field.zone===z,z);await p.waitForFunction(()=>NpcArt.readyFor(City.npcs),null,{timeout:30000});await p.waitForTimeout(300);await p.evaluate(()=>ZoneJourney.clear());
   const fit=await p.evaluate(module=>{
    const api=window[module],area=[WORLD_MAP,...WORLD_MAP.zones][Field.zone],people=City.npcs.filter(n=>NpcArt.manifest.npcs[n.id]&&!n.travelStop&&!['stone','scenery'].includes(n.art)&&!n.id.includes('meetingstone')&&n.x>=area.city.x0&&n.x<=area.city.x1&&n.y>=area.city.y0&&n.y<=area.city.y1);
    const c=document.createElement('canvas'),o=document.createElement('canvas');c.width=o.width=80;c.height=o.height=56;const g=c.getContext('2d',{willReadFrequently:true}),h=o.getContext('2d',{willReadFrequently:true});let frames=0;const bad=[];
    const sheet=document.createElement('canvas');sheet.width=8*180;sheet.height=Math.ceil(people.length/8)*220;const gg=sheet.getContext('2d');gg.fillStyle='#254038';gg.fillRect(0,0,sheet.width,sheet.height);
    for(const[index,n0]of people.entries()){
     for(const clip of ['idle','walk','talk'])for(const mirrored of [false,true])for(const step of [0,NpcArt.manifest.clips[clip].n-1]){
      const n={...n0,moving:clip==='walk',fx:mirrored?0:1,fy:mirrored?1:0},spec=NpcArt.manifest.clips[clip],phase=[...n.id].reduce((a,ch)=>a+ch.charCodeAt(0),0),t=(step-phase+spec.n*200)/spec.fps,socket=api.head(n,t,clip==='talk');
      g.clearRect(0,0,80,56);h.clearRect(0,0,80,56);for(const ctx of[g,h]){ctx.save();ctx.translate(40-socket.x,28-socket.y);}g.save();g.scale(n.look?.scale||1,n.look?.scale||1);NpcArt.draw(g,n,t,clip==='talk');g.restore();api.drawNpc(h,n,t,NpcArt.top(n),clip==='talk');g.restore();h.restore();const a=g.getImageData(0,0,80,56).data,b=h.getImageData(0,0,80,56).data;let overlap=0,headpaint=0,floating=0;
      for(let y=0;y<44;y++)for(let x=10;x<70;x++){const i=(y*80+x)*4+3;if(b[i]>100){if(y<12)floating++;if(y>=20&&y<39){headpaint++;if(a[i]>100)overlap++;}}}frames++;if(overlap<3||headpaint<10||floating)bad.push({id:n.id,clip,step,mirrored,overlap,headpaint,floating});
     }
     const x=(index%8)*180+90,y=Math.floor(index/8)*220+175;gg.save();gg.translate(x,y);gg.save();gg.scale(n0.look?.scale||1,n0.look?.scale||1);NpcArt.draw(gg,n0,0);gg.restore();api.drawNpc(gg,n0,0,NpcArt.top(n0));gg.restore();gg.font='11px sans-serif';gg.textAlign='center';gg.fillStyle='#fff0ce';gg.fillText(n0.name,x,y+22,172);
    }
    return{people:people.length,frames,bad,sheet:sheet.toDataURL()};
   },module);
   check(fit.people>0&&fit.bad.length===0,`${season}/${name}: accessories touch real hair/head pixels without floating across ${fit.frames} poses: ${JSON.stringify(fit.bad.slice(0,3))}`);
   fs.writeFileSync(path.join(w.runDir,`festival-${season}-${name}-npc-hair.png`),Buffer.from(fit.sheet.split(',')[1],'base64'));
   for(const[hour,suffix]of[[12,'day'],[22,'night']]){await p.evaluate(hour=>Online.send({type:'debug',command:{op:'set_time',hour,freeze:true}}),hour);await p.waitForFunction(h=>Math.abs(DayNight.hour-h)<.1,hour);const png=await p.evaluate(()=>{Field._debug.drawFrame(3);return document.querySelector('#fieldcv').toDataURL();});fs.writeFileSync(path.join(w.runDir,`festival-${season}-${name}-${suffix}.png`),Buffer.from(png.split(',')[1],'base64'));}
   check(await p.evaluate(()=>Festival.objects(Field.zone).length===1&&Seasonal.decor(Field.zone).length>10),`${season}/${name}: city remains decorated at night and has exactly one dance centerpiece`);
   await p.setViewportSize({width:844,height:390});const phone=await p.evaluate(()=>{Field._debug.drawFrame(3);return document.querySelector('#fieldcv').toDataURL();});fs.writeFileSync(path.join(w.runDir,`festival-${season}-${name}-phone.png`),Buffer.from(phone.split(',')[1],'base64'));await p.setViewportSize({width:1280,height:800});
  }
 }
 check(errors.length===0,'No art browser errors: '+errors.join('; '));console.log(`festival-art-ui: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
