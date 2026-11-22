'use strict';
(() => {
  const data = window.ALCHEMY_DATA;
  const tr = text => window.Locale?.translate(text) || text;
  const format = (text, ...values) => tr(text).replace(/\{(\d+)\}/g, (_, n) => values[Number(n)]);
  const itemName = id => tr(Inventory.definition(id)?.name || id);
  const zoneName = id => tr((id === 0 ? WORLD_MAP : WORLD_MAP.zones[id - 1])?.name || '');
  const recipesByItem = new Map(data.recipes.map(recipe => [recipe.item, recipe]));
  const status = document.getElementById('picking-status');
  const image = new Image();
  image.src = 'assets/alchemy.png';

  let patches = [], workshop = null, pending = false, section = 'recipes';
  let active = null, noticeTimer = 0, craftedTimer = 0, sound = null;

  function node(tag, text = '', className = '') {
    const element = document.createElement(tag);
    element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function button(label, action, unavailable = false) {
    const control = node('button', tr(label), 'btn ghost');
    control.type = 'button';
    control.addEventListener('click', action);
    control.disabled = unavailable || pending;
    return control;
  }
  function effect(item) {
    const recipe = recipesByItem.get(item?.id);
    if (!recipe) return '';
    const templates = {
      damage: '+{0}% damage',
      ward: '{0}% less damage taken',
      healing: '+{0}% outgoing healing',
      speed: '+{0}% movement speed',
      health: '+{0}% maximum health',
    };
    const bonus = format(templates[recipe.stat], recipe.amount);
    return recipe.flask
      ? format('{0} for 45 min. PvE only. Drink out of combat. Requires level {1}.', bonus, recipe.level)
      : format('{0} for 15 s. PvE only. Shares the 60 s potion cooldown. Requires level {1}.', bonus, recipe.level);
  }

  function command(op, fields = {}) {
    if (pending || !Online.send({type:'alchemy', request:{op, ...fields}})) return;
    pending = true;
    renderWorkshop();
  }

  function render(npc, packet, target) {
    if (!packet.alchemy) return;
    if (workshop?.npc !== npc.id) section = 'recipes';
    workshop = {npc:npc.id, target, inventory:packet.inventory || [], notice:'',
      zone:Field.zone || 0, ...packet.alchemy};
    renderWorkshop();
  }

  function sourceGuide(target, workshop) {
    const label = node('label', tr('Flower sources'));
    const select = node('select');
    const zones = Object.keys(data.sources).map(Number);
    select.setAttribute('aria-label', tr('Flower sources'));
    for (const id of zones) {
      const option = node('option', zoneName(id));
      option.value = id;
      select.append(option);
    }
    select.value = String(zones.includes(workshop.zone) ? workshop.zone : 0);
    const flowers = node('ul', '', 'alchemy-flowers');
    const update = () => {
      workshop.zone = Number(select.value);
      flowers.replaceChildren(...data.sources[workshop.zone].map(index => {
        const flower = data.flowers[index];
        const label = flower.region ? format('{0} · {1}', itemName(flower.item), tr(flower.region)) : itemName(flower.item);
        return node('li', format('{0} · Requires Alchemy {1}', label, Math.max(1, flower.band * 30)));
      }));
    };
    select.addEventListener('change', update);
    update();
    label.append(select);
    target.append(label, flowers);
  }

  function recipeCard(recipe, amounts, skill, learned, npc) {
    const item = Inventory.definition(recipe.item);
    const card = node('article', '', 'smith-recipe');
    card.dataset.recipe = recipe.item;
    card.dataset.rarity = item.rarity;
    const icon = node('span', '', 'smith-icon');
    icon.innerHTML = Inventory.icon(item);
    Inventory.attachTooltip(icon, () => item);
    const detail = node('div', '', 'smith-detail');
    detail.append(node('b', itemName(recipe.item)), node('small', effect(item)),
      node('small', format('Requires Alchemy {0}', recipe.skill)));
    const list = node('ul', '', 'smith-ingredients');
    let enough = true;
    for (const [ids, count] of recipe.ingredients) {
      const have = ids.reduce((sum, id) => sum + (amounts.get(id) || 0), 0);
      const group = node('li', format('{0} · {1}/{2}', ids.map(itemName).join(' / '), have, count));
      group.dataset.short = String(have < count);
      enough &&= have >= count;
      list.append(group);
    }
    detail.append(list);
    let action;
    if (learned) {
      action = button('Brew', () => command('brew', {npc, recipe:recipe.item}), !enough || skill < recipe.skill);
    } else if (!recipe.formula) {
      action = button('Learn recipe', () => command('learn', {npc, recipe:recipe.item}), skill < recipe.skill);
    } else if (amounts.get(recipe.formula)) {
      action = button('Study formula', () => study(recipe.formula));
    } else {
      const source = recipe.boss ? format('Formula drops in {0}.', zoneName(data.formulaZones[recipe.boss]))
        : tr('Formula drops from Cairnspine elites.');
      action = node('small', source);
    }
    action.dataset.alchemyAction = recipe.item;
    card.append(icon, detail, action);
    return card;
  }

  function renderWorkshop() {
    if (!workshop) return;
    const {target, skill, trainer, recipes, inventory, npc, notice} = workshop;
    const page = target.closest('.gossip-parchment');
    const scrollTop = page?.scrollTop || 0;
    const focusKey = document.activeElement?.dataset.alchemyAction;
    target.classList.add('smith-workshop', 'alchemy-workshop');
    const feedback = node('p', tr(notice), 'smith-notice');
    feedback.setAttribute('role', 'status');
    target.replaceChildren(feedback, node('p', format('Alchemy skill {0} / {1}', skill, 600), 'smith-skill'));
    if (!skill) {
      if (trainer) target.append(button('Learn Alchemy', () => command('train', {npc})));
      else target.append(node('p', tr('Learn Alchemy from Maera in Alderhaven.')));
    }
    const tabs = node('div', '', 'smith-tabs');
    for (const [value, label] of [['recipes','Recipes'], ['flowers','Flower sources']]) {
      const tab = button(label, () => { section = value; renderWorkshop(); });
      tab.dataset.alchemyAction = value;
      tab.setAttribute('aria-pressed', String(section === value));
      tabs.append(tab);
    }
    target.append(tabs);
    if (section === 'flowers') {
      sourceGuide(target, workshop);
    } else if (skill) {
      if (skill < 600) {
        const band = Math.floor(skill / 30);
        const sources = data.flowers.filter(f => f.band === band)
          .map(f => format('{0} · {1}', itemName(f.item), f.region ? tr(f.region) : zoneName(f.zone)));
        target.append(node('p', format('Train to {0} by picking or brewing with these flowers.', (band + 1) * 30)));
        target.append(node('p', sources.join(' / ')));
      }
      const amounts = new Map(inventory.map(stack => [stack.item, stack.quantity]));
      const list = node('div', '', 'smith-recipes');
      for (const recipe of data.recipes) {
        list.append(recipeCard(recipe, amounts, skill, recipes.includes(recipe.item), npc));
      }
      target.append(list);
    }
    if (page) page.scrollTop = scrollTop;
    if (focusKey) [...target.querySelectorAll('button')]
      .find(element => element.dataset.alchemyAction === focusKey)?.focus({preventScroll:true});
  }

  function onPacket(packet) {
    pending = false;
    window.City?.alchemyUpdate(packet);
    if (workshop && (!packet.npc || workshop.npc === packet.npc)) {
      Object.assign(workshop, {skill:packet.skill, recipes:packet.recipes, inventory:packet.inventory, notice:packet.text});
      renderWorkshop();
      if (packet.ok && packet.output) {
        const card = [...workshop.target.querySelectorAll('[data-recipe]')].find(element => element.dataset.recipe === packet.output);
        clearTimeout(craftedTimer);
        card?.classList.add('alchemy-brewed');
        craftedTimer = setTimeout(() => card?.classList.remove('alchemy-brewed'), 600);
      }
    } else if (!packet.ok) {
      window.Field?.error(packet.text);
    } else if (!packet.npc) {
      showStatus(tr(packet.text));
    }
    if (packet.ok && packet.output) sound?.('brew');
  }

  function close() {
    workshop = null;
    pending = false;
  }
  function study(formula) { command('study', {formula}); }
  function showStatus(text, duration = 2300) {
    status.textContent = text;
    status.hidden = false;
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => { status.hidden = true; }, duration);
  }
  function sync(packet, play) {
    sound = play;
    patches = packet.flowerPatches || [];
    if (active && !patches.some(patch => patch.id === active.id)) active = null;
  }
  function picking(packet) {
    if (packet.state === 'started') {
      active = {id:packet.patch, start:performance.now(), duration:packet.duration * 1000};
      showStatus(tr('Picking flowers…'), active.duration + 300);
      sound?.('pick');
      return;
    }
    active = null;
    if (packet.state === 'done') {
      const reward = format('+{0} {1}', packet.quantity, itemName(packet.item));
      showStatus(packet.skillUp ? format('{0} · Alchemy {1}', reward, packet.skill) : reward);
    } else {
      showStatus(tr(packet.text));
    }
  }
  function hit(x, y, project) {
    let hit, bottom = -Infinity;
    for (const patch of patches) {
      const [px, py] = project(patch.x, patch.y);
      if (py > bottom && Math.abs(px - x) <= 22 && y >= py - 44 && y <= py + 10) {
        hit = patch;
        bottom = py;
      }
    }
    return hit;
  }
  function start(patch) { Online.send({type:'pick_flower', id:patch.id}); }
  function drawPatch(g, patch, x, y) {
    const art = window.ALCHEMY_ART;
    if (!art || !image.complete || !image.naturalWidth) return;
    const flower = data.flowers[patch.flower];
    const [col, row] = art.at['patch_' + flower.item];
    const {size} = art;
    g.save();
    g.imageSmoothingEnabled = false;
    g.drawImage(image, col * size, row * size, size, size, x - 23, y - 43, 46, 46);
    if (active?.id === patch.id) {
      const fraction = Math.min(1, (performance.now() - active.start) / active.duration);
      g.fillStyle = '#261d1e';
      g.fillRect(x - 18, y - 45, 36, 5);
      g.fillStyle = '#dcf29a';
      g.fillRect(x - 17, y - 44, 34 * fraction, 3);
    }
    g.restore();
  }
  function reset() {
    close();
    patches = [];
    active = sound = null;
    clearTimeout(noticeTimer);
    clearTimeout(craftedTimer);
    status.hidden = true;
  }
  window.Alchemy = {render, close, onPacket, sync, picking, hit, start, drawPatch, reset, effect, study,
    get patches() { return patches; },
    isBrew: item => recipesByItem.has(item?.id)};
})();
