const fs = require('node:fs');
const { run, replace, debug, safeSpot } = require('./lib/touch.cjs');
const catalog = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, '../world/achievements.txt'), 'utf8'));
const milestone = catalog.find(a => a.id === 'level_50');
const exploration = catalog.filter(a => a.category === 'Exploration');
const gameSource = fs.readFileSync(require('node:path').join(__dirname, '../client/game.js'), 'utf8');
const soundSource = gameSource.match(/function achievementSound\(\) \{[\s\S]*?\n  \}/)[0];
const busSource = gameSource.match(/function sfxOut\(c\) \{[\s\S]*?\n  \}/)[0];
// Compile the unchanged production functions in Node, then send a function to Playwright.
// The page's production CSP remains enabled; no browser eval or inline script is needed.
const measureAudio = new Function(`return async () => {
  let offline, save, sfxGain = null;
  const taper = v => v * v, audio = () => offline;
  ${busSource}
  ${soundSource}
  const results = [];
  for (const [sound, sfxVol] of [[true, 1], [true, .5], [false, 1]]) {
    offline = new OfflineAudioContext(1, 96000, 48000); save = { sound, sfxVol }; sfxGain = null;
    let voices = 0;
    const createOscillator = offline.createOscillator.bind(offline);
    offline.createOscillator = () => { voices++; return createOscillator(); };
    achievementSound(); const buffer = await offline.startRendering();
    const samples = buffer.getChannelData(0); let peak = 0, square = 0;
    for (const sample of samples) { peak = Math.max(peak, Math.abs(sample)); square += sample * sample; }
    results.push({ peak, rms: Math.sqrt(square / samples.length), voices });
  }
  return results;
}`)();
const suite = {
  name: 'achievement-effects',
  mutate: page => replace(page, 'online.js', 'window.Achievements?.onNotice(packet);', ''),
  async test({ player, check, width, height, out, sleep }) {
    const notices = [];
    const page = await player('Laureate', { onPacket: p => { if (p.type === 'notice' && p.text?.startsWith('Achievement earned:')) notices.push(p); } });
    await safeSpot(page);
    check(await page.locator('#achievement-toast').isHidden(), 'joining with existing milestones does not replay old achievements');
    await debug(page, { op: 'set_level', level: 50 });
    await page.waitForSelector('#levelup-banner:not([hidden])');
    check(await page.locator('#achievement-toast').isHidden(), 'achievement celebration waits while the level-up banner is visible');
    await page.waitForSelector('#achievement-toast:not([hidden])', { timeout: 12000 });
    check(await page.locator('#levelup-banner').isHidden(), 'level-up has finished before the achievement celebration begins');
    check(await page.locator('#achievement-toast-name').textContent() === milestone.name, 'real server notice displays the earned achievement name');
    check(await page.locator('#achievement-toast-points').textContent() === `+${milestone.points} points`, 'celebration shows authoritative awarded points');
    check(await page.locator('#achievement-toast-heading').textContent() === 'Achievement unlocked', 'single achievement announcement');
    check(await page.locator('#achievement-toast').evaluate(n => getComputedStyle(n).pointerEvents === 'none'), 'celebration never captures gameplay input');
    check(await page.locator('#achievement-toast').evaluate(n => getComputedStyle(n).animationName === 'none'), 'reduced-motion celebration is still');
    const box = await page.locator('#achievement-toast').boundingBox(), stage = await page.locator('#stage').boundingBox();
    check(box.x >= stage.x && box.y >= stage.y && box.x + box.width <= stage.x + stage.width && box.y + box.height <= stage.y + stage.height, 'ribbon fits within the phone or tablet stage');
    await page.screenshot({ path: `${out}/achievement-celebration-${width}x${height}.png` });
    await page.keyboard.press('e'); check(await page.locator('#equipment').isVisible(), 'game shortcuts remain available during the celebration');
    await page.keyboard.press('e');
    await page.waitForSelector('#achievement-toast[hidden]', { state: 'attached', timeout: 7000 });
    await page.evaluate(packet => Achievements.onNotice(packet), notices[0]); await sleep(350);
    check(await page.locator('#achievement-toast').isHidden(), 'a repeated award notice does not replay the celebration');
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await debug(page, { op: 'explore_all' });
    await page.waitForSelector('#achievement-toast:not([hidden])', { timeout: 10000 });
    check(await page.locator('#achievement-toast-heading').textContent() === 'Achievements unlocked', 'simultaneous exploration awards share a celebration');
    check(await page.locator('#achievement-toast-extra').textContent() === `+${exploration.length - 2} more achievements`, 'large batches keep the ribbon compact');
    check(await page.locator('#achievement-toast-points').textContent() === `+${exploration.reduce((s,a) => s + a.points,0)} points`, 'batch points are summed once');
    check(await page.locator('#achievement-toast').evaluate(n => getComputedStyle(n).animationName.includes('achievement-arrive')), 'normal motion unfolds the achievement ribbon');
    check(await page.locator('.achievement-burst i').count() === 6, 'diamond celebration uses a fixed six motes');
    await sleep(650); await page.screenshot({ path: `${out}/achievement-burst-${width}x${height}.png` });
    await page.evaluate(() => Achievements.reset());
    await sleep(500); check(await page.locator('#achievement-toast').isHidden(), 'reset clears visible and queued celebrations');
    // Render the actual cue and effects-bus functions in a native offline graph.
    // Keep the game's live weather/music timers outside this isolated audio measurement.
    const audio = await page.evaluate(measureAudio);
    check(audio[0].voices === 12 && audio[0].rms > .015 && audio[0].peak < .95, `distinct bell cadence is audible without clipping (${JSON.stringify(audio[0])})`);
    check(Math.abs(audio[1].peak / audio[0].peak - .25) < .005, 'bell uses the shared effects slider and its squared taper');
    check(audio[2].voices === 0 && audio[2].peak === 0, 'Sound off silences the achievement cue');
    await page.context().close();
    const swedish = await player('Pristagare', { lang: 'sv' }); await safeSpot(swedish);
    await debug(swedish, { op: 'set_level', level: 50 });
    await swedish.waitForSelector('#achievement-toast:not([hidden])', { timeout: 12000 });
    check(await swedish.locator('#achievement-toast-heading').textContent() === 'Prestation upplåst', 'achievement announcement is translated into Swedish');
    check(await swedish.locator('#achievement-toast-name').textContent() === await swedish.evaluate(name => Locale.translate(name), milestone.name), 'Swedish achievement name is translated before display');
    check((await swedish.locator('#achievement-toast-points').textContent()).includes('poäng'), 'awarded points use Swedish text');
    await swedish.context().close();
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
