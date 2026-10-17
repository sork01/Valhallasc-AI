// BANK-CHECK: the bank end to end on a private server, with no browser. Real WebSocket clients walk (teleport) between
// the five bankers and check what docs/bank.md promises: a deposit in one city is a withdrawal in another, the bank
// survives logout, a server restart and a rebirth, a gear copy keeps its data, a full bank or bag refuses and leaves
// everything as it was, two sockets of one character cannot both take the same item, and a long seeded random run
// loses and copies nothing. The Rust tests prove the same rules on one World; this proves the running server.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld, root } = require('../scripts/testing/driver.cjs');

const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
const items = JSON.parse(fs.readFileSync(path.join(root, 'world/items.txt'), 'utf8'));
const CITIES = ['Alderhaven', 'Skaldholm', 'Nacrehold', 'Astralhollow', 'Asterion'];
const bankers = [];
// The top level of map.txt is zone 0 (Alderhaven's meadow); map.zones[k] is zone k + 1.
[map, ...map.zones].forEach((zone, zoneIndex) => {
  for (const n of zone.npcs || []) if ((n.offers || []).some(o => o.id === 'bank')) bankers.push({ id: n.id, zone: zoneIndex, x: n.x, y: n.y });
});
assert.equal(bankers.length, 5, 'exactly five bankers in the world');
assert.deepEqual(bankers.map(b => b.id.replace('banker_', '')).sort(), CITIES.map(c => c.toLowerCase()).sort());

const materials = items.filter(i => i.kind === 'material').map(i => i.id);
const epic = items.find(i => i.rarity === 'epic' && i.kind === 'armor');
const sleep = ms => new Promise(r => setTimeout(r, ms));
let seed = 20261017;
const random = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32;

