'use strict';
// Action errors share the screen announcement stack; ground loot uses viewport-positioned tooltips.
window.WorldFeedback = (() => {
  let pointer = null, hover = null, anchor = null, tooltipSize = null;
  const tr = text => window.Locale?.translate(text) || text;
  function clearHover() {
    if (hover !== null) window.Inventory?.hideTooltip();
    hover = null; tooltipSize = null;
    const gold = document.getElementById('loot-gold-tooltip'); if (gold) gold.hidden = true;
  }
  function error(text) {
    if (!window.Online?.connected || !window.Field?.hero || typeof text !== 'string' || !text.trim()) return;
    window.Announce?.show(text.trim(), 'error');
  }
  function goldTooltip() {
    let node = document.getElementById('loot-gold-tooltip');
    if (!node) { node = document.createElement('div'); node.id = 'loot-gold-tooltip'; node.className = 'item-tooltip'; node.role = 'tooltip'; node.hidden = true; }
    // A transformed game stage is a containing block for position:fixed. Keep viewport tooltips outside it.
    if (node.parentElement !== document.body) document.body.append(node);
    return node;
  }
  function placeTooltip(node) {
    if (!node || node.hidden || !pointer) return;
    if (!tooltipSize) { const rect = node.getBoundingClientRect(); tooltipSize = { width: rect.width, height: rect.height }; }
    node.style.left = Math.max(8, Math.min(innerWidth - tooltipSize.width - 8, pointer.x + 14)) + 'px';
    node.style.top = Math.max(8, Math.min(innerHeight - tooltipSize.height - 8, pointer.y + 12)) + 'px';
  }
  function draw({ canvas, hero, project, width, height, drops, blocked }) {
    const rect = canvas.getBoundingClientRect();
    if (!pointer || blocked || !rect.width || window.Cutscene?.active) { clearHover(); return; }
    const mx = (pointer.x - rect.left) / rect.width * width, my = (pointer.y - rect.top) / rect.height * height;
    let selected = null, depth = -Infinity;
    for (const d of drops) {
      const [x, y] = project(d.x, d.y), dx = mx - x - (d.item ? 12 : -8), dy = my - y + (d.z || 0);
      if (Math.abs(dx) <= 23 && Math.abs(dy) <= 25 && d.x + d.y >= depth) { selected = d; depth = d.x + d.y; }
    }
    if (!selected) { clearHover(); return; }
    const d = selected, item = window.Inventory?.definition(d.item);
    const key = JSON.stringify([d.id, d.item, d.quantity, d.value, d.gear]);
    if (item) {
      const tooltip = document.getElementById('item-tooltip');
      if (hover !== key || !tooltip || tooltip.hidden) {
        clearHover();
        if (!anchor) { anchor = document.createElement('span'); anchor.className = 'loot-hover-anchor'; anchor.setAttribute('aria-hidden', 'true'); document.body.append(anchor); }
        anchor.style.left = pointer.x + 'px'; anchor.style.top = pointer.y + 'px';
        Inventory.showTooltip(anchor, item, undefined, {
          copies: d.gear ? [d.gear] : [], count: d.quantity || 1,
          in: tr('on the ground'), hint: tr('Walk over the drop to pick it up.'),
        });
        hover = key;
      }
      placeTooltip(document.getElementById('item-tooltip'));
    } else if (!d.item) {
      const gold = goldTooltip();
      if (gold && hover !== key) {
        clearHover(); gold.textContent = Money.text(d.value); gold.hidden = false; hover = key;
      }
      placeTooltip(gold);
    }
  }
  return {
    error, draw,
    pointer(event) { pointer = event.pointerType === 'touch' ? null : { x: event.clientX, y: event.clientY }; },
    leave() { pointer = null; clearHover(); },
    reset() { pointer = null; clearHover(); window.Announce?.clearErrors(); },
  };
})();
