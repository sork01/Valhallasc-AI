// Only the new finite intro score: actual MP3/WebAudio in a bounded private world.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
require('./lib/touch.cjs').requireMemoryLimit();
const world=new TestWorld();let browser,checks=0;
const check=(v,s)=>{assert.ok(v,s);console.log(`${++checks}: ${s}`);};
(async()=>{try{
 await world.start();browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const page=await browser.newPage({viewport:{width:960,height:600}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:true,musicVol:.8,sfxVol:.4,weatherAudio:0,combatSounds:'synthesized'})));
 if(process.env.MUTATE==='score')await page.route('**/intro.js*',route=>route.fulfill({contentType:'text/javascript',body:fs.readFileSync('client/intro.js','utf8').replace("music: 'assets/music_intro.mp3',",'')}));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('StringScore');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0);
 if(await page.locator('#low-gfx-dismiss').isVisible())await page.locator('#low-gfx-dismiss').click();
 if(process.env.PART!=='tail'){
 await page.evaluate(()=>Cutscene.play(['intro'],{skippable:false}));
 await page.waitForFunction(()=>CutsceneAudio.score?.playing,null,{timeout:20000});
 const first=await page.evaluate(()=>({duration:CutsceneAudio.score.duration,offset:CutsceneAudio.score.offset,elapsed:Cutscene.state.el,level:CutsceneAudio.score.output.gain.value}));
 check(Math.abs(first.duration-62)<.1,'The actual score decodes to 62 seconds');
 check(first.offset>=0&&first.offset<=first.elapsed&&first.elapsed-first.offset<3,'Playback follows the intro clock');
 await page.waitForTimeout(3500);
 check(await page.evaluate(()=>CutsceneAudio.narrating&&CutsceneAudio.score.playing),'Recorded narration and the new score play together');
 check(await page.evaluate(()=>Math.abs(CutsceneAudio.score.output.gain.value-.55*.8*.8)<.001),'The score uses the saved music volume with headroom for narration');
 check(await page.evaluate(()=>valhalla.fmusic.output.gain.value<.001&&valhalla.music.output.gain.value<.001),'Field and title music are silent beneath the intro');
 await page.evaluate(()=>Prefs.set({musicVol:.5,sfxVol:.7}));await page.waitForTimeout(500);
 check(await page.evaluate(()=>Math.abs(CutsceneAudio.score.output.gain.value-.55*.25)<.001&&Math.abs(__combatAudioTest.bus().gain.value-.49)<.001),'Music and narration keep independent volume controls');
 // The one-second day/night timer must not raise a field track under the score.
 await page.evaluate(()=>Online.send({type:'debug',command:{op:'set_time',hour:0,freeze:true}}));await page.waitForTimeout(2500);
 check(await page.evaluate(()=>valhalla.fmusic.output.gain.value<.001&&valhalla.meadowNightMusic.output.gain.value<.001),'Day/night crossfades keep background scores silent during the intro');
 await page.evaluate(()=>Prefs.set({sound:false}));await page.waitForTimeout(500);
 check(await page.evaluate(()=>CutsceneAudio.score.output.gain.value<.001&&!CutsceneAudio.narrating),'Mute silences the score and narration');
 await page.evaluate(()=>Prefs.set({sound:true,musicVol:.8}));await page.waitForTimeout(500);
 check(await page.evaluate(()=>Math.abs(CutsceneAudio.score.output.gain.value-.55*.64)<.001),'Unmute restores the current score without restarting it');
 // Resuming an AudioContext after a hidden tab must seek to the advancing scene clock.
 const resumed=await page.evaluate(async()=>{
  const c=new AudioContext();await c.resume();let elapsed=7;
  const p=createCutsceneMusic(c,'assets/music_intro.mp3',()=>elapsed);p.start();
  for(let i=0;i<100&&!p.playing;i++)await new Promise(r=>setTimeout(r,25));
  const before=p.offset;await c.suspend();elapsed=29;await c.resume();
  for(let i=0;i<100&&p.offset!==29;i++)await new Promise(r=>setTimeout(r,25));
  const after=p.offset;p.stop();await c.close();return{before,after};
 });
 check(resumed.before===7&&resumed.after===29,'Audio resume catches up to the cutscene clock');
 await page.evaluate(()=>{window.__oldScore=CutsceneAudio.score;Cutscene.reset();});await page.waitForTimeout(1700);
 check(await page.evaluate(()=>!CutsceneAudio.score&&!__oldScore.running&&!__oldScore.playing),'Reset releases the finite score and narration');
 check(await page.evaluate(()=>valhalla.meadowNightMusic.output.gain.value>.1),'Finishing the intro restores the current night score');
 await page.evaluate(()=>document.getElementById('set-replay-intro').click());await page.waitForFunction(()=>CutsceneAudio.score?.playing);
 const replay=await page.evaluate(()=>({skippable:Cutscene.state.skippable,fresh:CutsceneAudio.score!==__oldScore,offset:CutsceneAudio.score.offset,elapsed:Cutscene.state.el}));
 check(replay.skippable&&replay.fresh&&replay.offset>=0&&replay.elapsed-replay.offset<3,`Settings replay follows its fresh scene clock: ${JSON.stringify(replay)}`);
 await page.keyboard.down('Space');await page.waitForTimeout(1200);await page.keyboard.up('Space');await page.waitForFunction(()=>!Cutscene.active);
 check(await page.evaluate(()=>!CutsceneAudio.score&&!CutsceneAudio.narrating),'Holding skip stops both score and narration');
 }else await page.evaluate(()=>Cutscene.reset());
 // Force a delayed download and cancel it while pending.
 await page.route('**/music_intro.mp3?late=1',async route=>{await page.waitForTimeout(500);await route.fulfill({path:'client/assets/music_intro.mp3',contentType:'audio/mpeg'});});
 const late=await page.evaluate(async()=>{
  const p=createCutsceneMusic(valhalla.ctx,'assets/music_intro.mp3?late=1',()=>0);p.setLevel(1,0);p.start();p.stop();for(let i=0;i<200&&!p.loaded;i++)await new Promise(r=>setTimeout(r,50));return{loaded:p.loaded,playing:p.playing,running:p.running};
 });
 check(late.loaded&&!late.playing&&!late.running,'A delayed score cannot start after cancellation');
 const seek=await page.evaluate(async()=>{
  const p=createCutsceneMusic(valhalla.ctx,'assets/music_intro.mp3',()=>61);p.setLevel(.3,0);p.start();
  for(let i=0;i<200&&!p.playing;i++)await new Promise(r=>setTimeout(r,50));
  const offset=p.offset;for(let i=0;i<100&&p.playing;i++)await new Promise(r=>setTimeout(r,50));const ended=!p.playing;p.stop();return{offset,ended};
 });
 check(seek.offset===61&&seek.ended,'A late start seeks correctly and the score ends without looping');
 check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
 fs.writeFileSync(path.join(world.runDir,'intro-music.json'),JSON.stringify({checks,late,seek,errors},null,2)+'\n');console.log(JSON.stringify({checks,runDir:world.runDir}));
}finally{await browser?.close();await world.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
