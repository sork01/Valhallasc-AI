'use strict';
// Painted silk galleries and a mask stage inside the Thousandfold Pavilion.
(() => {
  const {iso, poly, line, prism} = City.kit;
  const oval=(g,x,y,rx,ry,fill,stroke) => {g.beginPath();g.ellipse(x,y,rx,ry,0,0,6.283);g.fillStyle=fill;g.fill();if(stroke){g.strokeStyle=stroke;g.lineWidth=3;g.stroke();}};
  City.art.pavilion_wall={box:[450,510,225,400],draw(g,o){
    const w=o.width,d=o.depth;prism(g,w,d,96,'#cc9fc2','#654a78','#342b58');
    for(let h=18;h<96;h+=20){const a=iso(-w/2,d/2,h),b=iso(w/2,d/2,h),c=iso(w/2,-d/2,h);line(g,[a,b,c],h===58?'#f9dc9b':'#60416b',3);}
    if(o.v%2){const p=iso(0,d/2,51);oval(g,p[0],p[1],19,28,'#2b264f','#f3c6d8');oval(g,p[0],p[1],6,17,'#fbe2ad');}
  }};
  City.art.pavilion_lantern={box:[180,260,90,215],draw(g,o){
    prism(g,.4,.4,56,'#e3bc91','#80647a','#443b62');
    poly(g,[[-25,-78],[0,-111],[25,-78],[0,-64]],o.v===1?'#e9abda':'#f1d795','#705575',3);
    oval(g,0,-80,10,16,'#fff2c7');
  },animate(g,o,t){g.save();g.shadowColor='#f6d6a5';g.shadowBlur=12+4*Math.sin(t*2+o.x);oval(g,0,-80,5,10,'#fff5d7');g.restore();}};
  City.art.pavilion_throne={box:[350,350,175,270],draw(g){
    prism(g,2.5,1.8,19,'#e1bd9e','#765d80','#473755');
    poly(g,[[-74,-33],[-61,-161],[0,-204],[61,-161],[74,-33]],'#563c68','#f5d39c',5);
    for(const x of [-45,-22,0,22,45])oval(g,x,-158+Math.abs(x)*.6,8,11,'#f3bad5');
    oval(g,0,-113,28,40,'#edd4b3','#f8e6c8');
  }};
  City.art.pavilion_seal={box:[220,110,110,85],draw(g){
    oval(g,0,0,79,28,'#503a68','#e9b3d2');oval(g,0,0,43,17,'#2d264f','#ffe1aa');
    for(let a=0;a<8;a++){const t=a*Math.PI/4;oval(g,Math.cos(t)*57,Math.sin(t)*19,5,5,'#f6d9aa');}
  }};
  const ground=(x,y,tone,alt)=>`hsl(${314+tone*11},${22+tone*7}%,${21+tone*8+alt*.7+((x+y)&1)*2}%)`;
  function detail(g,px,py,x,y,TW,TH){
    g.strokeStyle='rgba(246,202,224,.25)';g.lineWidth=1.4;
    g.beginPath();g.moveTo(px-TW/2,py+TH/2);g.quadraticCurveTo(px,py+TH/3,px+TW/2,py+TH/2);g.stroke();
    if((x*13+y*7)%19===0)oval(g,px,py+TH/2,4,2,'rgba(255,219,157,.7)');
  }
  function weather(g,t,w,h){for(let i=0;i<32;i++){const x=(i*167+t*(2+i%3))%w,y=(i*89+Math.sin(t+i)*18+h)%h;oval(g,x,y,2,1,'rgba(255,222,183,.28)');}}
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);
    poly(g,[[-57,0],[-49,-105],[-26,-144],[0,-161],[26,-144],[49,-105],[57,0]],'#674674','#f5cf9e',5);
    const glow=g.createRadialGradient(0,-70,3,0,-70,66);glow.addColorStop(0,'#ffe5c4');glow.addColorStop(.5,'#ba79a5');glow.addColorStop(1,'#342b58');
    oval(g,0,-73,38+Math.sin(t*2)*2,60,glow,'#ffe5b7');
    oval(g,0,-87,9,14,'#3c3158');
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#2b2345';g.lineWidth=4;g.fillStyle='#ffe1bb';g.strokeText(p.name,0,-170);g.fillText(p.name,0,-170);
    g.restore();
  }
  window.PavilionArt={ground,detail,weather,portal};
})();
