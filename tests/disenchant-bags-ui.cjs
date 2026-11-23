// Run with TOUCH_SIZE=844x390 bash scripts/test-touch-bounded.sh tests/disenchant-bags-ui.cjs.
const { run, debug, record } = require('./lib/touch.cjs');

const item = 'necklace_moonstone_l1_green';
const trainer = 'alder_enchanting';

const suite = {
  name: 'disenchant-bags',
  async test({ player, check }) {
    const page = await player('DisenchantBag', { characterClass: 'warrior' });
    const { x, y } = await page.evaluate(id => WORLD_MAP.npcs.find(npc => npc.id === id), trainer);
    await debug(page, { op: 'teleport', zone: 0, x, y });
    await page.waitForFunction(({x, y}) => Math.hypot(Field.hero.x - x, Field.hero.y - y) < 1, { x, y });
    await page.evaluate(npc => Online.send({ type: 'interact', npc, offer: 'learn_enchanting' }), trainer);
    await page.locator('#npc-dialogue').waitFor({ state: 'visible' });
    await page.locator('#npc-x').tap();

    await debug(page, { op: 'give_item', item, quantity: 2 });
    await page.waitForFunction(id => Inventory.looseCopies(id).length === 2, item);
    const [first, second] = await page.evaluate(id => Inventory.looseCopies(id).map(gear => gear.id), item);
    const cell = id => page.locator('#inventory-list [data-key="' + item + '@' + id + '"] .item-tile');
    const details = page.locator('#bag-details');
    const preview = details.getByRole('button', { name: 'Disenchant this copy', exact: true });
    const confirm = details.getByRole('button', { name: 'Confirm disenchant', exact: true });

    await record(page);
    await page.locator('#inventory-open').tap();
    await page.locator('#enchanting-toggle').tap();
    await page.getByRole('button', { name: 'Disenchant', exact: true }).tap();
    check(await page.locator('#enchanting-panel select').count() === 0, 'Disenchant has no equipment dropdown');
    check(await page.locator('#bag-tabs').isVisible(), 'the real bag tabs remain visible');
    check(await page.locator('#inventory-list .bag-cell').count() === 16, 'the native backpack keeps its layout');

    await page.locator('#bag-search').fill('moonstone');
    check(await page.locator('#inventory-list .item-tile').count() === 2, 'bag search filters the same inventory grid');
    await cell(first).tap();
    check((await details.textContent()).includes('Copy #' + first), 'the first physical copy is previewed');
    await preview.tap();
    check(await confirm.isVisible(), 'preview offers a separate confirmation in the bag details');
    await cell(second).tap();
    check((await details.textContent()).includes('Copy #' + second)
      && (await details.textContent()).includes('2 × Enchanting Dust'), 'the other copy has its own preview and yield');
    check(await cell(second).getAttribute('aria-pressed') === 'true' && !await confirm.count(),
      'selecting another native tile highlights it and resets confirmation');
    check(await page.evaluate(() => !touchSent.some(p => p.type === 'enchanting' && p.request.op === 'disenchant')),
      'selecting and reviewing bag items has not destroyed any gear');

    await preview.tap();
    await confirm.tap();
    await page.waitForFunction(({item, first}) => Inventory.bagQuantity('enchant_dust') === 2
      && Inventory.looseCopies(item).length === 1 && Inventory.looseCopies(item)[0].id === first,
    { item, first });
    check(await cell(first).isVisible(), 'the other copy remains selectable in the bag');
    check(await page.evaluate(id => touchSent.filter(p => p.type === 'enchanting' && p.request.op === 'disenchant')
      .map(p => p.request.copy).join(',') === String(id), second), 'only the selected copy is sent for disenchanting');
    await page.locator('#enchanting-toggle').tap();
    check(!await confirm.count() && await page.locator('#inventory-list').isVisible(),
      'closing Enchanting restores ordinary bag details');
  },
};

run([suite]).catch(error => { console.error(error); process.exitCode = 1; });
