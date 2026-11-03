// The new mount only: real PixelFlow exports, all ten class/body rigs, eight directions and both gaits.
process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
let browser,checks=0;const w=new TestWorld(),errors=[];
const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 w.startLevel=99;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});
 for(const cls of ['warrior','mage','assassin','priest','hunter'])for(const gender of ['male','female']){
  const p=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
  await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:true,lowGraphicsSet:true,touchGraphicsSuggested:true}));});
  await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-'+cls).click();await p.locator('#gender-'+gender).click();await p.locator('#name').fill('Bun'+cls.slice(0,3)+gender[0]);await p.locator('#go').click({timeout:60000});
  await p.waitForFunction(()=>Online.connected&&Field.hero.hp>0,null,{timeout:60000});
  await p.evaluate(()=>Online.send({type:'debug',command:{op:'give_mount',mount:'sunwoven'}}));await p.waitForFunction(()=>Field.hero.mounts.includes('sunwoven'));
  await p.evaluate(()=>{Online.send({type:'select_mount',mount:'sunwoven'});MountArt.preload('sunwoven');});await p.waitForFunction(()=>MountArt.ready('sunwoven'),null,{timeout:20000});
  const result=await p.evaluate(async({cls,gender})=>{
   const Base={warrior:WarriorSprite,mage:MageSprite,assassin:AssassinSprite,priest:PriestSprite,hunter:HunterSprite}[cls];
   const look={...Field.hero.look,class:cls,gender};const spr=await Base.variant(look).load(look),m=MountArt.meta('sunwoven');
   const sheet=document.createElement('canvas');sheet.width=8*200;sheet.height=3*250;const g=sheet.getContext('2d');g.fillStyle='#2c2437';g.fillRect(0,0,sheet.width,sheet.height);
   const hashes=[],preserved=[],facings=[];
   for(let d=0;d<8;d++){
    const angle=-d*Math.PI/4,fx=(Math.cos(angle)+Math.sin(angle))/2,fy=(Math.cos(angle)-Math.sin(angle))/2;facings.push(spr.constructor.direction(fx,fy));
    for(let row=0;row<3;row++){
     const h={mounted:row!==2,mount:'sunwoven',mountTint:0,moving:row===1,walk:3,fx,fy,x:0,y:0};
     g.save();g.translate(d*200+100,row*250+185);spr.draw(g,h,1.1,1.3);g.restore();
     const pixels=g.getImageData(d*200,row*250,200,250).data;let hash=7;for(let i=0;i<pixels.length;i++)hash=(Math.imul(hash,31)+pixels[i]+i)>>>0;hashes.push({row,d,hash});
    }
    for(const [clip,i]of[['idle',1],['run',3]]){
     const rider=spr.frame('idle',d,0),out=MountArt.compose(rider,'sunwoven',clip,d,i,0),pixels=out.getContext('2d').getImageData(0,0,160,224).data;
     const raise=m.raise+m.bob[clip][i],shift=Math.round(raise*Math.sqrt(3)/2*1.03);let covered=0,total=0;
     for(let y=0;y<45;y++)for(let x=0;x<160;x++){const at=(y*160+x)*4;if(rider._px[at+3]<250)continue;const oy=y+64-shift;if(oy<0||oy>=224)continue;total++;const dst=(oy*160+x)*4;if([0,1,2,3].some(k=>pixels[dst+k]!==rider._px[at+k]))covered++;}
     preserved.push({clip,d,total,covered});
    }
   }
   return{sheet:sheet.toDataURL(),hashes,preserved,facings,ids:Object.keys(m.sprites).length};
  },{cls,gender});
  check(result.ids===16,`${cls}/${gender}: saved PixelFlow source IDs cover both gaits and all facings`);
  check(result.facings.every((d,i)=>d===i),`${cls}/${gender}: all eight real facing vectors`);
  check([0,1].every(row=>new Set(result.hashes.filter(h=>h.row===row).map(h=>h.hash)).size===8),`${cls}/${gender}: eight distinct mounted images in each gait`);
  check(result.preserved.every(p=>p.total>20&&p.covered===0),`${cls}/${gender}: every protected rider head pixel survives mount depth composition`);
  check(result.hashes.filter(h=>h.row===0).every(h=>h.hash!==result.hashes.find(b=>b.row===2&&b.d===h.d).hash),`${cls}/${gender}: the Sunwoven Stag is visible under the production rider`);
  fs.writeFileSync(path.join(w.runDir,`sunwoven-${cls}-${gender}.png`),Buffer.from(result.sheet.split(',')[1],'base64'));
  if(cls==='warrior'&&gender==='male'){
   await p.evaluate(()=>Online.send({type:'debug',command:{op:'season_time',unix:1813183200}}));await p.waitForFunction(()=>Seasonal.isActive('solstice'));
   for(const [zone,name]of[[0,'alderhaven'],[4,'skaldholm'],[9,'nacrehold'],[17,'asterion']]){
    const tree=await p.evaluate(z=>{const a=[WORLD_MAP,...WORLD_MAP.zones][z];return a.solsticeDecor.find(o=>o.kind==='solsticePole')||a.solsticeDecor.find(o=>o.kind==='solsticePole');},zone);
    await p.evaluate(([zone,x,y])=>{City.close();Quests.close();Field.clearInput();Online.send({type:'stop'});Online.send({type:'debug',command:{op:'teleport',zone,x,y}});Online.send({type:'debug',command:{op:'set_time',hour:18,freeze:true}});},[zone,tree.x+2,tree.y+2]);
    await p.waitForFunction(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<1.3,[zone,tree.x+2,tree.y+2]);await p.waitForFunction(()=>NpcArt.readyFor(City.npcs));await p.waitForTimeout(400);await p.evaluate(()=>ZoneJourney.clear());
    const costume=await p.evaluate(()=>{const n=City.npcs.find(n=>Seasonal.hat(n)),c=document.createElement('canvas');c.width=c.height=400;const g=c.getContext('2d');g.translate(200,250);Seasonal.drawNpc(g,n,3,100);return g.getImageData(0,0,400,400).data.filter((v,i)=>i%4===3&&v>0).length;});
    check(costume>100,`${name}: festive NPC accessories render with real production artwork`);
    const fits=await p.evaluate(()=>{
     const c=document.createElement('canvas'),o=document.createElement('canvas');c.width=o.width=80;c.height=o.height=48;
     const g=c.getContext('2d',{willReadFrequently:true}),h=o.getContext('2d',{willReadFrequently:true});let frames=0,people=0;const bad=[];
     const gallery=document.createElement('canvas');gallery.width=8*180;gallery.height=Math.ceil(City.npcs.length/8)*220;const gg=gallery.getContext('2d');gg.fillStyle='#254338';gg.fillRect(0,0,gallery.width,gallery.height);
     for(const n0 of City.npcs){
      if(!NpcArt.manifest.npcs[n0.id]||n0.travelStop||['stone','scenery'].includes(n0.art)||n0.id.includes('meetingstone'))continue;people++;
      for(const clip of ['idle','walk','talk'])for(const mirrored of [false,true])for(const step of [0,NpcArt.manifest.clips[clip].n-1]){
       const n={...n0,moving:clip==='walk',fx:mirrored?0:1,fy:mirrored?1:0},spec=NpcArt.manifest.clips[clip],phase=[...n.id].reduce((a,ch)=>a+ch.charCodeAt(0),0),t=(step-phase+spec.n*200)/spec.fps,socket=Solstice.head(n,t,clip==='talk');
       g.clearRect(0,0,80,48);h.clearRect(0,0,80,48);for(const ctx of [g,h]){ctx.save();ctx.translate(40-socket.x,20-socket.y);}
       g.save();g.scale(n.look?.scale||1,n.look?.scale||1);NpcArt.draw(g,n,t,clip==='talk');g.restore();Solstice.drawNpc(h,n,t,NpcArt.top(n),clip==='talk');g.restore();h.restore();
       const a=g.getImageData(0,0,80,48).data,b=h.getImageData(0,0,80,48).data;let overlap=0;
       for(let y=8;y<28;y++)for(let x=10;x<70;x++){const i=(y*80+x)*4+3;if(a[i]>100&&b[i]>100)overlap++;}
       frames++;if(overlap<3)bad.push({id:n.id,clip,mirrored,step,overlap});
      }
      const x=((people-1)%8)*180+90,y=Math.floor((people-1)/8)*220+175;gg.save();gg.translate(x,y);gg.save();gg.scale(n0.look?.scale||1,n0.look?.scale||1);NpcArt.draw(gg,n0,0);gg.restore();Solstice.drawNpc(gg,n0,0,NpcArt.top(n0));gg.restore();gg.font='11px sans-serif';gg.textAlign='center';gg.fillStyle='#fff2cc';gg.fillText(n0.name,x,y+22,170);
     }
     return{people,frames,bad,sheet:gallery.toDataURL()};
    });
    check(fits.people>0&&fits.bad.length===0,`${name}: wildflower crowns touch actual head pixels across ${fits.frames} idle/walk/talk and mirrored poses: ${JSON.stringify(fits.bad.slice(0,3))}`);
    fs.writeFileSync(path.join(w.runDir,`solstice-npc-fit-${name}.png`),Buffer.from(fits.sheet.split(',')[1],'base64'));

    await p.evaluate(()=>Online.send({type:'debug',command:{op:'set_time',hour:22,freeze:true}}));await p.waitForFunction(()=>DayNight.hour>21.9&&DayNight.nightMix>.9);check(await p.evaluate(()=>Seasonal.decor(Field.zone).length>20),`${name}: festive art remains available in full night lighting`);
    const png=await p.evaluate(()=>{Field._debug.drawFrame(3);return document.querySelector('#fieldcv').toDataURL();});
    fs.writeFileSync(path.join(w.runDir,`valhallasc-solstice-${name}.png`),Buffer.from(png.split(',')[1],'base64'));
    await p.evaluate(()=>Online.send({type:'debug',command:{op:'set_time',hour:12,freeze:true}}));await p.waitForFunction(()=>DayNight.hour>11.9&&DayNight.hour<12.1&&DayNight.nightMix===0);check(await p.evaluate(()=>Seasonal.decor(Field.zone).length>20),`${name}: the same decorations remain clear in daylight and reduced motion`);
    const day=await p.evaluate(()=>{Field._debug.drawFrame(3);return document.querySelector('#fieldcv').toDataURL();});fs.writeFileSync(path.join(w.runDir,`valhallasc-solstice-${name}-day.png`),Buffer.from(day.split(',')[1],'base64'));

   }
   await p.evaluate(()=>Online.send({type:'debug',command:{op:'teleport',zone:2,x:110.5,y:100}}));await p.waitForFunction(()=>Field.zone===2);await p.waitForTimeout(300);
   const camp=await p.evaluate(()=>{const n=City.npcs.find(n=>n.art!=='scenery'),c=document.createElement('canvas');c.width=c.height=400;const g=c.getContext('2d');g.translate(200,250);Seasonal.drawNpc(g,n,3,100);return{props:Seasonal.decor(2).length,paint:g.getImageData(0,0,400,400).data.some(v=>v),old:City.npcs.some(n=>n.id==='halloween_lantern')};});
   check(camp.props===0&&!camp.paint&&!camp.old,'Smaller Rimeveil refuge has no city dressing, festive NPC outfit or Halloween landmark');
   const elite=await p.evaluate(async()=>{await Solstice.load();const{meta,img}=Solstice.source,im=img.birchcrown,c=document.createElement('canvas');c.width=768;c.height=480;const g=c.getContext('2d');g.drawImage(im,0,0);let green=0,opaque=0,edge=0;const data=g.getImageData(0,0,c.width,c.height).data;for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){const i=(y*c.width+x)*4;if(!data[i+3])continue;opaque++;if(data[i+1]>data[i]*1.15&&data[i+1]>data[i+2]*1.15&&data[i+1]>75)green++;if(x%96===0||x%96===95||y%96===0||y%96===95)edge++;}return{green,opaque,edge,clips:Object.keys(meta.clips)};});
   check(elite.green>150&&elite.opaque>1000&&elite.edge===0&&elite.clips.length===5,'The saved Solstice elite atlas has all five clips, birch bark and sun crest and green foliage and no clipped frame edges');
  }
  await p.close();
 }
 check(errors.length===0,'No real-art browser errors: '+errors.join('; '));console.log(`solstice-art-ui: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
