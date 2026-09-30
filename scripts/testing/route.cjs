const assert = require('node:assert/strict');
// Find a route through the REAL exported collision geometry, without changing server state.
function route(map, start, goal) {
  const segmentFree = (a,b,margin=.4) => map.objects.every(o => {
    const dx=b.x-a.x,dy=b.y-a.y;
    if(o.width) { const steps=Math.ceil(Math.hypot(dx,dy)/.1);for(let i=0;i<=steps;i++){const t=i/(steps||1);if(Math.abs(a.x+dx*t-o.x)<o.width/2+margin&&Math.abs(a.y+dy*t-o.y)<o.depth/2+margin)return false;}return true; }
    const t=Math.max(0,Math.min(1,((o.x-a.x)*dx+(o.y-a.y)*dy)/(dx*dx+dy*dy || 1)));
    return Math.hypot(o.x-a.x-dx*t,o.y-a.y-dy*t)>o.r+margin;
  });
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
module.exports = { route };
