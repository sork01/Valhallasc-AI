'use strict';
(() => {
  const { tiers, materials, enchants } = window.ENCHANTING;
  const byId = new Map(enchants.map(row => [row.id, row]));
  const $ = id => document.getElementById(id);
  const tr = (text, ...args) => (window.Locale?.translate(text) || text).replace(/\{(\d+)\}/g, (_, i) => args[i]);
  const slots = { weapon: 'Weapon', gloves: 'Gloves', armor: 'Chest', necklace: 'Necklace',
    cloak: 'Cloak', accessory: 'Both ring slots', pants: 'Pants', headgear: 'Headgear', shoulders: 'Shoulders' };
  const rarity = name => tr(Inventory.rarityName({rarity: name}));
  const itemId = (prefix, id) => ['enchant', prefix, id].join('_');
  const rowForItem = item => ['enchant_recipe','enchant_scroll'].includes(item?.kind)
    ? byId.get(item.id.replace(/^enchant_(recipe|scroll)_/, '')) : undefined;
  let packet, mode, recipeId, copyId, confirmation, pending = false, refresh = false;
  let requestAt = 0, notice = '';
  const modes = [['apply', 'Apply'], ['study', 'Study'], ['craft', 'Craft'], ['disenchant', 'Disenchant']];

  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function action(label, click, disabled = pending) {
    const node = el('button', tr(label), 'window-tool');
    node.type = 'button'; node.disabled = disabled;
    node.addEventListener('click', click);
    return node;
  }
  function send(request) {
    if (pending || !Online.send({type:'enchanting', request})) return false;
    pending = true;
    clearTimeout(requestAt);
    requestAt = setTimeout(() => {
      pending = false;
      notice = 'No reply. Try again.';
      if (visible()) render();
    }, 5000);
    return true;
  }
  function visible() { return !$('enchanting-panel').hidden; }
  function selectingDisenchant() { return visible() && mode === 'disenchant'; }
  function close() {
    const restoreDetails = selectingDisenchant();
    $('enchanting-panel').hidden = true;
    $('enchanting-toggle').setAttribute('aria-expanded', 'false');
    $('enchanting-panel').parentElement.classList.remove('enchanting-open', 'enchanting-disenchant');
    confirmation = null;
    refresh = false;
    if (restoreDetails) Inventory.renderDetails();
  }
  function open(item) {
    const row = rowForItem(Inventory.definition(item));
    mode = row ? (Inventory.definition(item).kind === 'enchant_recipe' ? 'study' : 'apply') : 'apply';
    recipeId = row?.id || '';
    copyId = '';
    confirmation = null;
    notice = '';
    packet = null;
    Inventory.hideTooltip();
    $('enchanting-panel').hidden = false;
    $('enchanting-panel').parentElement.classList.add('enchanting-open');
    $('enchanting-toggle').setAttribute('aria-expanded', 'true');
    send({op:'open'});
    render();
  }
  function picker(label, rows, value, changed, placeholder) {
    const field = el('label', tr(label), 'enchanting-field');
    const select = el('select');
    select.dataset.enchantingField = label;
    select.append(el('option', tr(placeholder)));
    select.options[0].value = '';
    for (const [id, text] of rows) {
      const option = el('option', text); option.value = id; select.append(option);
    }
    select.value = rows.some(([id]) => id === value) ? value : '';
    select.disabled = pending || !rows.length;
    select.addEventListener('change', () => {
      changed(select.value);
      notice = '';
      render();
      [...$('enchanting-panel').querySelectorAll('select')].find(input => input.dataset.enchantingField === label)?.focus();
    });
    field.append(select);
    return field;
  }
  function enchantInfo(container, enchant) {
    const recipe = byId.get(enchant);
    if (!recipe) return;
    const tier = tiers[recipe.tier];
    container.append(el('strong', tr(recipe.name), 'enchanting-name'),
      el('p', tr(recipe.effect)),
      el('small', tr('{0} · {1} or higher · {2} s cooldown', tr(slots[recipe.kind]), rarity(tier.rarity), recipe.cooldown)));
  }
  const copies = () => (packet?.copies || []).filter(({gear}) => Inventory.definition(gear.item));
  function copyLabel({gear, worn}) {
    return tr('{0} · Copy #{1} · {2}', tr(Inventory.definition(gear.item).name), gear.id, rarity(gear.rarity))
      + (worn ? ' · ' + tr('Equipped') : '') + (gear.enchant ? ' · ' + tr(byId.get(gear.enchant)?.name || '') : '');
  }
  function fits({gear}, recipe) {
    return Inventory.definition(gear.item).kind === recipe.kind
      && tiers.findIndex(tier => tier.rarity === gear.rarity) >= recipe.tier;
  }
  function selectedCopy(panel, rows) {
    panel.append(picker('Equipment copy', rows.map(row => [String(row.gear.id), copyLabel(row)]), copyId, value => {
      copyId = value; confirmation = null;
    }, rows.length ? 'Choose equipment' : 'No eligible equipment'));
    return rows.find(row => String(row.gear.id) === copyId);
  }
  function trainingNote(panel, skill, cap) {
    if (!skill || !cap || skill >= packet.maxSkill) return;
    panel.append(el('small', skill < cap ? tr('Can raise Enchanting through skill {0}.', cap)
      : tr('This action is below your current Enchanting training band.')));
  }
  function confirmAction(label, request, disabled = pending) {
    return action(label, () => { notice = ''; if (send(request)) render(); }, disabled);
  }
  function renderDisenchant(container, item, copy) {
    if (!selectingDisenchant()) return false;
    const target = copy && packet?.skill
      ? copies().find(({gear, worn}) => !worn && gear.id === copy.id && gear.rarity === copy.rarity
        && (gear.enchant ?? null) === (copy.enchant ?? null))
      : undefined;
    if (confirmation !== target?.gear.id) confirmation = null;
    if (!target) {
      const message = item && packet && !pending
        ? 'This item cannot be disenchanted.' : 'Select gear in your bags to disenchant.';
      container.append(el('p', tr(message), 'bag-empty-note'));
      return true;
    }

    const {gear} = target;
    const material = materials.find(row => row.rarity === gear.rarity);
    const title = el('b', copyLabel(target), 'item-name');
    title.dataset.rarity = gear.rarity;
    container.append(title, el('p', tr('Destroys this copy. You receive {0} × {1}.', material.yield, tr(material.name))));
    const control = confirmation === gear.id
      ? confirmAction('Confirm disenchant', {op:'disenchant', copy:gear.id, expected:gear.enchant ?? null})
      : action('Disenchant this copy', () => {
        confirmation = gear.id;
        Inventory.renderDetails();
        container.querySelector('button')?.focus({preventScroll:true});
      });
    container.append(control);
    trainingNote(container, packet.skill, target.skillCap);
    return true;
  }
  function render() {
    const root = $('enchanting-panel');
    const selecting = selectingDisenchant();
    const updateBag = selecting || root.parentElement.classList.contains('enchanting-disenchant');
    root.parentElement.classList.toggle('enchanting-disenchant', selecting);
    if (updateBag) Inventory.renderDetails();
    const heading = el('h4', tr('Enchanting'));
    const status = el('p', notice ? tr(notice) : pending ? tr('Waiting for Enchanting…') : '', 'enchanting-status');
    status.setAttribute('role', 'status');
    root.replaceChildren(heading, status);
    if (!packet) {
      if (!pending) root.append(confirmAction('Refresh', {op:'open'}));
      return;
    }
    const { skill, maxSkill, recipes, trainingGearLevel, craftSkillCaps } = packet;
    root.append(el('p', skill ? tr('Enchanting skill {0} / {1}', skill, maxSkill) : tr('An Enchanting Master can teach you. In Alderhaven, find one near the apothecary.')));
    if (trainingGearLevel) root.append(el('small', tr('Use level {0} or higher gear for your next skill point.', trainingGearLevel)));
    const nav = el('div', '', 'enchanting-modes');
    for (const [key, label] of modes) {
      const tab = action(label, () => { mode = key; copyId = ''; confirmation = null; notice = ''; render(); }, pending || (!skill && key !== 'apply'));
      tab.setAttribute('aria-pressed', String(mode === key));
      nav.append(tab);
    }
    root.append(nav);
    if (!skill && mode !== 'apply') return;

    if (selecting) return;
    const panel = el('div', '', 'enchanting-form');
    root.append(panel);
    const owned = new Map(packet.inventory.map(stack => [stack.item, stack.quantity]));
    const options = enchants.filter(row => {
      if (mode === 'craft') return recipes.includes(row.id);
      return owned.get(itemId(mode === 'study' ? 'recipe' : 'scroll', row.id)) > 0
        && (mode !== 'study' || !recipes.includes(row.id));
    });
    panel.append(picker('Enchantment', options.map(row => [row.id, tr(row.name)]), recipeId, value => {
      recipeId = value; copyId = '';
    }, options.length ? 'Choose an enchantment' : {
      apply: 'No crafted scrolls in your bags', craft: 'No known recipes', study: 'No unlearned recipe scrolls in your bags',
    }[mode]));
    const recipe = options.find(row => row.id === recipeId);
    if (!recipe) return;
    enchantInfo(panel, recipe.id);
    if (mode === 'study') {
      panel.append(el('p', tr('Consumes one recipe scroll and permanently teaches the recipe.')),
        confirmAction('Study recipe', {op:'study', enchant:recipe.id}));
    } else if (mode === 'craft') {
      const required = tiers[recipe.tier].skill;
      panel.append(el('p', tr('Requires Enchanting skill {0}.', required)));
      const costs = el('ul', '', 'enchanting-cost');
      let canCraft = skill >= required;
      recipe.cost.forEach((amount, index) => {
        if (!amount) return;
        const material = materials[index];
        const have = owned.get(material.id) || 0;
        const line = el('li', tr('{0} · {1} of {2} in bags', tr(material.name), have, amount));
        line.dataset.short = String(have < amount); costs.append(line);
        canCraft &&= have >= amount;
      });
      panel.append(costs);
      trainingNote(panel, skill, craftSkillCaps?.[recipe.tier]);
      const actions = el('div', '', 'recipe-actions');
      actions.append(
        confirmAction('Craft one scroll', {op:'craft', enchant:recipe.id}, pending || !canCraft),
        confirmAction('Craft All', {op:'craft', enchant:recipe.id, all:true}, pending || !canCraft),
      );
      panel.append(actions);
    } else {
      const target = selectedCopy(panel, copies().filter(row => fits(row, recipe) && row.gear.enchant !== recipe.id));
      panel.append(el('p', tr('Cost · One crafted scroll')));
      if (target?.gear.enchant) panel.append(el('p', tr('Replaces {0} on this copy.', tr(byId.get(target.gear.enchant).name))));
      if (target) trainingNote(panel, skill, target.skillCap);
      if (target) panel.append(confirmAction('Apply enchantment', {op:'apply', enchant:recipe.id, copy:target.gear.id, expected:target.gear.enchant ?? null}));
    }
  }
  function tooltip(container, item, gear) {
    const recipe = byId.get(gear?.enchant) || rowForItem(item);
    if (!recipe) return false;
    const note = el('div', '', 'enchanting-note');
    enchantInfo(note, recipe.id);
    if (item.kind === 'enchant_recipe') note.append(el('p', tr('Permanently teaches the recipe · Crafting requires Enchanting skill {0}.', tiers[recipe.tier].skill)));
    if (item.kind === 'enchant_scroll') note.append(el('p', tr('Single use · Anyone can apply this scroll.')));
    container.append(note);
    return true;
  }
  function drawFields(context, fields, worldToScreen, tileWidth, tileHeight, width, height) {
    for (const field of fields) {
      const [x, y] = worldToScreen(field.x, field.y);
      const rx = field.radius * tileWidth / Math.SQRT2;
      const ry = field.radius * tileHeight / Math.SQRT2;
      if (x + rx < 0 || x - rx > width || y + ry < 0 || y - ry > height) continue;
      const grove = field.enchant === 'heartwood_grove';
      const decoy = field.enchant === 'moonstep';
      const mark = field.enchant === 'passing_spark';
      context.save();
      context.strokeStyle = grove ? '#a7e791' : decoy || mark ? '#c9a8ee' : '#b6dcff';
      context.fillStyle = grove ? 'rgba(74,170,78,.22)' : decoy || mark ? 'rgba(142,96,183,.14)' : 'rgba(80,155,210,.14)';
      context.lineWidth = 2;
      context.beginPath();
      context.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
      context.fill(); context.stroke();
      if (grove) {
        for (let n = 0; n < 10; n++) {
          const angle = n * Math.PI / 5;
          const lx = x + Math.cos(angle) * rx * .83, ly = y + Math.sin(angle) * ry * .83;
          context.beginPath();
          context.ellipse(lx, ly - 4, 4, 8, angle, 0, Math.PI * 2);
          context.fill(); context.stroke();
        }
      } else if (decoy) {
        context.beginPath();
        context.arc(x, y - 29, 6, 0, Math.PI * 2);
        context.moveTo(x, y - 23); context.lineTo(x, y - 10);
        context.moveTo(x - 10, y - 14); context.lineTo(x, y - 19); context.lineTo(x + 10, y - 14);
        context.moveTo(x - 6, y); context.lineTo(x, y - 10); context.lineTo(x + 6, y);
        context.stroke();
      } else if (!mark) {
        context.beginPath();
        context.moveTo(x, y); context.lineTo(x, y - 26);
        context.lineTo(x + 5, y - 20); context.moveTo(x, y - 26); context.lineTo(x - 5, y - 20);
        context.stroke();
      }
      context.restore();
    }
  }
  window.Enchanting = {
    open, close, tooltip, drawFields, selectingDisenchant, renderDisenchant, name: id => byId.has(id) ? tr(byId.get(id).name) : '', isScroll: item => !!rowForItem(item),
    onPacket(answer) {
      pending = false;
      clearTimeout(requestAt);
      if (!visible()) return;
      packet = answer;
      if (answer.text) notice = tr(answer.text);
      if (answer.skillUp) notice = [notice, tr('Enchanting skill increased to {0}.', answer.skill)].filter(Boolean).join(' ');
      confirmation = null;
      if (refresh) { refresh = false; send({op:'open'}); }
      render();
    },
  };
  $('enchanting-toggle').addEventListener('click', () => visible() ? close() : open());
  window.addEventListener('inventory-change', () => {
    if (!visible()) return;
    if (pending) refresh = true;
    else if (send({op:'open'})) render();
  });
})();
