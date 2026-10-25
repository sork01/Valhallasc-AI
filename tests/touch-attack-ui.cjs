const { run, replace, debug, record, touch } = require('./lib/touch.cjs');
const suite = {
  name: 'touch-attack',
  mutate: page => replace(page, 'touch.js', 'Field.startNearestAutoattack()', "Field.action('attack')"),
  async test({ player, check, sleep, width, height }) {
    let serverTime = 0, actor = null, tracking = false, shots = 0, impacts = 0;
    const page = await player('PhoneAttack', {
      characterClass: 'warrior',
      onPacket(packet) {
        if (packet.type === 'snapshot') serverTime = packet.time;
        if (!tracking || packet.type !== 'event' || packet.actor !== actor || packet.skill) return;
        if (['swing', 'cast'].includes(packet.kind)) shots++;
        if (['hit', 'miss'].includes(packet.kind)) impacts++;
      },
    });
    actor = await page.evaluate(() => Online.id);
    await debug(page, { op: 'set_level', level: 99 });
    await debug(page, { op: 'teleport', zone: 0, x: 80, y: 25 });
    await page.waitForFunction(() => Field.hero.level === 99 && Math.hypot(Field.hero.nx - 80, Field.hero.ny - 25) < 1);
    // Stage a short control check on open ground, using durable monsters and test shortcuts.
    const nearby = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - 80, s.y - 25) < 15).map(s => s.id));
    for (const id of nearby) await debug(page, { op: 'kill_enemy', id });
    await page.waitForFunction(ids => ids.every(id => Field.slimes.find(s => s.id === id)?.dead), nearby);
    await debug(page, { op: 'spawn_enemy', kind: 'green', level: 1, x: 80.5, y: 25 });
    await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'green' && !s.dead && Math.hypot(s.nx - 80.5, s.ny - 25) < 2));
    const corpse = await page.evaluate(() => Field.slimes.find(s => s.kind === 'green' && !s.dead && Math.hypot(s.nx - 80.5, s.ny - 25) < 2).id);
    await debug(page, { op: 'kill_enemy', id: corpse });
    await page.waitForFunction(id => Field.slimes.find(s => s.id === id)?.dead, corpse);
    await debug(page, { op: 'spawn_enemy', kind: 'cf_crawler', level: 99, x: 88, y: 25 });
    await debug(page, { op: 'spawn_enemy', kind: 'cf_brute', level: 99, x: 84, y: 25 });
    await page.waitForFunction(() => Field.slimes.filter(s => !s.dead && ['cf_brute', 'cf_crawler'].includes(s.kind)).length === 2);
    const expected = await page.evaluate(() => Field.slimes.filter(s => !s.dead && ['cf_brute', 'cf_crawler'].includes(s.kind))
      .sort((a, b) => Math.hypot(a.nx - Field.hero.nx, a.ny - Field.hero.ny) - Math.hypot(b.nx - Field.hero.nx, b.ny - Field.hero.ny))[0].id);
    await record(page);
    const send = await touch(page), stick = await page.locator('#touch-stick').boundingBox(), button = await page.locator('#touch-skills .touch-attack').boundingBox();
    const x = stick.x + stick.width / 2, y = stick.y + stick.height / 2, ax = button.x + button.width / 2, ay = button.y + button.height / 2;
    await send('touchStart', [[1, x, y]]); await send('touchMove', [[1, x + 30, y]]); await sleep(100);
    tracking = true; const began = serverTime;
    await send('touchStart', [[1, x + 30, y], [2, ax, ay]]); await send('touchEnd', [[2, ax, ay]]);
    check(await page.evaluate(id => Field.hero.target?.id === id, expected), 'Attack selects the closest living monster, ignoring the nearer corpse');
    check(await page.evaluate(id => touchSent.some(p => p.type === 'target' && p.id === id), expected), 'Attack sends the existing authoritative target action');
    check(await page.evaluate(() => !document.querySelector('#touch-stick').classList.contains('held')), 'autoattack releases held movement so it cannot cancel the target');
    await send('touchEnd', []);
    const deadline = Date.now() + 15000;
    while (serverTime < began + 2.5 && Date.now() < deadline) await sleep(100);
    check(serverTime >= began + 2.5, 'the private server advanced through the observation window');
    check(shots >= 2, `one tap starts repeated server-authored basic attacks (${shots})`);
    check(impacts >= 1, `an attack reaches a monster (${impacts} hit/miss events)`);
    check(await page.evaluate(id => Field.hero.target?.id === id, expected), 'autoattack keeps its selected monster after all fingers lift');
    await page.waitForFunction(() => Field.hero.atkCd > 0);
    check(await page.locator('#touch-skills .touch-attack').isEnabled(), 'the target action is available during a basic-attack cooldown');
    tracking = false;
    await debug(page, { op: 'teleport', zone: 4, x: 104.2, y: 125.4 });
    await page.waitForFunction(() => Field.zone === 4 && Field.slimes.length === 0);
    await page.evaluate(() => { touchSent.length = 0; });
    await page.locator('#touch-skills .touch-attack').tap();
    check(await page.evaluate(() => !touchSent.some(p => ['target', 'attack', 'pvp'].includes(p.type))), 'no monsters means no target, NPC or player is attacked');
    await page.context().close();
    const mouse = await player('MouseAttack', { isMobile: false, hasTouch: false }); await record(mouse);
    await mouse.keyboard.press('Space');
    check(await mouse.evaluate(() => touchSent.some(p => p.type === 'attack') && !touchSent.some(p => p.type === 'target')), 'the desktop Attack key keeps its existing behavior');
    await mouse.context().close();
    console.log(`${width}x${height}: ${shots} basic attacks, ${impacts} impacts after one touch`);
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
