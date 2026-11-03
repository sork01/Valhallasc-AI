// Private native-client previews for the owner's requested FileDrop review.
process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser;
(async()=>{try{
 w.startLevel=99;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});
 const p=await browser.newPage({viewport:{width:1440,height:960},reducedMotion:'reduce'});
 await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:true,lowGraphicsSet:true}));});
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('Newyear Preview');await p.locator('#go').click({timeout:60000});await p.waitForFunction(()=>Online.connected&&Field.hero.hp>0,null,{timeout:60000});
 const save=async(name,data)=>fs.writeFileSync(path.join(w.runDir,name),Buffer.from(data.split(',')[1],'base64'));
 const elite=await p.evaluate(async()=>{await NewYear.load();const {meta,img}=NewYear.source,c=document.createElement('canvas');c.width=1100;c.height=490;const g=c.getContext('2d');const bg=g.createLinearGradient(0,0,0,490);bg.addColorStop(0,'#34324f');bg.addColorStop(1,'#181e33');g.fillStyle=bg;g.fillRect(0,0,1100,490);g.fillStyle='#ffe1a0';g.font='30px sans-serif';g.textAlign='center';g.fillText('New Year · The Starfire Rocketeer',550,53);g.imageSmoothingEnabled=false;for(const [i,[clip,k]]of[['idle',0],['walk',3],['attack',4]].entries()){const x=40+i*355,row=meta.clips[clip].row;g.drawImage(img.starrocketeer,k*96,row*96,96,96,x,90,288,288);g.font='18px sans-serif';g.fillStyle='#c8c9e0';g.fillText(clip,x+144,425);}return c.toDataURL();});await save('valhallasc-newyear-rocketeer.png',elite);
 const rocket=await p.evaluate(async()=>{MountArt.preload('rocket');for(let i=0;i<200&&!MountArt.ready('rocket');i++)await new Promise(r=>setTimeout(r,50));const m=MountArt.meta('rocket'),im=new Image();im.src='assets/'+m.png;await im.decode();const c=document.createElement('canvas');c.width=1280;c.height=760;const g=c.getContext('2d');g.fillStyle='#252d43';g.fillRect(0,0,1280,760);g.fillStyle='#ffe1a0';g.textAlign='center';g.font='30px sans-serif';g.fillText('New Year · Starflight Rocket',640,50);g.imageSmoothingEnabled=false;for(let d=0;d<8;d++){const x=(d%4)*320+40,y=Math.floor(d/4)*320+80;g.drawImage(im,0,d*160,160,160,x,y,240,240);g.font='17px sans-serif';g.fillStyle='#ced3ea';g.fillText(['S','SW','W','NW','N','NE','E','SE'][d],x+120,y+260);}return c.toDataURL();});await save('valhallasc-newyear-rocket-art.png',rocket);
 await p.evaluate(()=>{Online.send({type:'debug',command:{op:'season_time',unix:1798498800}});Online.send({type:'debug',command:{op:'teleport',zone:0,x:36,y:75}});});await p.waitForFunction(()=>Seasonal.isActive('newyear')&&Field.zone===0&&Math.abs(Field.hero.ny-75)<3);
 const interact=async(offer)=>{await p.waitForTimeout(700);await p.evaluate(offer=>Online.send({type:'interact',npc:'baker',offer}),offer);};
 const n=await p.evaluate(()=>WORLD_MAP.npcs.find(n=>n.id==='baker'));await p.evaluate(n=>Online.send({type:'debug',command:{op:'teleport',zone:0,x:n.x,y:n.y}}),n);await p.waitForTimeout(400);
 await interact('quest:accept:newyear_hunt');await p.evaluate(()=>Online.send({type:'debug',command:{op:'quest',id:'newyear_hunt',action:'complete'}}));await p.waitForTimeout(300);await interact('quest:claim:newyear_hunt');await p.waitForTimeout(400);
 await p.evaluate(()=>Achievements.open());await p.locator('[data-achievement="newyear"][data-complete="true"]').waitFor();
 await p.locator('#achievement-categories [data-category="Quests"]').click();await p.locator('[data-achievement="newyear"]').scrollIntoViewIfNeeded();
 if(await p.locator('#low-gfx-dismiss').isVisible())await p.locator('#low-gfx-dismiss').click();
 await p.screenshot({path:path.join(w.runDir,'valhallasc-newyear-achievement.png')});
 console.log('New Year native previews: '+w.runDir);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
