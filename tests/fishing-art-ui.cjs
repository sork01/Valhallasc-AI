// Production inventory/NPC renderers and actual MP3 decoding in a private game.
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const {chromium}=require('./lib/playwright.cjs');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const root=path.resolve(__dirname,'..'),w=new TestWorld();let browser;
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p)));
const meta=read('client/assets/fishing-icons.txt'),map=read('world/map.txt');
const fishers=[map,...map.zones].flatMap(z=>z.npcs||[]).filter(n=>n.id.startsWith('fisher_'));
(async()=>{
 await w.start();browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const page=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
 if(process.env.MUTATE==='icons')await page.route('**/inventory.js',r=>r.fulfill({contentType:'application/javascript',body:execFileSync('git',['show','a1764688:client/inventory.js'],{cwd:root,encoding:'utf8'})}));
 if(process.env.MUTATE==='npc')await page.route('**/assets/npcp.txt',r=>{const m=read('client/assets/npcp.txt');delete m.sprites.fisher_rod;return r.fulfill({contentType:'application/json',body:JSON.stringify(m)});});
 if(process.env.MUTATE==='sound')await page.route('**/assets/sfx_fish_plop.mp3',r=>r.fulfill({contentType:'audio/mpeg',body:Buffer.from('broken')}));
 await page.goto(w.url);await page.evaluate(()=>NpcArt.ready);
 const result=await page.evaluate(meta=>{
   const rows=[];
   for(const [id,cell] of Object.entries(meta.at)){
     const item=WORLD_ITEMS.find(i=>i.id===id),host=document.createElement('div');host.innerHTML=Inventory.icon(item);
     const icon=host.querySelector('.item-art');
     rows.push({id,icon:!!icon,background:icon?.style.backgroundImage,position:icon?.style.backgroundPosition,expected:`${cell[0]/(meta.cols-1)*100}% ${cell[1]/(meta.rows-1)*100}%`});
   }
   return rows;
 },meta);
 for(const row of result){assert(row.icon,`${row.id}: uses pixel artwork`);assert(row.background.includes('fishing-icons.png'));const actual=row.position.split(' ').map(parseFloat),expected=row.expected.split(' ').map(parseFloat);assert(actual.every((v,i)=>Math.abs(v-expected[i])<.001),row.id);}
 for(const n of fishers)assert.equal(await page.evaluate(n=>NpcArt.styleOf(n),n),'player',`${n.id}: new Fisher source selected`);
 await page.waitForFunction(f=>NpcArt.readyFor(f),fishers);
 const poses=await page.evaluate(fishers=>{
   const canvas=document.createElement('canvas');canvas.width=256;canvas.height=256;const g=canvas.getContext('2d',{willReadFrequently:true});
   return fishers.map(n=>{
     const out=[];n={...n,fx:1,fy:0};
     const phase=[...n.id].reduce((s,c)=>s+c.charCodeAt(0),0);
     for(const [row,count,fps] of [['idle',6,6],['walk',8,10],['talk',6,6]])for(let k=0;k<count;k++){
       n.moving=row==='walk';const t=(k+.05-phase)/fps;
       g.clearRect(0,0,256,256);g.save();g.translate(128,210);const drawn=NpcArt.draw(g,n,t,row==='talk');g.restore();
       const pixels=g.getImageData(0,0,256,256).data;let opaque=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i])opaque++;
       out.push({drawn,opaque,frame:NpcArt.frame(n,t,row==='talk'),head:NpcArt.head(n,t,row==='talk')});
     }
     return {id:n.id,style:NpcArt.styleOf(n),poses:out};
   });
 },fishers);
 for(const n of poses){assert.equal(n.style,'player');for(const p of n.poses){assert(p.drawn&&p.opaque>500,n.id);assert.equal(p.frame.art,'fisher_rod');assert(p.head&&Number.isFinite(p.head.y),n.id);}}
 const cues=read('client/assets/fishing-sounds.txt');
 const decoded=await page.evaluate(async cues=>{
   const ctx=new AudioContext();const results=[];
   for(const [name,entry] of Object.entries(cues.clips)){
     const response=await fetch('assets/'+entry.file);if(!response.ok)throw Error(entry.file);
     const b=await ctx.decodeAudioData(await response.arrayBuffer());let peak=0;
     for(const sample of b.getChannelData(0))peak=Math.max(peak,Math.abs(sample));
     results.push({name,seconds:b.duration,channels:b.numberOfChannels,peak});
   }
   await ctx.close();return results;
 },cues);
 for(const cue of decoded){assert.equal(cue.channels,1);assert(cue.seconds>.2&&cue.seconds<2.2);assert(cue.peak>.05&&cue.peak<1);}
 // Actual bag and Fisher scene, using the new shared inventory renderer.
 await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('FishArtReview');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&!!Field.hero,null,{timeout:60000});
 const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:Math.floor(Math.random()*1e9),command}),command);
 const sample=['fish_pier_sprat','fish_glass_eel','fish_jade_dragonfish','fish_sunfire_ray','rod_twig_rod','rod_magma_reel','fishing_sunken_coffer','fishing_message_bottle','fishing_rod_charm','dish_shore_grill','dish_jungle_feast','dish_lava_feast'];
 for(const item of sample)await debug({op:'give_item',item,quantity:1});
 await page.waitForFunction(ids=>ids.every(id=>Inventory.bagQuantity(id)>=1),sample);
 const fisher=fishers.find(n=>n.id==='fisher_meadow_0');await debug({op:'teleport',zone:0,x:fisher.x,y:fisher.y});
 await page.waitForFunction(n=>Math.hypot(Field.hero.x-n.x,Field.hero.y-n.y)<1,fisher);
 await page.locator('#inventory-open').click();
 for(const id of sample)assert(await page.locator(`#inventory-list [data-icon="${id}"]`).count(),`${id}: visible bag pixel icon`);
 await page.screenshot({path:path.join(w.runDir,'fishing-bags.png')});
 await page.locator('#bags-close').click();
 await page.evaluate(()=>Online.send({type:'interact',npc:'fisher_meadow_0'}));await page.locator('[data-view="fisher"]').waitFor();await page.locator('[data-view="fisher"]').click();
 await page.screenshot({path:path.join(w.runDir,'fishing-workshop-art.png')});
 await page.locator('#npc-x').click();await page.screenshot({path:path.join(w.runDir,'fishing-scene-art.png')});
 assert.deepEqual(errors,[]);console.log('PASS: 91 production item icons, 260 Fisher poses, seven browser-decoded cues, actual bags/workshop/scene');console.log('Screenshots:',w.runDir);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await w.stop();});
