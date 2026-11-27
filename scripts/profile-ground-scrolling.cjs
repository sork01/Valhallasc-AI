'use strict';
// Bounded, private-world measurements. BASELINE=1 routes the pre-fix field.js;
// it never swaps files in the checkout or creates a player in the public game.
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { firefox, chromium } = require('playwright');
const { requireMemoryLimit } = require('../tests/lib/touch.cjs');
const { TestWorld } = require('./testing/driver.cjs');
requireMemoryLimit();
const root=path.resolve(__dirname,'..'),world=new TestWorld(),reports=[];
const baseline=process.env.BASELINE==='1',engine=process.env.BROWSER==='chromium'?chromium:firefox;
let browser;
(async()=>{
  await world.start();
  browser=await engine.launch({headless:true,...(engine===firefox?{firefoxUserPrefs:{
    'dom.ipc.processCount':1,'dom.ipc.processCount.webIsolated':1,
    'dom.ipc.processPrelaunch.enabled':false,'fission.autostart':false,
    'network.process.enabled':false,'media.rdd-process.enabled':false,'media.utility-process.enabled':false,
  }}:{})});
  const page=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const version=fs.readFileSync(path.join(root,'client/index.html'),'utf8').match(/class="version">([^<]+)</)[1];
  await page.addInitScript(version=>{
    window.AudioContext=window.webkitAudioContext=undefined;window.__valhallaTestSprites=true;
    window.confirm=()=>true;localStorage.setItem('valhallasc.whats-new.v1',version);
    localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,lowGraphics:true}));
    window.__profile={};window.__measure=(name,took)=>{
      const row=__profile[name]||={n:0,total:0,max:0};row.n++;row.total+=took;row.max=Math.max(row.max,took);
    };
    window.__timed=(fn,name)=>function(...args){const start=performance.now();
      try{return fn.apply(this,args);}finally{__measure(name,performance.now()-start);}};
  },version);
  let source=baseline?execFileSync('git',['show','b75fdb20:client/field.js'],{cwd:root,maxBuffer:1<<24}).toString():fs.readFileSync(path.join(root,'client/field.js'),'utf8');
  source=source.replace('    // ground', '    const groundStart=performance.now();\n    // ground');
  source=source.replace('    City.drawPlaza(g, w2s);', "    window.__measure('ground',performance.now()-groundStart);\n    City.drawPlaza(g, w2s);");
  source=source.replace('  const Field = {', ['draw','update','renderChunk'].map(name=>`${name}=window.__timed(${name},'${name}');`).join('\n')+'\n  const Field = {');
  await page.route('**/field.js*',route=>route.fulfill({contentType:'text/javascript',body:source}));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('FrameProbe');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0,null,{timeout:60000});
  await page.evaluate(()=>Tutorial.disable());
  await page.locator('#connection-overlay').waitFor({state:'hidden',timeout:60000});
  await page.evaluate(()=>GM.request({op:'set_time',hour:12,freeze:true}));
  await page.evaluate(()=>GM.request({op:'set_weather',kind:'clear'}));
  for(const [zone,x,y] of (process.env.ONE_ZONE?[[0,250,235]]:[[0,250,235],[9,40,24]])){
    await page.evaluate(command=>GM.request(command),{op:'teleport',zone,x,y});
    await page.waitForFunction(zone=>Field.zone===zone,zone);await page.waitForTimeout(2000);
    for(const walking of [false,true]){
      await page.waitForFunction(()=>Field.canAct,null,{timeout:15000});
      const start=await page.evaluate(()=>{document.activeElement?.blur();return[Field.hero.x,Field.hero.y];});
      await page.evaluate(()=>{
        window.__profile={};window.__frames=[];window.__sample=true;
        const generation=window.__generation=(window.__generation||0)+1;let last=performance.now();
        function tick(){if(!__sample||generation!==__generation)return;const now=performance.now();__frames.push(now-last);last=now;requestAnimationFrame(tick);}
        requestAnimationFrame(tick);
      });
      if(walking){await page.keyboard.down('ArrowRight');await page.keyboard.down('ArrowDown');}
      await page.waitForTimeout(4500);
      if(walking){await page.keyboard.up('ArrowRight');await page.keyboard.up('ArrowDown');}
      const sample=await page.evaluate(({zone,walking})=>{
        __sample=false;const frames=__frames.slice(5).sort((a,b)=>a-b);
        return{zone,walking,lowGraphics:Prefs.lowGraphics,frames:frames.length,p50:frames[Math.floor(frames.length*.5)],p95:frames[Math.floor(frames.length*.95)],profile:__profile,pos:[Field.hero.x,Field.hero.y]};
      },{zone,walking});
      if(walking&&Math.hypot(sample.pos[0]-start[0],sample.pos[1]-start[1])<2)throw Error('The profiling walk did not move.');
      reports.push(sample);console.log(JSON.stringify(sample));
    }
  }
  if(errors.length)throw Error(errors.join('; '));
  const out=path.join(root,'test-results/firefox-scrolling');fs.mkdirSync(out,{recursive:true});
  const report=path.join(out,`${engine.name()}-${baseline?'baseline':'candidate'}.json`);
  fs.writeFileSync(report,JSON.stringify({browser:engine.name(),baseline:baseline?'b75fdb20':null,viewport:[1280,800],reports},null,2));
  console.log(report);
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{
  const cg=fs.readFileSync('/proc/self/cgroup','utf8').trim().split('::')[1];
  for(const name of ['memory.peak','memory.events','pids.events'])console.log(name,fs.readFileSync('/sys/fs/cgroup'+cg+'/'+name,'utf8').trim());
  await browser?.close();await world.stop();
});
