'use strict';
// Jade masonry, falling rain and a flooded altar in the sealed Rain Crown Temple.
(() => {
  const {iso,poly,line,prism}=City.kit;
  const oval=(g,x,y,rx,ry,fill,stroke)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,6.283);g.fillStyle=fill;g.fill();if(stroke){g.strokeStyle=stroke;g.lineWidth=3;g.stroke();}};
  City.art.rain_wall={box:[450,520,225,410],draw(g,o){DungeonVisual.structure(g,o,'rain_crown');}};
  City.art.rain_brazier={box:[180,260,90,220],draw(g,o){
    prism(g,.7,.7,59,'#789486','#3d6663','#204853');
    poly(g,[[-24,-74],[0,-86],[24,-74],[19,-64],[-19,-64]],'#adc99f','#366768',3);
    oval(g,0,-84,11,20,o.v===2?'#d6ef9f':'#8be5cf');
  },animate(g,o,t){g.save();g.shadowColor='#9ff5d9';g.shadowBlur=15+5*Math.sin(t*2+o.x);oval(g,0,-84,5,14,'#defce5');g.restore();}};
  City.art.rain_crown_altar={box:[370,360,185,285],draw(g){
    prism(g,2.4,2,24,'#8ba996','#47726e','#29545b');
    for(let s of [-1,1])poly(g,[[s*9,-80],[s*17,-174],[s*42,-154],[s*31,-87]],'#82c3a0','#d6edbb',4);
    oval(g,0,-113,37,52,'#4b8e81','#d4eaba');oval(g,0,-120,14,30,'#e4f6c7');
  }};
  City.art.rain_crown_glyph={box:[220,110,110,85],draw(g){
    oval(g,0,0,80,28,'#235961','#90c9af');oval(g,0,0,47,17,'#143d4c','#cbe9b4');
    for(let a=0;a<8;a++){const t=a*Math.PI/4;oval(g,Math.cos(t)*60,Math.sin(t)*20,4,5,'#c5eed0');}
  }};
  const ground=(x,y,tone,alt,zone)=>DungeonVisual.ground('rain_crown',x,y,tone,alt,zone);
  const detail=(g,px,py,x,y,TW,TH,zone)=>DungeonVisual.detail(g,'rain_crown',px,py,x,y,TW,TH,zone);
  function weather(g,t,w,h){g.save();g.strokeStyle='rgba(180,248,219,.24)';g.lineWidth=1.2;for(let i=0;i<37;i++){const x=(i*151+t*8)%w,y=(i*97+t*(16+i%3)*3)%h;g.beginPath();g.moveTo(x,y);g.lineTo(x-4,y+14);g.stroke();}g.restore();}
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);poly(g,[[-55,0],[-51,-91],[-32,-145],[0,-169],[32,-145],[51,-91],[55,0]],'#23545c','#b0d8b1',5);
    const glow=g.createRadialGradient(0,-72,2,0,-72,67);glow.addColorStop(0,'#ecffe0');glow.addColorStop(.5,'#79c5ae');glow.addColorStop(1,'#1b4b57');
    oval(g,0,-72,39+Math.sin(t*2)*2,61,glow,'#d7edc3');oval(g,0,-72,7,45,'#235c5a');
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#153d49';g.lineWidth=4;g.fillStyle='#def5cb';g.strokeText(p.name,0,-177);g.fillText(p.name,0,-177);g.restore();
  }
  window.RainCrownArt={ground,detail,weather,portal};
})();
