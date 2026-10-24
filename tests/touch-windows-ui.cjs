const fs = require('node:fs');
const path = require('node:path');
const { run, replace, debug, safeSpot } = require('./lib/touch.cjs');
const smith = JSON.parse(fs.readFileSync(path.join(__dirname, '../world/map.txt'), 'utf8')).npcs.find(n => n.id === 'smith');
const suite = {
  name: 'touch-windows',
  mutate: page => replace(page, 'touch.css', 'min-width: var(--touch-target); min-height: var(--touch-target);', 'min-width: 12px; min-height: 12px;'),
  async test({ player, check, width, height, out, sleep }) {
    const page = await player('TouchWindows'), failures = [];
    async function clear() {
      await page.evaluate(() => {
        City.close(false); Quests.close(false); Skillbar.close(false); WorldMap.close(false); Bank.close(); Social.close(); Inspect.close(); WhatsNew.close(); Settings.close(false); GMTest.close();
        for (const id of ['pause', 'equipment', 'rebirth-dialog', 'connection-overlay', 'sign-panel']) document.getElementById(id).hidden = true;
        Field.setPaused(false);
      });
    }
    async function audit(selector, name) {
      await page.locator(selector).waitFor({ state: 'visible' });
      await page.evaluate(() => Settings.applyScale()); await sleep(100);
      const result = await page.locator(selector).evaluate(el => {
        const stage = document.querySelector('#stage').getBoundingClientRect(), r = el.getBoundingClientRect(), problems = [];
        if (r.left < stage.left - 1 || r.top < stage.top - 1 || r.right > stage.right + 1 || r.bottom > stage.bottom + 1) problems.push(`window outside stage: ${[r.left, r.top, r.right, r.bottom].map(Math.round)}`);
        if (r.width < stage.width * .3 || r.height < 44) problems.push('window collapsed');
        const controls = [...el.querySelectorAll('button, select, input:not([type=hidden]):not([type=checkbox]):not([type=radio]), summary, [role=button]')].filter(n => {
          if (!n.getClientRects().length || !n.getBoundingClientRect().width) return false;
          for (let p = n.parentElement; p && p !== el; p = p.parentElement) if (p.tagName === 'DETAILS' && !p.open && p.querySelector(':scope > summary') !== n) return false;
          return true;
        });
        for (const n of controls) {
          n.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
          const b = n.getBoundingClientRect(), label = n.id || n.getAttribute('aria-label') || n.textContent.trim().slice(0, 45);
          if (b.width < 43.8 || b.height < 43.8) problems.push(`${label}: target ${b.width.toFixed(1)} × ${b.height.toFixed(1)}`);
          if (b.left < stage.left - 1 || b.right > stage.right + 1 || b.top < stage.top - 1 || b.bottom > stage.bottom + 1) problems.push(`${label}: unreachable stage edge`);
          const hit = document.elementFromPoint(b.left + b.width/2, b.top + b.height/2);
          if (!n.disabled && (!hit || !(hit === n || n.contains(hit)))) problems.push(`${label}: covered by ${hit?.id || hit?.className || 'nothing'}`);
          for (let parent = n.parentElement; parent && parent !== el.parentElement; parent = parent.parentElement) {
            const cs = getComputedStyle(parent), p = parent.getBoundingClientRect();
            if (/(auto|scroll|hidden|clip)/.test(cs.overflowY) && (b.top < p.top - 2 || b.bottom > p.bottom + 2)) problems.push(`${label}: clipped vertically by ${parent.id || parent.className}`);
            if (/(auto|scroll|hidden|clip)/.test(cs.overflowX) && (b.left < p.left - 2 || b.right > p.right + 2)) problems.push(`${label}: clipped horizontally by ${parent.id || parent.className}`);
          }
        }
        return { problems, controls: controls.length, rect: { width: r.width, height: r.height } };
      });
      if (result.problems.length) failures.push({ name, ...result });
      if (process.env.MUTATE) check(!result.problems.length, `mutation detected in ${name}: ${result.problems.join('; ')}`);
      check(result.controls > 0, `${name} has real controls to inspect`);
      await page.screenshot({ path: `${out}/${name}-${width}x${height}.png` });
      console.log(`${name}: ${result.controls} controls, ${result.problems.length} layout issues`);
    }
    await page.evaluate(() => Keys.invoke('menu')); await audit('#pause .pause-panel', 'menu'); await clear();
    await page.evaluate(() => { Field.setPaused(true); Settings.show(); }); await audit('#settings-panel .settings-panel', 'settings');
    await page.locator('#set-keys').click(); await audit('#keys-panel .keys-panel', 'keyboard'); await clear();
    await page.evaluate(() => Skillbar.show()); await audit('#skills-panel .skills-panel', 'skills'); await clear();
    await page.evaluate(() => Quests.show()); await audit('#quest-journal .quest-panel', 'quests'); await clear();
    await debug(page, { op: 'explore_all' }); await page.waitForFunction(() => Object.values(Field.explored || {}).filter(Boolean).length > 20);
    await page.evaluate(() => WorldMap.show()); await audit('#worldmap .wm-panel', 'world-map');
    await page.locator('.wm-tile[data-zone="0"]').click(); await audit('#worldmap .wm-panel', 'zone-map'); await clear();
    await page.keyboard.press('e'); await audit('.equipment-workspace', 'character-bags'); await clear();
    await page.evaluate(() => Keys.invoke('bags')); await audit('.equipment-workspace', 'bags'); await clear();
    await page.evaluate(() => Social.show('party')); await audit('#social-panel .social-panel', 'party-raid'); await clear();
    await page.evaluate(() => Social.show('pvp')); await audit('#social-panel .social-panel', 'arena'); await clear();
    await page.evaluate(() => { document.querySelector('#rebirth-dialog').hidden = false; }); await audit('#rebirth-dialog .rebirth-dialog', 'rebirth'); await clear();
    await page.evaluate(() => WhatsNew.show()); await audit('#whats-new .news-panel', 'whats-new'); await clear();
    await page.evaluate(() => { document.querySelector('#connection-overlay').hidden = false; }); await audit('#connection-overlay .connection-panel', 'connection'); await clear();
    await page.evaluate(() => GMTest.open()); await audit('#gmtest-panel .gmtest-window', 'gm-dungeon-gauntlet'); await clear();
    await debug(page, { op: 'teleport', zone: 0, x: smith.x, y: smith.y + 1 });
    await page.waitForFunction(p => Math.hypot(Field.hero.nx-p.x, Field.hero.ny-p.y) < 2, smith);
    await debug(page, { op: 'give_item', item: 'warrior_weapon_royal_l10_purple', quantity: 1, force: true });
    await sleep(550); await page.evaluate(() => Online.send({ type: 'interact', npc: 'smith' }));
    await audit('#npc-dialogue .gossip-window', 'npc');
    await page.locator('#npc-offers [data-view="sell"]').click();
    await page.locator('#sell-pick [data-item="warrior_weapon_royal_l10_purple"]').waitFor(); await audit('#npc-dialogue .gossip-window', 'sell');
    await page.locator('#sell-pick [data-item="warrior_weapon_royal_l10_purple"] button').click();
    await page.locator('#sell-confirm').click(); await audit('#sell-warning', 'sell-confirmation');
    await page.locator('#sell-cancel').click(); await page.locator('#npc-back').click();
    await page.locator('#npc-dialogue [data-offer="repair"]').click(); await audit('#npc-dialogue .gossip-window', 'repair');
    await clear();
    await debug(page, { op: 'teleport', zone: 0, x: 39, y: 83.6 });
    await page.waitForFunction(() => Math.hypot(Field.hero.nx-39, Field.hero.ny-83.6) < 2); await sleep(550);
    await page.evaluate(() => Online.send({ type: 'interact', npc: 'banker_alderhaven' }));
    await page.locator('#npc-dialogue [data-offer="bank"]').click(); await audit('#bank-panel .bank-panel', 'bank'); await clear();
    const other = await player('InspectTouch'); await safeSpot(other); await safeSpot(page);
    const id = await other.evaluate(() => Online.id);
    await page.waitForFunction(id => Field.remotePlayers.some(p => p.id === id), id);
    await page.evaluate(id => Inspect.open(id, 'InspectTouch'), id); await page.waitForFunction(() => !document.querySelector('#inspect-body').hidden);
    await audit('#inspect-panel .inspect-window', 'inspect'); await clear();
    await page.evaluate(id => Trade.request(id), id); await other.locator('#trade-accept').click();
    await audit('#trade-panel .trade-panel', 'trade'); await page.locator('#trade-cancel').click(); await clear();
    await page.evaluate(id => Online.send({ type: 'social', command: { op: 'party_invite', id } }), id);
    await other.waitForFunction(() => Social.state.incoming.some(i => i.kind === 'party'));
    const leader = await page.evaluate(() => Online.id);
    await other.evaluate(id => Online.send({ type: 'social', command: { op: 'party_accept', id } }), leader);
    await page.waitForFunction(() => Social.state.party?.members.length === 2);
    await page.evaluate(() => Online.send({ type: 'social', command: { op: 'party_raid', on: true } }));
    await page.waitForFunction(() => Social.state.party?.raid);
    await page.evaluate(() => Social.show('party')); await audit('#social-panel .social-panel', 'raid-members'); await clear();
    await debug(page, { op: 'set_level', level: 99 });
    await debug(page, { op: 'teleport', zone: 46, x: 35, y: 303 });
    await page.waitForFunction(() => Field.zone === 46 || Field.zoneTheme === 'chained_forge'); await sleep(550);
    await page.evaluate(() => Online.send({ type: 'interact', npc: 'cf_quartermaster' })); await audit('#npc-dialogue .gossip-window', 'raid-hiring'); await clear();
    await debug(page, { op: 'teleport', zone: 41, x: 64, y: 110 });
    await page.waitForFunction(() => Field.zoneTheme === 'nornroot');
    const sign = await page.evaluate(() => Field.signs[0]);
    if (sign) {
      await debug(page, { op: 'teleport', x: sign.x, y: sign.y, zone: await page.evaluate(() => Field.zone) });
      await page.waitForFunction(s => Math.hypot(Field.hero.nx-s.x, Field.hero.ny-s.y) < 2, sign);
      await page.evaluate(id => Online.send({ type: 'sign_read', sign: id }), sign.id); await audit('#sign-panel', 'boss-sign'); await clear();
    }

    // At the largest global scale the same window cap still has to protect the stage.
    await page.evaluate(() => { Prefs.set({ uiScale: 1.5 }); Settings.applyScale(); Skillbar.show(); }); await audit('#skills-panel .skills-panel', 'skills-150'); await clear();
    fs.writeFileSync(`${out}/windows-${width}x${height}.txt`, JSON.stringify(failures, null, 2));
    check(failures.length === 0, `window layout failures: ${JSON.stringify(failures).slice(0, 12000)}`);
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