(async () => {
  const w = new TestWorld();
  try {
    await w.start();
    await w.connect({ bot: 'hoarder', class: 'warrior' });
    const send = (bot, message) => w.bots.get(bot).socket.send(JSON.stringify(message));
    const debug = (op, rest = {}) => w.debug('hoarder', { op, ...rest });
    // One request, one answer: the `bank` packet (a refusal before the bank is reached is an `error` packet).
    const ask = async (message, bot = 'hoarder') => {
      const earlier = new Set(w.events);
      send(bot, message);
      const reply = await w.waitFor(() => w.events.find(e => !earlier.has(e) && e.bot === bot && (e.type === 'bank' || e.type === 'error')), 5000, message.type);
      return reply;
    };
    const stackMap = list => new Map((Array.isArray(list) ? list : Object.entries(list).map(([item, quantity]) => ({ item, quantity }))).map(s => [s.item, s.quantity]));
    // Everything the character owns, whichever side it is on: items, gear copies' count, and gold.
    const totals = packet => {
      const all = new Map(), add = (m) => { for (const [k, v] of m) all.set(k, (all.get(k) || 0) + v); };
      add(stackMap(packet.inventory)); add(stackMap(packet.bank.items));
      return { items: all, gold: packet.gold + packet.bank.gold, copies: packet.gearInstances.length + packet.bank.gear.length };
    };
    const same = (a, b, label) => {
      assert.deepEqual([...a.items].filter(([, v]) => v).sort(), [...b.items].filter(([, v]) => v).sort(), `${label}: items`);
      assert.equal(a.gold, b.gold, `${label}: gold`);
      assert.equal(a.copies, b.copies, `${label}: gear copies`);
    };
    const at = async banker => {
      await debug('teleport', { zone: banker.zone, x: banker.x, y: banker.y + 1.1 });
      await w.waitFor(() => { const p = w.player('hoarder'); return (p.zone || 0) === banker.zone && Math.hypot(p.x - banker.x, p.y - banker.y - 1.1) < 1; }, 10000, `Arrive at ${banker.id}`);
    };
    const open = async banker => { const r = await ask({ type: 'bank_open', npc: banker.id }); assert.equal(r.type, 'bank', `${banker.id} opens`); assert.equal(r.ok, true); return r; };
    const deposit = (banker, item, quantity, copy) => ask({ type: 'bank_deposit', npc: banker.id, item, quantity, ...(copy ? { copy } : {}) });
    const withdraw = (banker, item, quantity, copy) => ask({ type: 'bank_withdraw', npc: banker.id, item, quantity, ...(copy ? { copy } : {}) });

    // 1. A banker answers in each city, and a banker out of reach is refused.
    for (const b of bankers) { await at(b); const r = await open(b); assert.equal(r.bank.capacity, 48); }
    await debug('teleport', { zone: 0, x: bankers[0].x + 6, y: bankers[0].y + 6 });
    await w.waitFor(() => Math.hypot(w.player('hoarder').x - bankers[0].x - 6, w.player('hoarder').y - bankers[0].y - 6) < 1);
    assert.equal((await ask({ type: 'bank_open', npc: bankers[0].id })).type, 'error', 'too far from the banker');
    assert.equal((await ask({ type: 'bank_open', npc: 'guide' })).type, 'error', 'an NPC without a bank offer');

    // 2. Stock the hero: a stack, an epic gear piece (two loose copies), a purse; then store in Alderhaven.
    const [alder, skald, nacre, astral, asterion] = ['alderhaven', 'skaldholm', 'nacrehold', 'astralhollow', 'asterion'].map(c => bankers.find(b => b.id === `banker_${c}`));
    await at(alder);
    await debug('set_gold', { gold: 5000 });
    await debug('give_item', { item: 'slime_gel', quantity: 40, force: true });
    await debug('give_item', { item: epic.id, quantity: 2, force: true });
    const start = totals(await open(alder));
    assert.equal(start.items.get('slime_gel'), 40);
    assert.equal(start.gold, 5000);
    const wornBefore = (await open(alder)).gearInstances;
    const copiesOfEpic = wornBefore.filter(g => g.item === epic.id);
    assert.equal(copiesOfEpic.length, 2);
    assert.ok(copiesOfEpic.every(g => g.rarity === epic.rarity));
    let r = await deposit(alder, 'slime_gel', 25);
    assert.equal(r.ok, true, r.notice);
    r = await deposit(alder, epic.id, 1, copiesOfEpic[1].id);
    assert.equal(r.ok, true, r.notice);
    const stored = r.bank.gear[0];
    assert.equal(stored.item, epic.id);
    r = await ask({ type: 'bank_gold', npc: alder.id, deposit: true, amount: 3000 });
    assert.equal(r.ok, true, r.notice);
    assert.equal(r.gold, 2000); assert.equal(r.bank.gold, 3000);
    same(totals(r), start, 'after the deposits');

    // 3. The next city has the same bank: take it all out in Asterion, and the gear copy has its data under a new id.
    await at(asterion);
    r = await open(asterion);
    assert.equal(r.bank.items.find(s => s.item === 'slime_gel').quantity, 25);
    r = await withdraw(asterion, 'slime_gel', 25); assert.equal(r.ok, true, r.notice);
    r = await withdraw(asterion, epic.id, 1, stored.id); assert.equal(r.ok, true, r.notice);
    const back = r.gearInstances.filter(g => g.item === epic.id).map(g => ({ ...g, id: 0 }));
    assert.equal(back.length, 2);
    assert.deepEqual(back[1], { ...stored, id: 0 }, 'the copy keeps every field but its id');
    assert.ok(r.gearInstances.every((g, i, all) => all.findIndex(o => o.id === g.id) === i), 'copy ids stay unique');
    r = await ask({ type: 'bank_gold', npc: asterion.id, deposit: false, amount: 3000 }); assert.equal(r.ok, true, r.notice);
    same(totals(r), start, 'after the round trip through two cities');
    assert.equal(r.gold, 5000);
    // The worn copy cannot be banked, whatever the quantity.
    r = await deposit(asterion, epic.id, 2);
    assert.equal(r.ok, true, 'both epic copies are loose, so both can go');
    r = await withdraw(asterion, epic.id, 2); assert.equal(r.ok, true, r.notice);
    const worn = (await open(asterion)).gearInstances.find(g => g.item !== epic.id);
    r = await deposit(asterion, worn.item, 5);
    assert.equal(r.ok, false, 'more than the loose copies is refused');
    same(totals(r), start, 'after a refused deposit');
    r = await ask({ type: 'bank_deposit', npc: asterion.id, item: 'no_such_item', quantity: 1 }); assert.equal(r.ok, false);
    r = await deposit(asterion, 'slime_gel', 0); assert.equal(r.ok, false, 'zero quantity');
    r = await deposit(asterion, 'slime_gel', 41); assert.equal(r.ok, false, 'more than carried');
    same(totals(r), start, 'after the refusals');

    // 4. Logout, a new session, and a server restart all give the same bank.
    r = await deposit(asterion, 'slime_gel', 30); assert.equal(r.ok, true);
    r = await ask({ type: 'bank_gold', npc: asterion.id, deposit: true, amount: 1234 }); assert.equal(r.ok, true);
    r = await ask({ type: 'bank_expand', npc: asterion.id }); assert.equal(r.ok, false, 'the first expansion costs 10,000 and the purse is short');
    const kept = JSON.stringify((await open(asterion)).bank);
    await w.disconnect('hoarder');
    await w.connect({ bot: 'hoarder' });
    await at(nacre);
    assert.equal(JSON.stringify((await open(nacre)).bank), kept, 'the same bank after logging out and in');
    await w.restart();
    await at(skald);
    r = await open(skald);
    assert.equal(JSON.stringify(r.bank), kept, 'the same bank after a server restart');
    same(totals(r), start, 'after the restart');

    // 5. A rebirth keeps the bank. (Level 50 is the first rebirth; the hero has no high-level gear to take off.)
    await debug('set_level', { level: 50 });
    const preview = await new Promise(async (resolve, reject) => {
      const earlier = new Set(w.events);
      send('hoarder', { type: 'rebirth_preview' });
      try { resolve(await w.waitFor(() => w.events.find(e => !earlier.has(e) && e.type === 'rebirthPreview'), 5000, 'rebirth preview')); } catch (e) { reject(e); }
    });
    assert.equal(preview.ok, true, preview.reason);
    const earlier = new Set(w.events);
    send('hoarder', { type: 'rebirth', nonce: preview.nonce });
    await w.waitFor(() => w.player('hoarder').level === 1, 10000, 'rebirth');
    assert.equal(w.events.filter(e => !earlier.has(e) && e.type === 'error').length, 0);
    await at(alder);
    r = await open(alder);
    assert.equal(JSON.stringify(r.bank), kept, 'the same bank after a rebirth');
    same(totals(r), start, 'after the rebirth');

    // 6. Two sockets of one character cannot both take the same stack: whichever the server handles second finds it gone.
    const twin = new (require('ws'))(w.url.replace(/^http/, 'ws') + 'ws', { origin: new URL(w.url).origin });
    const twinPackets = [];
    twin.on('message', d => twinPackets.push(JSON.parse(d.toString())));
    await new Promise(res => twin.on('open', res));
    twin.send(JSON.stringify({ type: 'join', version: 1, token: w.bots.get('hoarder').token }));
    await sleep(800);
    const sockets = [w.bots.get('hoarder').socket, twin].filter(s => s.readyState === 1);
    const before = totals(await open(alder));
    const seen = new Set(w.events), twinSeen = twinPackets.length;
    const request = JSON.stringify({ type: 'bank_withdraw', npc: alder.id, item: 'slime_gel', quantity: 30 });
    for (const s of sockets) s.send(request), s.send(request);
    await sleep(1000);
    const answers = [...w.events.filter(e => !seen.has(e) && e.bot === 'hoarder' && e.type === 'bank'), ...twinPackets.slice(twinSeen).filter(p => p.type === 'bank')].filter(p => p.notice?.startsWith('Took'));
    assert.equal(answers.length, 1, `the stack came out ${answers.length} times from ${sockets.length} socket(s)`);
    twin.close();
    r = await open(alder);
    same(totals(r), before, 'two sockets, four identical withdrawals');
    assert.equal(r.bank.items.find(s => s.item === 'slime_gel')?.quantity ?? 0, 0);

    // 7. A long seeded run across all five cities: after every answer, accepted or refused, the totals are unchanged.
    const pool = ['slime_gel', epic.id, ...materials.filter(m => m !== 'slime_gel').slice(0, 6)];
    await at(alder);
    for (const id of pool.slice(2)) await debug('give_item', { item: id, quantity: 20, force: true });
    for (const id of pool.slice(1)) { r = await deposit(alder, id, id === epic.id ? 1 : 10); assert.equal(r.ok, true, r.notice); }
    await debug('set_gold', { gold: 6000 });
    const owned = totals(await open(alder));
    let accepted = 0, refused = 0, city = 0;
    for (let step = 0; step < 400; step++) {
      if (step % 25 === 0) { city = Math.floor(random() * bankers.length); await at(bankers[city]); }
      const banker = bankers[city], id = pool[Math.floor(random() * pool.length)], n = 1 + Math.floor(random() * 6);
      const kind = random();
      const reply = kind < .4 ? await deposit(banker, id, n) : kind < .8 ? await withdraw(banker, id, n)
        : await ask({ type: 'bank_gold', npc: banker.id, deposit: kind < .9, amount: Math.floor(random() * 700) });
      if (reply.type === 'error') { refused++; continue; }
      reply.ok ? accepted++ : refused++;
      same(totals(reply), owned, `step ${step} (${kind < .4 ? 'deposit' : kind < .8 ? 'withdraw' : 'gold'} ${id} x${n})`);
    }
    assert.ok(accepted > 120 && refused > 20, `the run exercised both outcomes (${accepted} accepted, ${refused} refused)`);
    // 8. A full bank refuses a new item and a full bag refuses a withdrawal, each leaving everything as it was.
    await at(alder);
    const fillers = materials.filter(m => m !== 'slime_gel').slice(0, 60);
    for (const m of fillers) await debug('give_item', { item: m, quantity: 1, force: true });
    const stocked = totals(await open(alder));
    let refusedFull = 0;
    for (const m of fillers) {
      const before = totals(await open(alder));
      r = await deposit(alder, m, 1);
      if (!r.ok) { refusedFull++; same(totals(r), before, `a full bank refusing ${m}`); assert.match(r.notice, /full|room/i); break; }
    }
    assert.equal(refusedFull, 1, 'the bank filled up and refused');
    assert.equal((await open(alder)).bank.used, 48);
    // The bags are already past their cells from the forced gifts, so a withdrawal that needs a new cell is refused.
    const full = await open(alder), carried = stackMap(full.inventory);
    const stored48 = full.bank.items.find(s => !carried.get(s.item));
    assert.ok(stored48, 'the bank holds an item the bags do not');
    const bagBefore = totals(full);
    r = await withdraw(alder, stored48.item, 1);
    assert.equal(r.ok, false, 'a withdrawal into a full bag is refused');
    assert.match(r.notice, /bag|room|full/i);
    same(totals(r), bagBefore, 'a full bag refusing a withdrawal');
    same(totals(await open(alder)), stocked, 'nothing lost to the full bank');

    console.log(`Bank check: five bankers, cross-city round trip with a gear copy, logout, server restart, rebirth, two sockets, full bank and bag, 400-step random run (${accepted} accepted, ${refused} refused) all passed`);
  } finally {
    await w.stop();
  }
})().catch(e => { console.error(e); process.exit(1); });
