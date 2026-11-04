process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const source=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../scripts/meadow_slime_sources.txt'))).beetle;
const{chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 w.startLevel=20;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});const p=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 // Mutation control: serve an atlas whose every pixel is moved up one row (grounding and the eight-frame checks must fail).
 if(process.env.MUTATE_PNG)await p.route('**/assets/ironhide.png',r=>r.fulfill({path:process.env.MUTATE_PNG,contentType:'image/png'}));
 await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:true,lowGraphicsSet:true,touchGraphicsSuggested:true}));});
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('BeetleArt');await p.locator('#go').click({timeout:60000});await p.waitForFunction(()=>Online.connected&&Field.beetleSprites,null,{timeout:30000});
 const result=await p.evaluate(async()=>{
  const src=Field.beetleSprites,{meta,img}=src,im=img.beetle,[FW,FH]=meta.frame,c=document.createElement('canvas');c.width=im.width;c.height=im.height;const g=c.getContext('2d',{willReadFrequently:true});g.drawImage(im,0,0);const rows=[];
  const gallery=document.createElement('canvas');gallery.width=8*FW*2;gallery.height=5*(FH*2+24);const gg=gallery.getContext('2d');gg.imageSmoothingEnabled=false;gg.fillStyle='#315441';gg.fillRect(0,0,gallery.width,gallery.height);
  for(const[clip,spec]of Object.entries(meta.clips))for(let k=0;k<spec.n;k++){
   const p=g.getImageData(k*FW,spec.row*FH,FW,FH).data;let opaque=0,edge=0,white=0,steel=0,hash=7,minY=FH,maxY=-1,minX=FW,maxX=-1;
   for(let y=0;y<FH;y++)for(let x=0;x<FW;x++){const i=(y*FW+x)*4;hash=(Math.imul(hash,31)+p[i]+p[i+1]*3+p[i+2]*7+p[i+3])>>>0;if(!p[i+3])continue;opaque++;minY=Math.min(minY,y);maxY=Math.max(maxY,y);minX=Math.min(minX,x);maxX=Math.max(maxX,x);if(p[i+2]>p[i]&&p[i+2]>=70)steel++;if(x===0||x===FW-1||y===0||y===FH-1)edge++;if(p[i]>220&&p[i+1]>230&&p[i+2]>220)white++;}
   rows.push({clip,k,opaque,edge,white,steel,hash,minY,maxY,minX,maxX});gg.drawImage(im,k*FW,spec.row*FH,FW,FH,k*FW*2,spec.row*(FH*2+24),FW*2,FH*2);gg.font='16px sans-serif';gg.fillStyle='#fff2c8';gg.fillText(`${clip} ${k}`,k*FW*2+5,spec.row*(FH*2+24)+FH*2+16);
  }
  const portrait=document.createElement('canvas');portrait.width=portrait.height=96;const ready=Field.drawTargetPortrait({kind:'beetle'},portrait);
  const bytes=portrait.getContext('2d').getImageData(0,0,96,96).data;
  return{frame:meta.frame,anchor:meta.anchor,size:[im.width,im.height],rows,clips:meta.clips,sprites:meta.sprites,tops:meta.tops,gallery:gallery.toDataURL(),portraitReady:ready,portraitPixels:Array.from(bytes).filter((v,i)=>i%4===3&&v>0).length,portrait:portrait.toDataURL()};
 });
 const [FW,FH]=result.frame,AY=result.anchor[1];
 check(result.frame.join()==='96,70'&&result.anchor.join()==='40,64'&&result.size.join()==='768,350','Declared 96x70 frame, anchor (40,64) and 768x350 atlas');
 check(result.rows.length===34&&result.rows.every(r=>r.opaque>10&&r.edge===0),'All 34 exported editor frames are nonempty and clear of every border');
 check(result.sprites.beetle===source,'The client loads the new saved PixelFlow source');
 const expected={idle:[6,6],walk:[10,8],attack:[12,8],hurt:[10,4],die:[8,8]};
 for(const[clip,[fps,n]]of Object.entries(expected)){const spec=result.clips[clip];check(spec.fps===fps&&spec.n===n&&new Set(result.rows.filter(r=>r.clip===clip).map(r=>r.hash)).size>=Math.min(4,n),`${clip}: timing preserved and frames animate distinctly`);}
 const idle=result.rows.filter(r=>r.clip==='idle'),attack=result.rows.filter(r=>r.clip==='attack'),die=result.rows.filter(r=>r.clip==='die');
 check(new Set(attack.map(r=>r.hash)).size===8,'All eight attack frames are distinct');
 check(new Set(die.map(r=>r.hash)).size===8,'All eight death frames are distinct');
 // QUADRUPED-GROUNDING: planted feet rest exactly on the anchor row in every living frame; nothing sinks below it.
 const living=result.rows.filter(r=>r.clip!=='die');
 check(living.every(r=>r.maxY===AY),`Every living frame rests exactly on the anchor row (${AY}): ${[...new Set(living.map(r=>r.maxY))]}`);
 check(die.every(r=>r.maxY<=AY),'No death frame sinks below the floor row');
 // Attack: wind-up rears the front up, the strike reaches forward of idle, recovery returns to the idle reach.
 const idleTop=Math.min(...idle.map(r=>r.minY)),idleReach=Math.max(...idle.map(r=>r.maxX));
 check(Math.min(...attack.slice(0,4).map(r=>r.minY))<=idleTop-8,'Wind-up: the beetle rears up at least 8 px above its idle height');
 check(Math.max(attack[4].maxX,attack[5].maxX)>=idleReach+6,'Strike: the horn reaches at least 6 px past the idle reach');
 check(Math.abs(attack[7].maxX-idleReach)<=3&&Math.abs(attack[7].minY-idleTop)<=3,'Recovery: the last attack frame is back at the idle silhouette');
 check(result.rows.find(r=>r.clip==='idle'&&r.k===0).white>20,'Large eye whites and glossy shell highlights remain visible');
 // The shell is rigid: its steel pixel count is constant (no squash) across the living frames, within the tilt tolerance.
 const steel0=idle[0].steel;check(living.filter(r=>!(r.clip==='hurt'&&r.k===0)).every(r=>r.steel>=steel0*.88&&r.steel<=steel0*1.12),'Living frames keep a constant steel shell area (rigid, no squash or stretch; the hurt flash frame is a white silhouette)');
 check(die.every(r=>r.steel>=steel0*.8)&&die[7].minY<die[0].minY+20,'Death ends with the intact shell flipped on its back and the legs in the air, not a puddle');
 check(result.tops.beetle===AY-Math.min(...idle.map(r=>r.minY)),'Health-bar top follows the tallest saved idle frame');
 check(result.portraitReady&&result.portraitPixels>200,'Production target portrait uses the new beetle atlas');
 for(const name of ['gallery','portrait'])fs.writeFileSync(path.join(w.runDir,'ironhide-slime-'+name+'.png'),Buffer.from(result[name].split(',')[1],'base64'));
 const beetle=await p.evaluate(()=>WORLD_MAP.slimes.find(s=>s.kind==='beetle'));await p.evaluate(s=>{Online.send({type:'debug',command:{op:'teleport',zone:0,x:s.x+3,y:s.y+2}});Online.send({type:'debug',command:{op:'set_time',hour:12,freeze:true}});},beetle);await p.waitForTimeout(600);
 check(await p.evaluate(()=>Field.slimes.some(s=>s.kind==='beetle'&&s.d.top===Field.beetleSprites.meta.tops.beetle)),'Authoritative Greenmeadow beetle uses the new health-bar height');await p.evaluate(()=>{City.close();ZoneJourney.clear();Field._debug.drawFrame(3);});await p.screenshot({path:path.join(w.runDir,'ironhide-slime-in-game.png')});
 await p.setViewportSize({width:844,height:390});await p.screenshot({path:path.join(w.runDir,'ironhide-slime-phone.png')});fs.writeFileSync(path.join(w.runDir,'meadow-art-checks.json'),JSON.stringify({rows:result.rows,source,tops:result.tops},null,2));check(errors.length===0,'No real-art browser errors: '+errors.join('; '));console.log(`ironhide-slime-art: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
