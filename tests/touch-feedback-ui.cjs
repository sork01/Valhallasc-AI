const { run, replace, debug, safeSpot, record } = require('./lib/touch.cjs');
const suite = {
  name: 'touch-feedback',
  mutate(page) {
    if (process.env.MUTATE === 'chat') return replace(page, 'touch.js', "coarse.matches && $('stage').classList.contains('touch-chat-open')", 'false');
    if (process.env.MUTATE === 'target') return replace(page, 'touch.js', "targetMenu.hidden = $('hud-target').hidden || !$('hud-target').classList.contains('has-menu');", 'targetMenu.hidden = false;');
    return replace(page, 'touch.css', 'bold calc(24px / var(--ui, .8))', 'bold calc(8px / var(--ui, .8))');
  },
  async test({ player, check, world, out, width, height }) {
    const page = await player('TouchFeedback'); await safeSpot(page);
    const chat = page.locator('#touch-actions [data-action="chat"]'), input = page.locator('#chat-input');
    const target = page.locator('#touch-actions [aria-controls="portrait-menu"]');
    check(await target.isHidden(), 'unavailable target actions take no space in the row');
    await chat.tap(); await input.waitFor({ state: 'visible' });
    check(await input.evaluate(n => n === document.activeElement), 'Chat opens and focuses typing');
    await input.fill('Unsent draft'); await chat.tap();
    check(await input.isHidden(), 'second Chat tap hides chat');
    await page.waitForFunction(() => document.querySelector('#touch-actions [data-action=chat]').getAttribute('aria-expanded') === 'false');
    check(await chat.getAttribute('aria-expanded') === 'false', 'Chat reports its closed state');
    check(await input.inputValue() === 'Unsent draft', 'closing preserves the draft');
    await chat.tap(); await input.waitFor({ state: 'visible' });
    check(await input.inputValue() === 'Unsent draft', 'Chat reopens with the draft');
    await chat.tap();

    await record(page);
    const skill = page.locator('#touch-skills [data-skill="arcaneward"]');
    await skill.tap();
    await page.waitForFunction(() => Field.hero.skillCd.arcaneward > 0);
    const countdown = skill.locator('.touch-cooldown'); await countdown.waitFor();
    check(await skill.isDisabled(), 'cooling skill cannot be recast');
    const appearance = await countdown.evaluate(n => {
      const r = n.getBoundingClientRect(), b = n.parentElement.getBoundingClientRect(), css = getComputedStyle(n);
      return { font: parseFloat(css.fontSize) * b.width / n.parentElement.offsetWidth,
        opacity: getComputedStyle(n.parentElement).opacity, color: css.color,
        inset: Math.abs(r.width - b.width) < 4 && Math.abs(r.height - b.height) < 4 };
    });
    check(appearance.font >= 22 && appearance.opacity === '1' && appearance.inset && appearance.color === 'rgb(255, 255, 255)', `large high-contrast countdown covers the icon: ${JSON.stringify(appearance)}`);
    const first = Number(await countdown.textContent());
    await page.waitForFunction(first => Number(document.querySelector('#touch-skills [data-skill="arcaneward"] .touch-cooldown')?.textContent) < first, first);
    check(Number(await countdown.textContent()) < first, 'countdown decreases with authoritative cooldown');
    const rect = await skill.boundingBox(); await page.touchscreen.tap(rect.x + rect.width / 2, rect.y + rect.height / 2);
    check(await page.evaluate(() => touchSent.filter(p => p.type === 'skill' && p.id === 'arcaneward').length) === 1, 'cooldown tap sends no second cast');
    await page.screenshot({ path: `${out}/feedback-${width}x${height}.png` });
    await debug(page, { op: 'reset_cooldowns' });
    await page.waitForFunction(() => !document.querySelector('#touch-skills [data-skill="arcaneward"]').disabled);
    check(await countdown.count() === 0, 'countdown disappears when ready');

    const peerName = 'MenuPeer' + width, peer = await world.connect({ bot: peerName });
    await world.debug(peerName, { op: 'teleport', zone: 0, x: 82, y: 80 });
    await page.waitForFunction(id => Field.remotePlayers.some(p => p.id === id), peer.id);
    await page.evaluate(id => Field.targetPlayer(id), peer.id);
    await target.waitFor({ state: 'visible' }); await target.scrollIntoViewIfNeeded();
    await target.tap(); await page.locator('#portrait-menu').waitFor({ state: 'visible' });
    await page.waitForFunction(() => document.querySelector('#touch-actions [aria-controls="portrait-menu"]').getAttribute('aria-expanded') === 'true');
    check(await target.getAttribute('aria-expanded') === 'true', 'available Target menu opens');
    await target.tap();
    check(await page.locator('#portrait-menu').isHidden(), 'second Target menu tap closes it');
    await page.evaluate(() => { Field.setTouchDirection(1, 0); Field.setTouchDirection(0, 0); });
    await target.waitFor({ state: 'hidden' });
    check(await target.isHidden(), 'target actions disappear when selection clears');
    await page.context().close();
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
