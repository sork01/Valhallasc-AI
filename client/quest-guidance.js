'use strict';
// Resolve objectives against the current authored world. No saved layout coordinates or translated ids.
window.QuestGuidance = {
  create(areas, sources) {
    const npcs = new Map(), places = new Map(), enemies = new Map(), pools = new Map();
    const point = (p, zone, extra = {}) => ({ x: p.x, y: p.y, zone, ...extra });
    const index = (map, key, value) => { if (!map.has(key)) map.set(key, []); map.get(key).push(value); };
    areas.forEach((area, zone) => {
      for (const n of area.npcs || []) index(npcs, n.id, point(n, zone, { npc: n.id, escort: n.escort }));
      for (const p of area.places || []) {
        index(places, p.id, point(p, zone, { place: p.id }));
        if (p.chain) index(places, `chain:${p.chain}`, point(p, zone, { place: p.id }));
      }
      for (const s of area.slimes || []) if (!s.ambush) index(enemies, s.kind, point(s, zone, { enemy: s.kind }));
    });
    const arena = areas.flatMap((a, z) => (a.npcs || []).filter(n => n.offers?.some(o => o.id === 'gauntlet')).map(n => point(n, z, { npc: n.id })));
    function pool(q, o) {
      const key = `${q.id}:${o.kind}:${o.target}`;
      if (pools.has(key)) return pools.get(key);
      let points = [];
      if (o.kind === 'kill') {
        if (q.summonNpc) points = (npcs.get(q.summonNpc) || []).filter(p => p.zone === q.summonZone);
        else {
          const kinds = o.target === 'slime' ? ['green', 'blue', 'pink', 'yellow'] : o.target === 'any' ? [...enemies.keys()] : [o.target];
          points = kinds.flatMap(kind => enemies.get(kind) || []);
          const local = points.filter(p => p.zone === q.zone);
          // Broad hunts belong to the quest's province. A named dungeon enemy may live several gates away.
          if (local.length || ['slime', 'any'].includes(o.target)) points = local;
        }
      } else if (o.kind === 'bring') {
        points = sources[o.target] || [];
        // Secret key hunts retain their giver's hint, never the positions of hidden crosses.
        if (!points.length && /^(hour_shard_|ember_shard_|ember_key$)/.test(o.target)) points = npcs.get(q.npc) || [];
      } else if (['visit', 'hold', 'memory', 'echo', 'chime'].includes(o.kind)) {
        points = places.get(o.kind === 'chime' ? `chain:${o.target}` : o.target) || [];
      } else if (['talk', 'escort', 'handoff'].includes(o.kind)) points = npcs.get(o.target) || [];
      else if (o.kind === 'reach') {
        points = areas.flatMap((a, z) => a.name === o.target && a.spawn ? [point(a.spawn, z)] : []);
      } else if (o.kind === 'gauntlet') points = arena;
      pools.set(key, points);
      return points;
    }
    function groups(q, counts, context = {}) {
      const out = [], first = q.objectives.findIndex((o, i) => (counts[i] || 0) < o.count);
      q.objectives.forEach((o, i) => {
        if ((counts[i] || 0) >= o.count) return;
        // Memory and echo scenes must be visited in the same order the authoritative story uses.
        if (q.story && ['memory', 'echo'].includes(o.kind) && i !== first) return;
        let points = pool(q, o);
        if (o.kind === 'escort' && context.escorts?.some(e => e.npc === o.target)) {
          points = points.map(p => {
            const end = p.escort?.route?.at(-1);
            return end ? { ...p, x: end[0], y: end[1], npc: undefined } : p;
          });
        }
        const buckets = new Map();
        for (const p of points) index(buckets, `${p.zone}:${p.enemy || p.npc || p.place || ''}`, p);
        for (const candidates of buckets.values()) out.push({ objective: i, label: o.label, candidates });
      });
      return out;
    }
    const livePoint = (p, context) => {
      const n = p.npc && context.npc?.(p.zone, p.npc);
      return n ? { ...p, x: n.x, y: n.y } : p;
    };
    function nearest(candidates, zone, x, y, context = {}) {
      let best = null, distance = Infinity;
      for (const candidate of candidates) {
        if (candidate.zone !== zone) continue;
        const p = livePoint(candidate, context), d = (p.x - x) ** 2 + (p.y - y) ** 2;
        if (d < distance) { best = p; distance = d; }
      }
      return best;
    }
    return { groups, nearest, pool };
  },
};
