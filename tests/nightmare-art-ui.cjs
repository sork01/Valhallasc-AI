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
  await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:true,lowGraphicsSet:true}));});
  await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-'+cls).click();await p.locator('#gender-'+gender).click();await p.locator('#name').fill('Night'+cls.slice(0,3)+gender[0]);await p.locator('#go').click({timeout:60000});
  await p.waitForFunction(()=>Online.connected&&Field.hero.hp>0,null,{timeout:60000});
  await p.evaluate(()=>Online.send({type:'debug',command:{op:'give_mount',mount:'nightmare'}}));await p.waitForFunction(()=>Field.hero.mounts.includes('nightmare'));
  await p.evaluate(()=>{Online.send({type:'select_mount',mount:'nightmare'});MountArt.preload('nightmare');});await p.waitForFunction(()=>MountArt.ready('nightmare'),null,{timeout:20000});
  const result=await p.evaluate(async({cls,gender})=>{
   const Base={warrior:WarriorSprite,mage:MageSprite,assassin:AssassinSprite,priest:PriestSprite,hunter:HunterSprite}[cls];
   const look={...Field.hero.look,class:cls,gender};const spr=await Base.variant(look).load(look),m=MountArt.meta('nightmare');
   const sheet=document.createElement('canvas');sheet.width=8*200;sheet.height=3*250;const g=sheet.getContext('2d');g.fillStyle='#2c2437';g.fillRect(0,0,sheet.width,sheet.height);
   const hashes=[],preserved=[],facings=[];
   for(let d=0;d<8;d++){
    const angle=-d*Math.PI/4,fx=(Math.cos(angle)+Math.sin(angle))/2,fy=(Math.cos(angle)-Math.sin(angle))/2;facings.push(spr.constructor.direction(fx,fy));
    for(let row=0;row<3;row++){
     const h={mounted:row!==2,mount:'nightmare',mountTint:0,moving:row===1,walk:3,fx,fy,x:0,y:0};
     g.save();g.translate(d*200+100,row*250+185);spr.draw(g,h,1.1,1.3);g.restore();
     const pixels=g.getImageData(d*200,row*250,200,250).data;let hash=7;for(let i=0;i<pixels.length;i++)hash=(Math.imul(hash,31)+pixels[i]+i)>>>0;hashes.push({row,d,hash});
    }
    for(const [clip,i]of[['idle',1],['run',3]]){
     const rider=spr.frame('idle',d,0),out=MountArt.compose(rider,'nightmare',clip,d,i,0),pixels=out.getContext('2d').getImageData(0,0,160,224).data;
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
  check(result.hashes.filter(h=>h.row===0).every(h=>h.hash!==result.hashes.find(b=>b.row===2&&b.d===h.d).hash),`${cls}/${gender}: the Nightmare Steed is visible under the production rider`);
  fs.writeFileSync(path.join(w.runDir,`nightmare-${cls}-${gender}.png`),Buffer.from(result.sheet.split(',')[1],'base64'));
  if(cls==='warrior'&&gender==='male'){
   const elite=await p.evaluate(async()=>{await Halloween.load();const{meta,img}=Halloween.source,im=img.hollow_rider,c=document.createElement('canvas');c.width=768;c.height=480;const g=c.getContext('2d');g.drawImage(im,0,0);let orange=0,opaque=0,edge=0;const data=g.getImageData(0,0,c.width,c.height).data;for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){const i=(y*c.width+x)*4;if(!data[i+3])continue;opaque++;if(data[i]>180&&data[i+1]>70&&data[i+1]<220&&data[i+2]<100)orange++;if(x%96===0||x%96===95||y%96===0||y%96===95)edge++;}return{orange,opaque,edge,clips:Object.keys(meta.clips)};});
   check(elite.orange>150&&elite.opaque>1000&&elite.edge===0&&elite.clips.length===5,'The saved Halloween elite atlas has all five clips, visible pumpkin/flames and no clipped frame edges');
  }
  await p.close();
 }
 check(errors.length===0,'No real-art browser errors: '+errors.join('; '));console.log(`nightmare-art-ui: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
