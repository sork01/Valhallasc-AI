process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const all=['ember_firelord','hollow_rider','grinch','bloomwarden','birchcrown','briarheart','starrocketeer'];
const kinds=process.env.SHARED_ART_KINDS?process.env.SHARED_ART_KINDS.split(','):all;
assert(kinds.length&&kinds.every(k=>all.includes(k)));
const out=path.join(__dirname,'../test-results/shared-slime');fs.mkdirSync(out,{recursive:true});
const baseline=!!process.env.BASELINE;
const registry=baseline?{}:JSON.parse(fs.readFileSync(path.join(__dirname,'../scripts/shared_slime_sources.txt')));
const expected=baseline?{}:JSON.parse(fs.readFileSync(path.join(out,'editor-export-proof.json')));
let browser,checks=0;const world=new TestWorld(),errors=[];
const check=(value,label)=>{assert(value,label);console.log(++checks+': '+label);};
(async()=>{try{
 world.startLevel=99;world.godMode=true;await world.start();
 browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const p=await browser.newPage({viewport:{width:960,height:600},reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 if(process.env.MUTATE_PNG)await p.route('**/assets/'+process.env.MUTATE_BANK+'_'+process.env.MUTATE_KIND+'.png*',r=>r.fulfill({path:process.env.MUTATE_PNG,contentType:'image/png'}));
 await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:true,lowGraphicsSet:true}));});
 await p.goto(world.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('SharedArt');await p.locator('#go').click({timeout:60000});await p.waitForFunction(()=>Online.connected&&Field.hero?.hp>0);
 // Activate the real shared Firelord through the ordinary quest and cross channel.
 const cross=await p.evaluate(()=>WORLD_MAP.crosses[0]);
 const keeper=await p.evaluate(()=>WORLD_MAP.zones[44].npcs.find(n=>n.id==='raid_key_keeper'));
 await p.evaluate(n=>Online.send({type:'debug',command:{op:'teleport',zone:45,x:n.x+1,y:n.y+1}}),keeper);await p.waitForFunction(()=>Field.zone===45);
 await p.evaluate(()=>Online.send({type:'interact',npc:'raid_key_keeper',offer:'quest:accept:raid_key'}));await p.waitForFunction(()=>Field.hero.quests.some(q=>q.id==='raid_key'&&!q.claimed));
 await p.evaluate(c=>{City.close();Online.send({type:'debug',command:{op:'teleport',zone:0,x:c.x,y:c.y}});Online.send({type:'debug',command:{op:'set_time',hour:12,freeze:true}});},cross);
 await p.waitForFunction(()=>Field.zone===0&&!!RaidKey.nearest());await p.evaluate(()=>RaidKey.interact());
 await p.waitForFunction(()=>Field.slimes.some(s=>s.kind==='ember_firelord'&&!s.dead)&&!!Field.cathedralSprites?.img.ember_firelord?.complete,null,{timeout:60000});
 check(await p.evaluate(()=>Field.enemyName('ember_firelord')===WORLD_MAP.crosses[0].bossName),'Firelord retains its cross identity');
 if(!baseline)check(await p.evaluate(()=>Field.cathedralSprites.img.ember_firelord.src.endsWith('cathedral_ember_firelord.png')),'Production loader uses independent Firelord atlas');
 await p.evaluate(async()=>{await Promise.all([Halloween.load(),Christmas.load(),Easter.load(),Solstice.load(),Valentines.load(),NewYear.load()]);ZoneJourney.clear();Field._debug.drawFrame(3);});
 await p.screenshot({path:path.join(out,baseline?'baseline-game.png':'firelord-game.png')});
 const result=await p.evaluate(({kinds,baseline})=>{
  const data={},boards=[];
  for(const kind of kinds){
   const src=Field._debug.enemySource({kind});if(!src)throw Error('Missing production source '+kind);
   const fr=Field.frameOf(src,kind),meta=src.meta,img=src.img[kind];
   const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=img.height;
   const g=canvas.getContext('2d',{willReadFrequently:true});g.drawImage(img,0,0);const rows=[];
   for(const [clip,c] of Object.entries(meta.clips))for(let n=0;n<c.n;n++){
    const pixels=g.getImageData(n*fr.w,c.row*fr.h,fr.w,fr.h).data;
    let opaque=0,low=-1,top=fr.h,left=fr.w,right=-1,edge=0,hash=7;
    for(let y=0;y<fr.h;y++)for(let x=0;x<fr.w;x++){const i=(y*fr.w+x)*4;for(let j=0;j<4;j++)hash=(Math.imul(hash,31)+pixels[i+j]+i+j)>>>0;if(!pixels[i+3])continue;opaque++;low=Math.max(low,y);top=Math.min(top,y);left=Math.min(left,x);right=Math.max(right,x);if(!x||!y||x===fr.w-1||y===fr.h-1)edge++;}
    rows.push({clip,n,hash,opaque,low,top,left,right,edge});
   }
   const portrait=document.createElement('canvas');portrait.width=portrait.height=96;const ready=Field.drawTargetPortrait({kind},portrait);
   const portraitPixels=portrait.getContext('2d').getImageData(0,0,96,96).data.filter((v,i)=>i%4===3&&v).length;
   const render=document.createElement('canvas');render.width=fr.w;render.height=fr.h;const dg=render.getContext('2d',{willReadFrequently:true}),drawn=[];
   const reference=document.createElement('canvas');reference.width=fr.w;reference.height=fr.h;const rg=reference.getContext('2d',{willReadFrequently:true});
   const image=kind==='ember_firelord'?RaidKey.tint(img,WORLD_MAP.crosses[0].color):img;
   const board=document.createElement('canvas');board.width=6*240;board.height=210;const bg=board.getContext('2d');bg.fillStyle='#202a3a';bg.fillRect(0,0,board.width,board.height);bg.imageSmoothingEnabled=false;
   const poses=[['idle',0],['attack',2],['attack',4],['attack',7],['die',4],['die',7]];
   const requests=[['idle',0],...Array.from({length:8},(_,i)=>['attack',i]),...Array.from({length:8},(_,i)=>['die',i])];
   for(const [clip,n] of requests){
    const a={kind,d:{scale:1/2.1},dir:1,seed:0,dead:false,hurtT:0,recT:0,hop:0,hopV:0,landT:0,blink:0,state:'idle',st:0};
    if(clip==='die'){a.dead=true;a.dieT=(n+.05)/meta.clips.die.fps;}
    if(clip==='attack'){if(n<3){a.state='windup';a.windupTime=.45;a.st=.45*(1-(n+.05)/3);}else if(n<6){a.state='lunge';a.st=.3*(1-(n-3+.05)/3);}else a.recT=.22*(1-(n-6+.05)/2);}
    dg.clearRect(0,0,fr.w,fr.h);dg.save();dg.translate(fr.ax,fr.ay);Field._debug.drawSlimeSprite(dg,a,0);dg.restore();
    rg.clearRect(0,0,fr.w,fr.h);rg.drawImage(image,n*fr.w,meta.clips[clip].row*fr.h,fr.w,fr.h,0,0,fr.w,fr.h);
    const actual=dg.getImageData(0,0,fr.w,fr.h).data,expect=rg.getImageData(0,0,fr.w,fr.h).data;
    drawn.push({clip,n,same:actual.every((v,i)=>v===expect[i])});
    const col=poses.findIndex(([c,i])=>c===clip&&i===n);
    if(col>=0){bg.drawImage(render,0,0,fr.w,fr.h,col*240+120-fr.ax*1.7,170-fr.ay*1.7,fr.w*1.7,fr.h*1.7);bg.fillStyle='#ffffff';bg.font='12px sans-serif';bg.fillText(kind+' '+clip+' '+n,col*240+5,195);}
   }
   boards.push({kind,png:board.toDataURL()});
   const hit=Field._debug.enemyHitbox({kind,d:{scale:1}});
   data[kind]={frame:[fr.w,fr.h,fr.ax,fr.ay],size:[img.width,img.height],source:meta.sprites[kind],top:meta.tops?.[kind],clips:meta.clips,rows,ready,portraitPixels,drawn,hit};
  }
  return {data,boards};
 },{kinds,baseline});
 for(const {kind,png} of result.boards)fs.writeFileSync(path.join(out,(baseline?'baseline-':process.env.MUTATE_KIND?'mutation-':'rendered-')+kind+'.png'),Buffer.from(png.split(',')[1],'base64'));
 const proofPath=path.join(out,baseline?'baseline-browser.json':(process.env.MUTATE_KIND?'mutation-':'')+'browser-proof.json');
 const previous=fs.existsSync(proofPath)?JSON.parse(fs.readFileSync(proofPath)):{};
 fs.writeFileSync(proofPath,JSON.stringify({...previous,...result.data},null,2));
 if(baseline){console.log('Original display-size captures: '+out);return;}
 for(const kind of kinds){
  const r=result.data[kind];check(r.source===registry[kind],kind+': native saved source selected');check(JSON.stringify(r.frame)==='[176,172,64,164]'&&r.size[0]===1408&&r.size[1]===860,kind+': declared frame and atlas geometry');
  check(r.rows.length===34&&r.rows.every(f=>f.opaque>30&&!f.edge&&f.low===164),kind+': 34 nonempty grounded frames, clear borders');
  check(r.ready&&r.portraitPixels>250,kind+': production portrait has visible full creature');
  check(r.drawn.every(x=>x.same),kind+': actual state machine/compositor matches all attack/death cells');
  const idle=r.rows.filter(f=>f.clip==='idle');check(r.top===164-Math.min(...idle.map(f=>f.top)),kind+': health-bar top follows idle art');
  for(const clip of ['attack','die'])check(new Set(r.rows.filter(f=>f.clip===clip).map(f=>f.hash)).size===8,kind+': eight distinct '+clip+' poses');
  const attack=r.rows.filter(f=>f.clip==='attack');check(Math.max(...attack.map(f=>f.right))-Math.min(...attack.map(f=>f.left))>idle[0].right-idle[0].left+8,kind+': attack has substantial wind-up/strike reach');
  const dead=r.rows.find(f=>f.clip==='die'&&f.n===7);check(164-dead.top<164-idle[0].top-8,kind+': death leaves a fallen silhouette');
  check(r.hit.x1-r.hit.x0>15&&r.hit.y1-r.hit.y0>20&&r.hit.y1<=1,kind+': click bounds follow opaque grounded art');
  // Compare browser frame bytes through SHA-256, including every less-used walk/hurt cell.
  const hashes=await p.evaluate(async kind=>{const src=Field._debug.enemySource({kind}),f=Field.frameOf(src,kind),c=document.createElement('canvas');c.width=src.img[kind].width;c.height=src.img[kind].height;const g=c.getContext('2d',{willReadFrequently:true});g.drawImage(src.img[kind],0,0);const out=[];for(const [clip,s] of Object.entries(src.meta.clips))for(let n=0;n<s.n;n++){const b=g.getImageData(n*f.w,s.row*f.h,f.w,f.h).data;out.push(Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b))).map(x=>x.toString(16).padStart(2,'0')).join(''));}return out;},kind);
  check(hashes.every((h,i)=>h===expected[kind].frames[i].sha256),kind+': all 34 browser-decoded frames equal verified editor export');
 }
 check(!errors.length,'No browser errors: '+errors.join('; '));console.log(checks+' focused checks passed; '+world.runDir);
}finally{await browser?.close();await world.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
