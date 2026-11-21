'use strict';
// Presentation and inputs only. Every cast, bite, catch, record and active spot comes from the world.
(() => {
  const $ = id => document.getElementById(id);
  const tr = text => window.Locale?.translate(text) || text;
  const now = () => performance.now();
  const clamp = n => Math.max(0, Math.min(1, n));
  const SKILL_BAND = 30;
  const water = zone => window.FISHING_WATERS?.[zone || 0];
  const lavaWater = zone => water(zone)?.habitat === 'Lava';
  const colours = { common: '#ddd6c7', uncommon: '#83df83', rare: '#80bdff', epic: '#cf9bff', legendary: '#ffbd59' };
  const catalogue = () => (window.WORLD_ITEMS || []).filter(i => i.kind === 'fish');
  const definition = id => window.Inventory?.definition(id);
  const node = (tag, text, cls) => { const el = document.createElement(tag); if (text != null) el.textContent = text; if (cls) el.className = cls; return el; };
  let own = null, zone = null, spots = [], log = {}, cast = null, result = null, miss = null, signature = '', shoreHint = false;
  let lastPress = -Infinity, sound = () => {}, clockOffset = 0;
  const lines = new Map();
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const calm = () => !!window.Prefs?.lowGraphics || motion.matches;

  // A visibility hint, never a claim that the world will accept a cast. Match the facing ray and liquid shapes.
  function shore(hero, map, checkRod = true) {
    if (!hero || !map || !water(hero.zone)) return false;
    const lava = lavaWater(hero.zone), level = hero.level || 1;
    if (checkRod && !(hero.inventory || []).some(s => {
      const i = definition(s.item); return s.quantity > 0 && i?.kind === 'rod' && i.requiredLevel <= level && (!lava || !!i.fishing?.lava);
    })) return false;
    const length = Math.hypot(hero.fx, hero.fy); if (!length) return false;
    const fx = hero.fx / length, fy = hero.fy / length, dock = map.dock;
    const onDock = dock && hero.x >= dock.x0 && hero.x <= dock.x1 && hero.y >= dock.y0 && hero.y <= dock.y1;
    for (const o of map.objects || []) {
      let start, end;
      const waters = ['water', 'jungle_water', 'jade_pool'], small = ['seafoam', 'year_spring_pool', 'frostwake_frozen_pool', 'lapis_oasis'];
      const r = lava ? (['lava', 'ew_lava'].includes(o.kind) ? o.r : 0) : waters.includes(o.kind) ? o.r : small.includes(o.kind) ? Math.max(1, o.r || 0) : 0;
      if (r) {
        const dx = o.x - hero.x, dy = o.y - hero.y, along = dx * fx + dy * fy, square = r * r - (dx * fy - dy * fx) ** 2;
        if (Math.hypot(dx, dy) < r) return false;
        if (square <= 0) continue;
        start = along - Math.sqrt(square); end = along + Math.sqrt(square);
      } else if (!lava && o.kind === 'void' && onDock) {
        const interval = (p, d, c, size) => Math.abs(d) < 1e-8 ? (Math.abs(p - c) < size / 2 ? [-Infinity, Infinity] : [Infinity, -Infinity]) : [(c - size / 2 - p) / d, (c + size / 2 - p) / d].sort((a, b) => a - b);
        const x = interval(hero.x, fx, o.x, o.w || o.width), y = interval(hero.y, fy, o.y, o.d || o.depth);
        start = Math.max(x[0], y[0]); end = Math.min(x[1], y[1]);
      } else continue;
      const lo = Math.max(3, start), hi = Math.min(6, end);
      if (start < 0 || start > 4 || lo >= hi) continue;
      const distance = (lo + hi) / 2, x = hero.x + fx * distance, y = hero.y + fy * distance, ship = dock?.ship;
      if (ship && Math.abs(x - ship.x) < ship.beam / 2 && y >= ship.y0 && y <= ship.y1) continue;
      return true;
    }
    if (!lava && !onDock && map.shapeFloor && map.shapeEdge) {
      const at = d => ({ x: hero.x + fx * d, y: hero.y + fy * d });
      const sea = p => p.x >= 0 && p.y >= 0 && map.shapeFloor[Math.floor(p.y)]?.[Math.floor(p.x)] === ' ' && map.shapeEdge[Math.floor(p.y)]?.[Math.floor(p.x)] === 'c';
      let start = null, end = 6;
      if (sea(hero)) return false;
      for (let step = 1; step <= 48; step++) {
        const distance = step / 8;
        if (sea(at(distance))) { if (start === null) { if (distance > 4) return false; start = distance; } }
        else if (start !== null) { end = distance - .125; break; }
      }
      if (start !== null && Math.max(3, start) < Math.min(6, end)) {
        const point = at((Math.max(3, start) + Math.min(6, end)) / 2), ship = dock?.ship;
        return !(ship && Math.abs(point.x - ship.x) < ship.beam / 2 && point.y >= ship.y0 && point.y <= ship.y1);
      }
    }
    return false;
  }
  function requiredRod(zone, rich = false) {
    return (window.WORLD_ITEMS || []).filter(i => i.kind === 'rod' && (i.fishing?.zones?.includes(zone) || rich && i.fishing?.richZones?.includes(zone))).sort((a,b) => b.fishing.tier - a.fishing.tier)[0];
  }
  function requirement(zone, rich = false) {
    const rod = requiredRod(zone, rich);
    return rod ? tr('Requires {0} · level {1}').replace('{0}',tr(rod.name)).replace('{1}',rod.requiredLevel) : '';
  }
  function available() {
    return !!own && !own.dead && !own.ghost && !own.sparkTravel && !own.inCombat && !(own.stun > 0) && !window.Cutscene?.active && !!(own.fishing || shoreHint);
  }
  function press() {
    if (!window.Field?.canAct || window.Cutscene?.active || Field.hero?.sparkTravel || now() - lastPress < 160) return false;
    lastPress = now();
    Field.clearInput();
    // Do not send a stop packet here: it can clear facing/targets before the authoritative cast check.
    return Online.send({ type: 'fish' });
  }
  function reset() {
    richPointer = null; hideRichTooltip();
    own = null; zone = null; spots = []; log = {}; cast = null; result = null; miss = null; signature = ''; shoreHint = false; lastPress = -Infinity; clockOffset = 0;
    lines.clear(); $('fishing-panel').hidden = true; $('fishing-catch').hidden = true; $('stage').classList.remove('fishing-legendary');
  }
  function sync(packet, hero, map, emit) {
    if (emit) sound = emit;
    if (own && (own.id !== hero.id || own.zone !== hero.zone)) { lines.clear(); cast = null; result = null; miss = null; }
    own = hero; zone = map; log = hero.fishingLog || {}; shoreHint = shore(hero, map, false);
    // Server's Unix clock, when supplied, avoids relying on the device wall clock for the draining ring.
    if (Number.isFinite(packet.fishingTime)) clockOffset = packet.fishingTime * 1000 - Date.now();
    spots = (packet.fishingSpots || []).filter(p => Number.isFinite(p.x) && Number.isFinite(p.y));
    const seen = new Set();
    for (const p of packet.players || []) {
      if ((p.zone || 0) !== (hero.zone || 0) || !p.fishing) continue;
      seen.add(p.id);
      const old = lines.get(p.id), f = p.fishing;
      const same = old && old.x === f.x && old.y === f.y;
      const richSpot = same ? old.richSpot : p.id === hero.id && cast ? cast.richSpot : spots.find(spot => Math.hypot(spot.x - f.x, spot.y - f.y) <= 3.) || null;
      const line = { ...f, richSpot, actor: p, at: same ? old.at : now(), biteAt: f.state === 'bite' ? (same && old.biteAt || now()) : null };
      lines.set(p.id, line);
      if (p.id === hero.id) {
        if (!same && !cast) { cast = { ...line, at: now(), landed: f.state !== 'cast' }; }
        if (Number.isFinite(hero.fishDeadline)) line.deadline = hero.fishDeadline;
      }
    }
    for (const id of lines.keys()) if (!seen.has(id)) lines.delete(id);
    if (cast && !hero.fishing && now() - cast.at > 700) cast = null;
    if (hero.dead || hero.sparkTravel) { cast = null; result = null; miss = null; }
    if (!hero.fishing && cast?.landed) cast = null;
    if (!$('fishing-panel').hidden) renderLog();
  }
  function event(e, self, emit) {
    if (emit) sound = emit;
    if (e.actor !== self || !e.kind?.startsWith('fish_')) return;
    if (e.kind === 'fish_cast') {
      result = null; miss = null; cast = { x: e.x, y: e.y, richSpot: spots.find(spot => Math.hypot(spot.x - e.x, spot.y - e.y) <= 3.) || null, lava: lavaWater(own?.zone), at: now(), landed: false };
      sound('cast');
    } else if (e.kind === 'fish_bite') {
      const line = lines.get(self); if (line) { line.state = 'bite'; line.deadline = e.deadline; line.biteAt = now(); }
      sound('bite');
    } else if (e.kind === 'fish_catch') {
      const from = lines.get(self) || cast;
      result = { ...e, from: from && { x: from.x, y: from.y, lava: from.lava }, at: now(), celebrated: false };
      lines.delete(self); cast = null; sound('reel');
    } else if (e.kind === 'fish_miss') {
      const from = lines.get(self) || cast;
      miss = from && { ...from, at: now() }; lines.delete(self); cast = null;
      window.Announce?.show(e.text || 'It got away.', 'error');
    }
  }
  function icon(item) {
    const el = node('span', null, 'fishing-icon');
    // Inventory.icon is trusted renderer output; item names and all packet text use textContent.
    el.innerHTML = window.Inventory?.icon(item) || ''; return el;
  }
  const trainingWaters = skill => window.FISHING_SKILL_WATERS?.[Math.floor(skill / SKILL_BAND)] || [];
  function trainingHint(skill) {
    const world = window.WORLD_MAP;
    const names = trainingWaters(skill).map(id => {
      const name = id === 0 ? world?.name : world?.zones?.[id - 1]?.name;
      const site = water(id)?.name;
      return name && (site ? tr(name) + ' · ' + tr(site) : tr(name));
    }).filter(Boolean);
    return names.length ? tr('Fish in {0} to reach skill {1}.').replace('{0}', names.join(' / '))
      .replace('{1}', (Math.floor(skill / SKILL_BAND) + 1) * SKILL_BAND) : '';
  }
  function renderLog() {
    const species = catalogue(), key = JSON.stringify([log, own?.inventory, own?.level, $('fishing-filter').value, window.Locale?.language]);
    if (key === signature) return; signature = key;
    const caught = species.filter(i => (log.species?.[i.id]?.count || 0) > 0).length;
    const skill = tr('Fishing skill {0} / {1}').replace('{0}', log.skill || 1).replace('{1}', window.FISHING_SKILL_WATERS.length * SKILL_BAND);
    $('fishing-records').textContent = skill + ' · ' + tr('Caught: {0} · Species: {1}/{2} · Legendary: {3} · Best streak: {4}')
      .replace('{0}', log.total || 0).replace('{1}', caught).replace('{2}', species.length).replace('{3}', log.legendary || 0).replace('{4}', log.longestStreak || 0);
    const training = $('fishing-training');
    training.textContent = trainingHint(log.skill || 1);
    training.hidden = !training.textContent;
    const rows = species.filter(i => !$('fishing-filter').value || i.fishing?.habitat === $('fishing-filter').value).map(i => {
      const record = log.species?.[i.id], known = (record?.count || 0) > 0, row = node('li', null, 'fishing-species'); row.dataset.item = i.id; row.dataset.caught = String(known);
      const art = icon(i); art.classList.toggle('silhouette', !known);
      const details = node('div'), name = node('strong', tr(known ? i.name : 'Undiscovered fish'));
      name.style.color = known ? colours[i.rarity] || colours.common : colours.common;
      details.append(name, node('small', tr(i.fishing.habitat)), node('span', known ? tr('{0} caught · Best: ca {1} kg').replace('{0}', record.count).replace('{1}', record.bestKg) : tr('Catch this species to reveal its record.')));
      row.append(art, details); return row;
    });
    const progression = node('li', null, 'fishing-progression');
    progression.append(node('strong', tr('Rod progression')));
    const rods = (window.WORLD_ITEMS || []).filter(i => i.kind === 'rod').sort((a,b)=>a.fishing.tier-b.fishing.tier);
    const current = rods.filter(i => i.requiredLevel <= (own?.level || 1) && own?.inventory?.some(s => s.item === i.id && s.quantity > 0)).at(-1);
    const next = rods.find(i => i.fishing.tier > (current?.fishing.tier || 0));
    progression.append(node('p', tr('Current rod: {0}').replace('{0}', tr(current?.name || 'No rod yet'))), node('p', tr('Next upgrade: {0}').replace('{0}', tr(next?.name || 'Fully upgraded'))));
    const ladder = node('details'); ladder.append(node('summary', tr('All rod upgrades')));
    for (const rod of rods) {
      const row = node('div'); row.append(node('b', tr(rod.name)));
      for (const text of window.Inventory?.rodDetails?.(rod) || []) row.append(node('small', text)); ladder.append(row);
    }
    progression.append(ladder);
    $('fishing-species').replaceChildren(progression, ...rows);
  }
  function close(resume = true) { $('fishing-panel').hidden = true; if (resume) window.Field?.setPaused(false); }
  function open() {
    if (!window.Online?.connected) return false;
    $('pause').hidden = true; $('fishing-panel').hidden = false; signature = ''; renderLog(); window.Field?.setPaused(true);
    $('fishing-close').focus({ preventScroll: true }); return true;
  }
  function card(project, width, height) {
    const el = $('fishing-catch'), age = result ? now() - result.at : Infinity;
    const show = result && age >= 600 && age < 3600 && own && !own.dead;
    el.hidden = !show;
    $('stage').classList.toggle('fishing-legendary', !!show && result.rarity === 'legendary' && !calm());
    if (!show) { if (age >= 3600) result = null; return; }
    if (!result.celebrated) {
      result.celebrated = true;
      const item = definition(result.item), name = tr(item?.name || result.item);
      el.replaceChildren(icon(item), node('strong', name), node('span', result.kg == null ? tr('Quantity: {0}').replace('{0}', result.quantity || 1) : tr('ca {0} kg · ×{1}').replace('{0}', result.kg).replace('{1}', result.quantity || 1)));
      if (result.skillUp) el.append(node('span', tr('Fishing skill increased to {0}.').replace('{0}', result.skillUp), 'fishing-skill-up'));
      else if (result.kg != null && !trainingWaters(log.skill || 1).includes(own.zone || 0)) {
        const hint = trainingHint(log.skill || 1);
        if (hint) el.append(node('span', hint, 'fishing-skill-up'));
      }
      el.style.setProperty('--fish-rarity', colours[result.rarity] || colours.common);
      sound(result.rarity === 'legendary' ? 'legendary' : 'catch');
    }
    const hero = window.Field?.hero || own, [x, y] = project(hero.x, hero.y), stage = $('stage'), box = el.getBoundingClientRect();
    // The scene uses virtual pixels; this DOM card uses device-sized CSS pixels, including on phones.
    const half = ((box.width || 240) / 2 + 8) / (stage.clientWidth || width) * width;
    const top = ((box.height || 80) + 8) / (stage.clientHeight || height) * height;
    el.style.left = `${Math.max(half, Math.min(width - half, x)) / width * 100}%`;
    el.style.top = `${Math.max(top, Math.min(height - 8, y - 145)) / height * 100}%`;
  }
  // Active points only: ordinary scenery ripples never become fishing hotspots.
  function richSpotAt(mx, my, project) {
    return spots.find(spot => { const [x, y] = project(spot.x, spot.y); return ((mx - x) / 96) ** 2 + ((my - y) / 56) ** 2 <= 1; }) || null;
  }
  function usingRichSpot() {
    const point = (lines.get(own?.id) || cast)?.richSpot;
    return !!point && spots.some(spot => Math.hypot(spot.x - point.x, spot.y - point.y) < .001);
  }
  let richPointer = null, richTooltip = null, tooltipKey = null;
  function hideRichTooltip() { if (richTooltip) richTooltip.hidden = true; }
  function waterAt(mx, my, project) {
    if (!zone || !own || !requiredRod(own.zone || 0)) return false;
    const a = project(0,0), b = project(1,0), c = project(0,1);
    const ux = b[0]-a[0], uy = b[1]-a[1], vx = c[0]-a[0], vy = c[1]-a[1], det = ux*vy-uy*vx;
    if (!det) return false;
    const dx = mx-a[0], dy = my-a[1], x = (dx*vy-dy*vx)/det, y = (ux*dy-uy*dx)/det, lava = lavaWater(own.zone);
    const pool = (zone.objects || []).some(o => {
      const r = lava ? (['lava','ew_lava'].includes(o.kind) ? o.r : 0) : ['water','jungle_water','jade_pool'].includes(o.kind) ? o.r : ['seafoam','year_spring_pool','frostwake_frozen_pool','lapis_oasis'].includes(o.kind) ? Math.max(1,o.r||0) : 0;
      return r > 0 && Math.hypot(x-o.x,y-o.y) < r;
    });
    const ship = zone.dock?.ship;
    if (ship && Math.abs(x-ship.x) < ship.beam/2 && y >= ship.y0 && y <= ship.y1) return false;
    return pool || !lava && x >= 0 && y >= 0 && zone.shapeFloor?.[Math.floor(y)]?.[Math.floor(x)] === ' ' && zone.shapeEdge?.[Math.floor(y)]?.[Math.floor(x)] === 'c';
  }
  function drawRichTooltip(project, width, height) {
    if (!richPointer || !window.Field?.canAct || own?.dead || window.Cutscene?.active) { hideRichTooltip(); return; }
    const rect = $('fieldcv').getBoundingClientRect();
    const spot = rect.width && rect.height && richSpotAt((richPointer.x - rect.left) / rect.width * width, (richPointer.y - rect.top) / rect.height * height, project);
    if (!spot && !(rect.width && rect.height && waterAt((richPointer.x-rect.left)/rect.width*width, (richPointer.y-rect.top)/rect.height*height, project))) { hideRichTooltip(); return; }
    if (!richTooltip) {
      richTooltip = node('div', null, 'fishing-spot-tooltip'); richTooltip.id = 'rich-fishing-tooltip'; richTooltip.setAttribute('role', 'tooltip');
      richTooltip.append(node('strong', tr('Rich fishing spot')), node('p', tr('Better chances for rare fish. Moves after 5–10 fish are caught here.')));
      document.body.append(richTooltip);
    }
    const key = `${own?.zone || 0}:${!!spot}:${window.Locale?.language}`;
    if (key !== tooltipKey) {
      const name = spot ? tr('Rich fishing spot') : tr(water(own?.zone)?.name || 'Ordinary fishing water');
      richTooltip.replaceChildren(node('strong', name), node('p', requirement(own?.zone || 0, !!spot)));
      if (spot) richTooltip.append(node('p', tr('Better chances for rare fish. Moves after 5–10 fish are caught here.')));
      tooltipKey = key;
    }
    richTooltip.hidden = false;
    const box = richTooltip.getBoundingClientRect();
    richTooltip.style.left = Math.max(8, Math.min(innerWidth - box.width - 8, richPointer.x + 14)) + 'px';
    richTooltip.style.top = Math.max(8, Math.min(innerHeight - box.height - 8, richPointer.y + 12)) + 'px';
  }
  function spotLabel(g, x, y) {
    g.save(); g.globalAlpha = 1; g.font = 'bold 14px sans-serif'; g.textAlign = 'center'; g.strokeStyle = '#10212b'; g.lineWidth = 4;
    g.strokeText(tr('Rich fishing spot'), x, y - 45); g.fillStyle = '#fff1a5'; g.fillText(tr('Rich fishing spot'), x, y - 45); g.font = '12px sans-serif'; g.strokeText(requirement(own?.zone || 0, true), x, y - 28); g.fillText(requirement(own?.zone || 0, true), x, y - 28); g.restore();
  }

  function ring(g, x, y, r, colour, alpha = 1) {
    g.save(); g.globalAlpha *= alpha; g.strokeStyle = colour; g.lineWidth = 1.6; g.beginPath(); g.ellipse(x, y, r, r * .42, 0, 0, Math.PI * 2); g.stroke(); g.restore();
  }
  // Ground ripples run below people; rods, bobbers and the reel arc run after the scene's depth-sorted actors.
  function drawFishing(g, project, width, height, ground = false, reduced = calm()) {
    const time = now(); reduced = reduced || calm();
    if (ground) {
      for (const spot of spots) {
        const [x, y] = project(spot.x, spot.y), phase = reduced ? .5 : (time / 1400 + spot.x) % 1;
        spotLabel(g, x, y);
        ring(g, x, y, 32 + phase * 50, lavaWater(own?.zone) ? '#ffa652' : '#b9efff', .85 - phase * .5);
        if (!reduced) ring(g, x, y, 24 + ((phase + .5) % 1) * 50, '#e1f7ff', .45);
      }
      return;
    }
    if (cast && !cast.landed && time - cast.at >= 500) { cast.landed = true; sound('plop'); if (cast.lava) sound('lava'); }
    for (const [id, line] of lines) {
      const actor = id === own?.id ? window.Field?.hero || line.actor : line.actor;
      const [hx, hy] = project(actor.x, actor.y), [bx, by] = project(line.x, line.y);
      if (Math.max(hx, bx) < -100 || Math.min(hx, bx) > width + 100 || Math.max(hy, by) < -150 || Math.min(hy, by) > height + 150) continue;
      const age = time - (id === own?.id && cast ? cast.at : line.at), progress = line.state === 'cast' ? clamp(age / 500) : 1;
      const biting = line.state === 'bite', bob = reduced ? 0 : Math.sin(time / 220) * 1.5;
      const x = reduced ? bx : hx + (bx - hx) * progress, y = reduced ? by : hy - 55 + (by - hy + 55) * progress - Math.sin(progress * Math.PI) * 75;
      g.save(); g.lineCap = 'round';
      const handX = hx + (bx > hx ? 16 : -16), handY = hy - 55, tipX = handX + (bx > hx ? 25 : -25), tipY = handY - (biting ? 20 : 38);
      g.strokeStyle = line.lava ? '#ca8252' : '#b8a17a'; g.lineWidth = 3; g.beginPath(); g.moveTo(handX, handY + 15); g.quadraticCurveTo(tipX, tipY - 10, tipX, tipY); g.stroke();
      g.strokeStyle = line.lava ? '#ffc486' : '#e1e4db'; g.lineWidth = .9; g.beginPath(); g.moveTo(tipX, tipY); g.quadraticCurveTo((tipX + x) / 2, (tipY + y) / 2 + (biting ? 0 : 20), x, y + bob); g.stroke();
      if (progress === 1) ring(g, bx, by, biting ? 18 : reduced ? 9 : 7 + (time / 1400 % 1) * 15, line.lava ? '#ffc080' : '#cfedff', .65);
      const dip = biting ? 3 : 0;
      g.fillStyle = line.lava ? '#30251f' : '#fff3dd'; g.beginPath(); g.ellipse(x, y + bob + dip - 4, 4, 7, .15, 0, Math.PI * 2); g.fill();
      g.fillStyle = line.lava ? '#ffb33b' : '#df4d49'; g.fillRect(x - 3, y + bob + dip - 10, 6, 5);
      if (line.lava && !reduced) { g.fillStyle = '#ffd581'; g.fillRect(x + 5 * Math.sin(time / 200), y - 15 - (time / 80 % 10), 2, 3); }
      if (biting) {
        g.fillStyle = '#ffe078'; g.font = 'bold 28px sans-serif'; g.textAlign = 'center'; g.fillText('!', bx, by - 24);
        const left = Number.isFinite(line.deadline) ? clamp((line.deadline * 1000 - Date.now() - clockOffset) / 1200) : clamp(1 - (time - line.biteAt) / 1200);
        g.strokeStyle = '#ffdf71'; g.lineWidth = 3; g.beginPath(); g.arc(bx, by - 35, 20, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * left); g.stroke();
        if (!reduced) for (let i = 0; i < 5; i++) { const a = i * 1.256 + time / 300; g.fillStyle = line.lava ? '#ffae61' : '#c0eeff'; g.fillRect(bx + Math.cos(a) * 15, by - 10 + Math.sin(a) * 7, 2, 4); }
        if (id === own?.id) { g.font = 'bold 14px sans-serif'; g.globalAlpha *= reduced ? 1 : .8 + .2 * Math.sin(time / 90); g.fillText(tr('Hook!') + '  ' + Keys.label('fish'), hx, hy + 27); }
      }
      if (id === own?.id) { const label = tr(usingRichSpot() ? 'Rich fishing spot' : 'Ordinary fishing water'); g.globalAlpha = 1; g.font = 'bold 14px sans-serif'; g.textAlign = 'center'; g.lineWidth = 4; g.strokeStyle = '#10212b'; g.strokeText(label, hx, hy + 49); g.fillStyle = usingRichSpot() ? '#fff1a5' : '#d2e6ec'; g.fillText(label, hx, hy + 49); }
      g.restore();
    }
    if (result?.from && time - result.at < 600 && own) {
      const h = window.Field?.hero || own, [hx, hy] = project(h.x, h.y), [bx, by] = project(result.from.x, result.from.y), p = clamp((time - result.at) / 600);
      const x = bx + (hx - bx) * p, y = by + (hy - by - 65) * p - (reduced ? 0 : Math.sin(p * Math.PI) * 90);
      g.save(); g.strokeStyle = '#c9aa7c'; g.lineWidth = 3; g.beginPath(); g.moveTo(hx + 12, hy - 42); g.quadraticCurveTo(hx + 50, hy - 115, hx + 25, hy - 85); g.stroke();
      g.strokeStyle = '#e8dec2'; g.lineWidth = 1; g.beginPath(); g.moveTo(hx + 25, hy - 85); g.lineTo(x, y); g.stroke();
      if (result.from.lava && !reduced) { g.strokeStyle = '#ff8d3c'; g.lineWidth = 4; g.beginPath(); g.moveTo(x + (bx - hx) * .12, y + 12); g.lineTo(x, y); g.stroke(); }
      g.fillStyle = colours[result.rarity] || colours.common; g.beginPath(); g.ellipse(x, y, 10, 5, -.4, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.moveTo(x + 7, y); g.lineTo(x + 16, y - 7); g.lineTo(x + 16, y + 6); g.closePath(); g.fill(); g.restore();
    }
    if (miss) { const age = (time - miss.at) / 600; if (age >= 1) miss = null; else { const [x, y] = project(miss.x, miss.y); ring(g, x, y, 8 + age * 24, '#b9dce7', 1 - age); } }
    card(project, width, height);
    drawRichTooltip(project, width, height);
  }
  $('fieldcv').addEventListener('pointermove', e => { richPointer = e.pointerType === 'touch' ? null : { x: e.clientX, y: e.clientY }; });
  $('fieldcv').addEventListener('pointerleave', () => { richPointer = null; hideRichTooltip(); });
  $('fishing-open').addEventListener('click', open); $('fishing-close').addEventListener('click', () => close());
  $('fishing-filter').addEventListener('change', renderLog);
  $('fishing-panel').addEventListener('click', e => { if (e.target === $('fishing-panel')) close(); });
  document.addEventListener('keydown', e => {
    if (!$('fishing-panel').hidden && Keys.is(e, 'menu')) { e.preventDefault(); e.stopPropagation(); close(); }
  }, true);
  const updateHint = () => { $('fishing-hint').textContent = tr('Face the water with a rod, then press ‹fish› to cast. Press again when a fish bites.').replace(/‹fish›/g, tr(Keys.label('fish', false))); };
  addEventListener('keymap-change', updateHint);
  updateHint();
  window.Fishing = { waterAt, requiredRod, requirement, sync, event, reset, press, available, shore, open, close, drawFishing, richSpotAt, get richActive() { return usingRichSpot(); }, get phase() { return lines.get(own?.id)?.state || 'idle'; } };
})();
