'use strict';
// Cosmetic event state comes only from the authoritative snapshot calendar.
(() => {
  let events=[], claims={}, key='';
  const areas=[WORLD_MAP,...WORLD_MAP.zones];
  const hosts=new Set(['baker','city_bard','nacre_gardener','asterion_singer']);
  const halloween=()=>events.some(e=>e.id==='halloween');
  const eligible=n=>halloween() && [areas[window.Field?.zone||0]?.city,...(areas[window.Field?.zone||0]?.camps||[])].some(h=>h&&n.x>=h.x0&&n.x<=h.x1&&n.y>=h.y0&&n.y<=h.y1) && !n.travelStop && !['stone','scenery'].includes(n.art) && n.id.indexOf('meetingstone')<0 && n.art!=='stone';
  const line=(g,points,color,width=2)=>{g.strokeStyle=color;g.lineWidth=width;g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.stroke();};
  const ellipse=(g,x,y,rx,ry,color)=>{g.fillStyle=color;g.beginPath();g.ellipse(x,y,rx,ry,0,0,Math.PI*2);g.fill();};
  City.art.festivalPumpkins={box:[132,110,66,96],draw(g,o){
    for(const [x,y,k] of [[-19,-8,.8],[17,0,1],[-1,12,.65]]){
      g.save();g.translate(x,y);g.scale(k,k);ellipse(g,0,-20,26,24,'#342132');
      ellipse(g,-11,-21,13,21,'#c45b24');ellipse(g,11,-21,13,21,'#dc7026');ellipse(g,0,-21,13,22,'#ef942f');
      line(g,[[0,-42],[3,-51],[7,-53]],'#5d6840',5);
      g.fillStyle='#ffe4a0';g.strokeStyle='#573220';g.lineWidth=2;
      for(const side of [-1,1]){g.beginPath();g.moveTo(side*7,-30);g.lineTo(side*14,-20);g.lineTo(side*4,-20);g.closePath();g.fill();g.stroke();}
      line(g,[[-13,-13],[-7,-8],[0,-12],[7,-8],[13,-13]],'#fff0af',3);g.restore();
    }
  }};
  City.art.festivalLantern={box:[128,190,64,174],draw(g){
    ellipse(g,0,1,23,8,'#2a24324d');line(g,[[0,0],[0,-138],[26,-138],[26,-120]],'#3a293c',9);
    line(g,[[-2,-1],[-2,-141],[25,-141]],'#b88f62',3);
    ellipse(g,26,-96,21,27,'#41233f');ellipse(g,26,-96,17,23,'#f3a443');ellipse(g,26,-96,10,20,'#ffdc80');
    line(g,[[6,-119],[46,-119],[41,-125],[11,-125],[6,-119]],'#49364b',4);line(g,[[7,-73],[45,-73]],'#49364b',4);
    for(const x of [17,35])line(g,[[x,-116],[x,-76]],'#bd753c',2);
  }};
  City.art.festivalBunting={box:[190,156,95,140],draw(g){
    for(const x of [-66,66]){line(g,[[x,0],[x,-120]],'#4b3241',7);ellipse(g,x,-124,7,7,'#f4b24f');}
    g.strokeStyle='#cfa470';g.lineWidth=3;g.beginPath();g.moveTo(-66,-113);g.quadraticCurveTo(0,-76,66,-113);g.stroke();
    for(let i=0;i<7;i++){
      const x=-52+i*17.3,y=-111+18*(1-(x/66)**2);g.fillStyle=i%2?'#8b5aaa':'#e88c36';g.strokeStyle='#3b293a';g.lineWidth=2;
      g.beginPath();g.moveTo(x-7,y);g.lineTo(x+7,y);g.lineTo(x,y+22);g.closePath();g.fill();g.stroke();
    }
    ellipse(g,-64,0,12,6,'#352336');ellipse(g,64,0,12,6,'#352336');
  }};
  window.Seasonal={
    update(next,nextClaims){const signature=JSON.stringify([next||[],nextClaims||{}]);if(signature===key)return;
      key=signature;events=next||[];claims=nextClaims||{};window.Quests?.seasonChanged();return true;},
    get active(){return halloween();},
    questState(q){if(!q.season)return null;const event=events.find(e=>e.id===q.season);return !event?'inactive':claims[q.id]===event.year?'completed':'open';},
    decor(zone){return halloween()?areas[zone]?.seasonDecor||[]:[];},
    hat(n){return eligible(n)&&hosts.has(n.id);},
    drawNpc(g,n,t,top){
      if(!eligible(n))return;
      const scale=n.look?.scale||1,pose=window.NpcArt?.frame(n,t),bob=pose?.clip==='walk'?Math.abs(Math.sin(pose.step*Math.PI/4))*1.4:0;
      g.save();g.lineJoin='round';const y=-top*.58;
      g.fillStyle='#3a244a';g.strokeStyle='#1f1b32';g.lineWidth=2;
      for(const side of [-1,1]){g.beginPath();g.moveTo(0,y);g.lineTo(side*16*scale,y-8*scale);g.lineTo(side*12*scale,y+7*scale);g.closePath();g.fill();g.stroke();}
      ellipse(g,0,y,5*scale,5*scale,'#f1a23c');
      if(hosts.has(n.id)){
        const hy=-top+7-bob;ellipse(g,0,hy,27*scale,6*scale,'#30223f');
        g.fillStyle='#654578';g.beginPath();g.moveTo(-17*scale,hy);g.lineTo(-6*scale,hy-33*scale);g.lineTo(20*scale,hy);g.closePath();g.fill();g.stroke();
        line(g,[[-13*scale,hy-7*scale],[14*scale,hy-7*scale]],'#eea547',5*scale);
      }
      g.restore();
    },
    glow(g,zone,w2s){if(!halloween())return;g.save();g.globalCompositeOperation='screen';
      for(const o of this.decor(zone)){if(o.kind==='festivalBunting')continue;const [x,y]=w2s(o.x,o.y,o.kind==='festivalLantern'?88:20);g.globalAlpha=.13;ellipse(g,x,y,46,24,'#ffbf6c');}g.restore();}
  };
})();
