// Run through scripts/test-touch-bounded.sh. Uses the server's roll packet shape and real equipped inventory.
const { run, replace, debug } = require('./lib/touch.cjs');

const suite = {
  name: 'roll-comparison',
  mutate: page => replace(page, 'rolls.js', '() => packet.gear ?? null', '() => null'),
  async test({ player, check, width }) {
    const phone = width < 900;
    const page = await player('CompareRoll', { characterClass: 'warrior', isMobile: phone, hasTouch: phone });
    const worn = 'warrior_armor_azure_l5_green';
    const drop = 'warrior_armor_crimson_l5_blue';
    await debug(page, { op: 'give_item', item: worn, quantity: 1, force: true });
    await page.waitForFunction(id => Inventory.quantity(id) === 1, worn);
    await page.evaluate(id => Online.send({ type: 'equip', slots: { chest: id } }), worn);
    await page.waitForFunction(id => Field.hero.equippedLook.warriorArmor === Inventory.definition(id).variant, worn);
    const sendRoll = () => page.evaluate(item => Rolls.onPacket({
      type: 'roll', op: 'start', id: 52, item, need: true, seconds: 30,
      gear: { item, id: 99001, rarity: 'rare', rank: 0, attack: 125.5, defense: 0, bonusStats: {} },
    }), drop);
    await sendRoll();
    const item = page.locator('.roll-card[data-roll="52"] .roll-name');
    const tooltip = page.locator('#item-tooltip');
    if (phone) await item.focus(); else await item.hover();
    await tooltip.waitFor();
    const comparison = tooltip.locator('.item-comparison');
    const wornName = await page.evaluate(id => Inventory.definition(id).name, worn);
    check((await comparison.textContent()).includes(wornName), 'the equipped item appears beside the drop stats');
    const attack = comparison.locator('[data-stat="attack"]');
    check((await attack.textContent()).includes('125.5') && await attack.locator('.stat-gain').count() === 1,
      'the positive delta uses the actual rolled attack');
    check(await comparison.locator('[data-stat="defense"] .stat-loss').count() === 1,
      'losing defense shows a negative delta');
    check(!(await tooltip.textContent()).includes('in bags'), 'the pending drop has no inventory footer');
    await item.focus();
    await page.evaluate(() => Rolls.onPacket({ type: 'roll', op: 'end', id: 52 }));
    await tooltip.waitFor({ state: 'hidden' });
    await page.evaluate(() => Online.send({ type: 'equip', slots: { chest: 'none' } }));
    await page.waitForFunction(() => Field.hero.equippedLook.warriorArmor === 'none');
    await sendRoll();
    await item.focus();
    check((await comparison.textContent()).includes('Empty slot'), 'an empty slot compares against zero');
    await page.context().close();
  },
};

run([suite]).catch(error => { console.error(error); process.exitCode = 1; });
