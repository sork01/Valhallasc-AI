'use strict';
// Root chambers, pollen lights, and a living doorway beneath the eldest oak.
(() => {
  const {iso, poly, line, prism} = City.kit;
  const ellipse = (g,x,y,rx,ry,fill,stroke,width=2) => {
    g.beginPath(); g.ellipse(x,y,rx,ry,0,0,Math.PI*2);
    if (fill) { g.fillStyle=fill; g.fill(); }
    if (stroke) { g.strokeStyle=stroke; g.lineWidth=width; g.stroke(); }
  };
  City.art.elder_wall={box:[440,520,220,410],draw(g,o) {
    const w=o.width,d=o.depth;
    prism(g,w,d,104,'#715b42','#463b31','#302c29');
    for(let h=14;h<104;h+=22){
      const a=iso(-w/2,d/2,h),b=iso(w/2,d/2,h),c=iso(w/2,-d/2,h);
      line(g,[a,b,c],h===58?'#93ae72':'#2e372a',3);
    }
    if(o.v%3===1){
      const p=iso(0,d/2,48); ellipse(g,p[0],p[1],15,21,'#304c38','#b1c88a',3);
      ellipse(g,p[0],p[1],5,15,'#dcebb1');
    }
  }};
  City.art.elder_lantern={box:[160,250,80,210],draw(g,o) {
    prism(g,.55,.55,58,'#755b42','#493b31','#302b24');
    for(let a=0;a<5;a++){
      const q=a*Math.PI*2/5; ellipse(g,Math.cos(q)*13,-91+Math.sin(q)*7,11,8,'#7ca36d','#d7dda1',2);
    }
    ellipse(g,0,-91,10,18,o.v===2?'#fff0bc':'#cce4a6');
  },animate(g,o,t){
    g.save();g.shadowColor='#d9f3a3';g.shadowBlur=13+5*Math.sin(t*2+o.x);
    ellipse(g,0,-91,6,12,'#edfac3');g.restore();
  }};
  City.art.elder_crown={box:[340,320,170,260],draw(g){
    prism(g,1.5,1.5,18,'#80674a','#4b4032','#2f322a');
    for(let a=0;a<7;a++){
      const q=a*Math.PI*2/7; const x=Math.cos(q)*42,y=-80+Math.sin(q)*21;
      ellipse(g,x,y,18,28,'#54744c','#a3c67f',3);
    }
    ellipse(g,0,-84,22,32,'#c0dc91','#eaf5b7',4);
    ellipse(g,0,-84,8,20,'#506b45');
  }};
  City.art.elder_seed={box:[210,100,105,80],draw(g){
    ellipse(g,0,0,75,27,'#46563d','#a7c27d',4);
    ellipse(g,0,0,43,17,'#253a2d','#d7e4a5',2);
    ellipse(g,0,0,16,11,'#d2e5a3');
  }};
  const ground=(x,y,tone,alt)=>`hsl(${87+tone*12}, ${21+tone*5}%, ${20+tone*8+alt*.6+((x+y)&1)*2}%)`;
  function detail(g,px,py,x,y,TW,TH){
    g.strokeStyle='rgba(197,224,151,.19)';g.lineWidth=1.5;
    g.beginPath();g.moveTo(px-TW/2,py+TH/2);g.quadraticCurveTo(px,py+TH/4,px+TW/2,py+TH/2);g.stroke();
    if((x*13+y*7)%17===0){
      ellipse(g,px,py+TH/2,14,5,'rgba(147,199,115,.16)','rgba(210,236,165,.3)',1);
      ellipse(g,px,py+TH/2,3,3,'#d9e9ae');
    }
  }
  function weather(g,t,w,h){
    g.save();
    for(let i=0;i<35;i++){
      const x=(i*149+Math.sin(t*.35+i)*21+w)%w,y=(i*97-t*(3+i%3)+h*20)%h;
      ellipse(g,x,y,1+i%2,1+i%2,'rgba(221,239,165,.27)');
    }
    g.restore();
  }
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);
    for(const s of [-1,1]){
      poly(g,[[s*48,0],[s*42,-74],[s*31,-123],[s*8,-153],[s*3,-140],[s*20,-88],[s*27,0]],'#584435','#a0b37c',4);
    }
    const glow=g.createRadialGradient(0,-68,3,0,-68,64);
    glow.addColorStop(0,'#eef7bc');glow.addColorStop(.47,'#85af72');glow.addColorStop(1,'#213d32');
    ellipse(g,0,-68,36+Math.sin(t*2)*2,60,glow,'#c6d99a',3);
    ellipse(g,0,-68,8+Math.sin(t*1.3)*2,43,'#2a493b');
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.lineWidth=4;
    g.strokeStyle='#1c2d25';g.fillStyle='#e3edb9';g.strokeText(p.name,0,-165);g.fillText(p.name,0,-165);
    g.restore();
  }
  window.ElderHollowArt={ground,detail,weather,portal};
})();
