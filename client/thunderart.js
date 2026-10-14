'use strict';
// Thunderheart's slate chambers, storm pylons and charged bronze gate.
(() => {
  const {iso,poly,line,prism}=City.kit;
  const oval=(g,x,y,rx,ry,fill,stroke)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,Math.PI*2);g.fillStyle=fill;g.fill();if(stroke){g.strokeStyle=stroke;g.lineWidth=3;g.stroke();}};
  City.art.thunder_wall={box:[465,570,230,450],draw(g,o){
    prism(g,o.width,o.depth,111,'#7b8590','#40536d','#243548');
    const a=iso(-o.width/2,o.depth/2,70),b=iso(o.width/2,o.depth/2,70);
    line(g,[a,b],'#d3b677',5);
    for(let h of [25,56,86]){const p=iso(0,o.depth/2,h);oval(g,p[0],p[1],22,7,'#315578','#9fcce8');}
  }};
  City.art.thunder_pylon={box:[185,310,92,270],draw(g,o){
    prism(g,.82,.82,70,'#a49a80','#546478','#28394f');
    poly(g,[[-24,-105],[0,-160],[24,-105],[0,-91]],'#b4d8ec','#e4e5ca',4);
    oval(g,0,-115,11,17,'#f7e7bb');
  },animate(g,o,t){g.save();g.globalAlpha=.18+.15*Math.sin(t*4+o.x);oval(g,0,-115,35,48,'#80d8f7');g.restore();}};
  City.art.thunder_altar={box:[410,380,205,330],draw(g){
    prism(g,2.7,2.2,32,'#8d806a','#58697a','#223447');
    for(let r of [42,63,83]){g.beginPath();g.ellipse(0,-115,r,r*.65,0,0,Math.PI*2);g.strokeStyle='#bcd9e7';g.lineWidth=5;g.stroke();}
    oval(g,0,-115,19,28,'#dcebf0','#f5dc9a');
    for(let a=0;a<8;a++){const q=a*Math.PI/4;oval(g,Math.cos(q)*77,-115+Math.sin(q)*47,5,5,'#f3d595');}
  }};
  City.art.thunder_seal={box:[235,130,115,95],draw(g){
    oval(g,0,0,83,30,'#2a4159','#d5b87d');oval(g,0,0,61,20,'#286882','#a7daf1');
    line(g,[[-47,0],[-18,-8],[-3,6],[22,-9],[49,0]],'#fff0b9',3);
  }};
  const ground=(x,y,tone,alt)=>`hsl(${214+tone*8},${24+tone*9}%,${19+tone*8+alt*.7+((x+y)&1)*2}%)`;
  function detail(g,px,py,x,y,TW,TH){
    g.strokeStyle='rgba(158,204,232,.31)';g.lineWidth=1.4;g.beginPath();g.moveTo(px-TW/2,py+TH/2);g.lineTo(px,py);g.lineTo(px+TW/2,py+TH/2);g.stroke();
    if((x*13+y*31)%17===0)oval(g,px,py+TH/2,8,3,'rgba(223,233,245,.27)','rgba(246,211,133,.3)');
  }
  function weather(g,t,w,h){g.save();for(let i=0;i<30;i++){const x=(i*149+t*(7+i%5))%w,y=(i*119+t*(11+i%3))%h;oval(g,x,y,1.5,2,'rgba(157,221,249,.36)');}g.restore();}
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);poly(g,[[-75,0],[-66,-113],[-34,-174],[0,-190],[34,-174],[66,-113],[75,0]],'#555d6b','#e1c78e',7);
    const glow=g.createRadialGradient(0,-88,2,0,-88,80);glow.addColorStop(0,'#fff0bc');glow.addColorStop(.4,'#b1e7fa');glow.addColorStop(1,'#304e83');
    oval(g,0,-88,44+Math.sin(t*3)*3,70,glow,'#efd79f');
    for(let i=0;i<10;i++){const a=i*Math.PI/5+t*.22;oval(g,Math.cos(a)*32,-88+Math.sin(a)*51,4,6,i%2?'#ffffff':'#f3ce87');}
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#25384f';g.lineWidth=4;g.fillStyle='#f5e9c6';g.strokeText(p.name,0,-201);g.fillText(p.name,0,-201);g.restore();
  }
  window.ThunderArt={ground,detail,weather,portal};
})();
