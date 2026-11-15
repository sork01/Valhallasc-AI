// The opening cutscene's camera and the hero aboard from the first frame. Run through test-touch-bounded.sh.
// MUTATE=old serves the previous intro.js (hero hidden until the summoning, per-shot eases) and must fail.
// MUTATE=beads serves the intro.js from before the volcano and iron-chain redraw (flat triangle, pale bead chains) and must fail.
// MUTATE=thinroots serves the intro.js from before the root redraw (thin red lines) and must fail.
// MUTATE=legs serves the previous cutscene.js + intro.js (walk phase advancing 11 per second whatever the ground covered) and must fail.
const assert=require('node:assert/strict'),path=require('node:path'),{execFileSync}=require('node:child_process');
const {chromium}=require('./lib/playwright.cjs');
const {TestWorld}=require('../scripts/testing/driver.cjs');
require('./lib/touch.cjs').requireMemoryLimit();
const world=new TestWorld();let browser,checks=0;
const check=(ok,label)=>{assert.ok(ok,label);console.log(`${++checks}: ${label}`);};
const ROOT_BARK=8000; // measured on the box at 29 s: 17,020 with the redraw, 664 with the old thin lines
(async()=>{try{
 await world.start();browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const page=await browser.newPage({viewport:{width:960,height:600}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 if(process.env.MUTATE==='old'){const body=execFileSync('git',['show','8b0bf236:client/intro.js'],{encoding:'utf8'});await page.route('**/intro.js*',r=>r.fulfill({contentType:'text/javascript',body}));}
 if(process.env.MUTATE==='beads'){const body=execFileSync('git',['show','8072eaae356ba7230201689f33ad197f4859a3b8:client/intro.js'],{encoding:'utf8',cwd:path.resolve(__dirname,'..')});await page.route('**/intro.js*',r=>r.fulfill({contentType:'text/javascript',body}));}
 if(process.env.MUTATE==='thinroots'){const body=execFileSync('git',['show','fd00a4a5386185763cf48f905b6d36dd279238a0:client/intro.js'],{encoding:'utf8',cwd:path.resolve(__dirname,'..')});await page.route('**/intro.js*',r=>r.fulfill({contentType:'text/javascript',body}));}
 if(process.env.MUTATE==='legs'){for(const f of ['intro','cutscene']){const body=execFileSync('git',['show','0106bebd:client/'+f+'.js'],{encoding:'utf8',cwd:path.resolve(__dirname,'..')});await page.route('**/'+f+'.js*',r=>r.fulfill({contentType:'text/javascript',body}));}}
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('IntroCamera');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0);if(await page.locator('#low-gfx-dismiss').isVisible())await page.locator('#low-gfx-dismiss').click();
 check(await page.evaluate(()=>!!window.IntroScene),'The scene exposes its camera and hero path');
 const m=await page.evaluate(()=>{
  const S=IntroScene,D=WORLD_MAP.dock,L=D.ship.y1-D.ship.y0,out={maxStep:0,maxZoomStep:0,zooms:[],onDeck:true,face:true};
  let prev=null;
  for(let t=0;t<=S.dur;t+=.05){
   const f=S.camera(t),ox=-22*(1-Math.min(1,t/54.5))**2,oy=150*Math.pow(1-Math.min(1,t/54.5),1.7),h=S.heroAt(t);
   out.zooms.push(f.k);
   if(prev){out.maxStep=Math.max(out.maxStep,Math.hypot(f.x-prev.x-(ox-prev.ox),f.y-prev.y-(oy-prev.oy)));out.maxZoomStep=Math.max(out.maxZoomStep,Math.abs(Math.log(f.k/prev.k)));}
   prev={x:f.x,y:f.y,k:f.k,ox,oy};
   if(t<53){const u=(h.y-(D.ship.y0+oy))/L;if(Math.abs(h.x-(D.ship.x+ox))>.01||Math.abs(u-S.heroU)>.01||S.heroU>.15||h.walk)out.onDeck=false;if(h.face[1]!==-1)out.face=false;}
  }
  const a=S.camera(0),h0=S.heroAt(0),peak=S.camera(49),hp=S.heroAt(49),end=S.camera(S.dur),he=S.heroAt(S.dur);
  return{...out,zooms:undefined,max:Math.max(...out.zooms),min:Math.min(...out.zooms),open:a.k,openOff:Math.hypot(a.x-h0.x,a.y-h0.y),peak:peak.k,peakOff:Math.hypot(peak.x-hp.x,peak.y-hp.y),lift:hp.z-S.heroAt(46).z,
   end:[end.k,end.x-D.start.x,end.y-D.start.y,end.z],heroEnd:[he.x-D.start.x,he.y-D.start.y]};
 });
 console.log(JSON.stringify(m));
 check(m.onDeck&&m.face,'The hero stands at the bow facing ahead for the whole voyage');
 check(m.open>=2&&m.openOff<.6,'The scene opens in a close-up of the hero');
 check(m.peak>=2.5&&m.peakOff<.6&&m.lift>3,'The camera pushes in on the hero as the magic finds them, and the light lifts them');
 check(m.max/m.min>=4.5,'The zoom range is wide (close-ups and a high wide shot)');
 check(m.maxStep<.25&&m.maxZoomStep<.03,'The camera is one continuous move without jumps');
 check(Math.abs(m.end[0]-1)<.001&&Math.hypot(m.end[1],m.end[2])<.01&&Math.abs(m.end[3])<.01&&Math.hypot(...m.heroEnd)<.01,'It ends on the pier start at the game zoom with the hero there');
 // The legs follow the ground covered: the walk phase advances in proportion to the distance walked and stands still while the hero does.
 const legs=await page.evaluate(()=>{
  const S=IntroScene,off=t=>({x:-22*(1-Math.min(1,t/54.5))**2,y:150*Math.pow(1-Math.min(1,t/54.5),1.7)});
  const rel=t=>{const h=S.heroAt(t),o=off(t);return[h.x-o.x,h.y-o.y];};
  let walkNull=true,dirOk=true,peak=0,sawWalk=false;
  for(let t=53;t<=59.2;t+=.05){
   const h=S.heroAt(t),[x0,y0]=rel(t-.1),[x1,y1]=rel(t+.1),d=Math.hypot(x1-x0,y1-y0),speed=d/.2;peak=Math.max(peak,speed);
   if(h.walk){sawWalk=true;if(speed<.2)walkNull=false;if(((x1-x0)*h.walk[0]+(y1-y0)*h.walk[1])/d<.97)dirOk=false;}
   else if(speed>.9)walkNull=false;
  }
  return{walkNull,dirOk,peak,sawWalk};
 });
 console.log(JSON.stringify(legs));
 check(legs.sawWalk&&legs.walkNull,'The hero walks while moving and stands while still (no walking pose at the ends of the ease)');
 check(legs.dirOk,'The walk direction is the real direction of travel (aft along the deck, then down the plank)');
 await page.evaluate(()=>{window.__rec=[];const tick=()=>{const s=Cutscene.state;if(s)window.__rec.push([s.el,s.legs]);requestAnimationFrame(tick);};requestAnimationFrame(tick);});
 await page.evaluate(()=>Cutscene.play(['intro'],{skippable:false}));
 for(const at of [2.5,8,12,18,23,29,36,42,48,49.5,52,54.4,55,55.6,57.5,60.5]){
  await page.waitForFunction(at=>!Cutscene.active||Cutscene.state.el>=at,at,{timeout:20000});
  await page.screenshot({path:path.join(world.runDir,`intro-${String(at).replace('.','_')}.png`)});
  if(at===29){   // the roots that hold up the sky: thick bark trunks (dark brown) with flames and lava cracks on them, not thin red lines
   const rt=await page.evaluate(()=>{const c=document.querySelector('.cs-view'),g=c.getContext('2d'),w=c.width,h=c.height,d=g.getImageData(0,Math.round(h*.15),w,Math.round(h*.2)).data;let bark=0,fire=0;
    for(let i=0;i<d.length;i+=4){const r=d[i],gr=d[i+1],b=d[i+2];if(r>35&&r<75&&gr>18&&gr<45&&b>10&&b<38)bark++;if(r>220&&gr>90&&gr<215&&b<110)fire++;}
    return{bark,fire};});
   console.log(JSON.stringify(rt));
   check(rt.bark>ROOT_BARK,`The sky roots are thick bark trunks (${rt.bark} bark pixels in the upper band; the old thin lines gave about 660)`);
  }
  if(at===18){   // the nine chains are heavy dark iron (not the old strings of pale beads), and the forge is a lit volcano
   const px=await page.evaluate(()=>{const c=document.querySelector('.cs-view'),g=c.getContext('2d'),w=c.width,h=c.height,x0=Math.round(w*.3),y0=Math.round(h*.2),d=g.getImageData(x0,y0,Math.round(w*.45),Math.round(h*.25)).data;let pale=0,iron=0;
    for(let i=0;i<d.length;i+=4){const r=d[i],gr=d[i+1],b=d[i+2];if(r>190&&b>r+12)pale++;if(r<115&&b>=r&&b>55&&r>35)iron++;}
    const cr=g.getImageData(Math.round(w*.22)-30,Math.round(h*.26)+6,60,40).data;let lava=0;for(let i=0;i<cr.length;i+=4)if(cr[i]>220&&cr[i+1]>110&&cr[i+2]<150)lava++;
    return{pale,iron,lava,w,h};});
   console.log(JSON.stringify(px));
   check(px.iron>22000,`The chains are heavy dark iron (${px.iron} steel pixels in the chain band; the old pale beads gave about 11,700)`);
   check(px.lava>150,`The volcano's crater glows with lava (${px.lava} lava pixels)`);
  }
 }
 await page.waitForFunction(()=>!Cutscene.active,null,{timeout:8000});
 const phase=await page.evaluate(()=>{
  const S=IntroScene,off=t=>({x:-22*(1-Math.min(1,t/54.5))**2,y:150*Math.pow(1-Math.min(1,t/54.5),1.7)}),rel=t=>{const h=S.heroAt(t),o=off(t);return[h.x-o.x,h.y-o.y];};
  const rec=window.__rec.filter(r=>r[0]>=52&&r[0]<=60);let moving=0,measured=0,idle=0,frames=0;
  for(let i=1;i<rec.length;i++){
   const [t0,w0]=rec[i-1],[t1,w1]=rec[i];if(t1<=t0||t1-t0>1)continue;frames++;
   // The cutscene clamps one frame to .1 s, so a slow frame covers only that much of the walk.
   const dt=Math.min(t1-t0,.1),[x0,y0]=rel(t1-.05),[x1,y1]=rel(t1+.05),speed=Math.hypot(x1-x0,y1-y0)/.1,d=speed*dt,dw=w1-w0;
   if(speed>.6){moving+=d*11/5.2;measured+=dw;}else if(speed<.05)idle+=Math.abs(dw);
  }
  return{frames,moving,measured,idle};
 });
 console.log(JSON.stringify(phase));
 check(phase.frames>20&&phase.moving>3,'Enough frames were sampled while the hero walked');
 check(phase.measured/phase.moving>.8&&phase.measured/phase.moving<1.2,`The walk cycle advances with the ground covered (${phase.measured.toFixed(2)} measured, ${phase.moving.toFixed(2)} expected)`);
 check(phase.idle<.3,`The legs do not tread on the spot while the hero is still (${phase.idle.toFixed(2)})`);
 check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
 console.log(JSON.stringify({checks,runDir:world.runDir}));
}finally{await browser?.close();await world.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
