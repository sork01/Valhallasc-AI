'use strict';
// Short action errors follow the hero; ground loot uses the ordinary item tooltip.
window.WorldFeedback = (() => {
  let pointer = null, hover = null, anchor = null, tooltipSize = null;
  const tr = text => window.Locale?.translate(text) || text;
  function clearHover() {
    if (hover !== null) window.Inventory?.hideTooltip();
    hover = null; tooltipSize = null;
    const gold = document.getElementById('loot-gold-tooltip'); if (gold) gold.hidden = true;
  }
  function error(text) {
    const box = document.getElementById('hero-errors');
    if (!box || !window.Online?.connected || !window.Field?.hero || typeof text !== 'string' || !text.trim()) return;
    const value = tr(text), last = box.lastElementChild;
    if (last?.textContent === value) last.dataset.until = String(performance.now() + 2400);
    else {
      const line = document.createElement('p'); line.textContent = value;
      line.dataset.until = String(performance.now() + 2400); box.append(line);
      while (box.children.length > 2) box.firstElementChild.remove();
    }
    box.hidden = false;
  }
  function placeTooltip(node) {
    if (!node || node.hidden || !pointer) return;
    if (!tooltipSize) { const rect = node.getBoundingClientRect(); tooltipSize = { width: rect.width, height: rect.height }; }
    node.style.left = Math.max(8, Math.min(innerWidth - tooltipSize.width - 8, pointer.x + 14)) + 'px';
    node.style.top = Math.max(8, Math.min(innerHeight - tooltipSize.height - 8, pointer.y + 12)) + 'px';
  }
  function draw({ canvas, hero, project, width, height, drops, blocked }) {
    const rect = canvas.getBoundingClientRect(), box = document.getElementById('hero-errors');
    if (box) {
      for (const line of [...box.children]) if (+line.dataset.until <= performance.now()) line.remove();
      box.hidden = !box.children.length || !rect.width || !!window.Cutscene?.active;
      if (!box.hidden) {
        const [x, y] = project(hero.x, hero.y, 156);
        const scene = canvas.parentElement.getBoundingClientRect();
        const margin = box.offsetWidth / 2 + 8;
        box.style.left = Math.max(margin, Math.min(rect.width - margin, x / width * rect.width)) + 'px';
        box.style.top = Math.max(box.offsetHeight + 8, y / height * rect.height + rect.top - scene.top) + 'px';
      }
    }
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
      const gold = document.getElementById('loot-gold-tooltip');
      if (gold && hover !== key) {
        clearHover(); gold.textContent = tr(`${d.value} gold`); gold.hidden = false; hover = key;
      }
      placeTooltip(gold);
    }
  }
  return {
    error, draw,
    pointer(event) { pointer = event.pointerType === 'touch' ? null : { x: event.clientX, y: event.clientY }; },
    leave() { pointer = null; clearHover(); },
    reset() { pointer = null; clearHover(); document.getElementById('hero-errors')?.replaceChildren(); const box = document.getElementById('hero-errors'); if (box) box.hidden = true; },
  };
})();
