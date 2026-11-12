// Real recorded intro audio and private client. Run through test-touch-bounded.sh.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require('./lib/playwright.cjs');
const {TestWorld}=require('../scripts/testing/driver.cjs');
require('./lib/touch.cjs').requireMemoryLimit();
const world=new TestWorld(), manifest=JSON.parse(fs.readFileSync('docs/intro-narration-sources.txt'));
let browser,checks=0;
const check=(ok,label)=>{assert.ok(ok,label);console.log(`${++checks}: ${label}`);};
(async()=>{try{
 check(manifest.files.length===7,'Seven recordings have a durable source mapping');
 for(let i=0;i<7;i++){
  const f=manifest.files[i],hash=crypto.createHash('sha256').update(fs.readFileSync(f.asset)).digest('hex');
  assert.equal(hash,f.sha256,'Original ElevenLabs bytes are preserved');
  assert(f.cue+f.duration+.12<=(manifest.files[i+1]?.cue??62),'Recordings fit without overlap at their normal speed');
 }
 check(true,'All seven originals match their hashes and fit inside the unchanged 62 seconds');
 await world.start();browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const page=await browser.newPage({viewport:{width:960,height:600}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 if(process.env.MUTATE==='narrate'){
  const source=fs.readFileSync('client/cutscene.js','utf8'),from='if (S.narration?.[index]) window.CutsceneAudio?.narrate(S.narration[index], el - at);';
  assert(source.includes(from));await page.route('**/cutscene.js*',r=>r.fulfill({contentType:'text/javascript',body:source.replace(from,'')}));
 }
 await page.addInitScript(()=>{
  localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:true,musicVol:0,sfxVol:.4,weatherAudio:0,combatSounds:'synthesized'}));
  window.__tts=0;window.SpeechSynthesisUtterance=function(){};
  Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{speak(){window.__tts++;},cancel(){},getVoices(){return[];}}});
 });
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('IntroRecords');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0);if(await page.locator('#low-gfx-dismiss').isVisible())await page.locator('#low-gfx-dismiss').click();
 const paths=manifest.files.map(f=>f.asset.replace('client/',''));
 const decoded=await page.evaluate(async paths=>(await CutsceneAudio.prepareNarration(paths)).map(b=>b?.duration||0),paths);
 check(decoded.length===7&&decoded.every((d,i)=>d>0&&Math.abs(d-manifest.files[i].duration)<.1),'The browser decodes all seven actual MP3 assets');
 await page.evaluate(()=>{
  window.__narration=[];const narrate=CutsceneAudio.narrate;
  CutsceneAudio.narrate=async(url,elapsed)=>{const started=await narrate(url,elapsed);__narration.push({url,started});return started;};
  Cutscene.play(['intro'],{skippable:false});
 });
 await page.waitForFunction(()=>Cutscene.state?.scene==='intro');
 check(await page.evaluate(()=>Cutscene.state.dur===62&&!Cutscene.state.skippable),'The first-character intro still lasts 62 seconds and cannot be skipped');
 const home=await page.evaluate(()=>({x:Field.hero.nx,y:Field.hero.ny}));
 await page.keyboard.down('ArrowRight');await page.waitForTimeout(2500);await page.keyboard.up('ArrowRight');
 check(await page.evaluate(home=>Math.hypot(Field.hero.nx-home.x,Field.hero.ny-home.y)<.05,home),'The existing intro movement lock is retained');
 check(await page.locator('#cutscene .cs-caption').textContent().then(t=>t.startsWith('Before the first harvest')),'Subtitles accompany the first recording');
 check(await page.evaluate(()=>__narration.length===1&&__narration[0].started&&CutsceneAudio.narrating),'The first cue starts a real recorded WebAudio voice');
 check(await page.evaluate(()=>Math.abs(__combatAudioTest.bus().gain.value-.16)<.001),'Narration uses the existing effects-volume bus');
 check(await page.evaluate(()=>__tts===0),'Browser TTS is never used');
 // One uninterrupted playback checks the actual recording/caption schedule.
 await page.waitForFunction(()=>Cutscene.state?.el>58.2,null,{timeout:65000});
 check(await page.locator('#cutscene .cs-caption').textContent()==='Welcome to Veyrheim, hero.','The final subtitle welcomes the hero to Veyrheim');
 check(await page.evaluate(()=>CutsceneAudio.narrating),'The final Veyrheim recording is playing');
 await page.screenshot({path:path.join(world.runDir,'intro-veyrheim-recorded.png')});
 await page.waitForFunction(()=>!Cutscene.active,null,{timeout:6000});
 const played=await page.evaluate(()=>__narration);
 check(played.length===7&&played.every((v,i)=>v.started&&v.url===paths[i]),'All seven recordings play exactly once in the right order');
 check(await page.evaluate(()=>__tts===0&&!CutsceneAudio.narrating),'Completion leaves no narrator running and never falls back to TTS');
 check(await page.locator('#cutscene').isHidden(),'The cutscene closes normally');
 // Sound setting and volume changes apply to active as well as future voices.
 const sound=await page.evaluate(async url=>{
  Prefs.set({sound:false});const muted=await CutsceneAudio.narrate(url,0);
  Prefs.set({sound:true,sfxVol:.5});const started=await CutsceneAudio.narrate(url,0),volume=__combatAudioTest.bus().gain.value;
  Prefs.set({sound:false});return{muted,started,volume,active:CutsceneAudio.narrating};
 },paths[0]);
 check(!sound.muted&&sound.started&&!sound.active&&Math.abs(sound.volume-.25)<.001,'Mute stops active narration; muted cues stay silent and volume is respected');
 await page.route('**/intro-narration-1.mp3?late=1',async route=>{await page.waitForTimeout(350);await route.fulfill({path:'client/assets/intro-narration-1.mp3',contentType:'audio/mpeg'});});
 const delayed=await page.evaluate(async()=>{Prefs.set({sound:true});const p=CutsceneAudio.narrate('assets/intro-narration-1.mp3?late=1',0);CutsceneAudio.stopNarration();return{started:await p,active:CutsceneAudio.narrating};});
 check(!delayed.started&&!delayed.active,'A delayed recording cannot start after narration has been cancelled');
 await page.evaluate(()=>document.getElementById('set-replay-intro').click());await page.waitForFunction(()=>Cutscene.state?.scene==='intro'&&Cutscene.state.el>2.7,null,{timeout:6500});
 check(await page.evaluate(()=>Cutscene.state.skippable&&CutsceneAudio.narrating),'Settings replay is skippable and uses the recordings');
 await page.keyboard.down('Space');await page.waitForTimeout(1200);await page.keyboard.up('Space');await page.waitForFunction(()=>!Cutscene.active);
 check(await page.evaluate(()=>!CutsceneAudio.narrating),'Holding skip stops the recording immediately');
 await page.evaluate(()=>{Cutscene.play(['intro'],{skippable:true});});await page.waitForFunction(()=>CutsceneAudio.narrating,null,{timeout:5000});
 await page.evaluate(()=>Cutscene.reset());
 check(await page.evaluate(()=>!Cutscene.active&&!CutsceneAudio.narrating),'Reset/disconnect cleanup stops the recorded voice');
 check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
 const report={checks,recordings:manifest.files.map(f=>({asset:f.asset,cue:f.cue,duration:f.duration,sha256:f.sha256})),runDir:world.runDir};
 fs.writeFileSync(path.join(world.runDir,'intro-recordings.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({checks,runDir:world.runDir}));
 }finally{await browser?.close();await world.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
