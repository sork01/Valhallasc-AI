const { run, replace, debug, safeSpot } = require('./lib/touch.cjs');
const suite = {
  name: 'town-window',
  mutate(page) {
    if (process.env.MUTATE === 'windows') return replace(page, 'settings.js', 'if (inside) return;', 'return;');
    if (process.env.MUTATE === 'merchant') return replace(page, 'shop.js', "if (!npc.buys) { lastNotice='This person does not buy items. Sell to a merchant or smith.'; draw(); return; }", '');
    if (process.env.MUTATE === 'mobile-default') return replace(page, 'game.js', "matchMedia('(pointer: coarse)').matches ? .6 : .8", '.8');
    if (process.env.MUTATE === 'mobile-bars') return replace(page, 'touch.css', 'width: calc(320px / .8);', 'width: calc(320px / var(--ui, .8));');
    if (process.env.MUTATE === 'fullscreen') return replace(page, 'touch.js', "fullscreen.id = 'touch-fullscreen'", "fullscreen.id = 'removed-fullscreen'");
    return replace(page, 'worldmap.js', 'selectedPerson = n.id; markPerson(z);', 'selectedPerson = null; markPerson(z);');
  },
  async test({ player, check, width, height, out, sleep }) {
    const page = await player('TownWindows', { userAgent: 'Mozilla/5.0 (Linux; Android 15; Odin 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36' });
    await safeSpot(page);
    check(await page.evaluate(() => Prefs.uiScale === .6), 'fresh mobile UI defaults to 60 percent');
    const bars = () => ['#touch-actions', '#touch-quickuse .quick-slot'].map(s => { const r=document.querySelector(s).getBoundingClientRect(); return [r.width,r.height]; });
    const small = await page.evaluate(bars);
    await page.evaluate(() => { Prefs.set({uiScale:1}); Settings.applyScale(); });
    const large = await page.evaluate(bars);
    check(large.every((r,i) => r.every((v,j) => Math.abs(v/small[i][j]-1/.6)<.03)), 'top menu and food bar follow UI size');
    await page.evaluate(() => { Prefs.set({uiScale:.6}); Settings.applyScale(); });
    if (await page.evaluate(() => document.fullscreenEnabled)) {
      check(await page.locator('#touch-fullscreen').isVisible(), 'fullscreen is available directly on the top bar');
      await page.locator('#touch-fullscreen').tap();
      await page.waitForFunction(() => document.fullscreenElement?.id === 'stage');
      check(await page.locator('#touch-fullscreen').textContent() === 'Exit fullscreen', 'top bar reflects fullscreen state');
      await page.locator('#touch-fullscreen').tap();
      await page.waitForFunction(() => !document.fullscreenElement);
    }

    async function outside(id) {
      const r = await page.locator('#' + id).boundingBox();
      check(!!r, `${id} opens`);
      if (width === 1024) await page.mouse.click(r.x + 2, r.y + 2);
      else await page.touchscreen.tap(r.x + 2, r.y + 2);
      await page.waitForFunction(id => document.getElementById(id).hidden, id);
      check(await page.locator('#' + id).isHidden(), `${id} closes outside with ${width === 1024 ? 'mouse' : 'touch'}`);
    }
    for (const [open, root, inside] of [
      [() => document.getElementById('inventory-open').click(), 'equipment', '#bag-title'],
      [() => Skillbar.show(), 'skills-panel', '#skills-title'],
      [() => Quests.show(), 'quest-journal', '#quest-title'],
      [() => Social.show(), 'social-panel', '#social-title'],
      [() => document.getElementById('p-settings').click(), 'settings-panel', '#set-language'],
    ]) {
      await page.evaluate(open); await page.locator(inside).tap();
      check(await page.locator('#' + root).isVisible(), `${root} stays open inside`);
      await outside(root);
      if (root === 'settings-panel') await outside('pause');
    }
    console.log('mobile sizing, fullscreen and window dismissal passed');
    const before = await page.evaluate(() => [Field.hero.nx, Field.hero.ny]);
    await sleep(250);
    check(await page.evaluate(before => Math.hypot(Field.hero.nx - before[0], Field.hero.ny - before[1]) < .1, before), 'outside dismissal does not walk the hero');
    for (const [zone, target] of [[4, 'city_stable'], [9, 'banker_nacrehold'], [17, 'banker_asterion'], [0, 'smith']]) {
      const arrival = await page.evaluate(zone => {
        const z = zone ? WORLD_MAP.zones[zone - 1] : WORLD_MAP;
        return z.city.entry || z.city.plaza;
      }, zone);
      await debug(page, { op: 'teleport', zone, x: arrival.x, y: arrival.y });
      await page.waitForFunction(zone => Field.zone === zone, zone);
      await page.evaluate(() => WorldMap.show());
      await page.locator(`.wm-tile[data-zone="${zone}"]`).tap();
      await page.waitForFunction(() => WorldMap.view === 'zone');
      check(await page.locator('.wm-people-list').isVisible(), `zone ${zone} has a people directory`);
      check(await page.locator('#wm-side').evaluate(n => n.getBoundingClientRect().width >= 160), 'directory keeps a readable width on mobile');
      check(await page.locator('.wm-stage').evaluate(n => {const r=n.getBoundingClientRect(); return Math.abs(r.width-r.height)<2;}), 'town map keeps square coordinates');
      const button = page.locator(`.wm-person-button[data-npc="${target}"]`);
      await button.tap();
      check(await button.getAttribute('aria-pressed') === 'true', `${target} selected`);
      const pin = page.locator(`.wm-person[data-npc="${target}"]`);
      check(await pin.isVisible(), `${target} is highlighted above fog`);
      check(await page.evaluate(target => {
        const z = Field.zone ? WORLD_MAP.zones[Field.zone - 1] : WORLD_MAP;
        const n = z.npcs.find(n => n.id === target), pin = document.querySelector('.wm-person');
        return Math.abs(parseFloat(pin.style.left) - n.x / z.size * 100) < .01 && Math.abs(parseFloat(pin.style.top) - n.y / z.size * 100) < .01;
      }, target), `${target} pin uses the real coordinates`);
      if (zone === 4) {
        await page.locator('.wm-people-search').pressSequentially('mounts');
        check(await button.isVisible(), 'search finds the horse seller by service');
        check(await button.textContent().then(t => t.includes('Greta')), 'Greta is named beside her mount service');
        await page.screenshot({ path: `${out}/town-directory-${width}x${height}.png` });
        await page.locator('.wm-people-search').fill('not-a-person');
        check(await page.locator('.wm-person-button:visible').count() === 0, 'search filters unrelated people');
        check(await page.getByText('No matching people.', { exact: true }).isVisible(), 'empty search gives feedback');
        await page.locator('.wm-people-search').fill('');
        await button.waitFor({ state: 'visible' });
        const sizes = await page.locator('.wm-person-button').evaluateAll(nodes => nodes.map(n => ({id:n.dataset.npc, h:n.getBoundingClientRect().height, min:getComputedStyle(n).minHeight, k:getComputedStyle(n).getPropertyValue('--window-k'), hidden:n.closest('[hidden]')?.tagName})));
        check(sizes.every(n => n.h >= 43), 'directory rows are touch sized: ' + JSON.stringify(sizes));
      }
      await outside('worldmap');
    }
    console.log('four town directories, search and real NPC pins passed');
    await debug(page, { op: 'give_item', item: 'slime_gel', quantity: 3 });
    async function visit(id) {
      const n = await page.evaluate(id => WORLD_MAP.npcs.find(n => n.id === id), id);
      await debug(page, { op: 'teleport', zone: 0, x: n.x, y: n.y + 1 });
      await page.waitForFunction(n => Math.hypot(Field.hero.nx - n.x, Field.hero.ny - n.y - 1) < .5, n);
      await page.evaluate(id => Field.visitNpc(id), id);
      await page.waitForFunction(() => Shop.open && document.querySelector('.merchant-workspace[aria-busy="false"]'));
    }
    await visit('apothecary');
    check(await page.locator('#merchant-service').textContent() === 'Does not buy items', 'non-buying vendor is labelled before selling');
    await page.locator('#inventory-list [data-item="slime_gel"] .item-tile').tap();
    check(await page.locator('#npc-notice').textContent() === 'This person does not buy items. Sell to a merchant or smith.', 'non-buying vendor explains the restriction and where to sell');
    check(await page.evaluate(() => Inventory.quantity('slime_gel')) === 3, 'non-buying vendor keeps the items');
    check(await page.locator('#npc-dialogue').isVisible(), 'using docked bags does not dismiss the merchant');
    await page.screenshot({ path: `${out}/merchant-selling-help-${width}x${height}.png` });
    await outside('npc-dialogue');
    check(await page.locator('#equipment .bag-window').count() === 1, 'outside closing restores the bags');
    await visit('smith');
    check(await page.locator('#merchant-service').textContent() === 'Buys items', 'buying merchant clearly accepts sales');
    await page.locator('#inventory-list [data-item="slime_gel"] .item-tile').tap();
    await page.waitForFunction(() => Inventory.quantity('slime_gel') === 0);
    check(/sold.*gold/i.test(await page.locator('#npc-notice').textContent()), 'Android browser tap sells to an accepting merchant');
    const valuable = await page.evaluate(() => WORLD_ITEMS.find(i => i.rarity === 'epic' && i.kind === 'necklace' && !i.starter).id);
    await debug(page, { op: 'give_item', item: valuable, quantity: 1 });
    await page.waitForFunction(id => document.querySelector('#inventory-list [data-item="' + id + '"] .item-tile'), valuable);
    await page.locator('#inventory-list [data-item="' + valuable + '"] .item-tile').tap();
    await page.locator('#sell-warning').waitFor({ state: 'visible' });
    const stage = await page.locator('#stage').boundingBox();
    await page.touchscreen.tap(stage.x + 2, stage.y + 2);
    await page.waitForFunction(() => !document.getElementById('sell-warning'));
    check(await page.evaluate(id => Inventory.quantity(id) === 1 && Shop.open, valuable), 'outside valuable confirmation cancels only the sale and preserves the item');
    await page.locator('.win-grip[data-window="npc-dialogue"]').click();
    check(await page.locator('#npc-dialogue').isVisible(), 'resize grip does not dismiss the merchant');
    await outside('npc-dialogue');
    console.log('non-buying vendor explanation, real sale and outside confirmation cancellation passed');
    await page.evaluate(() => Prefs.set({ uiScale: .8 }));
    await Promise.all([page.waitForEvent('load'), page.evaluate(() => Prefs.set({ lang: 'sv' }))]);
    await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    check(await page.evaluate(() => Prefs.uiScale === .8), 'explicit UI size is preserved after reload');
    await visit('apothecary');
    check(await page.locator('#merchant-service').textContent() === 'Köper inte föremål', 'buying restriction is translated into Swedish');
    await outside('npc-dialogue');
    await page.context().close();
    const desktop = await player('DesktopSize', { isMobile: false, hasTouch: false });
    check(await desktop.evaluate(() => Prefs.uiScale === .8), 'fresh mouse desktop keeps its 80 percent default');
    await desktop.context().close();
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
