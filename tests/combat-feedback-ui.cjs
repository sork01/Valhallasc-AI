// New TODOs only: real-protocol elite selection, HUD geometry, recorded/synth sound routing and saved settings.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..'), out = path.join(root, 'test-results/combat-feedback');
const world = new TestWorld(); world.startLevel = 40; world.levelSpread = 0;
let browser, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
const debug = (page, command) => page.evaluate(command => Online.send({ type: 'debug', command }), command);
async function join(page, name) {
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
}
async function resume(page) {
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
}
async function select(page, kind) {
  console.log('Selecting '+kind);
  const spot = await page.evaluate(kind => { const enemy = Field.slimes.find(s => s.kind === kind && !s.dead); return {x:enemy.x-4,y:enemy.y}; }, kind);
  await debug(page, {op:'teleport',zone:0,...spot});
  await page.waitForFunction(p => Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<2,spot);
  // Selection is local input state; snapshots retain it by id. Use the same state/action
  // as the pointer handler so a moving enemy/camera cannot make the fixture click its neighbour.
  await page.evaluate(kind => {
    const enemy = Field.slimes.find(s => s.kind === kind && !s.dead && (kind==='big'||s.level===99));
    Field.hero.pvpTargetId=null; Field.hero.target=enemy;
    Online.send({type:'target',id:enemy.id});
  },kind);
  await page.waitForFunction(kind => Field.hero.target?.kind === kind && !document.querySelector('#hud-target').hidden && document.querySelector('#hud-target-name').textContent === Locale.translate(Field.hero.target.d.name), kind);
}
async function frameChecks(page, label) {
  await debug(page, { op: 'teleport', zone: 0, x: 80, y: 80 });
  await page.waitForFunction(() => Math.hypot(Field.hero.x - 80, Field.hero.y - 80) < 2);
  for (const [kind, x] of [['cinderlord', 84], ['green', 76]]) {
    await debug(page, { op: 'spawn_enemy', kind, level: 99, x, y: 84 });
    await page.waitForFunction(kind => Field.slimes.some(s => s.kind === kind && !s.dead && s.level === 99), kind);
  }
  await debug(page, {op:'summon_king'});
  await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'big' && !s.dead));
  for (const kind of ['cinderlord', 'green', 'big', 'green', 'cinderlord']) {
    await select(page, kind);
    const expected = kind !== 'green';
    check(await page.locator('.hud-elite-dragon').isVisible() === expected, `${label}: ${kind} has exactly the correct frame after selection changes`);
    if (!expected) continue;
    const geometry = await page.evaluate(() => {
      const box = selector => { const r = document.querySelector(selector).getBoundingClientRect(); return { x:r.x, y:r.y, right:r.right, bottom:r.bottom, width:r.width, height:r.height }; };
      const g = box('.hud-elite-dragon'), face = box('#hud-target-face'), text = box('.hud-target-bars'), stage = box('#stage');
      const image = document.querySelector('.hud-elite-dragon');
      return { g, face, text, stage, loaded: image.complete && image.naturalWidth > 0, hp: document.querySelector('#hud-target-text').textContent };
    });
    check(geometry.loaded, `${label}: the dragon vector loaded`);
    check(geometry.g.right <= geometry.text.x + 1, `${label}: dragon clears the name, level and health (${JSON.stringify(geometry)})`);
    check(geometry.g.x >= geometry.stage.x && geometry.g.y >= geometry.stage.y && geometry.g.bottom <= geometry.stage.bottom, `${label}: dragon fits within the stage`);
    check(geometry.g.width > geometry.face.width && /\d+ \/ \d+/.test(geometry.hp), `${label}: frame surrounds the portrait and health remains readable`);
  }
  await page.screenshot({ path: path.join(out, `${label}-elite.png`) });
  const widths = [];
  for (const scale of [.6, 1]) {
    await page.evaluate(scale => { Prefs.set({ uiScale: scale }); Settings.applyScale(); }, scale);
    widths.push((await page.locator('.hud-elite-dragon').boundingBox()).width);
  }
  check(Math.abs(widths[1] / widths[0] - 1 / .6) < .03, `${label}: dragon scales exactly once with the Character frame`);
  await page.keyboard.press('w');
  await page.waitForFunction(() => document.querySelector('#hud-target').hidden);
  check(await page.locator('.hud-elite-dragon').isHidden(), `${label}: clearing the target hides the frame`);
}
async function audioChecks(page) {
  await page.waitForFunction(() => RecordedCombat.ready, null, { timeout: 30000 });
  check(await page.evaluate(() => Prefs.combatSounds) === 'recorded', 'Legacy preferences without a mode default to recorded sounds');
  if (process.env.MUTATE !== 'audio') {
  // One actual server attack verifies the new enemy-hurt path, without grinding an encounter.
  await page.evaluate(() => {
    window.__heard = []; const play = RecordedCombat.play;
    RecordedCombat.play = function (...args) { __heard.push([args[2], args[3]]); return play(...args); };
  });
  await debug(page, {op:'teleport', zone:0, x:80, y:80});
  await page.waitForFunction(() => Math.hypot(Field.hero.x-80,Field.hero.y-80)<.2);
  await debug(page, {op:'spawn_enemy', kind:'green', level:99, x:81.2, y:80});
  await page.waitForFunction(() => Field.slimes.some(s=>s.kind==='green'&&!s.dead&&Math.hypot(s.x-Field.hero.x,s.y-Field.hero.y)<1.8));
  await debug(page, {op:'reset_cooldowns'});
  await page.evaluate(() => { const e = Field.slimes.find(s => s.kind === 'green' && !s.dead && s.level===99); Online.send({type:'attack', fx:e.x-Field.hero.x, fy:e.y-Field.hero.y}); });
  try { await page.waitForFunction(() => __heard.some(([,stage]) => stage === 'hurt'), null, { timeout: 10000 }); }
  catch (e) { console.log(await page.evaluate(() => ({heard:__heard,hero:{x:Field.hero.x,y:Field.hero.y},enemies:Field.slimes.filter(s=>Math.hypot(s.x-Field.hero.x,s.y-Field.hero.y)<4).map(s=>({kind:s.kind,hp:s.hp,x:s.x,y:s.y}))}))); throw e; }
  check(await page.evaluate(() => __heard.some(([,stage]) => stage === 'hurt')), 'A real authoritative hit reaches the recorded enemy hurt path');
  }
  await page.evaluate(() => {
    Field.stop(); RecordedCombat.stop();
    __combatAudioTest.play('hit');
    const bus = __combatAudioTest.bus(), analyser = bus.context.createAnalyser(); analyser.fftSize = 2048; bus.connect(analyser);
    const data = new Float32Array(2048); window.__peak = 0;
    setInterval(() => { analyser.getFloatTimeDomainData(data); for (const v of data) __peak = Math.max(__peak, Math.abs(v)); }, 5);
  });
  await page.waitForTimeout(1600);
  const play = async (name, data = {}, delay = 650) => {
    const before = await page.evaluate(() => ({ osc:__audio.osc, samples:__audio.samples }));
    await page.evaluate(([name,data]) => { __peak = 0; __combatAudioTest.play(name, {x:Field.hero.x, y:Field.hero.y, ...data}); }, [name, data]);
    await page.waitForTimeout(delay);
    return page.evaluate(before => ({ peak:__peak, osc:__audio.osc-before.osc, samples:__audio.samples-before.samples }), before);
  };
  for (const className of ['warrior','priest','assassin','mage','hunter']) {
    const r = await play('combatSwing', {className,own:true}, 1500);
    check(r.samples > 0 && r.osc === 0 && r.peak > .004 && r.peak < .95, `${className}: real weapon recording is audible without a synthesized replacement (${JSON.stringify(r)})`);
  }
  for (const kind of ['wolf','beetle','wraith','golem','rootlurker','moray','acolyte']) {
    for (const event of ['enemyAttack','enemyHurt','enemyDeath']) {
      const r = await play(event, {kind}, 1700);
      check(r.samples > 0 && r.osc === 0 && r.peak > .003 && r.peak < .95, `${kind} ${event}: real recording, audible and below clipping (${JSON.stringify(r)})`);
    }
  }
  for (const event of ['hit','crit','hurt','death','miss']) {
    const r = await play(event, {}, 1600);
    check(r.samples > 0 && r.osc === 0 && r.peak > .004 && r.peak < .95, `${event}: recorded impact or human performance is audible (${JSON.stringify(r)})`);
  }
  const far = await play('enemyAttack', {kind:'wolf', x:10000, y:10000});
  check(far.samples === 0 && far.peak < .001, 'Distant enemies remain silent in recorded mode');
  const crowd = await page.evaluate(() => {
    const before = __audio.samples; for (let i=0;i<20;i++) __combatAudioTest.play('enemyAttack', {kind:'wolf',x:Field.hero.x,y:Field.hero.y});
    return {count:__audio.samples-before,active:__combatAudioTest.active()};
  });
  check(crowd.count <= 4 && crowd.active <= 4, 'Twenty recorded enemy attacks retain the four-voice crowd ceiling');
  await page.waitForTimeout(1600);
  await page.evaluate(() => Prefs.set({sfxVol:0}));
  check((await play('hit')).peak < .001, 'Effects volume zero mutes recorded effects');
  await page.evaluate(() => Prefs.set({sfxVol:.5}));
  const low = await play('hit');
  await page.evaluate(() => Prefs.set({sfxVol:1}));
  const full = await play('hit');
  check(low.peak > .001 && low.peak / full.peak > .18 && low.peak / full.peak < .32, 'Recorded effects use the existing squared volume taper');
  await page.evaluate(() => { __combatAudioTest.play('death'); Prefs.set({sound:false}); });
  await page.waitForTimeout(100); await page.evaluate(() => { __peak=0; }); await page.waitForTimeout(200);
  check(await page.evaluate(() => __peak) < .001, 'Muting stops an already-playing recording');
  check((await play('hit')).samples === 0, 'Muted combat starts no new recording');
  await page.evaluate(() => { Prefs.set({sound:true}); Settings.show(); });
  await page.locator('#set-combat-sounds').selectOption('synthesized');
  await page.waitForTimeout(700);
  const synth = await play('enemyAttack', {kind:'wolf'});
  check(synth.osc > 0 && synth.samples === 0 && synth.peak > .004, 'Settings switches back to the original synthesized enemy sound');
  await page.reload(); await page.waitForFunction(() => !!window.Prefs);
  check(await page.evaluate(() => Prefs.combatSounds) === 'synthesized', 'Synthesized preference survives reload');
  await resume(page);
  await page.evaluate(() => Settings.show());
  check(await page.locator('#set-combat-sounds').inputValue() === 'synthesized', 'Settings reflects the saved synthesized preference');
  await page.locator('#set-combat-sounds').selectOption('recorded');
  await page.reload(); await page.waitForFunction(() => !!window.Prefs);
  check(await page.evaluate(() => Prefs.combatSounds) === 'recorded', 'Recorded preference survives reload');
  // An unavailable file must not silence combat or trigger delayed effects.
  await page.route('**/assets/combat/impact.mp3', r => r.abort());
  await page.reload(); await page.waitForFunction(() => !!window.Prefs);
  await resume(page);
  await page.evaluate(() => { Settings.show(); Prefs.set({sound:true}); });
  await page.waitForTimeout(500);
  const fallback = await page.evaluate(() => { const before = __audio.osc; Prefs.preview(); return __audio.osc > before; });
  check(fallback, 'A failed recording falls back immediately to the original synthesized effect');
}
(async () => {
  requireMemoryLimit(); fs.mkdirSync(out, {recursive:true});
  const sources = JSON.parse(fs.readFileSync(path.join(root,'client/assets/combat/sources.txt')));
  for (const clip of Object.values(sources.clips)) check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'client/assets/combat',clip.file))).digest('hex') === clip.sha256, `${clip.file}: shipped bytes match the source manifest`);
  await world.start();
  for (const [width,height,touch,lang] of [[1440,900,false,'en'],[844,390,true,'en'],[1024,768,true,'sv']]) {
    const label = `${width}x${height}-${lang}`; console.log(label);
    browser = await chromium.launch({headless:true,args:['--autoplay-policy=no-user-gesture-required']});
    const context = await browser.newContext({viewport:{width,height},hasTouch:touch,isMobile:touch,deviceScaleFactor:1,reducedMotion:'reduce'});
    const page = await context.newPage(), errors=[]; page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(({lang,touch}) => {
      if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang,sound:!touch,musicVol:0,sfxVol:1,weatherAudio:0}));
      if (touch) { window.AudioContext=undefined; window.webkitAudioContext=undefined; return; }
      window.__audio={osc:0,samples:0};
      const osc=AudioContext.prototype.createOscillator, source=AudioContext.prototype.createBufferSource;
      AudioContext.prototype.createOscillator=function(){ __audio.osc++; return osc.call(this); };
      AudioContext.prototype.createBufferSource=function(){ const s=source.call(this),start=s.start; s.start=function(...args){ if (!s.loop) __audio.samples++; return start.apply(this,args); }; return s; };
    }, {lang,touch});
    if (process.env.MUTATE) {
      let source=fs.readFileSync(path.join(root,'client/game.js'),'utf8');
      if (process.env.MUTATE === 'frame') source=source.replace("!!target && !target.player && !!target.elite", 'false');
      if (process.env.MUTATE === 'audio') source=source.replace("if (recordedVoice(family, stage, level, enemy, finalBoss, heavy)) return;", '');
      await page.route('**/game.js', r => r.fulfill({contentType:'text/javascript',body:source}));
    }
    await join(page, 'Feedback'+width);
    await frameChecks(page,label);
    await page.evaluate(() => Settings.show());
    check(await page.locator('#set-combat-sounds').isVisible(), `${label}: combat sound selector is reachable`);
    if (lang === 'sv') {
      check(await page.locator('label[for="set-combat-sounds"] span').textContent() === 'Stridsljud', 'Swedish combat sound label');
      check((await page.locator('#set-combat-sounds option').allTextContents()).join('|') === 'Inspelade|Syntetiska', 'Both sound modes have Swedish labels');
    }
    await page.waitForTimeout(100);
    const bounds = await page.locator('#set-combat-sounds').boundingBox();
    check(bounds.x >= 0 && bounds.x+bounds.width <= width && bounds.y >= 0 && bounds.y+bounds.height <= height, `${label}: selector fits the screen`);
    if (touch) check(bounds.height>=43.5 && bounds.width>=43.5, `${label}: selector keeps a 44 px physical touch target`);
    const panel = await page.locator('.settings-panel').first().boundingBox();
    check(panel.x >= 0 && panel.y >= 0 && panel.x+panel.width <= width && panel.y+panel.height <= height, `${label}: the Settings panel fits after adding the new row (${JSON.stringify(panel)})`);
    await page.screenshot({path:path.join(out,`${label}-settings.png`)});
    await page.evaluate(() => Settings.close(false));
    if (!touch) await audioChecks(page);
    check(errors.length === 0, `${label}: no page errors (${errors.join('; ')})`);
    await browser.close(); browser=null;
  }
  console.log(`${checks} combat feedback checks passed`);
})().catch(e=>{ console.error(e); process.exitCode=1; }).finally(async()=>{
  if (browser) await browser.close(); await world.stop();
  try { const cgroup=fs.readFileSync('/proc/self/cgroup','utf8').trim().split('::')[1]; console.log('Memory peak: '+Math.round(+fs.readFileSync('/sys/fs/cgroup'+cgroup+'/memory.peak','utf8')/1048576)+' MiB'); } catch (_) {}
});
