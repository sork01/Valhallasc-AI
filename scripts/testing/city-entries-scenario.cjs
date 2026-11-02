// Focused optimized-release probe; direct fixtures, normal movement, no grinding.
module.exports = kit => ({
  description:'Street-aligned approaches through every entrance of the four major cities.',
  startLevel:99, levelSpread:0,
  async run(w,check){
    const bot='CityRoadProbe';await w.connect({bot,class:'warrior'});let count=0;
    for(const zone of [0,4,9,17]){
      const map=kit.zones[zone];
      for(const e of map.cityEntrances){
        const portal=map.portals.find(p=>p.id===e.portal),first=e.points[0];
        const start=portal?[first[0]-portal.walk[0]*6,first[1]-portal.walk[1]*6]:first;
        await w.debug(bot,{op:'teleport',zone,x:start[0],y:start[1]});
        for(const [x,y]of e.points.slice(1)){
          await w.action(bot,{type:'move',x,y});
          await w.waitFor(()=>w.player(bot).zone===zone&&Math.hypot(w.player(bot).x-x,w.player(bot).y-y)<.4,15000,e.id);
          await w.action(bot,{type:'stop'});
        }
        check(true,`${map.city.name}/${e.id}: authoritative movement reaches the city street`);count++;
      }
    }
    check(count===12,'All twelve city entrances were walked');
  }
});
