'use strict';
// Amber-veined roots, living lamps, and the awakening heart of the Seed Vault.
(() => {
  const {iso,poly,line,prism}=City.kit;
  const oval=(g,x,y,rx,ry,fill,stroke)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,6.283);g.fillStyle=fill;g.fill();if(stroke){g.strokeStyle=stroke;g.lineWidth=3;g.stroke();}};
  City.art.seed_wall={box:[450,540,225,430],draw(g,o){
    const w=o.width,d=o.depth;prism(g,w,d,105,'#887956','#506243','#293d32');
    for(let h=17;h<105;h+=23){const a=iso(-w/2,d/2,h),b=iso(w/2,d/2,h),c=iso(w/2,-d/2,h);line(g,[a,b,c],'#bdac77',3);}
    const p=iso(0,d/2,52);oval(g,p[0],p[1],16,23,'#52794f','#dfc987');oval(g,p[0],p[1],5,14,'#e5e2a2');
  }};
  City.art.seed_lamp={box:[190,270,95,230],draw(g,o){
    prism(g,.65,.65,58,'#967d55','#526448','#344737');
    for(let s of [-1,1])poly(g,[[0,-66],[s*26,-80],[s*13,-104]],'#5b8755','#d8c185',2);
    oval(g,0,-91,14,20,o.v===1?'#e8c482':'#b9d98b','#f5e5a5');
  },animate(g,o,t){g.save();g.shadowColor='#e4e2a2';g.shadowBlur=15+5*Math.sin(t*2+o.x);oval(g,0,-91,6,13,'#f8ebba');g.restore();}};
  City.art.seed_altar={box:[390,360,195,295],draw(g){
    prism(g,2.4,2,27,'#9c8c62','#63744d','#354b3b');
    for(let s of [-1,1]){poly(g,[[s*11,-81],[s*36,-178],[s*43,-147],[s*25,-84]],'#6e965f','#e5d29c',4);}
    oval(g,0,-112,39,55,'#8d784a','#f4daa0');oval(g,0,-123,18,33,'#dbe49b');
  }};
  City.art.seed_glyph={box:[230,120,115,90],draw(g){
    oval(g,0,0,82,28,'#394e35','#cbb77f');oval(g,0,0,51,17,'#243c32','#e5d29c');
    for(let a=0;a<8;a++){const t=a*Math.PI/4;oval(g,Math.cos(t)*62,Math.sin(t)*20,4,5,'#dce7a6');}
  }};
  const ground=(x,y,tone,alt)=>`hsl(${80+tone*8},${20+tone*6}%,${19+tone*7+alt*.7+((x+y)&1)*2}%)`;
  function detail(g,px,py,x,y,TW,TH){
    g.strokeStyle='rgba(201,184,112,.23)';g.lineWidth=1.4;g.beginPath();g.moveTo(px-TW/2,py+TH/2);g.lineTo(px,py);g.lineTo(px+TW/2,py+TH/2);g.stroke();
    if((x*13+y*19)%17===0)oval(g,px,py+TH/2,10,3,'rgba(193,220,137,.35)','rgba(231,218,154,.4)');
  }
  function weather(g,t,w,h){g.save();for(let i=0;i<29;i++){const x=(i*157+t*(4+i%3))%w,y=(i*109+t*(10+i%4))%h;oval(g,x,y,1.5,2.5,'rgba(225,235,163,.3)');}g.restore();}
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);poly(g,[[-56,0],[-47,-103],[-23,-151],[0,-173],[23,-151],[47,-103],[56,0]],'#465b3d','#dec88d',5);
    const glow=g.createRadialGradient(0,-75,2,0,-75,71);glow.addColorStop(0,'#fff3b5');glow.addColorStop(.5,'#bfd08d');glow.addColorStop(1,'#3b5942');
    oval(g,0,-75,39+Math.sin(t*2)*2,64,glow,'#f2dfa2');oval(g,0,-75,7,48,'#436449');
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#213a31';g.lineWidth=4;g.fillStyle='#f4e7b5';g.strokeText(p.name,0,-181);g.fillText(p.name,0,-181);g.restore();
  }
  window.SeedVaultArt={ground,detail,weather,portal};
})();
