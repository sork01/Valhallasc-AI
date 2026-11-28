// A damage skill with nothing selected picks the nearest monster and the server keeps swinging at it; Settings shows the frame rate.
// MUTATE=1 removes the target pick from the served field.js and must fail.
const { run, replace, debug, record, sleep } = require('./lib/touch.cjs');
const suite = {
  name: 'skill-autotarget',
  mutate: page => replace(page, 'field.js', 'if (dealsDamage(def.effect)) acquireTarget(); ', ''),
  async test({ player, check, width, height }) {
    const phone = width < 900;
    let serverTime = 0, actor = null, shots = 0, skills = 0;
    const page = await player(phone ? 'PhonePick' : 'DeskPick', {
      characterClass: 'warrior', ...(phone ? {} : { isMobile: false, hasTouch: false }),
      onPacket(packet) {
        if (packet.type === 'snapshot') serverTime = packet.time;
        if (packet.type !== 'event' || packet.actor !== actor) return;
        if (packet.skill) skills++; else if (packet.kind === 'swing') shots++;
      },
    });
    actor = await page.evaluate(() => Online.id);
    await debug(page, { op: 'set_level', level: 99 });
    await debug(page, { op: 'teleport', zone: 0, x: 250, y: 235 });
    await page.waitForFunction(() => Field.hero.level === 99 && Math.hypot(Field.hero.nx - 250, Field.hero.ny - 235) < 1);
    const nearby = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - 250, s.y - 235) < 20).map(s => s.id));
    for (const id of nearby) await debug(page, { op: 'kill_enemy', id });
    await page.waitForFunction(ids => ids.every(id => Field.slimes.find(s => s.id === id)?.dead), nearby);
    await debug(page, { op: 'spawn_enemy', kind: 'cf_brute', level: 99, x: 255, y: 235 });
    await debug(page, { op: 'spawn_enemy', kind: 'cf_crawler', level: 99, x: 259, y: 235 });
    await page.waitForFunction(() => Field.slimes.filter(s => !s.dead && ['cf_brute', 'cf_crawler'].includes(s.kind)).length === 2);
    await page.evaluate(() => { Field.clearInput(); Online.send({ type: 'stop' }); });
    await page.waitForFunction(() => Field.canAct && !(Field.hero.skillCd?.cleave > 0));
    const expected = await page.evaluate(() => Field.slimes.filter(s => !s.dead && ['cf_brute', 'cf_crawler'].includes(s.kind))
      .sort((a, b) => Math.hypot(a.nx - Field.hero.nx, a.ny - Field.hero.ny) - Math.hypot(b.nx - Field.hero.nx, b.ny - Field.hero.ny))[0].id);
    await record(page);
    check(await page.evaluate(() => !Field.hero.target), 'nothing is selected before the skill');
    const began = serverTime;
    if (phone) await page.evaluate(() => Field.useSkill('cleave'));
    else await page.locator('#skillbar-slots [data-skill="cleave"]').click();
    check(await page.evaluate(id => Field.hero.target?.id === id, expected), 'the skill selects the closest monster');
    check(await page.evaluate(id => { const at = touchSent.findIndex(p => p.type === 'target' && p.id === id), cast = touchSent.findIndex(p => p.type === 'skill' && p.id === 'cleave'); return at >= 0 && cast > at; }, expected), 'the target is sent before the skill');
    const deadline = Date.now() + 25000;
    while ((shots < 2 || serverTime < began + 3) && Date.now() < deadline) await sleep(100);
    check(skills >= 1, `the skill was performed (${skills})`);
    check(shots >= 2, `autoattack follows with repeated basic attacks (${shots})`);
    const end = await page.evaluate(id => { const foe = Field.slimes.find(s => s.id === id); return { target: Field.hero.target?.id, id, hero: [Field.hero.nx, Field.hero.ny], foe: [foe?.nx, foe?.ny], dead: foe?.dead, heroDead: Field.hero.dead }; }, expected);
    // The monster walks too, so how far the hero went depends on timing: what matters is that they met and the selection held.
    check(end.target === expected && Math.hypot(end.hero[0] - end.foe[0], end.hero[1] - end.foe[1]) < 3.5, `the hero closed in on the selected monster and kept it (${JSON.stringify(end)})`);

    // Settings > Video > Show FPS.
    check(await page.evaluate(() => document.querySelector('#fps-counter').getBoundingClientRect().width === 0 && !Prefs.showFps), 'the counter is off by default');
    await page.evaluate(() => Settings.show());
    await page.locator('#set-tab-video').click(); await page.locator('#set-show-fps').check();
    await page.waitForFunction(() => /^\d+$/.test(document.querySelector('#fps-counter output').textContent), null, { timeout: 15000 });
    await page.locator('#set-back').click(); await page.evaluate(() => { document.querySelector('#pause').hidden = true; Field.setPaused(false); });
    const box = await page.evaluate(() => {
      const r = el => el.getBoundingClientRect(), counter = document.querySelector('#fps-counter'), fps = r(counter), map = r(document.querySelector('#minimap'));
      const covers = [...document.querySelectorAll('#stage button')].filter(el => { const b = r(el); return b.width && b.height && b.left < fps.right && b.right > fps.left && b.top < fps.bottom && b.bottom > fps.top; }).map(el => el.id || el.className);
      return { text: counter.textContent, width: fps.width, inside: fps.left >= map.left && fps.right <= map.right + .5 && fps.top >= map.top && fps.bottom <= map.bottom + .5, covers };
    });
    check(/^FPS \d+$/.test(box.text) && +box.text.slice(4) > 0, `the counter reads a frame rate (${box.text})`);
    check(box.width > 0 && box.inside && box.covers.length === 0, `the counter sits in the minimap corner, clear of every button (${JSON.stringify(box)})`);
    await page.screenshot({ path: `test-results/touch/fps-${width}x${height}.png` });
    await page.evaluate(() => Settings.show()); await page.locator('#set-tab-video').click();
    check(await page.evaluate(() => JSON.parse(localStorage.getItem('valhallasc.save.v1')).showFps === true), 'the choice is saved');
    await page.locator('#set-show-fps').uncheck();
    await page.waitForFunction(() => document.querySelector('#fps-counter').getBoundingClientRect().width === 0);
    check(true, 'unchecking hides the counter');
    console.log(`${width}x${height}: ${skills} skill, ${shots} basic attacks, ${box.text}`);
    await page.context().close();
  },
};
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
module.exports = suite;
