// Real Chromium audio graph: the analyser sits on the speaker bus, with music and weather muted.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name:'valhallasc-combat-sound', version:'1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments:args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  const env = { ...process.env, ...getDefaultEnvironment(), ...(process.env.VALHALLA_BINARY ? { VALHALLA_BINARY:process.env.VALHALLA_BINARY } : {}) };
  await client.connect(new StdioClientTransport({ command:process.execPath, args:[path.join(root,'scripts/test-mcp.cjs')], cwd:root, stderr:'pipe', env }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless:true, args:['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport:{width:1440,height:900} });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang:'en',sound:true,combatSounds:'synthesized',musicVol:0,sfxVol:1,weatherAudio:0,char:null,draft:null }));
    const tap = window.__tap = { peak:0, voices:[] }, create = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function () { const o = create.call(this); tap.voices.push(o); return o; };
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Soundcheck'); await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(() => Online.connected && !!window.__combatAudioTest, null, {timeout:60000});
  await page.evaluate(() => {
    __combatAudioTest.play('combatSwing',{className:'warrior',own:true,x:Field.hero.x,y:Field.hero.y});
    const bus = __combatAudioTest.bus(), analyser = bus.context.createAnalyser(); analyser.fftSize = 2048;
    bus.connect(analyser); const data = new Float32Array(2048);
    setInterval(() => { analyser.getFloatTimeDomainData(data); for (const sample of data) __tap.peak = Math.max(__tap.peak,Math.abs(sample)); },10);
  });
  // The live world can add unrelated combat effects to the same bus. Keep the real browser
  // audio graph running, but disconnect its game socket before measuring isolated cues.
  await page.evaluate(() => Field.stop());
  await page.waitForTimeout(700);
  const play = async (name,data) => {
    await page.evaluate(([n,d]) => { __tap.peak = 0; __combatAudioTest.play(n,{ x:Field.hero.x, y:Field.hero.y, ...d }); },[name,data]);
    await page.waitForTimeout(560);
    return page.evaluate(() => ({ peak:__tap.peak, voices:__tap.voices.length, last:__tap.voices.at(-1)?.frequency.value, active:__combatAudioTest.active() }));
  };
  const swing = [];
  const eventPath = await page.evaluate(() => {
    const before = __tap.voices.length;
    Field._debug.event({kind:'swing',actor:Online.id,x:Field.hero.x,y:Field.hero.y});
    return __tap.voices.length > before;
  });
  check(eventPath, 'A server swing event reaches the weapon sound');
  await page.waitForTimeout(180);
  for (const className of ['warrior','priest','assassin','mage','hunter']) {
    const heard = await play('combatSwing',{className,own:true});
    check(heard.peak > .005 && heard.peak < .95, `${className} swing is audible and below clipping (${heard.peak})`);
    swing.push(heard.last);
  }
  check(new Set(swing.map(n => Math.round(n / 10))).size === 5, 'Five weapon families have different pitch paths');
  const spell = await play('skill',{skill:'twinbolt'});
  check(spell.peak > .005 && Math.abs(spell.last-swing[3]) > 20, 'A spell cast differs from a staff swing');
  const own = await play('combatSwing',{className:'warrior',own:true});
  const remote = await play('combatSwing',{className:'warrior',own:false});
  check(remote.peak < own.peak * .7, `Other players are quieter (${remote.peak} vs ${own.peak})`);
  const far = await play('combatSwing',{className:'warrior',own:false,x:10000,y:10000});
  check(far.peak < .01, 'A distant swing is silent');
  const familyPitch = [];
  for (const kind of ['beetle','wraith','golem','rootlurker','moray','acolyte','wolf']) {
    const attack = await play('enemyAttack',{kind});
    const death = await play('enemyDeath',{kind});
    check(attack.peak > .008 && death.peak > .008 && attack.peak < .95 && death.peak < .95, `${kind} family attack and death are audible and below clipping (${attack.peak}, ${death.peak}; active ${attack.active}, ${death.active}; voices ${attack.voices}, ${death.voices})`);
    familyPitch.push(attack.last);
  }
  check(new Set(familyPitch.map(Math.round)).size === 7, 'Every enemy family has a different attack pitch');
  const unseen = await play('enemyAttack',{kind:'wolf',x:10000,y:10000});
  check(unseen.peak < .005, 'An enemy outside hearing range makes no sound');
  const miss = await play('miss',{}), hit = await play('hit',{});
  check(Math.abs(miss.last-hit.last) > 20, 'A miss has a different pitch from a hit');
  const boss = await play('enemyDeath',{kind:'hollowking',boss:true,finalBoss:true});
  check(boss.peak > .01 && boss.peak < .95, 'Dungeon final boss has a heavier death voice without clipping');
  await page.evaluate(() => { __tap.peak = 0; for(let i=0;i<20;i++) __combatAudioTest.play('enemyAttack',{kind:'wolf',x:Field.hero.x,y:Field.hero.y}); });
  await page.waitForTimeout(60);
  check(await page.evaluate(() => __combatAudioTest.active()) <= 4, 'Twenty simultaneous enemies use at most four voices');
  await page.waitForTimeout(500);
  check((await page.evaluate(() => __tap.peak)) < .95, 'The crowded mix does not clip');
  await page.evaluate(() => Prefs.set({sfxVol:0}));
  const muted = await play('enemyAttack',{kind:'wolf'});
  check(muted.peak < .01, 'Effects volume zero mutes combat');
  check(errors.length === 0, `No page errors: ${errors.join('; ')}`);
  console.log(`${checks} combat sound checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
