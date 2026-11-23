'use strict';
(() => {
  const data = window.BLACKSMITHING_DATA;
  const tr = text => window.Locale?.translate(text) || text;
  const format = (text, ...values) => tr(text).replace(/\{(\d+)\}/g, (_, n) => values[Number(n)]);
  const itemName = id => tr(Inventory.definition(id)?.name || id);
  const status = document.getElementById('mining-status');
  let veins = [], miners = [], nearestVein = null, ownMining = false, active = null, sound = null, noticeTimer = 0;
  let workshop = null, pending = false, section = 'staple';

  function element(tag, text = '', className = '') {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function button(text, action, unavailable = false) {
    const node = element('button', tr(text), 'btn ghost');
    node.type = 'button';
    node.disabled = unavailable || pending;
    node.addEventListener('click', action);
    return node;
  }
  function command(op, fields = {}) {
    if (pending || !Online.send({type:'blacksmithing', request:{op, ...fields}})) return;
    pending = true;
    if (workshop) renderWorkshop();
  }

  function render(npc, packet, target) {
    if (!packet.blacksmithing || !data) return;
    if (workshop?.npc !== npc.id) section = 'staple';
    workshop = {npc:npc.id, target, inventory:packet.inventory || [], gold:packet.gold || 0,
      notice:'', ...packet.blacksmithing};
    renderWorkshop();
  }
  function close() {
    workshop = null;
    pending = false;
  }
  function renderWorkshop() {
    if (!workshop) return;
    const {target, skill, trainer, recipes, inventory, gold, npc, notice} = workshop;
    const page = target.closest?.('.gossip-parchment');
    const scrollTop = page?.scrollTop || 0;
    const focusKey = document.activeElement?.dataset.smithAction;
    target.classList.add('smith-workshop');
    target.replaceChildren(element('h3', tr('Blacksmithing')));
    const feedback = element('p', tr(notice), 'smith-notice');
    feedback.setAttribute('role', 'status');
    target.append(feedback);
    if (!skill) {
      target.append(element('p', tr('Learn Blacksmithing from Bram Emberforge in Alderhaven.')));
      if (trainer) target.append(button('Learn Blacksmithing', () => command('train', {npc})));
      return;
    }
    target.append(element('p', format('Blacksmithing skill {0} / {1}', skill, 300), 'smith-skill'));
    if (skill < 300) {
      const band = Math.floor(skill / 30), next = data.tiers[band];
      const region = next.zones[0];
      const zone = region === 0 ? WORLD_MAP : WORLD_MAP.zones[region - 1];
      target.append(element('p', format('Train to {0} with {1} in {2}.', (band + 1) * 30, itemName(next.ore), tr(zone.name))));
      if (next.zones.length > 1) {
        const otherZones = next.zones.slice(1).map(id => tr(WORLD_MAP.zones[id - 1].name)).join(', ');
        target.append(element('small', format('Other mining areas · {0}', otherZones)));
      }
    }
    const tabs = element('div', '', 'smith-tabs');
    for (const [value, label] of [['staple','Equipment'],['smelt','Smelting'],['upgrade','Mining picks']]) {
      const control = button(label, () => { section = value; renderWorkshop(); });
      control.dataset.smithAction = value;
      control.setAttribute('aria-pressed', String(section === value));
      tabs.append(control);
    }
    target.append(tabs);
    const list = element('div', '', 'smith-recipes');
    const amounts = new Map(inventory.map(({item, quantity}) => [item, quantity]));
    for (const recipe of data.recipes) {
      const gear = ['staple','rare','epic'].includes(recipe.method);
      if (section === 'staple' ? !gear : recipe.method !== section) continue;
      const piece = Inventory.definition(recipe.item);
      if (!piece) continue;
      const learned = recipes.includes(recipe.item);
      const supplies = recipe.ingredients.every(([id, count]) => (amounts.get(id) || 0) >= count);
      const row = element('article', '', 'smith-recipe');
      row.dataset.recipe = recipe.item;
      row.dataset.rarity = piece.rarity;
      const icon = element('span', '', 'smith-icon');
      icon.innerHTML = Inventory.icon(piece);
      Inventory.attachTooltip(icon, () => piece);
      const details = element('div', '', 'smith-detail');
      details.append(element('b', itemName(piece.id)));
      if (gear) {
        const preview = Inventory.gearPreview(piece);
        if (preview) details.append(element('small', preview));
      } else if (recipe.method === 'upgrade') {
        details.append(element('small', format('Mines through {0}.', itemName(data.tiers[data.picks.find(p => p.item === piece.id).reaches].ore))));
      }
      details.append(element('small', format('Requires Blacksmithing {0}', recipe.skill)));
      const requires = element('ul', '', 'smith-ingredients');
      for (const [id, count] of recipe.ingredients) {
        const have = amounts.get(id) || 0;
        const ingredient = element('li', format('{0} · {1}/{2}', itemName(id), have, count));
        ingredient.dataset.short = String(have < count);
        requires.append(ingredient);
      }
      if (recipe.cost) {
        const fee = element('li');
        fee.innerHTML = Money.html(recipe.cost);
        fee.dataset.short = String(gold < recipe.cost);
        requires.append(fee);
      }
      details.append(requires);
      const actions = element('div', '', 'recipe-actions');
      let action;
      if (gear && !learned) {
        if (!recipe.plan) action = button('Learn blueprint', () => command('learn', {npc, recipe:piece.id}), skill < recipe.skill);
        else if (amounts.get(recipe.plan)) action = button('Study blueprint', () => command('study', {plan:recipe.plan}));
        else action = element('small', tr(recipe.method === 'epic' ? 'Blueprint drops from final bosses.' : 'Blueprint drops from enemies.'));
      } else {
        const unavailable = skill < recipe.skill || !supplies || gold < recipe.cost;
        action = button(recipe.method === 'smelt' ? 'Smelt' : 'Forge item',
          () => command('craft', {npc, recipe:piece.id}), unavailable);
        if (recipe.method !== 'upgrade') {
          const bulk = button(recipe.method === 'smelt' ? 'Smelt All' : 'Forge All',
            () => command('craft', {npc, recipe:piece.id, all:true}), unavailable);
          bulk.dataset.smithAction = 'all:' + piece.id;
          actions.append(action, bulk);
        }
      }
      action.dataset.smithAction = recipe.item;
      row.append(icon, details, actions.children.length ? actions : action);
      list.append(row);
    }
    target.append(list);
    if (page) page.scrollTop = scrollTop;
    if (focusKey) [...target.querySelectorAll('[data-smith-action]')].find(node => node.dataset.smithAction === focusKey)?.focus({preventScroll:true});
  }

  function onPacket(packet) {
    pending = false;
    window.City?.blacksmithingUpdate(packet);
    if (packet.ok && packet.output) {
      const recipe = data.recipes.find(r => r.item === packet.output);
      sound?.(recipe?.method === 'smelt' ? 'smelt' : 'forge');
    }
    if (workshop && (!packet.npc || workshop.npc === packet.npc)) {
      Object.assign(workshop, {skill:packet.skill, recipes:packet.recipes, inventory:packet.inventory, gold:packet.gold, notice:packet.text});
      renderWorkshop();
      if (packet.ok && packet.output) {
        const row = [...workshop.target.querySelectorAll('[data-recipe]')].find(node => node.dataset.recipe === packet.output);
        row?.classList.add('smith-crafted');
      }
      return;
    }
    if (packet.ok) Online.log?.(packet.text);
    else Field.error(packet.text);
  }

  function sync(packet, own, cue) {
    veins = packet.miningVeins || [];
    miners = packet.players.filter(player => player.mining);
    sound = cue;
    ownMining = !!own.mining;
    if (active && !ownMining) active = null;
    nearestVein = null;
    let best = 2.6; // Keep in step with the server's mining reach.
    for (const vein of veins) {
      const distance = Math.hypot(vein.x - own.x, vein.y - own.y);
      if (distance > best) continue;
      nearestVein = vein;
      best = distance;
    }
  }
  function showStatus(text, timed = true) {
    if (!status) return;
    clearTimeout(noticeTimer);
    status.hidden = false;
    status.textContent = text;
    if (timed) noticeTimer = setTimeout(() => { status.hidden = true; }, 2000);
  }
  function mining(packet) {
    if (packet.state === 'started') {
      active = {vein:packet.vein, start:performance.now(), duration:packet.duration};
      showStatus(tr('Mining…'), false);
    } else if (packet.state === 'done') {
      active = null;
      sound?.('strike');
      const ore = format('Mined {0} × {1}', packet.quantity, itemName(packet.item));
      showStatus(packet.skillUp ? format('{0} · Blacksmithing {1}', ore, packet.skill) : ore);
    } else {
      active = null;
      if (status) status.hidden = true;
      Field.error(packet.text);
    }
  }
  const VEIN_SIZE = 92, VEIN_BASE = 3;
  function pick(mx, my, project) {
    return veins.map(vein => {
      const [x,y] = project(vein.x, vein.y);
      return {vein, x, y};
    }).filter(({x,y}) => Math.abs(mx-x) <= VEIN_SIZE / 2 && my >= y + VEIN_BASE - VEIN_SIZE && my <= y + 8)
      .sort((a,b) => b.y - a.y)[0]?.vein;
  }
  function start(vein) {
    return Online.send({type:'mine', id:vein.id});
  }

  const atlas = new Image();
  atlas.src = 'assets/blacksmithing.png';
  function sprite(g, id, x, y, size) {
    const meta = window.BLACKSMITHING_ART;
    const cell = meta?.at[id];
    if (!cell || !atlas.naturalWidth) return false;
    g.drawImage(atlas, cell[0]*meta.size, cell[1]*meta.size, meta.size, meta.size,
      -size/2 + x, y - size, size, size);
    return true;
  }
  function drawVein(g, vein, sx, sy) {
    sprite(g, 'vein_' + vein.tier, sx, sy + VEIN_BASE, VEIN_SIZE);
    if (active?.vein === vein.id) {
      const fraction = Math.min(1, Math.max(0, (performance.now() - active.start) / (1000 * active.duration)));
      g.fillStyle = '#221a16'; g.fillRect(sx-19,sy+6,38,5);
      g.fillStyle = '#f3ce79'; g.fillRect(sx-18,sy+7,36*fraction,3);
    }
  }
  function drawMiners(g, project, width, height, reduced) {
    for (const actor of miners) {
      const vein = veins.find(v => v.id === actor.mining);
      if (!vein) continue;
      const [sx,sy] = project(actor.x, actor.y);
      if (sx < -45 || sx > width + 45 || sy < -10 || sy > height + 100) continue;
      const [tx] = project(vein.x, vein.y), side = tx < sx ? -1 : 1;
      g.save();
      g.translate(sx + side*13, sy - 28);
      g.rotate(side * (reduced ? .15 : .25 + Math.sin(performance.now()/120)*.9));
      sprite(g, 'smith_pick_1', 0, 12, 31);
      g.restore();
    }
  }

  function reset() {
    veins = []; miners = []; nearestVein = null; ownMining = false; active = null; sound = null;
    clearTimeout(noticeTimer);
    if (status) status.hidden = true;
    close();
  }
  window.Blacksmithing = {render, close, onPacket, sync, mining, pick, start, drawVein, drawMiners, reset,
    get veins() { return veins; },
    get nearbyVein() { return nearestVein; },
    get isMining() { return !!active || ownMining; },
    study:plan => command('study', {plan}),
    pickDetails(item) {
      const pick = data?.picks.find(entry => entry.item === item.id);
      return pick ? format('Mines through {0}.', itemName(data.tiers[pick.reaches].ore)) : '';
    },
  };
})();
