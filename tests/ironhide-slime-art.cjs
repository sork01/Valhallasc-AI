process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const sources=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../scripts/meadow_slime_sources.txt')));
const source=sources.valhallasc_meadow_ironhide_rigid_all;
const{chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 w.startLevel=20;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});const p=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:true,lowGraphicsSet:true,touchGraphicsSuggested:true}));});
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('BeetleArt');await p.locator('#go').click({timeout:60000});await p.waitForFunction(()=>Online.connected&&Field.beetleSprites,null,{timeout:30000});
 const result=await p.evaluate(async()=>{
  const src=Field.beetleSprites,{meta,img}=src,im=img.beetle,c=document.createElement('canvas');c.width=im.width;c.height=im.height;const g=c.getContext('2d',{willReadFrequently:true});g.drawImage(im,0,0);const rows=[];
  const gallery=document.createElement('canvas');gallery.width=8*144;gallery.height=5*152;const gg=gallery.getContext('2d');gg.imageSmoothingEnabled=false;gg.fillStyle='#315441';gg.fillRect(0,0,gallery.width,gallery.height);
  for(const[clip,spec]of Object.entries(meta.clips))for(let k=0;k<spec.n;k++){
   const p=g.getImageData(k*72,spec.row*64,72,64).data;let opaque=0,edge=0,white=0,steel=0,hash=7,minY=64,maxY=-1;
   for(let y=0;y<64;y++)for(let x=0;x<72;x++){const i=(y*72+x)*4;hash=(Math.imul(hash,31)+p[i]+p[i+1]*3+p[i+2]*7+p[i+3])>>>0;if(!p[i+3])continue;opaque++;minY=Math.min(minY,y);maxY=Math.max(maxY,y);if(p[i+2]>p[i]&&p[i+2]>=70)steel++;if(x===0||x===71||y===0||y===63)edge++;if(p[i]>220&&p[i+1]>230&&p[i+2]>220)white++;}
   rows.push({clip,k,opaque,edge,white,steel,hash,minY,height:maxY-minY+1});gg.drawImage(im,k*72,spec.row*64,72,64,k*144,spec.row*152,144,128);gg.font='16px sans-serif';gg.fillStyle='#fff2c8';gg.fillText(`${clip} ${k}`,k*144+5,spec.row*152+146);
  }
  const portrait=document.createElement('canvas');portrait.width=portrait.height=96;const ready=Field.drawTargetPortrait({kind:'beetle'},portrait);
  const old=new Image();old.src='assets/slimes_green.png';await old.decode();
  const compare=document.createElement('canvas');compare.width=600;compare.height=220;const cg=compare.getContext('2d');cg.imageSmoothingEnabled=false;cg.fillStyle='#315441';cg.fillRect(0,0,600,220);cg.drawImage(old,0,0,64,60,40,10,192,180);cg.drawImage(im,0,0,72,64,330,0,216,192);cg.font='18px sans-serif';cg.fillStyle='#fff2c8';cg.fillText('Slime reference',55,210);cg.fillText('Redrawn Ironhide Beetle',315,210);
  return{frame:meta.frame,anchor:meta.anchor,size:[im.width,im.height],rows,clips:meta.clips,sprites:meta.sprites,tops:meta.tops,gallery:gallery.toDataURL(),compare:compare.toDataURL(),portraitReady:ready,portrait:portrait.toDataURL()};
 });
 check(result.frame.join()==='72,64'&&result.anchor.join()==='36,60'&&result.size.join()==='576,320','Existing frame, anchor and atlas contract is preserved');
 check(result.rows.length===34&&result.rows.every(r=>r.opaque>10&&r.edge===0),'All 34 exported editor frames are nonempty and unclipped');
 check(Object.values(result.sprites).includes(source),'The client loads the new saved PixelFlow source');
 for(const clip of ['idle','walk','attack','hurt','die'])check(new Set(result.rows.filter(r=>r.clip===clip).map(r=>r.hash)).size>=Math.min(result.clips[clip].n,4),`${clip}: real exported frames animate distinctly`);
 check(result.rows.find(r=>r.clip==='idle'&&r.k===0).white>20,'Large eye whites and glossy shell highlights remain visible');check(result.portraitReady,'Production target portrait uses the new beetle atlas');
 const idle=result.rows.find(r=>r.clip==='idle'&&r.k===0),death=result.rows.filter(r=>r.clip==='die');
 check(death.every(r=>r.opaque>idle.opaque*.65&&r.height>idle.height*.7),'Death retains a solid tipped beetle body, with no flattened puddle');
 check(death.every(r=>r.steel>idle.steel*.75),'All death frames preserve the rigid steel shell');
 check(new Set(death.map(r=>r.hash)).size===8,'All eight death poses show the crack, buckle and tipping sequence');
 check(result.tops.beetle===60-Math.min(...result.rows.filter(r=>r.clip==='idle').map(r=>r.minY)),'Health-bar top follows the tallest saved idle frame');
 for(const name of ['gallery','compare','portrait'])fs.writeFileSync(path.join(w.runDir,'ironhide-slime-'+name+'.png'),Buffer.from(result[name].split(',')[1],'base64'));
 const beetle=await p.evaluate(()=>WORLD_MAP.slimes.find(s=>s.kind==='beetle'));await p.evaluate(s=>{Online.send({type:'debug',command:{op:'teleport',zone:0,x:s.x+3,y:s.y+2}});Online.send({type:'debug',command:{op:'set_time',hour:12,freeze:true}});},beetle);await p.waitForTimeout(600);
 check(await p.evaluate(()=>Field.slimes.some(s=>s.kind==='beetle'&&s.d.top===Field.beetleSprites.meta.tops.beetle)),'Authoritative Greenmeadow beetle uses the new health-bar height');await p.evaluate(()=>{City.close();ZoneJourney.clear();Field._debug.drawFrame(3);});await p.screenshot({path:path.join(w.runDir,'ironhide-slime-in-game.png')});
 await p.setViewportSize({width:844,height:390});await p.screenshot({path:path.join(w.runDir,'ironhide-slime-phone.png')});fs.writeFileSync(path.join(w.runDir,'meadow-art-checks.json'),JSON.stringify({rows:result.rows,source:source,tops:result.tops},null,2));check(errors.length===0,'No real-art browser errors: '+errors.join('; '));console.log(`ironhide-slime-art: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
