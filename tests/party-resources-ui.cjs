// Real party packets, including other zones and offline seats; compact raid layout on phone and desktop.
const { run, replace } = require('./lib/touch.cjs');
const path = require('node:path');

run([{
  name: 'party-resources',
  mutate: page => replace(page, 'social.js', 'resource.hidden = !known;', 'resource.hidden = true;'),
  async test({ player, check, world, width, height, out }) {
    const page = await player('Resources', { characterClass: 'warrior', isMobile: width < 1000, hasTouch: width < 1000 });
    const owner = await page.evaluate(() => Online.id);
    const classes = ['mage', 'priest', 'hunter', 'assassin', 'warrior', 'mage', 'priest', 'hunter', 'assassin'];
    const names = classes.map((_, i) => `Resource${i}`);
    async function disconnect(bot) {
      // Driver.disconnect's health count assumes every human is a driver bot; this suite also has a browser player.
      const identity = world.bots.get(bot);
      clearInterval(identity.heartbeat);
      const closed = new Promise(resolve => identity.socket.once('close', resolve));
      identity.socket.close(); await closed;
    }
    async function invite(i) {
      await world.connect({ bot: names[i], class: classes[i] });
      const id = world.bots.get(names[i]).id;
      await page.evaluate(id => Online.send({ type: 'social', command: { op: 'party_invite', id } }), id);
      await world.waitFor(() => world.bots.get(names[i]).social?.incoming.some(p => p.id === owner), 5000, 'invite');
      await world.social(names[i], { op: 'party_accept', id: owner });
      await page.waitForFunction(id => Social.state.party?.members.some(m => m.id === id), id);
    }
    for (let i = 0; i < 4; i++) await invite(i);
    // A distant mage still sends resources to the party.
    await world.debug(names[0], { op: 'teleport', zone: 1, x: 120, y: 120 });
    await world.debug(names[0], { op: 'set_resource', amount: 37 });
    await page.waitForFunction(() => Social.state.party?.members.some(m => m.class === 'mage' && m.zone === 1 && m.resource < m.maxResource / 2));
    await page.waitForFunction(() => document.querySelectorAll('#party-frame .member-resource:not([hidden])').length === 5);
    const read = () => page.evaluate(() => Social.state.party.members.map(m => {
      const row = [...document.querySelectorAll('#party-frame [data-member]')].find(r => r.dataset.member === m.id);
      const bar = row.querySelector('.member-resource');
      return { name: m.name, type: m.resourceType, shown: !bar.hidden, value: bar.getAttribute('aria-valuenow'),
        expected: String(m.resource), max: bar.getAttribute('aria-valuemax'), expectedMax: String(m.maxResource),
        width: parseFloat(bar.querySelector('i').style.width), expectedWidth: m.resource / m.maxResource * 100,
        text: bar.textContent, color: getComputedStyle(bar.querySelector('i')).backgroundImage };
    }));
    const values = await read();
    check(values.every(m => m.shown && m.value === m.expected && m.max === m.expectedMax), 'all five classes show authoritative current/max resources');
    check(values.every(m => Math.abs(m.width - m.expectedWidth) < .01), 'fill widths match the current resource fraction');
    check(new Set(values.map(m => m.color)).size === 3, 'mana, energy and rage have distinct colours');
    check(values.some(m => m.type === 'mana' && m.text.startsWith('Mana')) && values.some(m => m.type === 'energy' && m.text.startsWith('Energy')) && values.some(m => m.type === 'rage' && m.text.startsWith('Rage')), 'each resource is named');
    const mageId = world.bots.get(names[0]).id;
    await page.evaluate(id => { document.querySelector(`[data-member="${id}"]`).dataset.probe = 'same'; }, mageId);
    await world.debug(names[0], { op: 'set_resource', amount: 0 });
    await page.waitForFunction(id => Social.state.party.members.find(m => m.id === id).resource < 30, mageId);
    check(await page.evaluate(id => document.querySelector(`[data-member="${id}"]`).dataset.probe === 'same', mageId), 'live resource updates keep the existing rows');
    check((await read()).every(m => m.value === m.expected && Math.abs(m.width - m.expectedWidth) < .01), 'unchanged rows repaint the new resource amounts');
    await page.evaluate(() => Social.show('party'));
    check(await page.locator('#social-body .member-resource:not([hidden])').count() === 5, 'the party panel also shows resources');
    await page.keyboard.press('Escape');
    await disconnect(names[0]);
    await page.waitForFunction(id => Social.state.party.members.find(m => m.id === id)?.online === false, mageId);
    check(await page.locator(`#party-frame [data-member="${mageId}"] .member-resource`).isHidden(), 'offline members have no stale resource bar');
    await world.connect({ bot: names[0], class: classes[0] });
    await page.waitForFunction(id => Social.state.party.members.find(m => m.id === id)?.online === true, mageId);
    check(await page.locator(`#party-frame [data-member="${mageId}"] .member-resource`).isVisible(), 'reconnecting restores the resource bar');
    await page.evaluate(() => Online.send({ type: 'social', command: { op: 'party_raid', on: true } }));
    await page.waitForFunction(() => Social.state.party.raid);
    for (let i = 4; i < 9; i++) await invite(i);
    const fits = await page.evaluate(() => {
      const stage = document.getElementById('stage').getBoundingClientRect();
      return [...document.querySelectorAll('#party-frame .member-bars')].every(group => {
        const r = group.getBoundingClientRect();
        const bars = [...group.children].map(b => b.getBoundingClientRect());
        return r.left >= stage.left && r.right <= stage.right && r.bottom <= stage.bottom && bars[0].bottom <= bars[1].top && bars.every(b => b.width > 0 && b.height > 0);
      });
    });
    check(await page.locator('#party-frame .member-resource:not([hidden])').count() === 10 && fits, 'ten raid members have separate health/resource bars inside the stage');
    await page.screenshot({ path: path.join(out, `party-resources-${width}x${height}.png`) });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => new Promise(requestAnimationFrame));
    check(await page.evaluate(() => {
      const stage = document.getElementById('stage').getBoundingClientRect();
      return [...document.querySelectorAll('#party-frame .member-resource')].every(bar => {
        const r = bar.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.left >= stage.left && r.right <= stage.right && r.bottom <= stage.bottom;
      });
    }), 'portrait phone: all ten resource bars fit inside the stage');
    for (const bot of names) { await world.social(bot, { op: 'party_leave' }); await disconnect(bot); }
    await page.close();
  },
}]);
