const assert = require('node:assert/strict');
// Find a route through the REAL exported collision geometry, without changing server state.
function route(map, start, goal) {
  // Objects are bucketed in 4-tile cells (inflated by 1 tile, more than any margin used here), so a segment tests only the few
  // objects near it: the shaped zones hold thousands of objects and a full scan per segment blocked this process for seconds, long
  // enough for the server to drop the bot (its packet queue filled). The per-object test is unchanged.
  const H=4,cells=bucketsOf(map,H);
  const segmentFree = (a,b,margin=.4) => {
    const x0=Math.floor((Math.min(a.x,b.x)-margin)/H),x1=Math.floor((Math.max(a.x,b.x)+margin)/H),y0=Math.floor((Math.min(a.y,b.y)-margin)/H),y1=Math.floor((Math.max(a.y,b.y)+margin)/H);
    const seen=new Set();
    for(let cy=y0;cy<=y1;cy++)for(let cx=x0;cx<=x1;cx++)for(const o of cells.get(cy*cells.w+cx)||[]){
      if(seen.has(o))continue;seen.add(o);
      const dx=b.x-a.x,dy=b.y-a.y;
      if(o.width) { const steps=Math.ceil(Math.hypot(dx,dy)/.1);for(let i=0;i<=steps;i++){const t=i/(steps||1);if(Math.abs(a.x+dx*t-o.x)<o.width/2+margin&&Math.abs(a.y+dy*t-o.y)<o.depth/2+margin)return false;}continue; }
      const t=Math.max(0,Math.min(1,((o.x-a.x)*dx+(o.y-a.y)*dy)/(dx*dx+dy*dy || 1)));
      if(!(Math.hypot(o.x-a.x-dx*t,o.y-a.y-dy*t)>o.r+margin))return false;
    }
    return true;
  };
  const key = p => `${p.x},${p.y}`;
  // An actor's real point can be clear while its rounded grid cell is inside a tree.
  const nearby = point => {
    const cells=[];
    for(let y=Math.floor(point.y)-2;y<=Math.ceil(point.y)+2;y++) for(let x=Math.floor(point.x)-2;x<=Math.ceil(point.x)+2;x++) {
      const cell={x,y};
      if(x>=1&&y>=1&&x<=map.size-2&&y<=map.size-2&&segmentFree(cell,cell))cells.push(cell);
    }
    return cells.sort((a,b)=>Math.hypot(a.x-point.x,a.y-point.y)-Math.hypot(b.x-point.x,b.y-point.y));
  };
  // Match the server's .3 player radius for the connector out of a collision edge.
  const source=nearby(start).find(cell=>segmentFree(start,cell,.3-1e-6)),end=nearby(goal)[0];
  assert.ok(source&&end,'Route endpoints have clear approach cells');
  const queue = [source], previous = new Map([[key(source), null]]);
  for (let i=0; i<queue.length; i++) {
    const current=queue[i]; if (key(current)===key(end)) break;
    for (const [dx,dy] of [[0,1],[0,-1],[1,0],[-1,0],[1,1],[-1,-1],[1,-1],[-1,1]]) {
      const next={x:current.x+dx,y:current.y+dy};
      if (next.x<1 || next.y<1 || next.x>map.size-2 || next.y>map.size-2 || previous.has(key(next)) || !segmentFree(current,next)) continue;
      previous.set(key(next),current);queue.push(next);
    }
  }
  assert.ok(previous.has(key(end)), 'Destination is reachable through shared collision geometry: '+JSON.stringify({start,goal,source,end}));
  const points=[]; for(let current=end; current; current=previous.get(key(current))) points.unshift(current);
  const simplified=[];let anchor=start;
  for (let i=0;i<points.length;) {let j=i;while(j+1<points.length && segmentFree(anchor,points[j+1],simplified.length===0?.3-1e-6:.4)) j++;simplified.push(points[j]);anchor=points[j];i=j+1;}
  return simplified;
}
const bucketCache = new WeakMap();
function bucketsOf(map, H) {
  const hit = bucketCache.get(map.objects);
  if (hit) return hit;
  const cells = new Map(); cells.w = Math.ceil((map.size || 512) / H) + 8;
  for (const o of map.objects) {
    const hx = (o.width ? o.width / 2 : o.r) + 1, hy = (o.width ? o.depth / 2 : o.r) + 1;
    for (let cy = Math.floor((o.y - hy) / H); cy <= Math.floor((o.y + hy) / H); cy++) for (let cx = Math.floor((o.x - hx) / H); cx <= Math.floor((o.x + hx) / H); cx++) {
      const k = cy * cells.w + cx; (cells.get(k) || cells.set(k, []).get(k)).push(o);
    }
  }
  bucketCache.set(map.objects, cells);
  return cells;
}
module.exports = { route };
