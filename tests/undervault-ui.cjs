// Browser-only checks for the Undervault (zone 5, the dungeon under Skaldholm): the stairs beside the Meeting Stone, the Stone's
// fighters for hire, the level-20 door, the vault's look (floor from its rooms, stone walls, dark with pools of torchlight),
// the monsters in every state, a ranged enemy's missiles, a boss's health bar and ground-pound ring, the exit that opens
// when the last boss falls, the minimap and the world map. Rules, loot, copies and balance are exercised by the Rust tests and
// the `undervault` MCP scenario; this clicks and looks. Run against the real art with REAL_SPRITES=1.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-undervault-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
const look = (page, [x0, y0, x1, y1] = [.15, .2, .85, .8]) => page.evaluate(([x0, y0, x1, y1]) => {
  const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), w = cv.width, h = cv.height;
  const d = g.getImageData(Math.floor(w * x0), Math.floor(h * y0), Math.floor(w * (x1 - x0)), Math.floor(h * (y1 - y0))).data;
  let r = 0, gr = 0, b = 0, n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; }
  return { r: r / n, g: gr / n, b: b / n, lum: (r + gr + b) / n / 3 };
}, [x0, y0, x1, y1]);
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' });
  await client.connect(transport);
  const world = await call('start_world', { godMode: true, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/401|Failed to load resource/.test(message.text())) errors.push(message.text()); });
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Delver');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);
  await debug({ op: 'explore_all' });
  await page.waitForFunction(() => Field.explored?.length >= 6 && Field.explored.every(m => m === 511), null, { timeout: 10000 });
  const stageAt = async (zone, x, y) => {
    await debug({ op: 'teleport', zone, x, y });
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [zone, x, y], { timeout: 10000 });
    await page.waitForTimeout(500);
  };
  const click = async (x, y, dy = 0) => {
    const [sx, sy] = await page.evaluate(([x, y]) => Field._debug.w2s(x, y), [x, y]);
    const box = await page.locator('#fieldcv').boundingBox();
    await page.mouse.click(box.x + sx / 1600 * box.width, box.y + (sy + dy) / 900 * box.height);
  };

  // ---- the data the client uses comes from the same file the server loads
  const zones = await page.evaluate(() => Field._debug.zones.map(z => ({ name: z.name, theme: z.theme, levels: z.levels, players: z.players, min: z.min_level, rooms: (z.rooms || []).length,
    kinds: [...new Set(z.objects.map(o => o.kind))].sort().join(), portals: z.portals.map(p => `${p.id}>${p.to}${p.look ? ':' + p.look : ''}${p.after_clear ? ':after' : ''}`).join(), slimes: (z.slimes || []).length })));
  check(zones.length >= 29 && zones[5].name === 'The Undervault' && zones[5].theme === 'vault' && zones[5].players === 5 && zones[5].min === 20 && zones[5].slimes === 50, 'The client knows zone 5: a vault-themed dungeon for 5 players, level 20, fifty enemies');
  check(zones[5].rooms === 15 && ['vaultwall', 'pillar', 'brazier', 'torch', 'sarcophagus', 'bones'].every(k => zones[5].kinds.includes(k)), `The vault is ${zones[5].rooms} rooms and corridors of walls, pillars, braziers, torches, sarcophagi and bones`);
  check(zones[5].portals === 'undervault_stairs_up>4:stairs_up,undervault_exit>4:exit:after' && zones[4].portals.includes('undervault_stairs>5:stairs_down'), 'Stairs down from Skaldholm; stairs up and a closed exit in the dungeon');
  const stairs = await page.evaluate(() => Field._debug.zones[4].portals.find(p => p.id === 'undervault_stairs'));
  const ret = await page.evaluate(() => { const p = Field._debug.zones[5].portals[0]; return { x: p.tx, y: p.ty }; });   // where the dungeon sets you down in Skaldholm

  // ---- Skaldholm: the stone speaks, the stairs are drawn
  await debug({ op: 'set_level', level: 19 });
  await debug({ op: 'set_gold', gold: 2000 });
  await page.waitForTimeout(6500);                        // the level-up banner
  await stageAt(4, ret.x, ret.y);
  await shot('stairs-down');
  const dark = await look(page, [.3, .25, .75, .6]);
  check(await page.evaluate(() => City.npcs.some(n => n.id === 'city_meetingstone' && n.art === 'stone')), 'The Meeting Stone is a speaker of its own, drawn as the stone itself');
  // Level 19: the door refuses.
  await click(stairs.x, stairs.y);
  await page.waitForFunction(() => /level 20/.test(document.getElementById('chat-log').textContent + document.getElementById('system-log').textContent), null, { timeout: 15000 });
  check(await page.evaluate(() => Field.zone === 4), 'A level-19 hero is told the dungeon is for level 20 and stays in Skaldholm');
  await stageAt(4, 100, 128);                             // off the stairs: at level 20 the door would take the hero in at once
  await debug({ op: 'set_level', level: 20 });
  await page.waitForTimeout(6500);

  // Click the monolith itself: the Stone offers fighters.
  // The Stone moved with the shaped city: stage beside it from its map position, clear of the stairs.
  const stoneAt = await page.evaluate(() => Field._debug.zones[4].npcs.find(n => n.id === 'city_meetingstone'));
  await stageAt(4, stoneAt.x - 2.5, stoneAt.y - 1.5);
  const stone = await page.evaluate(() => City.npcs.find(n => n.id === 'city_meetingstone'));
  await click(stone.x, stone.y, -150);
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 15000 });
  check(await page.locator('#npc-name').textContent() === 'The Meeting Stone' && await page.locator('#npc-dialogue .gossip-row').count() >= 6, 'A click on the monolith opens the Stone: five classes and a dismissal');
  const priceRow = await page.locator('#npc-dialogue .gossip-row', { hasText: 'Priest mercenary' }).innerText();
  // merc_price(20) is 1200 copper, which the coin display shows as 12 silver (COIN-DENOMINATIONS).
  check(/\b12\s+silver\b/.test(priceRow), `The offer row shows the level-20 price, 12 silver (row text: ${JSON.stringify(priceRow)})`);
  await page.locator('#npc-dialogue .gossip-row', { hasText: 'Priest mercenary' }).click();
  await page.waitForFunction(() => /Merc Priest joins your party/.test(document.getElementById('npc-notice').textContent), null, { timeout: 15000 });
  check(await page.evaluate(() => Field.remotePlayers.some(p => p.look.name === 'Merc Priest')), 'The hired Priest stands beside the hero');
  await page.keyboard.press('Escape');

  // ---- down the stairs with a real click
  await stageAt(4, ret.x, ret.y);
  await click(stairs.x, stairs.y);
  await page.waitForFunction(() => Field.zone === 5, null, { timeout: 8000 }).catch(async () => {    // a click that lands on the hired Priest means attack/inspect: send the plain move
    await page.evaluate(([x, y]) => Online.send({ type: 'move', x, y }), [stairs.x, stairs.y]);
    await page.waitForFunction(() => Field.zone === 5, null, { timeout: 30000 });
  });
  await page.waitForTimeout(1500);
  await shot('vault-arrival');
  check(await page.evaluate(() => Field.zoneName === 'The Undervault' && Field.zoneTheme === 'vault'), 'The stairs lead into the Undervault');
  check((await page.locator('#area-title b').textContent()) === 'The Undervault' && (await page.locator('#area-title span').textContent()).includes('Dungeon · 5 players'), 'The banner names the dungeon and its five players');
  const lit = await look(page, [.35, .3, .65, .7]), edge = await look(page, [0, .85, .12, 1]);
  check(lit.lum > edge.lum * 1.4 && edge.lum < 40, `Torchlight pools in the dark: ${lit.lum.toFixed(0)} near the hero, ${edge.lum.toFixed(0)} at the edge`);
  check(await page.evaluate(() => document.getElementById('city-travel').hidden), 'No "visit the camp" button in a dungeon');
  const floor = await page.evaluate(() => { const z = Field._debug.zones[5], inRoom = (x, y) => z.rooms.some(([a, b, c, d]) => x >= a && x < c && y >= b && y < d); return [inRoom(20, 110), inRoom(60, 80), inRoom(105, 80)]; });
  check(floor.join() === 'true,false,true', 'The floor is painted from the room list; solid rock stays black');
  const mini = await page.evaluate(() => { const c = document.getElementById('minimap'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let floorPx = 0, black = 0; for (let i = 0; i < d.length; i += 4) { if (d[i] > 40 && d[i + 2] > 70) floorPx++; else if (d[i] < 20 && d[i + 1] < 20) black++; } return { floorPx, black }; });
  check(mini.floorPx > 800 && mini.black > 2000, `The minimap shows rooms (${mini.floorPx}) in the black of the rock (${mini.black})`);
  check(await page.evaluate(() => Field.remotePlayers.some(p => p.look.name === 'Merc Priest')), 'The hired Priest followed down the stairs');
  await debug({ op: 'set_hp', hp: 500 });

  // ---- monsters in every state (the real atlas when REAL_SPRITES=1)
  const kinds = ['thrall', 'archer', 'acolyte', 'gatewarden', 'choir', 'colossus', 'hollowking'];
  check(await page.evaluate(([kinds, stub]) => { const s = Field.vaultSprites; return !!s && s.meta.kinds.join() === kinds.join() && (stub || (s.meta.frame[0] === 96 && s.meta.clips.attack.n === 8 && Object.keys(s.img).length === 7)); }, [kinds, STUB]), 'The vault atlas has all seven kinds with the standard clips');
  const nameOf = await page.evaluate(kinds => kinds.map(k => Field.enemyName(k)), kinds);
  check(nameOf.join('|') === 'Vault Thrall|Bone Archer|Hollow Acolyte|Hrolf Bonegate|Valka, the Hollow Choir|Ironwake, the Vault Colossus|Haldor, the Hollow King', 'Every kind has its name for the system log');

  // ---- a ranged enemy: arrows in flight, drawn and carried between snapshots
  // Pick an archer that is not already in a fight with the hero (a chasing archer parked beside the hero backs off into a corner and never looses a shot).
  // The hero is staged 7 tiles from an archer INSIDE the same room, on a line that clears every wall, pillar and bone
  // by 0.9 tiles. A point across a vault wall (x 47.5 in zone 5) is outside every room, so the teleport snaps it to the
  // nearest free ground behind the wall: the archer then has no line and no path to the hero, and never shoots.
  // MUTATE=wall restores the old fixture (nearest archer, 7 tiles west of it): the wait below must then fail.
  const archer = await page.evaluate(mutate => {
    const z = Field._debug.zones[5], h = Field.hero;
    if (mutate) {   // the old fixture: the nearest archer, staged 7 tiles west of it whatever lies between
      const far = Field.slimes.filter(s => s.kind === 'archer' && !s.dead && s.state !== 'chase' && Math.hypot(s.x - h.x, s.y - h.y) > 9);
      far.sort((a, b) => Math.hypot(a.x - h.x, a.y - h.y) - Math.hypot(b.x - h.x, b.y - h.y));
      const a = far[0] || Field.slimes.find(s => s.kind === 'archer' && !s.dead);
      return { id: a.id, x: a.x, y: a.y, hx: a.x - 7, hy: a.y };
    }
    const room = (x, y) => z.rooms.find(([a, b, c, d]) => x >= a + 1.5 && x <= c - 1.5 && y >= b + 1.5 && y <= d - 1.5);
    const solids = z.objects.filter(o => o.kind !== 'void' && o.r > 0);
    const clear = (ax, ay, bx, by) => solids.every(o => {
      const dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy || 1;
      const t = Math.max(0, Math.min(1, ((o.x - ax) * dx + (o.y - ay) * dy) / L));
      return Math.hypot(ax + dx * t - o.x, ay + dy * t - o.y) > o.r + 0.9;
    });
    const free = (x, y) => solids.every(o => Math.hypot(o.x - x, o.y - y) > o.r + 0.9);
    const options = [];
    for (const s of Field.slimes) {
      if (s.kind !== 'archer' || s.dead || s.state === 'chase') continue;
      const home = room(s.x, s.y);
      if (!home) continue;
      for (let k = 0; k < 8; k++) {
        const hx = s.x + Math.cos(k * Math.PI / 4) * 7, hy = s.y + Math.sin(k * Math.PI / 4) * 7;
        if (room(hx, hy) === home && free(hx, hy) && clear(hx, hy, s.x, s.y)) options.push({ id: s.id, x: s.x, y: s.y, hx, hy, d: Math.hypot(s.x - h.x, s.y - h.y) });
      }
    }
    options.sort((a, b) => a.d - b.d);
    const a = options[0];
    if (!a) throw new Error('no archer in a room with a clear 7-tile line to stand in');
    return a;
  }, process.env.MUTATE === 'wall');
  await stageAt(5, archer.hx, archer.hy);
  // Capture the arrow inside the wait itself: at 2 tiles it lands within a few frames, so a later read finds it gone.
  await page.waitForFunction(() => {
    const b = Field._debug.ebolts.find(b => b.kind === 'archer');
    if (b) window.__archerArrow = { speed: b.speed, color: b.color, x0: b.x, y0: b.y };
    return !!b;
  }, null, { timeout: 25000 }).catch(async (err) => {
    // Diagnostic on failure: where the archers are, what state they are in and where the hero stands.
    console.error('archer probe', JSON.stringify(await page.evaluate(() => ({ hero: [Field.hero.x, Field.hero.y], zone: Field.zone, archers: Field.slimes.filter(s => s.kind === 'archer').map(s => ({ id: s.id, x: +s.x.toFixed(1), y: +s.y.toFixed(1), state: s.state, dead: s.dead, target: s.target ?? null, dormant: s.dormant ?? null })) }))));
    throw err;
  });
  const arrow = await page.evaluate(() => window.__archerArrow);
  await page.waitForTimeout(60);
  check(arrow.speed > 5 && /^#/.test(arrow.color), `An arrow flies at ${arrow.speed} tiles a second`);
  await shot('archer-arrows');

  // ---- a boss: health bar, ground-pound ring, loot glow
  const boss = await page.evaluate(() => Field.slimes.find(s => s.kind === 'gatewarden'));
  await stageAt(5, boss.x - 5, boss.y);
  await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'gatewarden' && (s.state === 'windup' || s.state === 'lunge' || s.state === 'chase')), null, { timeout: 15000 });
  await page.waitForTimeout(300);
  await shot('boss-fight');
  const bar = await look(page, [.34, .13, .66, .17]);
  check(bar.r > bar.g + 40, `The boss bar shows across the top (${bar.r | 0},${bar.g | 0},${bar.b | 0})`);
  await page.evaluate(() => Field._debug.event({ type: 'event', kind: 'slam', actor: '', x: Field.hero.x + 1, y: Field.hero.y, value: 3.6 }));
  check(await page.evaluate(() => Field._debug.effects.some(e => e.kind === 'slam' && e.r === 3.6)), 'A ground-pound event draws its ring');

  // ---- the exit: shut until the last boss falls, then drawn and usable
  const exit = await page.evaluate(() => Field._debug.zones[5].portals.find(p => p.after_clear));
  const king = await page.evaluate(() => Field.slimes.find(s => s.kind === 'hollowking'));
  await stageAt(5, exit.x - 3, exit.y - 3);
  const closed = await look(page, [.4, .35, .6, .65]);
  check(await page.evaluate(() => Field._debug.cleared === false), 'The dungeon is not cleared yet');
  await stageAt(5, king.x - 3, king.y);
  await debug({ op: 'kill_enemy', id: king.id });
  await page.waitForFunction(() => Field._debug.cleared === true, null, { timeout: 15000 });
  await stageAt(5, exit.x - 3, exit.y - 3);
  await page.waitForTimeout(2200);
  await shot('exit-open');
  const open = await look(page, [.4, .35, .6, .65]);
  check(open.g > closed.g + 8, `The way out glows green once the king is down (${closed.g | 0} -> ${open.g | 0})`);
  await click(exit.x, exit.y);
  await page.waitForFunction(() => Field.zone === 4, null, { timeout: 30000 });
  check(await page.evaluate(([x, y]) => Math.hypot(Field.hero.x - x, Field.hero.y - y) < 1.5, [exit.tx, exit.ty]), 'Walking into the opened portal leads out beside the stairs in Skaldholm');

  // ---- the world map has a tile for it
  await page.keyboard.press('m');
  // Dungeon interiors have no atlas tile: the Undervault opens from its entrance marker on Skaldholm (data-to 5), named by aria-label.
  await page.locator('#worldmap .wm-entrance[data-to="5"]').waitFor({ timeout: 10000 });
  check(await page.evaluate(() => (document.querySelector('#worldmap .wm-entrance[data-to="5"]').getAttribute('aria-label') || '').startsWith('The Undervault') && Field._debug.zones[5].min_level === 20), 'The world map shows the Undervault entrance; its door is level 20');
  await shot('world-map');
  await page.keyboard.press('Escape');
  check(errors.length === 0, `No page errors: ${errors.join(' | ')}`);
  console.log(`${checks} focused Undervault UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
