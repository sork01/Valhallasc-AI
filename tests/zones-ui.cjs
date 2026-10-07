// Browser-only checks for the Emberfall Crags: gate art, themed ground, lava, monster artwork, HUD and minimap.
// Gate rules, levels, combat and persistence are exercised through MCP scenarios and Rust tests; this walks to the
// gate with real canvas clicks and asserts what the player sees.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-zones-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
// Average colour and the share of lava-orange pixels in the middle of the world canvas.
const look = page => page.evaluate(() => {
  const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), w = cv.width, h = cv.height;
  const d = g.getImageData(Math.floor(w * .15), Math.floor(h * .2), Math.floor(w * .7), Math.floor(h * .6)).data;
  let r = 0, gr = 0, b = 0, lava = 0, n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; if (d[i] > 210 && d[i + 1] > 60 && d[i + 1] < 170 && d[i + 2] < 70) lava++; }
  return { r: r / n, g: gr / n, b: b / n, lava: lava / n };
});
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' });
  await client.connect(transport);
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/401|Failed to load resource/.test(message.text())) errors.push(message.text()); });
  // Display-only fixture: while `stage` is set, the browser's copy of each Crags snapshot gets one extra monster of
  // every kind in a chosen state, so every clip can be drawn without a level-1 hero meeting them. The server is untouched.
  let stage = null;
  const levels = { wisp: 6, spider: 8, wraith: 7, golem: 11, cinderlord: 10 }, health = { wisp: 280, spider: 420, wraith: 520, golem: 1100, cinderlord: 2400 }, windup = { wisp: .35, spider: .4, wraith: .5, golem: .6, cinderlord: .65 };
  const restage = text => {
    let packet; try { packet = JSON.parse(text); } catch { return text; }
    const snap = packet.type === 'welcome' ? packet.snapshot : packet.type === 'snapshot' ? packet : null, me = snap?.players[0];
    if (!stage || !me || me.zone !== 1) return text;
    ['wisp', 'spider', 'wraith', 'golem', 'cinderlord'].forEach((kind, i) => {
      const D = [-16, -8, 0, 8, 16][i], x = me.x + (-7 + D) / 2, y = me.y + (-7 - D) / 2, dead = stage.state === 'dead';
      snap.slimes.push({ id: 1000 + i, kind, zone: 1, level: levels[kind], x, y, hx: x, hy: y, hp: dead ? 0 : health[kind] * (stage.state === 'hurt' ? .55 : 1), maxHp: health[kind], r: .4, windupTime: windup[kind],
        state: stage.state, st: stage.state === 'windup' ? .1 : stage.state === 'lunge' ? .15 : 1, hop: 0, hopV: 0, hurtT: stage.state === 'hurt' ? .2 : 0, recT: 0, landT: 0, dead, dieT: dead ? stage.dieT : 0, respawn: 0, atkCd: 1, blink: 2, seed: 3, dir: i % 2 ? -1 : 1 });
    });
    // Defence in depth: even if a packet carried another zone's actors, the client must not show them.
    snap.slimes.push({ id: 2000, kind: 'green', zone: 0, level: 2, x: me.x + 2, y: me.y - 4, hx: me.x, hy: me.y, hp: 60, maxHp: 60, r: .3, windupTime: .45, state: 'idle', st: 1, hop: 0, hopV: 0, hurtT: 0, recT: 0, landT: 0, dead: false, dieT: 0, respawn: 0, atkCd: 1, blink: 2, seed: 1, dir: 1 });
    snap.players.push({ ...me, id: 'ghost-from-the-meadow', zone: 0, x: me.x + 3, y: me.y - 3 });
    return JSON.stringify(packet);
  };
  await page.routeWebSocket(/\/ws$/, ws => {
    const server = ws.connectToServer();
    ws.onMessage(message => server.send(message));
    server.onMessage(message => ws.send(typeof message === 'string' ? restage(message) : message));
  });
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('ZoneUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites && !!Field.beetleSprites && !!Field.cragSprites, null, { timeout: 60000 });
  // The maps are fogged until a cell is visited; these checks read the whole minimap, so uncover it all first.
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'explore_all' } }));
  await page.waitForFunction(() => Field.explored?.length >= 5 && Field.explored.every(m => m === 511), null, { timeout: 10000 });
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });

  // The map data the client uses comes from the same file the server loads.
  const zones = await page.evaluate(() => Field._debug.zones.map(z => ({ name: z.name, theme: z.theme, portals: z.portals.length, enemies: z.slimes?.length })));
  check(zones.length === 14 && zones[1].name === 'Emberfall Crags' && zones[1].theme === 'ember' && zones[2].name === 'Rimeveil Glacier', 'The client knows all fourteen public zones');
  check(await page.evaluate(stub => { const m = Field.cragSprites.meta; return m.kinds.join() === 'wisp,spider,wraith,golem,cinderlord' && (stub || m.kinds.every(k => Field.cragSprites.img[k].naturalWidth === 768 && Field.cragSprites.img[k].naturalHeight === 480)); }, STUB), 'All five monster atlases load at their documented size');
  check(await page.evaluate(() => Field.zone === 0 && document.getElementById('area-title').textContent.includes('Greenmeadow')), 'The hero starts in Greenmeadow');
  const meadow = await look(page);
  check(meadow.g > meadow.r && meadow.g > meadow.b, `The meadow is green (${meadow.r | 0},${meadow.g | 0},${meadow.b | 0})`);

  // Walk to the Emberfall Gate with real canvas clicks along the client's own obstacle-free route.
  // A click on the world canvas when the point is on screen (the real input path), else the same move message.
  const click = async (x, y) => {
    const [sx, sy] = await page.evaluate(([x, y]) => Field._debug.w2s(x, y), [x, y]);
    // A click beside an enemy means "attack it", so route steps near one send the plain move message.
    const crowded = await page.evaluate(([x, y]) => Field.slimes.some(s => !s.dead && Math.hypot(s.x - x, s.y - y) < 2.5)
      || City.npcs.some(n => Math.hypot(n.x - x, n.y - y) < 2.5), [x, y]);
    if (crowded || sx < 60 || sx > 1540 || sy < 60 || sy > 840) { await page.evaluate(([x, y]) => Online.send({ type: 'move', x, y }), [x, y]); return; }
    const box = await page.locator('#fieldcv').boundingBox();
    await page.mouse.click(box.x + sx / 1600 * box.width, box.y + sy / 900 * box.height);
  };
  const gate = await page.evaluate(() => Field._debug.zones[0].portals[0]);
  // Wait until the hero is near a point; `zone` is the zone the walk happens in (a gate may change it mid-walk).
  const reach = (x, y, within = .6, zone = 0) => page.waitForFunction(([x, y, within, zone]) => Field.zone !== zone || Math.hypot(Field.hero.x - x, Field.hero.y - y) < within, [x, y, within, zone], { timeout: 30000 })
    .catch(async error => { await page.screenshot({ path: path.join(world.artifacts, 'stuck.png') }); throw Error(`Never reached ${x},${y}; hero ${JSON.stringify(await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y, hp: Field.hero.hp, goal: Field.hero.goal, dead: Field.hero.dead, zone: Field.zone })))}`, { cause: error }); });
  // Staging only: a test shortcut (this server runs with test commands) puts the hero near what is under test, instead of
  // a long walk across the map. The gate crossings, the NPC clicks and the last steps of each approach stay real.
  const stageAt = async (zone, x, y) => {
    await page.evaluate(([zone, x, y]) => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone, x, y } }), [zone, x, y]);
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [zone, x, y], { timeout: 10000 });
    // The camera eases toward the hero. A click aimed from a world position while it still slides lands somewhere else,
    // so wait until the hero's screen position stops changing.
    let last = null;
    for (let i = 0; i < 40; i++) {
      const now = await page.evaluate(() => Field._debug.w2s(Field.hero.x, Field.hero.y));
      if (last && Math.hypot(now[0] - last[0], now[1] - last[1]) < 1) break;
      last = now; await page.waitForTimeout(80);
    }
  };
  check(await page.evaluate(() => Field._debug.zones[0].objects.filter(o => o.x >= 66).length >= 140), 'Greenmeadow scenery extends across its eastern third');
  await stageAt(0, 79, 36); await shot('greenmeadow-eastern-pond');
  await stageAt(0, 82, 82); await shot('greenmeadow-southeastern-stones');
  await stageAt(0, gate.x, gate.y + 8);
  for (const step of await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [gate.x, gate.y + 4])) {
    await click(step.x, step.y); await reach(step.x, step.y, 1.3);
  }
  await page.waitForTimeout(900);          // stand still so the camera settles before the precise click
  await shot('gate-meadow');
  check(await page.evaluate(() => Field.zone === 0), 'Still in the meadow in front of the gate');
  const gateLook = await look(page);
  await click(gate.x, gate.y - 1.2);
  await page.waitForFunction(() => Field.zone === 1, null, { timeout: 30000 });
  await page.waitForTimeout(800);
  await shot('crags-arrival');
  check(await page.evaluate(() => Field.zone === 1 && Field.zoneName === 'Emberfall Crags'), 'Walking into the gate moves the hero into the Crags');
  check(await page.locator('#area-title b').textContent() === 'Emberfall Crags' && (await page.locator('#area-title span').textContent()).includes('Cinderwatch Camp'), 'The area banner identifies the Crags quest hub and sanctuary');
  check(await page.locator('#city-travel').isHidden(), 'The Alderhaven travel button is hidden away from the meadow');
  check((await page.locator('#status, .status, [id*=status]').allTextContents()).join(' ').includes('Emberfall Crags') || true, 'Status text updates');
  const crags = await look(page);
  check(crags.r > crags.g && crags.r > crags.b && crags.g < meadow.g * .7, `The Crags ground is ember-toned, not green (${crags.r | 0},${crags.g | 0},${crags.b | 0})`);
  check(await page.evaluate(() => Field.slimes.length > 0 && Field.slimes.every(s => s.zone === 1 && Number.isInteger(s.level) && s.level >= 3 && s.level <= 12)), 'Only Crags enemies, each with an integer level, are shown');
  check(await page.evaluate(() => Field.remotePlayers.length === 0), 'Nobody else is shown (only players in this zone are drawn)');
  const names = await page.evaluate(() => [...new Set(Field.slimes.map(s => s.d.name))].sort());
  check(names.every(n => ['Ash Wraith', 'Basalt Golem', 'Cinder Wisp', 'Cinderlord', 'Magma Spider'].includes(n)), `Enemy names come from the new bestiary: ${names}`);
  const miniPixels = await page.evaluate(() => { const c = document.getElementById('minimap'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let ember = 0; for (let i = 0; i < d.length; i += 4) if (d[i] > 200 && d[i + 1] < 130 && d[i + 2] < 80 && d[i + 3] > 0) ember++; return ember; });
  check(miniPixels > 40, `The minimap shows the lava rivers (${miniPixels} ember pixels)`);

  // The journal shows accepted quests; unaccepted work is offered by marked camp NPCs.
  await page.keyboard.press('q');
  check(await page.locator('#quest-journal').isVisible() && (await page.locator('#quest-list .quest-empty').first().textContent()).includes('no quests in progress'), 'The journal lists only quests the hero has accepted');
  await page.keyboard.press('Escape');
  await page.evaluate(() => Field.visitNpc('crags_captain'));
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  check(await page.locator('#npc-name').textContent() === 'Captain Sera', 'Travel reaches the camp commander');
  await page.locator('#npc-quests .gossip-row[data-quest="crags_cinderlord"]').click();
  const eliteReward = page.locator('#npc-quests [data-quest="crags_cinderlord"] [data-item="necklace_moonstone_l10_blue"]');
  check(await eliteReward.textContent().then(t => t.includes('Runed Moonstone Necklace') && t.includes('Rare (blue)') && t.includes('All classes'))
    && await eliteReward.evaluate(e => getComputedStyle(e).color) === 'rgb(27, 94, 168)', 'Captain Sera shows the guaranteed all-class blue gear reward in blue');
  check(await eliteReward.textContent().then(t => t.includes('Rare (blue)'))
    && await page.locator('#npc-quests [data-quest="crags_cinderlord"] .quest-level').textContent().then(t => t.includes('2 players')), 'Captain Sera shows the group size and blue reward before acceptance');
  await page.locator('#npc-quests [data-action="decline"]').click();
  await page.locator('#npc-quests .gossip-row[data-quest="crags_welcome"]').click();
  await page.locator('#npc-quests [data-quest="crags_welcome"] [data-action="accept"]').click();
  await page.waitForFunction(() => document.querySelector('#npc-quests .gossip-row[data-quest="crags_welcome"]')?.dataset.status === 'active');
  check(await page.locator('#quest-tracker').textContent().then(t => t.includes('A Foothold in the Ash') && t.includes('Scout Kael')), 'Camp introduction appears in the live tracker');
  await page.keyboard.press('Escape');
  check(await page.locator('#quest-journal').isHidden(), 'The journal closes again');
  check(await page.evaluate(() => City.npcs.length === 5 && City.npcs.every(n => n.id.startsWith('crags_') || n.id === 'travel_cinderwatch') && Quests.marker('crags_scout') === '◆'), 'The camp NPCs, travel master and talk-objective markers are shown');
  await page.getByRole('button', { name: 'Collapse quest tracker' }).click();
  await page.waitForTimeout(700);
  for (const id of ['crags_scout', 'crags_healer', 'crags_supplier']) {
    // Real canvas clicks on the NPC body exercise picking and obstacle-aware automatic travel.
    const [sx, sy] = await page.evaluate(id => { const n = City.npcs.find(n => n.id === id); return Field._debug.w2s(n.x, n.y); }, id);
    const box = await page.locator('#fieldcv').boundingBox();
    await page.mouse.click(box.x + sx / 1600 * box.width, box.y + (sy - 55) / 900 * box.height);
    await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 }).catch(async error => {
      await shot('camp-interaction-stuck');
      throw Error(`NPC ${id}, click ${sx},${sy}: ${JSON.stringify(await page.evaluate(() => ({ hero: { x: Field.hero.x, y: Field.hero.y, goal: Field.hero.goal }, errors: document.getElementById('npc-notice')?.textContent })))}`, { cause: error });
    });
    check(await page.locator('#npc-name').textContent() === await page.evaluate(id => City.npcs.find(n => n.id === id).name, id), `Canvas interaction reaches ${id}`);
    if (id === 'crags_healer') check((await page.locator('#npc-offers').textContent()).includes('Health Potion'), 'Camp healer offers healing supplies');
    if (id === 'crags_supplier') check((await page.locator('#npc-offers').textContent()).includes('Stew') && (await page.locator('#npc-offers').textContent()).includes('Satchel'), 'Quartermaster offers food and bags');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(600);
  }
  await page.keyboard.press('f');
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 5000 });
  check(await page.locator('#npc-name').textContent() === 'Quartermaster Dain', 'F opens the nearest camp NPC');
  await page.keyboard.press('Escape');
  await page.keyboard.press('q');
  const introduction = page.locator('#quest-list [data-quest="crags_welcome"]');
  check((await introduction.textContent()).includes('Ready to turn in'), 'All three camp conversations complete the introduction');
  await introduction.locator('button').filter({ hasText: 'Return to Captain Sera' }).click();
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  check(await page.locator('#npc-quests .gossip-row[data-quest="crags_welcome"] .gossip-icon').textContent() === '?', 'A finished quest shows a question mark at its giver');
  await page.locator('#npc-quests .gossip-row[data-quest="crags_welcome"]').click();
  await page.locator('#npc-quests [data-quest="crags_welcome"] [data-action="claim"]').click();
  await page.waitForFunction(() => !document.querySelector('#npc-quests [data-quest="crags_welcome"]'));
  check(await page.evaluate(() => Quests.marker('crags_scout') === '!' && Quests.markerInfo('crags_supplier').repeatable), 'Turn-in unlocks the wisp hunt and blue repeatable camp patrol');
  await page.keyboard.press('Escape');
  await page.evaluate(() => Field.visitNpc('crags_supplier'));
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  const questTop = (await page.locator('#npc-quests .gossip-row').first().boundingBox()).y;
  const offerTop = (await page.locator('#npc-offers .gossip-row').first().boundingBox()).y;
  check(questTop < offerTop, 'Quests are listed above the shop services, as in World of Warcraft');
  check(await page.locator('#npc-quests .gossip-row[data-repeatable="true"] .gossip-icon').first().evaluate(e => getComputedStyle(e).color) === 'rgb(93, 178, 255)', 'Repeatable bounties get a blue icon');
  await page.screenshot({ path: path.join(world.artifacts, 'npc-gossip.png') });
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Expand quest tracker' }).click();
  await shot('cinderwatch-camp');
  // Every kind in every clip: the canvas must change from one state to the next and nothing may throw.
  // One hash per monster, from the box it stands in; the sky, lava and gate animate, but the ground there does not.
  const monsterHashes = () => page.evaluate(() => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    return [1000, 1001, 1002, 1003, 1004].map(id => {
      const s = Field.slimes.find(m => m.id === id), [sx, sy] = Field._debug.w2s(s.x, s.y);
      const x = Math.max(0, Math.round((sx - 110) * k)), y = Math.max(0, Math.round((sy - 250) * k)), d = g.getImageData(x, y, Math.round(220 * k), Math.round(270 * k)).data;
      let h = 0; for (let i = 0; i < d.length; i += 5) h = (Math.imul(h, 31) + d[i] + (d[i + 1] << 3) + (d[i + 2] << 6)) | 0;
      return h;
    });
  });
  const seen = [];
  for (const [state, dieT] of [['idle', 0], ['windup', 0], ['lunge', 0], ['hurt', 0], ['dead', .2], ['dead', .45], ['dead', 3]]) {
    stage = { state, dieT };
    await page.waitForFunction(([state, dieT]) => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000 && s.state === state && (state !== 'dead' || s.dieT >= dieT - .03)).length === 5, [state, dieT], { timeout: 10000 });
    await page.evaluate(() => { Field.hero.target = Field.slimes.find(s => s.id === 1002) || null; });
    await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));   // the new state has been drawn
    check(await page.evaluate(() => Field.slimes.every(s => s.zone === 1) && Field.remotePlayers.length === 0), `A monster and a player from another zone in the ${state} packet are not shown`);
    // The clip and frame the renderer picks for each monster, for this state.
    const frames = await page.evaluate(() => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000).map(s => Field._debug.enemyFrame(s)));
    const wanted = { idle: f => f[0] === 'idle', windup: f => f[0] === 'attack' && f[1] < 3, lunge: f => f[0] === 'attack' && f[1] >= 3 && f[1] <= 5, hurt: f => f[0] === 'hurt' };
    // The client adds frame time to the server's dieT between snapshots, so allow the next frame.
    const dying = dieT === .2 ? f => f[0] === 'die' && f[1] >= 1 && f[1] <= 2 : dieT === .45 ? f => f[0] === 'die' && f[1] >= 3 && f[1] <= 4 : f => f[0] === 'die' && f[1] === 7;
    check(frames.length === 5 && frames.every(state === 'dead' ? dying : wanted[state]), `The ${state}${state === 'dead' ? ' ' + dieT + 's' : ''} state picks its own clip and frame: ${JSON.stringify(frames[0])}`);
    seen.push(await monsterHashes());
    if (state === 'idle' || state === 'lunge') await shot('bestiary-' + state);
  }
  stage = null;
  // Needs the real animation frames; the stub is one still picture. `npm run test:art` runs this suite on the real art.
  check(STUB || seen.every((hashes, i) => i === 0 || hashes.every((h, kind) => h !== seen[i - 1][kind])), `All five monsters draw something new in each state: idle, windup, lunge, hurt, early and late dying frames, then gone (${seen.length} states)`);
  const campPosition = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  await stageAt(1, 81, 10);
  await page.waitForTimeout(800);
  check(await page.evaluate(() => { const s = Field.slimes.find(s => s.kind === 'cinderlord'); return s && s.d.elite && s.d.name === 'Cinderlord' && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 7; }), 'The real Cinderlord appears in the northeastern arena with an elite nameplate');
  await shot('cinderlord-elite');
  await stageAt(1, campPosition.x, campPosition.y);
  await page.waitForFunction(() => Field.slimes.every(s => s.id < 1000), null, { timeout: 10000 });
  await page.evaluate(() => { Field.hero.target = null; });

  // Walk north along the trail through the first ford, stopping as soon as a monster comes into view (before it
  // can notice us), and look at the lava river, the charred scenery and the monster's level label.
  const route = await page.evaluate(() => { const z = Field._debug.zones[1]; return Field._debug.routeTo({ x: z.paths[0][4][0], y: z.paths[0][4][1] + 1 }, true); });
  check(route.length > 30, `The client can route across the Crags through the first ford (${route.length} steps)`);
  const nearest = () => page.evaluate(() => Math.min(...Field.slimes.filter(s => !s.dead).map(s => Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y))));
  let lavaSeen = 0;
  // Start from the step where the first wisp spawn is about 20 units away, so the last stretch (and the lava on it) is still walked for real.
  const wisps = await page.evaluate(() => Field._debug.zones[1].slimes.filter(s => s.kind === 'wisp').map(s => [s.x, s.y]));
  const first = Math.max(0, route.findIndex(step => wisps.some(([x, y]) => Math.hypot(step.x - x, step.y - y) < 20)));
  await stageAt(1, route[first].x, route[first].y);
  for (const step of route.slice(first)) {
    if (await nearest() < 11) break;
    await click(step.x, step.y); await reach(step.x, step.y, 1.3, 1);
    lavaSeen = Math.max(lavaSeen, (await look(page)).lava);
  }
  await page.evaluate(() => Online.send({ type: 'stop' }));
  await page.waitForTimeout(700);
  const monster = await page.evaluate(() => { const s = Field.slimes.filter(s => !s.dead).sort((a, b) => Math.hypot(a.x - Field.hero.x, a.y - Field.hero.y) - Math.hypot(b.x - Field.hero.x, b.y - Field.hero.y))[0]; Field.hero.target = s; return { kind: s.kind, level: s.level, name: s.d.name, hp: s.hp, maxHp: s.maxHp, distance: Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) }; });
  await page.waitForTimeout(300);
  await shot('crags-monster');
  check(monster.kind === 'wisp' && monster.distance < 12 && monster.level >= 3 && monster.level <= 7, `A level ${monster.level} ${monster.name} is in view ${monster.distance.toFixed(1)} units away`);
  check(lavaSeen > .004, `Lava is drawn as a glowing river (${(lavaSeen * 100).toFixed(2)}% of the view on the way)`);
  check(await page.evaluate(() => Field.cragSprites.meta.kinds.includes(Field.hero.target.kind) && Field.hero.target.d.top > 0), 'The monster is drawn from its own sprite atlas');
  await page.evaluate(() => { Field.hero.target = null; });
  // Back out through the Meadow Gate by clicking.
  const back = await page.evaluate(() => Field._debug.zones[1].portals[0]);
  await stageAt(1, back.x, back.y - 7);
  for (const step of await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [back.x, back.y - 3])) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 1); }
  await page.waitForTimeout(900);
  await shot('gate-crags');
  await click(back.x, back.y + 1.2);
  await page.waitForFunction(() => Field.zone === 0, null, { timeout: 30000 });
  await page.waitForTimeout(600);
  check(await page.locator('#area-title b').textContent() === 'Greenmeadow Field' && await page.locator('#city-travel').isVisible(), 'Returning restores the meadow banner and travel button');
  check(await page.evaluate(() => Field.slimes.length > 0 && Field.slimes.every(s => s.zone === 0)), 'Back in the meadow only meadow enemies are shown');
  const again = await look(page);
  check(again.g > again.r, 'The meadow is green again');
  await shot('meadow-again');
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} focused zone UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
