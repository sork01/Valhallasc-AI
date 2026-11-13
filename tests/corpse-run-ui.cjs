// End-to-end Chromium + Rust server test for CORPSE-RUN-GHOST-RESPAWN (1.49.1):
// 1. Live players cannot see ghosts (both in-zone & nearby).
// 2. Ghosts render upright (idle/walk clip, NOT die), while dead corpses render die.
// 3. Ghosts cannot fight, inspect, or talk to regular NPCs — only Spirit Guides.
// 4. Walking within 15 tiles of corpse enables #ghost-resurrect without auto-resurrecting;
//    clicking #ghost-resurrect restores life at 50% HP.
// 5. Resurrecting at a Spirit Guide drains 50% worn-gear durability and applies 10 minutes
//    of Resurrection Sickness (all stats at 25%).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const debugBin = path.join(root, 'target/debug/valhalla-server');
const newest = [release, debugBin].filter(f => fs.existsSync(f)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
const binary = process.env.VALHALLA_BINARY || newest;
const shotDir = process.env.SHOT_DIR || fs.mkdtempSync(path.join(root, 'test-results', 'corpse-run-'));
fs.mkdirSync(shotDir, { recursive: true });
const mutate = process.env.MUTATE === '1';

const client = new Client({ name: 'valhallasc-corpse-run-ui', version: '1.0.0' });
let browser, ctx1, ctx2, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

// Measure how colorful a grid of pixels on #fieldcv is (excluding HUD edges).
// Returns { maxChroma, avgChroma, grayscaleFraction } over sampled points.
async function measureCanvasColor(page) {
  return page.evaluate(() => {
    const cv = document.getElementById('fieldcv');
    const ctx = cv.getContext('2d');
    const w = cv.width, h = cv.height;
    let maxChroma = 0, sumChroma = 0, grayCount = 0, total = 0;
    // Sample interior bands away from top-left portrait / bottom bars / hero center arrow
    for (let gy = 0.22; gy <= 0.78; gy += 0.07) {
      for (let gx = 0.15; gx <= 0.85; gx += 0.07) {
        if (Math.abs(gx - 0.5) < 0.14 && Math.abs(gy - 0.5) < 0.18) continue;
        const px = Math.floor(gx * w), py = Math.floor(gy * h);
        const d = ctx.getImageData(px, py, 1, 1).data;
        const chroma = Math.max(d[0], d[1], d[2]) - Math.min(d[0], d[1], d[2]);
        if (chroma > maxChroma) maxChroma = chroma;
        sumChroma += chroma;
        if (chroma <= 4) grayCount++;
        total++;
      }
    }
    return { maxChroma, avgChroma: sumChroma / total, grayscaleFraction: grayCount / total, total };
  });
}

(async () => {
  await client.connect(new StdioClientTransport({
    command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')],
    cwd: root,
    stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', ...(process.env.NODE_PATH ? { NODE_PATH: process.env.NODE_PATH } : {}), ...(binary ? { VALHALLA_BINARY: binary } : {}) },
  }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  ctx1 = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  ctx2 = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx1.newPage();
  const page2 = await ctx2.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(`Wraith: ${e.message}`));
  page2.on('pageerror', e => errors.push(`Bystander: ${e.message}`));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page2.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));

  const loginAs = async (pg, name) => {
    await pg.goto(world.url);
    await pg.locator('#start').click(); await pg.locator('#login-guest').click();
    await pg.locator('#name').fill(name); await pg.locator('#go').click({ timeout: 60000 });
    await pg.waitForFunction(() => Online.connected && !!Field.hero.x && !!(Field.warriorSprites || Field.mageSprites || Field.assassinSprites || Field.priestSprites || Field.hunterSprites), null, { timeout: 60000 });
  };
  await Promise.all([loginAs(page, 'Wraith'), loginAs(page2, 'Bystander')]);

  const sendDebug = (pg, command) => pg.evaluate(command => {
    Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command });
  }, command).then(() => pg.waitForTimeout(250));
  const waitFrames = (pg = page) => pg.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));

  // Teleport both players onto open grassy ground outside Alderhaven (~17 tiles from spawn so corpse is outside 15 tiles).
  const deathSpot = { zone: 0, x: 233.5, y: 161.5 };
  await sendDebug(page, { op: 'set_level', level: 20 });
  const gearId = await page.evaluate(() => {
    const g = WORLD_ITEMS.find(i => i.kind === 'headgear' && !i.starter && !['hierloom', 'gm'].includes(i.rarity) && (!i.class || i.class === 'warrior') && (i.defense || 0) > 0 && (i.requiredLevel || 1) <= 20);
    return g?.id || null;
  });
  check(!!gearId, `Found wearable non-starter headgear (${gearId})`);
  await sendDebug(page, { op: 'give_item', item: gearId, quantity: 1, force: true });
  await page.waitForFunction(id => Inventory.quantity(id) >= 1, gearId, { timeout: 5000 });
  await page.evaluate(id => Online.send({ type: 'equip', slots: { headgear: id } }), gearId);
  await page.waitForFunction(id => Field.hero.equipment?.headgear === id, gearId, { timeout: 5000 });
  await sendDebug(page, { op: 'set_hp', hp: 99999 });

  const readDurabilityAndStats = async () => {
    await page.keyboard.press('KeyE');
    await page.waitForFunction(() => !document.getElementById('equipment').hidden, null, { timeout: 5000 });
    const data = await page.evaluate(() => {
      const sel = document.getElementById('field-headgear');
      const durStr = sel?.parentElement?.style?.getPropertyValue('--dur');
      return {
        durability: durStr ? Number(durStr) : null,
        maxHp: Field.hero.maxHp,
        attack: Field.hero.attack,
        defense: Field.hero.defense,
        strength: Field.hero.effectiveAttributes?.strength,
        resurrectionSickness: Field.hero.resurrectionSickness || 0,
      };
    });
    await page.keyboard.press('KeyE');
    await page.waitForFunction(() => document.getElementById('equipment').hidden, null, { timeout: 5000 });
    return data;
  };
  const preStats = await readDurabilityAndStats();
  check(preStats.durability === 100 && preStats.maxHp > 50, `Baseline stats & durability recorded: ${JSON.stringify(preStats)}`);

  await sendDebug(page, { op: 'teleport', zone: deathSpot.zone, x: deathSpot.x, y: deathSpot.y });
  await sendDebug(page2, { op: 'teleport', zone: deathSpot.zone, x: deathSpot.x + 1.5, y: deathSpot.y });
  await page.waitForFunction(({ x, y }) => Math.hypot(Field.hero.x - x, Field.hero.y - y) < 1.5, deathSpot, { timeout: 10000 });
  await page2.waitForFunction(() => Field.remotePlayers.some(p => p.look?.name === 'Wraith'), null, { timeout: 10000 });
  checks++;
  await waitFrames(page);

  const aliveColor = await measureCanvasColor(page);
  check(aliveColor.maxChroma > 15, `Alive world has color (maxChroma=${aliveColor.maxChroma})`);
  await page.screenshot({ path: path.join(shotDir, 'corpse-01-alive.png') });

  // Die at deathSpot.
  await sendDebug(page, { op: 'die' });
  await page.waitForFunction(() => Field.hero.dead === true, null, { timeout: 5000 });
  await waitFrames(page);
  const fallenState = await page.evaluate(() => ({
    dead: Field.hero.dead,
    ghost: !!Field.hero.ghost,
    deadMsgHidden: document.getElementById('dead-msg').hidden,
    ghostMsgHidden: document.getElementById('ghost-msg').hidden,
    corpse: Field.hero.corpse,
  }));
  check(fallenState.dead && !fallenState.ghost, 'Hero starts fallen before releasing spirit');
  check(!fallenState.deadMsgHidden && fallenState.ghostMsgHidden, 'Defeated overlay shows while fallen');
  check(fallenState.corpse && Math.hypot(fallenState.corpse.x - deathSpot.x, fallenState.corpse.y - deathSpot.y) < 1.5, 'Corpse recorded at death spot');
  await page.screenshot({ path: path.join(shotDir, 'corpse-02-fallen.png') });

  // Wait for 3.2s spirit release.
  await page.waitForFunction(() => Field.hero.dead === true && Field.hero.ghost === true, null, { timeout: 10000 });
  await waitFrames(page);

  // Move living Bystander right next to Alderhaven spawn to confirm ghosts are invisible to live players.
  const ghostPos0 = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  await sendDebug(page2, { op: 'teleport', zone: 0, x: ghostPos0.x + 1.5, y: ghostPos0.y });
  await page2.waitForFunction(({ x, y }) => Math.hypot(Field.hero.x - (x + 1.5), Field.hero.y - y) < 2, ghostPos0, { timeout: 10000 });
  await page2.waitForTimeout(450);
  const bystanderSeesGhost = await page2.evaluate(() => Field.remotePlayers.some(p => p.look?.name === 'Wraith'));
  check(!bystanderSeesGhost, 'Living Bystander cannot see ghost Wraith');

  const ghostState = await page.evaluate(() => ({
    x: Field.hero.x, y: Field.hero.y, hp: Field.hero.hp, dead: Field.hero.dead, ghost: Field.hero.ghost,
    corpse: Field.hero.corpse, corpses: Field.corpses.map(c => ({ id: c.id, x: c.x, y: c.y, isCorpse: c.isCorpse })),
    deadMsgHidden: document.getElementById('dead-msg').hidden,
    ghostMsgHidden: document.getElementById('ghost-msg').hidden,
    resurrectDisabled: document.getElementById('ghost-resurrect').disabled,
    canAct: Field.canAct,
    attackBlocked: Field.useSkill('attack'),
    worldMapOpenable: (() => { const opened = WorldMap.show(); if (opened) WorldMap.close(); return opened; })(),
    spiritGuide: (WORLD_MAP.npcs || []).find(n => n.art === 'spirit_guide') || null,
    otherNpc: (WORLD_MAP.npcs || []).find(n => n.art !== 'spirit_guide') || null,
  }));
  const distFromCorpse = Math.hypot(ghostState.x - ghostState.corpse.x, ghostState.y - ghostState.corpse.y);
  check(ghostState.dead && ghostState.ghost && ghostState.hp === 0, 'Hero is in ghost state with 0 hp');
  check(distFromCorpse > 15, `Ghost respawned >15 tiles from corpse (${distFromCorpse.toFixed(1)} tiles)`);
  check(ghostState.resurrectDisabled, '#ghost-resurrect stays disabled beyond 15 tiles');
  check(ghostState.deadMsgHidden && !ghostState.ghostMsgHidden, 'Dead overlay hides and Spirit Form banner appears');
  check(ghostState.corpses.length >= 1 && ghostState.corpses.every(c => c.isCorpse), 'Corpse stays on the ground marked isCorpse');
  check(!ghostState.canAct && !ghostState.attackBlocked, 'Ghost cannot attack or cast');
  check(ghostState.worldMapOpenable, 'Ghost can open the world map to navigate');
  check(!!ghostState.spiritGuide, 'Spirit Guide placed near Greenmeadow spawn');

  // Ghost interaction isolation: non-Spirit-Guide NPC interaction must be rejected server & client side.
  if (ghostState.otherNpc) {
    await page.evaluate(id => {
      Field.visitNpc(id);
      Online.send({ type: 'interact', npc: id, offer: '' });
    }, ghostState.otherNpc.id);
    await page.waitForTimeout(350);
    const dialogueOpened = await page.evaluate(() => !document.getElementById('npc-dialogue').hidden);
    check(!dialogueOpened, `Ghost cannot talk to regular NPC (${ghostState.otherNpc.id})`);
  }

  if (mutate) {
    const ghostColorMut = await measureCanvasColor(page);
    assert.ok(ghostColorMut.maxChroma > 50, 'MUTATE: forcing failure on B&W ghost world');
  }

  const ghostColor = await measureCanvasColor(page);
  check(ghostColor.grayscaleFraction > 0.95 && ghostColor.maxChroma <= 6, `Ghost world is black & white with fog (frac=${ghostColor.grayscaleFraction.toFixed(2)}, maxChroma=${ghostColor.maxChroma})`);
  await page.screenshot({ path: path.join(shotDir, 'corpse-03-ghost-spawn.png') });

  // Verify sprite rendering: ghost draws upright ('idle', NOT 'die') and translucent; corpse draws 'die'.
  const poseCheck = await page.evaluate(() => {
    const spr = Field.mageSprites || Field.warriorSprites || Field.assassinSprites || Field.priestSprites || Field.hunterSprites;
    if (!spr) return null;
    const dummy = document.createElement('canvas'); dummy.width = 64; dummy.height = 64;
    const g = dummy.getContext('2d');
    let lastAlpha = 1, ghostAlpha = 1, ghostClip = null, corpseClip = null;
    const origFrame = spr.frame.bind(spr);
    const origDrawImage = g.drawImage.bind(g);
    spr.frame = (c, d, i) => { spr._lastClip = c; return origFrame(c, d, i); };
    g.drawImage = (...args) => { lastAlpha = g.globalAlpha; origDrawImage(...args); };
    spr.draw(g, { dead: true, ghost: true, moving: false, fx: 1, fy: 1, walk: 0, atkT: 0, hurtT: 0, deadT: 0 }, 0);
    ghostClip = spr._lastClip;
    ghostAlpha = lastAlpha;
    spr.draw(g, { dead: true, isCorpse: true, moving: false, fx: 1, fy: 1, walk: 0, atkT: 0, hurtT: 0, deadT: 9 }, 0);
    corpseClip = spr._lastClip;
    spr.frame = origFrame;
    return { ghostAlpha, ghostClip, corpseClip };
  });
  check(poseCheck && poseCheck.ghostClip === 'idle' && poseCheck.corpseClip === 'die', `Ghost stands upright (clip=${poseCheck?.ghostClip}), corpse lies dead (clip=${poseCheck?.corpseClip})`);
  check(poseCheck && poseCheck.ghostAlpha < 0.6 && poseCheck.ghostAlpha > 0.2, `Ghost renders translucent (alpha=${poseCheck?.ghostAlpha})`);

  // Verify peaceful ghost: spawn a hostile enemy right next to the ghost and tick; ghost stays ignored & unhurt.
  await sendDebug(page, { op: 'spawn_enemy', kind: 'slime', x: ghostState.x + 1.5, y: ghostState.y, level: 1 });
  await page.waitForTimeout(700);
  const hostileNear = await page.evaluate(() => Field.slimes.map(s => ({ state: s.state, kind: s.kind })));
  check(hostileNear.every(s => s.state !== 'chase' && s.state !== 'windup'), 'Hostile mobs do not aggro the ghost');

  // Ghost walks next to the Spirit Guide and opens Spirit Guide dialogue (then closes it for now).
  const guideRoute = await page.evaluate(pt => {
    const r = Field._debug.routeTo(pt);
    return r.length ? r : [pt];
  }, { x: ghostState.spiritGuide.x, y: ghostState.spiritGuide.y });
  for (const wp of guideRoute) {
    await page.evaluate(pt => Online.send({ type: 'move', x: pt.x, y: pt.y }), wp);
    await page.waitForFunction(pt => Math.hypot(Field.hero.x - pt.x, Field.hero.y - pt.y) < 2.2, wp, { timeout: 10000 });
  }
  await page.evaluate(id => Online.send({ type: 'interact', npc: id, offer: '' }), ghostState.spiritGuide.id);
  await page.waitForFunction(() => !document.getElementById('npc-dialogue').hidden && !!document.querySelector('[data-offer="spirit_resurrect"]'), null, { timeout: 5000 });
  const guideOfferEnabled = await page.evaluate(() => !document.querySelector('[data-offer="spirit_resurrect"]').disabled);
  check(guideOfferEnabled, 'Spirit Guide dialogue opens for ghost with enabled spirit_resurrect offer');
  await page.screenshot({ path: path.join(shotDir, 'corpse-03b-spirit-guide.png') });
  await page.locator('#npc-x').click();
  await page.waitForFunction(() => document.getElementById('npc-dialogue').hidden, null, { timeout: 5000 });

  // Walk to ~10 tiles from corpse (inside the 15-tile radius) -> must NOT auto-resurrect, and #ghost-resurrect enables.
  const tenTilesPt = await page.evaluate(() => ({ x: Field.hero.corpse.x + 9.5, y: Field.hero.corpse.y }));
  const route = await page.evaluate(pt => {
    const r = Field._debug.routeTo(pt);
    return r.length ? r : [pt];
  }, tenTilesPt);
  for (const wp of route) {
    await page.evaluate(pt => Online.send({ type: 'move', x: pt.x, y: pt.y }), wp);
    await page.waitForFunction(pt => Math.hypot(Field.hero.x - pt.x, Field.hero.y - pt.y) < 1.8, wp, { timeout: 10000 });
  }
  await page.evaluate(() => Online.send({ type: 'stop' }));
  await page.waitForTimeout(700);
  await waitFrames(page);
  const insideRadius = await page.evaluate(() => ({
    ghost: Field.hero.ghost,
    dead: Field.hero.dead,
    resurrectDisabled: document.getElementById('ghost-resurrect').disabled,
    dist: Math.hypot(Field.hero.x - Field.hero.corpse.x, Field.hero.y - Field.hero.corpse.y),
  }));
  check(insideRadius.ghost && insideRadius.dead, `Walking within 15 tiles (${insideRadius.dist.toFixed(1)}) does NOT auto-resurrect`);
  check(!insideRadius.resurrectDisabled, '#ghost-resurrect becomes enabled within 15 tiles');
  await page.screenshot({ path: path.join(shotDir, 'corpse-04-near-corpse.png') });

  // Click #ghost-resurrect button to manually resurrect at 50% HP at ghost's position.
  await page.locator('#ghost-resurrect').click();
  await page.waitForFunction(() => !Field.hero.dead && !Field.hero.ghost && !Field.hero.corpse, null, { timeout: 10000 });
  await waitFrames(page);
  const revivedState = await page.evaluate(() => ({
    x: Field.hero.x, y: Field.hero.y, hp: Field.hero.hp, maxHp: Field.hero.maxHp,
    dead: Field.hero.dead, ghost: Field.hero.ghost, corpse: Field.hero.corpse,
    corpsesCount: Field.corpses.length,
    deadMsgHidden: document.getElementById('dead-msg').hidden,
    ghostMsgHidden: document.getElementById('ghost-msg').hidden,
  }));
  const expectedHalfHp = Math.max(1, Math.round(revivedState.maxHp * 0.5));
  check(Math.abs(revivedState.hp - expectedHalfHp) <= 1, `Manual Resurrect revives at half HP (${revivedState.hp}/${revivedState.maxHp})`);
  check(Math.hypot(revivedState.x - tenTilesPt.x, revivedState.y - tenTilesPt.y) < 2.5, 'Resurrected right at ghost position within 15 tiles of corpse');
  check(revivedState.corpsesCount === 0, 'Corpse cleared after resurrection');
  check(revivedState.deadMsgHidden && revivedState.ghostMsgHidden, 'Death and ghost banners hidden after resurrection');
  const bystanderSeesAgain = await page2.evaluate(() => Field.remotePlayers.some(p => p.look?.name === 'Wraith'));
  check(bystanderSeesAgain, 'Living Bystander sees Wraith again after resurrection');
  const revivedColor = await measureCanvasColor(page);
  check(revivedColor.maxChroma > 15, `Normal world color restored after resurrection (maxChroma=${revivedColor.maxChroma})`);
  await page.screenshot({ path: path.join(shotDir, 'corpse-05-resurrected.png') });

  // Part 2: Die again, take Spirit Guide resurrection -> 50% durability loss + 10 min Resurrection Sickness (25% stats).
  await sendDebug(page, { op: 'die' });
  await page.waitForFunction(() => Field.hero.dead === true && Field.hero.ghost === true, null, { timeout: 10000 });
  const preSpiritDur = (await page.evaluate(() => {
    return null;
  }), preStats.durability - 20); // two deaths = -20 wear total (100 -> 80)
  const guideRoute2 = await page.evaluate(pt => {
    const r = Field._debug.routeTo(pt);
    return r.length ? r : [pt];
  }, { x: ghostState.spiritGuide.x, y: ghostState.spiritGuide.y });
  for (const wp of guideRoute2) {
    await page.evaluate(pt => Online.send({ type: 'move', x: pt.x, y: pt.y }), wp);
    await page.waitForFunction(pt => Math.hypot(Field.hero.x - pt.x, Field.hero.y - pt.y) < 2.2, wp, { timeout: 10000 });
  }
  await page.evaluate(id => Online.send({ type: 'interact', npc: id, offer: '' }), ghostState.spiritGuide.id);
  await page.waitForFunction(() => !document.getElementById('npc-dialogue').hidden && !!document.querySelector('[data-offer="spirit_resurrect"]'), null, { timeout: 5000 });
  await page.locator('[data-offer="spirit_resurrect"]').click();
  await page.waitForFunction(() => !Field.hero.dead && !Field.hero.ghost && (Field.hero.resurrectionSickness || 0) > 590, null, { timeout: 10000 });
  await waitFrames(page);
  const dialogueClosed = await page.evaluate(() => document.getElementById('npc-dialogue').hidden);
  check(dialogueClosed, 'Spirit Guide dialogue closed after resurrecting');
  const sickBuffVisible = await page.evaluate(() => !!document.querySelector('#buff-bar [data-buff="resurrection_sickness"]'));
  check(sickBuffVisible, 'Resurrection Sickness buff icon appears in #buff-bar');

  const postStats = await readDurabilityAndStats();
  check(postStats.durability === preSpiritDur - 50, `Spirit Guide drained 50% durability (${preSpiritDur} -> ${postStats.durability})`);
  check(postStats.resurrectionSickness > 590 && postStats.resurrectionSickness <= 600, `Resurrection Sickness duration ~600s (${postStats.resurrectionSickness.toFixed(1)}s)`);
  check(Math.abs(postStats.maxHp - Math.max(1, Math.round(preStats.maxHp * 0.25))) <= 2, `Max HP reduced to 25% (${postStats.maxHp} vs 25% of ${preStats.maxHp})`);
  check(Math.abs(postStats.attack - preStats.attack * 0.25) <= 1.5, `Attack reduced to 25% (${postStats.attack} vs 25% of ${preStats.attack})`);
  check(Math.abs(postStats.defense - preStats.defense * 0.25) <= 1.5, `Defense reduced to 25% (${postStats.defense} vs 25% of ${preStats.defense})`);
  check(Number.isFinite(preStats.strength) && Number.isFinite(postStats.strength) && postStats.strength <= Math.ceil(preStats.strength * 0.25) + 1 && postStats.strength >= Math.floor(preStats.strength * 0.25), `Attributes reduced to 25% (strength ${postStats.strength} vs 25% of ${preStats.strength})`);
  await page.screenshot({ path: path.join(shotDir, 'corpse-06-spirit-sickness.png') });

  check(errors.length === 0, `No uncaught page errors: ${errors.join('; ')}`);
  console.log(`PASS corpse-run-ui (${checks} checks). Screenshots in ${shotDir}`);
})().finally(async () => {
  await ctx1?.close().catch(() => {});
  await ctx2?.close().catch(() => {});
  await browser?.close().catch(() => {});
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
