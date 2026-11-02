// Real sprite pixel proof for far/near melee arcs; no fight simulation.
process.env.REAL_SPRITES = '1';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const world = new TestWorld();world.godMode=true;
const candidate=process.env.OWNER_FIXES_CLIENT;
let browser, checks=0;
const check=(ok,label)=>{assert.ok(ok,label);console.log(`${++checks}: ${label}`);};
(async()=>{
  await world.start();browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'}), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.context().grantPermissions(['local-network-access'],{origin:world.url});
  for(const file of ['index.html','field.js','quest-sources.js','quests.js','online.css']){
    let body=fs.readFileSync(path.join(candidate || 'client',file),'utf8');
    if(process.env.MUTATE && file==='field.js') {
      body=body.replace('g.save(); clipFxHalf(g, sy, back);','g.save(); /* old single foreground pass */');
      body=body.replace('list.push({ d: origin.x + origin.y - .002, fx: e, back: true }, { d: origin.x + origin.y + .002, fx: e, back: false });','list.push({ d: origin.x + origin.y + .002, fx: e, back: false });');
    }
    await page.route(file==='index.html'?world.url:'**/'+file,r=>r.fulfill({body,contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html'}));
  }
  await page.addInitScript(version=>{window.AudioContext=undefined;window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false}));localStorage.setItem('valhallasc.whats-new.v1',version);},fs.readFileSync(path.join(candidate||'client','index.html'),'utf8').match(/class="version">([^<]+)/)[1]);
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('DepthProof');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&Field.warriorSprites?.source?.parts?.body,null,{timeout:60000});
  if(await page.locator('#low-gfx-dismiss').isVisible())await page.locator('#low-gfx-dismiss').click();
  await page.evaluate(()=>Online.send({type:'debug',command:{op:'teleport',zone:0,x:15,y:15}}));
  await page.waitForFunction(()=>Math.hypot(Field.hero.x-15,Field.hero.y-15)<.1);
  await page.evaluate(()=>Online.send({type:'debug',command:{op:'set_time',hour:12,freeze:true}}));
  await page.waitForTimeout(250);
  await world.connect({bot:'DepthRemote',class:'warrior'});
  await world.debug('DepthRemote',{op:'teleport',zone:0,x:18,y:15});
  await page.waitForFunction(()=>Field.remotePlayers.some(p=>p.look?.name==='DepthRemote'&&p.sprite?.source?.parts?.body),null,{timeout:60000});
  const results=await page.evaluate(()=>{
    Field.setPaused(true);
    const cv=document.getElementById('fieldcv'),g=cv.getContext('2d'),k=cv.width/1600;
    const effects=Field._debug.effects, saved=effects.splice(0), t=5;
    const c=document.createElement('canvas');c.width=cv.width;c.height=cv.height;const mg=c.getContext('2d');
    const frame=e=>{effects.length=0;if(e)effects.push(e);Field._debug.drawFrame(t);return g.getImageData(0,0,cv.width,cv.height).data;};
    const out=[];
    try {
      for (const h of [Field.hero,Field.remotePlayers.find(p=>p.look?.name==='DepthRemote')]) {
      const actor=h===Field.hero?'local':'remote', sprite=h===Field.hero?Field.warriorSprites:h.sprite, original=sprite.draw;
      const [sx,sy]=Field._debug.w2s(h.x,h.y);
      h.atkT=.14; h.moving=false;h.buffs=[];h.absorb=0;h.hurtT=0;
      for(const kind of ['slash','skCleave','dualSlash','skCone','skAssassinFan'])for(const up of [true,false]){
        const a=up?-Math.PI*3/4:Math.PI/4;h.fx=Math.cos(a);h.fy=Math.sin(a);
        const height={slash:26,skCleave:35,dualSlash:53,skCone:26,skAssassinFan:38}[kind];
        const e={kind,actor:h===Field.hero?Online.id:h.id,x:h.x,y:h.y,a,t:kind==='skCleave'?.22:kind==='skAssassinFan'?.23:.16,life:.7,r:kind==='skAssassinFan'?3.7:1.9,arc:2*Math.acos(kind==='skAssassinFan'?-.4:-.2),core:'#ffffff',glow:'#59d9ff'};
        mg.setTransform(1,0,0,1,0,0);mg.clearRect(0,0,c.width,c.height);mg.setTransform(k,0,0,k,0,0);mg.translate(sx,sy);original.call(sprite,mg,h,t);
        const mask=mg.getImageData(0,0,c.width,c.height).data;
        const base=frame(null),drawn=frame(e);
        sprite.draw=()=>{};const empty=frame(null),uncovered=frame(e);sprite.draw=original;
        let protectedPixels=0, potential=0,covered=0,visible=0;
        const diff=(a,b,i)=>Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>18;
        for(let y=Math.max(1,Math.floor((sy-180)*k));y<Math.min(c.height-1,Math.ceil((sy+70)*k));y++)for(let x=Math.max(1,Math.floor((sx-180)*k));x<Math.min(c.width-1,Math.ceil((sx+180)*k));x++){
          const i=(y*c.width+x)*4, opaque=[i,i-4,i+4,i-c.width*4,i+c.width*4].every(j=>mask[j+3]===255);
          if(diff(base,drawn,i))visible++;
          if(!opaque)continue;
          const far=y<(sy-height-4)*k;
          if(far){protectedPixels++;if(diff(empty,uncovered,i))potential++;if(diff(base,drawn,i))covered++;}
          else if(diff(base,drawn,i))covered+=0; // near overlap is measured separately below
        }
        let near=0,nearSpace=0;
        for(let y=Math.max(0,Math.ceil((sy-height+3)*k));y<Math.min(c.height,Math.ceil((sy+10)*k));y++)for(let x=Math.max(0,Math.floor((sx-70)*k));x<Math.min(c.width,Math.ceil((sx+70)*k));x++){
          const i=(y*c.width+x)*4;if(diff(base,drawn,i)){nearSpace++;if(mask[i+3]===255)near++;}
        }
        const order=[], stroke=g.stroke;
        sprite.draw=function(...args){order.push('body');return original.apply(this,args);};
        g.stroke=function(...args){if(['#59d9ff','#bff6ff'].includes(this.strokeStyle))order.push('streak');return stroke.apply(this,args);};
        try{frame(e);}finally{sprite.draw=original;g.stroke=stroke;}
        const inFront=order.lastIndexOf('streak')>order.lastIndexOf('body');
        out.push({actor,kind,up,potential,covered,visible,near,nearSpace,inFront,protectedPixels});
      }
      }
    } finally {effects.length=0;effects.push(...saved);Field._debug.drawFrame(t);}
    return out;
  });
  fs.writeFileSync(path.join(world.runDir,'melee-pixels.txt'),JSON.stringify(results,null,2));
  for(const r of results){
    check(r.visible>5 || (r.up && r.potential>0),`${r.actor} ${r.kind} ${r.up?'up':'down'} still draws visible streak pixels: ${JSON.stringify(r)}`);
    if(r.up && ['slash','skCleave'].includes(r.kind))check(r.potential>(r.actor==='local'?10:0),'The upward '+r.kind+' crosses real opaque body pixels, so the occlusion assertion is meaningful');
    check(r.covered===0,`${r.actor} ${r.kind} ${r.up?'up':'down'} preserves opaque body pixels on its far side: ${JSON.stringify(r)}`);
    if(!r.up && ['slash','skCleave'].includes(r.kind))check(r.nearSpace>10 && r.inFront,'Downward '+r.kind+' has visible near-side pixels drawn after the body');
  }
  check(errors.length===0,'No browser errors: '+errors.join('; '));
  await page.screenshot({path:path.join(world.runDir,'melee-depth.png')});
  console.log(`melee-depth-ui: ${checks} checks passed; ${world.runDir}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
