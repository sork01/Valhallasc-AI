'use strict';
// Rimeveil Glacier's own scenery: the snow-capped mountains of the painted atlas (scripts/rimeveil_design.py places them).
(() => {
  const {poly}=City.kit;
  const C={ink:'#1d2636',stone:'#7d93ad',lee:'#4c607b',snow:'#f6fafd',snowLee:'#b5cce3',crack:'#38475e'};
  const line=(g,p,c,w=2)=>{g.beginPath();p.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineJoin='round';g.stroke();};
  // Three sizes (`v`), the foot is the collision circle. Blue-grey rock with a dark lee side, a ragged cap of snow, a few ice-blue gullies.
  const PEAK=[4.6,5.2,6.1];
  City.art.rime_peak={box:[820,840,410,630],occludes:true,draw(g,o){
    const size=PEAK[Math.min(o.v||0,2)],W=size*62.2,D=size*31.1,H=size*96,ax=((o.v||0)-1)*10,top=[ax,-H];
    const edge=[];for(let i=0;i<=10;i++){const a=Math.PI*i/10;edge.push([Math.cos(a)*W,Math.sin(a)*D]);}
    const left=[-W,0],right=[W,0],foot=[W*.16,D];
    poly(g,[top,left,...edge.slice(5).reverse(),foot],C.stone,C.ink,3);
    poly(g,[top,foot,...edge.slice(0,4).reverse(),right],C.lee,C.ink,3);
    for(const [t,k] of [[.3,.5],[.46,-.34],[.6,.18],[.74,-.62],[.4,.72]]){
      const y=-H*(1-t*.9),x=ax*(1-t)+W*t*k;
      line(g,[[x,y],[x+W*.05*Math.sign(k||1),y+H*.12],[x+W*.02,y+H*.2],[x+W*.09*Math.sign(k||1),y+H*.3]],k<0?'#9bb3cc':C.crack,3);
    }
    // the cap: a ragged skirt of snow, its shaded half on the lee side
    poly(g,[top,[ax-W*.3,-H*.64],[ax-W*.2,-H*.7],[ax-W*.13,-H*.58],[ax-W*.02,-H*.68],[ax+W*.08,-H*.57],[ax+W*.18,-H*.66],[ax+W*.3,-H*.6]],C.snow,C.ink,2.5);
    poly(g,[top,[ax+W*.02,-H*.68],[ax+W*.08,-H*.57],[ax+W*.18,-H*.66],[ax+W*.3,-H*.6]],C.snowLee,C.snowLee,1);
  }};
})();
