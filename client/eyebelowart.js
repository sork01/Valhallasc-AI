'use strict';
// Deepglass masonry, watch lamps and the living lens. All shapes are drawn in
// world units by City; the animated aperture marks the actual Stormglass gate.
(() => {
  const {iso, poly, line, prism} = City.kit;
  const ellipse = (g,x,y,rx,ry,fill,stroke,width=2) => {
    g.beginPath(); g.ellipse(x,y,rx,ry,0,0,Math.PI*2);
    if (fill) { g.fillStyle=fill; g.fill(); }
    if (stroke) { g.strokeStyle=stroke; g.lineWidth=width; g.stroke(); }
  };
  City.art.eye_wall = {box:[440,520,220,410],draw(g,o) {
    const w=o.width,d=o.depth;
    prism(g,w,d,100,'#577583','#273d52','#162a3c');
    for(let h=19;h<100;h+=20) {
      const a=iso(-w/2,d/2,h),b=iso(w/2,d/2,h),c=iso(w/2,-d/2,h);
      line(g,[a,b,c],h===59?'#55a8b3':'#132c3b',2);
    }
    if(o.v===1 || o.v===3) {
      const p=iso(0,d/2,51);
      ellipse(g,p[0],p[1],13,19,'#1c394e','#a5e6dc',3);
      ellipse(g,p[0],p[1],5,16,'#b6e9dd');
    }
  }};
  City.art.eye_lamp={box:[160,250,80,210],draw(g,o) {
    prism(g,.6,.6,69,'#728b94','#365365','#233849');
    ellipse(g,0,-83,17,27,'#123b4a','#b4e2d5',3);
    ellipse(g,0,-83,8,18,o.v===1?'#f8d69d':'#7ae1d7');
  },animate(g,o,t) {
    g.save();g.shadowColor=o.v===1?'#f8d69d':'#7ae1d7';g.shadowBlur=12+5*Math.sin(t*2+o.x);
    ellipse(g,0,-83,6,15,o.v===1?'#ffe7ba':'#a6fff0');g.restore();
  }};
  City.art.eye_lens={box:[340,320,170,260],draw(g) {
    prism(g,2.1,1.4,25,'#637f8b','#344f61','#203849');
    ellipse(g,0,-91,63,39,'#1b4250','#93e8dd',5);
    ellipse(g,0,-91,31,37,'#a3dbcc');
    ellipse(g,0,-91,9,36,'#152939');
    for(let x of [-46,46]) ellipse(g,x,-91,5,8,'#f1cf91');
  }};
  City.art.eye_rune={box:[210,100,105,80],draw(g) {
    ellipse(g,0,0,80,27,'#20516a','#9ad9d8',3);
    ellipse(g,0,0,45,16,'#102b42','#f1d28e',2);
    ellipse(g,0,0,14,13,'#7be4d8');
  }};
  const ground=(x,y,tone,alt) => `hsl(${193+tone*9}, ${28+tone*5}%, ${18+tone*7+alt*.6+((x+y)&1)*2}%)`;
  function detail(g,px,py,x,y,TW,TH) {
    g.strokeStyle='rgba(115,214,215,.18)';g.lineWidth=1;
    g.beginPath();g.moveTo(px-TW/2,py+TH/2);g.lineTo(px,py);g.lineTo(px+TW/2,py+TH/2);g.stroke();
    if((x*11+y*7)%13===0) {
      ellipse(g,px,py+TH/2,16,5,'rgba(84,216,211,.18)','rgba(151,239,231,.35)',1);
      ellipse(g,px,py+TH/2,3,4,'#9be5df');
    }
  }
  function weather(g,t,w,h) {
    g.save();g.fillStyle='rgba(133,228,221,.22)';
    for(let i=0;i<30;i++) {
      const x=(i*173+Math.sin(t*.3+i)*19+w)%w,y=(i*89-t*(2+i%3)+h*20)%h;
      ellipse(g,x,y,1+(i%3),1+(i%3),'rgba(133,228,221,.24)');
    }
    g.restore();
  }
  function portal(g,p,sx,sy,t) {
    g.save();g.translate(sx,sy);
    poly(g,[[-51,0],[-50,-80],[-32,-132],[0,-150],[32,-132],[50,-80],[51,0]],'#213d52','#84b6bd',5);
    const glow=g.createRadialGradient(0,-69,3,0,-69,63);
    glow.addColorStop(0,'#e4f4dd');glow.addColorStop(.43,'#69b6bd');glow.addColorStop(1,'#10283d');
    ellipse(g,0,-68,39+Math.sin(t*2)*2,61,glow,'#c5dfce',3);
    ellipse(g,0,-68,11+Math.sin(t*1.5)*2,50,'#162b42');
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.lineWidth=4;
    g.strokeStyle='#081c2b';g.fillStyle='#bdebe3';g.strokeText(p.name,0,-162);g.fillText(p.name,0,-162);
    g.restore();
  }
  window.EyeBelowArt={ground,detail,weather,portal};
})();
