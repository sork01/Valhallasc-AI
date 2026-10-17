'use strict';
// Brass meridian chambers, starlit dust and the open iris beneath the Lapis Erg.
(() => {
  const {iso,poly,line,prism}=City.kit;
  const oval=(g,x,y,rx,ry,fill,stroke)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,Math.PI*2);g.fillStyle=fill;g.fill();if(stroke){g.strokeStyle=stroke;g.lineWidth=3;g.stroke();}};
  City.art.astro_wall={box:[465,570,230,450],draw(g,o){DungeonVisual.structure(g,o,'sunken_astrolabe');}};
  City.art.astro_lamp={box:[170,265,85,230],draw(g,o){
    prism(g,.75,.75,65,'#b28c5b','#586a6b','#344c54');
    oval(g,0,-83,23,23,'#d8bb7c','#f2dfad');oval(g,0,-83,15,15,'#366f81');
    for(let a=0;a<6;a++){const t=a*Math.PI/3;oval(g,Math.cos(t)*31,-83+Math.sin(t)*31,4,4,'#f2d895');}
  },animate(g,o,t){g.save();g.globalAlpha=.22+.12*Math.sin(t*2+o.x);oval(g,0,-83,40,40,'#a9f1ed');g.restore();}};
  City.art.astro_orrery={box:[445,390,220,325],draw(g){
    prism(g,2.6,2.3,27,'#987c57','#5e6671','#293d4b');
    for(let r of [43,63,86]){g.beginPath();g.ellipse(0,-113,r,r*.55,0,0,Math.PI*2);g.strokeStyle='#ebd59b';g.lineWidth=5;g.stroke();}
    oval(g,0,-113,27,27,'#7dcbd0','#f4e7bd');
    for(let a=0;a<8;a++){const t=a*Math.PI/4;oval(g,Math.cos(t)*80,-113+Math.sin(t)*46,6,6,a%2?'#f8de9a':'#87d4dc');}
  }};
  City.art.astro_seal={box:[235,130,115,95],draw(g){
    oval(g,0,0,82,30,'#314954','#dfc38c');oval(g,0,0,57,20,'#245c70','#f2dfab');
    for(let a=0;a<12;a++){const t=a*Math.PI/6;oval(g,Math.cos(t)*69,Math.sin(t)*25,3,4,'#ebd6a3');}
  }};
  const ground=(x,y,tone,alt,zone)=>DungeonVisual.ground('sunken_astrolabe',x,y,tone,alt,zone);
  const detail=(g,px,py,x,y,TW,TH,zone)=>DungeonVisual.detail(g,'sunken_astrolabe',px,py,x,y,TW,TH,zone);
  function weather(g,t,w,h){g.save();for(let i=0;i<26;i++){const x=(i*173+t*(3+i%4))%w,y=(i*127+t*(7+i%3))%h;oval(g,x,y,1.3,1.7,'rgba(249,229,172,.3)');}g.restore();}
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);poly(g,[[-66,0],[-56,-93],[-31,-149],[0,-171],[31,-149],[56,-93],[66,0]],'#725d50','#f0d496',6);
    const glow=g.createRadialGradient(0,-77,2,0,-77,72);glow.addColorStop(0,'#fff0bb');glow.addColorStop(.5,'#86d5dc');glow.addColorStop(1,'#265c6c');
    oval(g,0,-76,42+Math.sin(t*2)*2,63,glow,'#f2d9a5');
    for(let a=0;a<8;a++){const q=a*Math.PI/4+t*.15;oval(g,Math.cos(q)*29,-76+Math.sin(q)*44,4,5,'#f7e6bd');}
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#233a43';g.lineWidth=4;g.fillStyle='#f5e6bc';g.strokeText(p.name,0,-182);g.fillText(p.name,0,-182);g.restore();
  }
  window.SunkenArt={ground,detail,weather,portal};
})();
