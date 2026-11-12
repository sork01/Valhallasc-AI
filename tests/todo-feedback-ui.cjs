// The eight November 12 requests: one bounded private browser, no combat or grinding.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const world = new TestWorld(); world.godMode = true;
let browser, checks = 0;
const errors = [];
const check = (ok, label) => { assert.ok(ok, label); console.log(`${++checks}: ${label}`); };
const wait = (page, fn, value) => page.waitForFunction(fn, value, { timeout: 15000 });
async function debug(page, command) {
  await page.evaluate(command => Online.send({ type: 'debug', command }), command);
  await page.waitForTimeout(180);
}
async function player(lang, className = 'warrior') {
  const page = await browser.newPage({ viewport: { width: 1100, height: 720 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(({ lang, version }) => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} }));
    localStorage.setItem('valhallasc.whats-new.v1', version);
  }, { lang, version: fs.readFileSync('client/index.html', 'utf8').match(/class="version">([^<]+)/)[1] });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-' + className).click(); await page.locator('#name').fill(`Todo${lang}${className === 'warrior' ? '' : className}`); await page.locator('#go').click({ timeout: 60000 });
  await wait(page, () => Online.connected && Field.hero?.hp > 0);
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  await page.evaluate(() => {
    window.todoNotices = []; const original = Announce.show;
    Announce.show = (text, kind) => { todoNotices.push({ text, kind }); original(text, kind); };
  });
  return page;
}
async function quest(page, id, action) {
  await debug(page, { op: 'quest', id, action });
  await wait(page, ({ id, action }) => {
    const p = Field.hero.quests?.find(p => p.id === id);
    if (!p) return false;
    if (action === 'claim') return p.claimed;
    if (action === 'accept') return !p.claimed;
    const q = [WORLD_MAP, ...WORLD_MAP.zones].flatMap(a => a.quests || []).find(q => q.id === id);
    return q.objectives.every((o, i) => p.counts[i] >= o.count);
  }, { id, action });
}
async function screenshot(page, name) { await page.screenshot({ path: path.join(world.runDir, name) }); }
(async () => {
  await world.start(); browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  const initialClass=process.env.PART === 'attack-errors' ? process.env.ATTACK_CLASS || 'mage' : 'warrior';
  const page = await player('en', initialClass);
  if (process.env.PART === 'attack-errors') {
    const layout = await page.evaluate(() => {
      Announce.show('A treasure chest has appeared!', 'treasure');
      Announce.show('Quest completed: A Home in Alderhaven', 'quest');
      for (let i = 1; i <= 5; i++) Field.error('Error ' + i);
      const box = document.getElementById('error-messages'), lines = [...box.children], r = document.getElementById('fieldcv').getBoundingClientRect();
      const head = Field._debug.w2s(Field.hero.x, Field.hero.y, 120)[1] / 1600 * r.width + r.top;
      const font = +getComputedStyle(lines[0]).fontSize.replace('px',''), banner = +getComputedStyle(document.querySelector('#announce .announce-line')).fontSize.replace('px','');
      return { count:lines.length, high:box.getBoundingClientRect().top < r.top+r.height*.1, clear:lines.at(-1).getBoundingClientRect().bottom < head, smaller:font < banner*.8 };
    });
    check(layout.count === 5 && layout.high && layout.clear, 'All five errors stay near the top and above the character, independently of chest and quest banners');
    check(layout.smaller, 'Error text is smaller than ordinary announcements');
    const barrier = await page.evaluate(() => {
      const objects=WORLD_MAP.objects, hubs=[WORLD_MAP.city,...WORLD_MAP.camps].filter(Boolean);
      const clear=p=>objects.every(o=>o.width ? Math.abs(p.x-o.x)>o.width/2+.8 || Math.abs(p.y-o.y)>o.depth/2+.8 : Math.hypot(p.x-o.x,p.y-o.y)>o.r+.8);
      const outside=p=>!hubs.some(h=>p.x>=h.x0 && p.x<=h.x1 && p.y>=h.y0 && p.y<=h.y1);
      for (const o of objects.filter(o=>o.kind==='oak_tree' && o.r>=.8 && o.r<=1.5)) {
        const left={x:o.x-o.r-1,y:o.y}, right={x:o.x+o.r+1,y:o.y};
        if(clear(left)&&clear(right)&&outside(left)&&outside(right)&&WORLD_MAP.slimes.every(e=>Math.hypot(e.x-o.x,e.y-o.y)>6)) return {left,right};
      }
    });
    assert.ok(barrier, 'There is a real tree with clear ground on both sides');
    for (const className of process.env.ATTACK_CLASS ? [process.env.ATTACK_CLASS] : ['mage','warrior']) {
      const current=className===initialClass?page:await player('en',className);
      await debug(current,{op:'teleport',zone:0,...barrier.left});
      await debug(current,{op:'spawn_enemy',kind:'green',level:1,...barrier.right});
      await wait(current, p=>Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.7,barrier.left);
      await wait(current,p=>Field.slimes.some(e=>e.kind==='green'&&!e.dead&&Math.hypot(e.x-p.x,e.y-p.y)<1),barrier.right);
      const enemy=await current.evaluate(p=>Field.slimes.filter(e=>e.kind==='green'&&!e.dead).sort((a,b)=>Math.hypot(a.x-p.x,a.y-p.y)-Math.hypot(b.x-p.x,b.y-p.y))[0].id,barrier.right);
      const selected=await current.evaluate(({id,className})=>{ WorldFeedback.reset(); window.losNotices=[]; const original=Announce.show; Announce.show=(text,kind)=>{if(text==='Out of line of sight.')losNotices.push(performance.now()); original(text,kind);}; if(className==='warrior') Field.startNearestAutoattack(); else Field.targetEnemy(id); return Field.hero.target?.id===id; },{id:enemy,className});
      check(selected, `${className}: ${className==='warrior'?'the touch Auto button':'enemy selection'} targets the enemy behind the obstacle`);
      await wait(current,()=>document.querySelector('#error-messages [data-kind="error"]')?.textContent==='Out of line of sight.');
      check(await current.evaluate(id=>Field.slimes.find(s=>s.id===id)?.hp===Field.slimes.find(s=>s.id===id)?.maxHp && Field.hero.atkCd===0,enemy), `${className}: a real blocked autoattack produces feedback without changing combat`);
      await current.waitForTimeout(250);
      check(await current.evaluate(()=>losNotices.length===1), `${className}: blocked autoattack warnings are throttled`);
      if(className==='mage') await screenshot(current,'higher-autoattack-error.png');
      await current.evaluate(()=>{ Field.clearInput(); Online.send({type:'stop'}); WorldFeedback.reset(); });
      const open=await current.evaluate(id=>{const s=Field.slimes.find(s=>s.id===id);return {x:s.x+2,y:s.y};},enemy);
      await debug(current,{op:'teleport',zone:0,...open});
      await current.evaluate(id=>Field.targetEnemy(id),enemy);
      await wait(current,id=>{const s=Field.slimes.find(s=>s.id===id);return s?.dead || s?.hp<s?.maxHp;},enemy);
      check(await current.locator('#error-messages [data-kind="error"]').count()===0, `${className}: attacks resume with no warning once the line is clear`);
      await current.close();
    }
    check(errors.length===0,'No browser errors: '+errors.join('; '));
    console.log(`higher-autoattack-errors: ${checks} focused checks passed; ${world.runDir}`); return;
  }
  if (['errors', 'corrections', 'gold'].includes(process.env.PART)) {
    await page.setViewportSize({ width: 2200, height: 700 });
    await wait(page, () => document.getElementById('fieldcv').getBoundingClientRect().left > 300);
    if (process.env.PART !== 'gold') {
      await quest(page, 'welcome', 'accept'); await quest(page, 'fold_strays', 'accept');
      await page.evaluate(() => Quests.track('fold_strays'));
      await quest(page, 'fold_strays', 'complete');
      check(await page.evaluate(() => {
        const rows = [...document.querySelectorAll('#quest-tracker .tracker-quest')];
        return rows.at(-1)?.dataset.quest === 'fold_strays' && rows.findIndex(n => n.dataset.quest === 'welcome') < rows.length - 1;
      }), 'A tracked quest moves to the bottom of the left tracker as soon as its objectives are complete');
      check(await page.evaluate(() => {
        const npc = WORLD_MAP.quests.find(q => q.id === 'fold_strays').npc;
        const map = Quests.mapMarkers(0).find(m => m.npc === npc), field = Quests.markerInfo(npc);
        return map.symbol === '?' && field.symbol === '?' && map.color === '#ffdf88' && field.color === '#ffdf88';
      }), 'Non-repeatable question marks are yellow on NPCs and maps');
      check(await page.evaluate(() => {
        const q = WORLD_MAP.quests.find(q => q.id === 'meadow_bounty'), own = Field.hero.quests;
        try {
          Quests.update([...own, { id: q.id, counts: q.objectives.map(o => o.count), claimed: false, completions: 0 }]);
          const map = Quests.mapMarkers(0).find(m => m.npc === q.npc), field = Quests.markerInfo(q.npc);
          return map.symbol === '?' && field.symbol === '?' && map.color === '#64b5ff' && field.color === '#64b5ff';
        } finally { Quests.update(own); }
      }), 'Repeatable question marks remain blue on NPCs and maps');
      const stack = await page.evaluate(() => {
        document.getElementById('announce').replaceChildren();
        Announce.show('A treasure chest has appeared!', 'treasure');
        for (let i = 1; i <= 6; i++) Field.error('Error ' + i);
        const rows = [...document.querySelectorAll('#error-messages [data-kind="error"]')], style = getComputedStyle(rows[0]);
        const cv = document.getElementById('fieldcv'), rect = cv.getBoundingClientRect();
        const before = rows[0].getBoundingClientRect();
        for (const edge of [0, 1600]) WorldFeedback.draw({ canvas: cv, hero: { x: edge, y: edge }, project: () => [edge, edge], width: 1600, height: 900, drops: [], blocked: true });
        const after = rows[0].getBoundingClientRect();
        const animation = rows[0].getAnimations().find(a => a.animationName === 'error-fade');
        animation.pause(); animation.currentTime = 1000;
        const midpointOpacity = +getComputedStyle(rows[0]).opacity;
        animation.currentTime = 0; animation.play();
        return { texts: rows.map(n => n.textContent), border: style.borderTopWidth, background: style.backgroundColor,
          color: style.color, shadow: style.boxShadow, animation: style.animationName, duration: style.animationDuration,
          midpointOpacity,
          stays: Math.abs(before.x-after.x) < 1 && Math.abs(before.y-after.y) < 1,
          atAnnouncement: before.top >= rect.top && before.top < rect.top + rect.height * .1,
          order: rows.every((n, i) => i === 0 || n.getBoundingClientRect().top > rows[i-1].getBoundingClientRect().top) };
      });
      check(JSON.stringify(stack.texts) === JSON.stringify(['Error 2','Error 3','Error 4','Error 5','Error 6']) && stack.order, 'Five errors fit simultaneously, oldest first and newest at the bottom');
      check(stack.border === '0px' && stack.background === 'rgba(0, 0, 0, 0)' && stack.color === 'rgb(255, 74, 74)' && stack.shadow === 'none', 'Errors are plain red text without a box, border or shadow');
      check(stack.stays && stack.atAnnouncement, 'Errors stay in the announcement area instead of following the hero');
      check(stack.animation === 'error-fade' && stack.duration === '2s', 'Errors fade over exactly two seconds, including with reduced motion');
      check(stack.midpointOpacity > .45 && stack.midpointOpacity < .55, 'The red text is half transparent midway through its fade');
      await wait(page, () => !document.querySelector('#error-messages [data-kind="error"]'));
      check(await page.locator('#announce [data-kind="treasure"]').count() === 1, 'Error expiry leaves the ordinary chest announcement intact');
      await page.evaluate(() => { Field.error('A wall blocks your skill.'); Field.error('A wall blocks your skill.'); });
      check(await page.locator('#error-messages [data-kind="error"]').count() === 2, 'Repeated errors occupy separate rows in the five-message stack');
      await page.evaluate(() => WorldFeedback.reset());
      check(await page.locator('#error-messages [data-kind="error"]').count() === 0, 'Reset clears the error stack');
    }
    // One shortcut kill creates a real gold drop; no combat or grinding is needed.
    const spawn = await page.evaluate(() => WORLD_MAP.slimes.find(s => s.kind === 'green' && !s.ambush));
    await debug(page, { op: 'teleport', zone: 0, x: spawn.x + 4, y: spawn.y });
    await wait(page, spawn => Math.hypot(Field.hero.x-spawn.x, Field.hero.y-spawn.y) < 12 && Field.slimes.some(s => s.kind === 'green' && !s.dead), spawn);
    const enemy = await page.evaluate(() => Field.slimes.filter(s => s.kind === 'green' && !s.dead).sort((a,b) => Math.hypot(a.x-Field.hero.x,a.y-Field.hero.y)-Math.hypot(b.x-Field.hero.x,b.y-Field.hero.y))[0].id);
    await page.evaluate(id => {
      const enemy = Field.slimes.find(s => s.id === id), objects = WORLD_MAP.objects;
      const retreat = [[7,0],[-7,0],[0,7],[0,-7],[6,6]].map(([dx,dy]) => ({x:enemy.x+dx,y:enemy.y+dy})).find(({x,y}) =>
        objects.every(o => o.width ? Math.abs(x-o.x)>o.width/2+.7 || Math.abs(y-o.y)>o.depth/2+.7 : Math.hypot(x-o.x,y-o.y)>o.r+.7));
      if (!retreat) throw Error('No clear position outside the loot magnet');
      Online.send({type:'debug',command:{op:'kill_enemy',id}});
      Online.send({type:'debug',command:{op:'teleport',zone:0,...retreat}});
    }, enemy);
    await wait(page, () => Field._debug.drops.some(d => !d.item && d.value > 0));
    const gold = await page.evaluate(() => Field._debug.drops.find(d => !d.item && d.value > 0));
    await wait(page, id => { const d=Field._debug.drops.find(d=>d.id===id); if(!d)return false; const [x,y]=Field._debug.w2s(d.x,d.y); return x>200 && x<1400 && y>100 && y<800; }, gold.id);
    await wait(page, id => {
      const d = Field._debug.drops.find(d => d.id === id); if (!d) return false;
      const point = Field._debug.w2s(d.x, d.y), old = window.goldProbePoint;
      window.goldProbeStable = old && Math.hypot(point[0]-old[0], point[1]-old[1]) < .3 ? (window.goldProbeStable || 0) + 1 : 0;
      window.goldProbePoint = point;
      return d.t > 1 && window.goldProbeStable >= 4;
    }, gold.id);
    const cursor = await page.evaluate(id => {
      const d=Field._debug.drops.find(d=>d.id===id), [x,y]=Field._debug.w2s(d.x,d.y), r=document.getElementById('fieldcv').getBoundingClientRect();
      return { x:r.x+(x-16)/1600*r.width, y:r.y+(y-d.z)/1600*r.width };
    }, gold.id);
    await page.mouse.move(cursor.x,cursor.y);
    await page.locator('#loot-gold-tooltip').waitFor({ state: 'visible' });
    const placement = await page.locator('#loot-gold-tooltip').evaluate(n => {
      const r=n.getBoundingClientRect(); return { body:n.parentElement===document.body, x:r.left, y:r.top, text:n.textContent };
    });
    await screenshot(page, 'feedback-gold-tooltip.png');
    check(placement.body && Math.abs(placement.x-cursor.x-14)<2 && Math.abs(placement.y-cursor.y-12)<2, 'Gold tooltip sits beside the hovered drop on a letterboxed wide screen: '+JSON.stringify({cursor,placement}));
    check(placement.text.includes(String(gold.value)), 'The gold tooltip shows the real pile amount');
    await page.mouse.move(10,10);
    check(await page.locator('#loot-gold-tooltip').isHidden(), 'Leaving the loot hides its gold tooltip');
    check(errors.length === 0, 'No browser errors: '+errors.join('; '));
    await page.close(); console.log(`feedback-corrections: ${checks} checks passed; ${world.runDir}`); return;
  }
  await wait(page, () => Field.hero.travelStops?.includes('travel_saltby'));
  check(true, 'Arriving at the Saltby dock discovers its hub without talking');
  const entry = await page.evaluate(() => {
    const c = WORLD_MAP.city, n = WORLD_MAP.npcs.find(n => n.id === 'travel_alderhaven');
    for (let y = c.y0 + 1; y < c.y1 - 1; y += 2) for (let x = c.x0 + 1; x < c.x1 - 1; x += 2) {
      if (Math.hypot(x-n.x, y-n.y) > 5 && WORLD_MAP.objects.every(o => o.width ? Math.abs(x-o.x) > o.width/2+.7 || Math.abs(y-o.y) > o.depth/2+.7 : Math.hypot(x-o.x,y-o.y) > o.r+.7)) return { x, y };
    }
  });
  await debug(page, { op: 'teleport', zone: 0, ...entry });
  await wait(page, () => Field.hero.travelStops?.includes('travel_alderhaven'));
  check(await page.evaluate(() => !City.open && todoNotices.filter(n => n.text === 'Discovered Alderhaven for Spark Travel.').length === 1), 'City entry unlocks Alderhaven once, without opening a dialogue');
  await quest(page, 'welcome', 'accept'); await quest(page, 'fold_strays', 'accept');
  await quest(page, 'welcome', 'complete');
  await wait(page, () => todoNotices.some(n => n.text === 'Quest completed: A Home in Alderhaven'));
  check(await page.locator('#announce').textContent().then(t => t.includes('Quest completed: A Home in Alderhaven')), 'Objective completion paints a toast naming the quest');
  await page.waitForTimeout(350);
  check(await page.evaluate(() => todoNotices.filter(n => n.text === 'Quest completed: A Home in Alderhaven').length === 1), 'Repeated snapshots do not repeat the completion toast');
  await page.evaluate(() => { Quests.track('welcome'); Quests.show(); });
  check(await page.evaluate(() => {
    const ids = [...document.querySelectorAll('#quest-list .journal-quest')].map(n => n.dataset.quest);
    return ids.indexOf('fold_strays') >= 0 && ids.indexOf('fold_strays') < ids.indexOf('welcome');
  }), 'An unfinished quest stays above a tracked quest ready to turn in');
  await screenshot(page, 'todo-quest-journal.png');
  await page.evaluate(() => Quests.close()); await quest(page, 'welcome', 'claim');
  await quest(page, 'slime_patrol', 'accept'); await quest(page, 'slime_patrol', 'complete'); await quest(page, 'slime_patrol', 'claim');
  await quest(page, 'meadow_bounty', 'accept'); await quest(page, 'meadow_bounty', 'complete'); await quest(page, 'meadow_bounty', 'claim');
  await page.evaluate(() => Quests.show());
  check(await page.evaluate(() => {
    const done = document.querySelector('#quest-list > .quest-completed');
    return done === document.querySelector('#quest-list').lastElementChild && !!done.querySelector('[data-quest="meadow_bounty"][data-status="completed"]');
  }), 'Claimed quests, including repeatable quest history, appear in the final section');
  await page.evaluate(() => Quests.close());
  const marker = await page.evaluate(() => {
    const q = WORLD_MAP.quests.find(q => q.id === 'meadow_bounty');
    return Quests.mapMarkers(0).find(m => m.npc === q.npc);
  });
  check(marker?.repeatable && marker.color === '#64b5ff', 'Available repeatable quest marker is blue');
  const mini = await page.evaluate(id => {
    const original = Quests.mapMarkers, cv = document.getElementById('minimap'), g = cv.getContext('2d');
    try {
      Quests.mapMarkers = zone => original(zone).filter(m => m.npc !== id); Field._debug.drawFrame(4); const a = g.getImageData(0, 0, cv.width, cv.height).data;
      Quests.mapMarkers = original; Field._debug.drawFrame(4); const b = g.getImageData(0, 0, cv.width, cv.height).data;
      let blue = 0; for (let i = 0; i < a.length; i += 4) if (a[i] !== b[i] || a[i+1] !== b[i+1] || a[i+2] !== b[i+2]) {
        if (Math.abs(b[i]-100)<20 && Math.abs(b[i+1]-181)<20 && Math.abs(b[i+2]-255)<20) blue++;
      }
      return blue;
    } finally { Quests.mapMarkers = original; }
  }, marker.npc);
  check(mini > 2, 'The actual minimap paints the repeatable marker in blue');
  check(await page.evaluate(() => {
    const q = WORLD_MAP.zones.flatMap(a => a.quests || []).find(q => q.id === 'city_gel');
    Quests.update([{ id: q.id, counts: q.objectives.map(() => 0), claimed: false, completions: 0 }]); Quests.track(q.id);
    const points = q.objectives.flatMap(o => QUEST_SOURCES[o.target] || []).filter(p => p.zone === 0), a = points[0], b = points.at(-1);
    const first = Quests.navigationTarget(0, a.x, a.y), second = Quests.navigationTarget(0, b.x, b.y);
    return first.x === a.x && first.y === a.y && second.x === b.x && second.y === b.y;
  }), 'Navigation reselects real gathering targets as the hero moves, without stale cached coordinates');
  await page.evaluate(() => Online.send({ type: 'use_item', item: 'not_a_real_item' }));
  await page.locator('#error-messages [data-kind="error"]').first().waitFor({ state: 'visible' });
  check(await page.locator('#error-messages [data-kind="error"]').count() > 0, 'A real refused action appears in the announcement area');
  await page.evaluate(() => { WorldFeedback.reset(); Field.error('A wall blocks your skill.'); Field.error('A wall blocks your skill.'); });
  check(await page.locator('#error-messages [data-kind="error"]').count() === 2, 'Repeated action errors keep their own rows');
  await screenshot(page, 'todo-error-announcement.png');
  await wait(page, () => !document.querySelector('#error-messages [data-kind="error"]'));
  check(true, 'Brief error messages fade and expire automatically');
  await page.evaluate(() => {
    Online.send({ type: 'debug', command: { op: 'drop_item', item: 'slime_gel', quantity: 3 } });
    Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: Field.hero.x + 4, y: Field.hero.y } });
  });
  await wait(page, () => Field._debug.drops.some(d => d.item === 'slime_gel'));
  const drop = await page.evaluate(() => Field._debug.drops.find(d => d.item === 'slime_gel'));
  assert.ok(drop, 'The real drop exists');
  await page.waitForTimeout(650);
  const cursor = await page.evaluate(id => {
    const d = Field._debug.drops.find(d => d.id === id), [x,y] = Field._debug.w2s(d.x,d.y), r = document.getElementById('fieldcv').getBoundingClientRect();
    return { x: r.x + (x + 12) / 1600 * r.width, y: r.y + (y - d.z) / 1600 * r.width };
  }, drop.id);
  await page.mouse.move(cursor.x, cursor.y);
  await page.locator('#item-tooltip').waitFor({ state: 'visible' });
  check((await page.locator('#item-tooltip').textContent()).includes('Slime Gel') && (await page.locator('#item-tooltip').textContent()).includes('3 on the ground'), 'Hovering a real ground pile reveals its item and quantity');
  await screenshot(page, 'todo-loot-hover.png');
  await debug(page, { op: 'teleport', zone: 0, x: drop.x, y: drop.y });
  await wait(page, id => !Field._debug.drops.some(d => d.id === id), drop.id);
  check(await page.locator('#item-tooltip').isHidden(), 'Picking up a hovered pile dismisses its tooltip');
  for (const kind of ['oak_tree', 'birch_tree', 'apple_tree', 'willow_tree']) {
    const target = await page.evaluate(kind => {
      const objects = WORLD_MAP.objects;
      for (const o of objects.filter(o => o.kind === kind)) for (const d of [1.5, 2, 2.5, 3]) {
        const x = o.x-d, y = o.y-d;
        if (objects.every(p => p.width ? Math.abs(x-p.x)>p.width/2+.5 || Math.abs(y-p.y)>p.depth/2+.5 : Math.hypot(x-p.x,y-p.y)>p.r+.5)) return { x, y, tree: o };
      }
    }, kind);
    assert.ok(target, `${kind}: clear point behind a real tree`);
    await debug(page, { op: 'teleport', zone: 0, x: target.x, y: target.y });
    await wait(page, target => Math.hypot(Field.hero.x-target.x, Field.hero.y-target.y) < 1, target);
    await wait(page, target => {
      const [x, y] = Field._debug.w2s(target.tree.x, target.tree.y), r = document.getElementById('fieldcv').getBoundingClientRect();
      return x > 350 && x < 1250 && y > 350 && y < r.height / r.width * 1600 - 60;
    }, target);
    const result = await page.evaluate(tree => {
      const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), original = City.drawObject;
      let faded = false, solid = false;
      City.drawObject = (ctx, o, x, y, alpha) => { if (o.kind === tree.kind && o.x === tree.x && o.y === tree.y) { faded ||= alpha < 1; if (solid) alpha = 1; } return original(ctx, o, x, y, alpha); };
      try {
        Field._debug.drawFrame(4); const a = g.getImageData(0,0,cv.width,cv.height).data;
        solid = true; Field._debug.drawFrame(4); const b = g.getImageData(0,0,cv.width,cv.height).data;
        let changed = 0; for (let i=0;i<a.length;i+=4) if (Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>12) changed++;
        return { faded, changed };
      } finally { City.drawObject = original; }
    }, target.tree);
    check(result.faded && result.changed > 250, `${kind} visibly fades in the real renderer when the hero stands behind it (${JSON.stringify(result)})`);
  }
  await page.close();
  const swedish = await player('sv');
  check(await swedish.evaluate(() => {
    const q = WORLD_MAP.zones.flatMap(a => a.quests || []).find(q => q.id === 'crags_onward');
    Quests.update([{ id: q.id, counts: [0], claimed: false, completions: 0 }]); Quests.track(q.id);
    const target = Quests.navigationTarget(0, Field.hero.x, Field.hero.y);
    return !!target?.viaPortal && target.destinationZone === 1 && Quests.mapMarkers(1).some(m => m.quest === q.id);
  }), 'Swedish reach guidance resolves the correct zone using its untranslated identity');
  await swedish.evaluate(() => { WorldFeedback.reset(); Field.error('A wall blocks your skill.'); });
  check((await swedish.locator('#error-messages [data-kind="error"]').textContent()).includes('vägg'), 'The red error announcement translates the action refusal into Swedish');
  check(errors.length === 0, 'No browser errors: ' + errors.join('; '));
  await swedish.close();
  console.log(`todo-feedback-ui: ${checks} focused checks passed; ${world.runDir}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); await world.stop(); });
