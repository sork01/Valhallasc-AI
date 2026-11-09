'use strict';
// The wild Veyrroot: tall teal-crowned trunks, ferns in the open glade, amber bloom and moss stones round the Great Tree.
(() => {
  const {poly}=City.kit,TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const line=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineCap='round';g.lineJoin='round';g.stroke();};
  const teal=(v)=>['#2f8d86','#3aa39a','#4bb8a8','#63c9b2'][((v%4)+4)%4];
  const shadow=(g,r)=>oval(g,0,5,r,r*.24,'rgba(8,44,40,.3)');
  const crown=(g,x,y,rx,ry,c)=>{oval(g,x,y,rx,ry,c);oval(g,x-rx*.25,y-ry*.28,rx*.5,ry*.26,'rgba(214,248,205,.24)');};
  City.art.vr_canopy_tree={box:[460,640,230,590],draw(g,o){
    shadow(g,100);
    for(const s of [-1,1])poly(g,[[0,-60],[s*16,-118],[s*44,-2],[s*24,0],[s*9,-38]],'#7a6644','#3a4a38',3);
    poly(g,[[-26,0],[-19,-230],[-33,-300],[-12,-330],[6,-262],[18,-336],[34,-300],[22,-214],[27,0]],'#8f7a52','#44543b',4);
    for(let j=-3;j<=3;j++){const x=j*42,y=-318-Math.cos(j*.4)*44;crown(g,x,y,78,58,teal(o.v+j));}
    crown(g,0,-398,96,62,'#35a698');
    for(let j=0;j<16;j++){const x=(j*61+o.v*29)%260-130,y=-318-(j*41)%92;oval(g,x,y,5,3,j%3?'#b7e8a0':'#f0d77a');}
    for(let j=-2;j<=2;j++)line(g,[[j*48,-360],[j*50+Math.sin(j)*8,-196]],'#4f8f6a',3);
  }};
  City.art.vr_fernbank={box:[190,150,95,125],draw(g,o){
    shadow(g,38);for(const side of [-1,1])for(let j=0;j<5;j++){
      const x=side*(20+j*14),y=-22-j*11;line(g,[[0,0],[x,y]],'#2f8660',3);
      for(let k=0;k<4;k++)oval(g,x*(k+1)/5,y*(k+1)/5,10,5,j%2?'#57b573':'#7cc86e');}
  }};
  City.art.vr_amber_bloom={box:[90,110,45,95],draw(g,o){
    line(g,[[0,0],[0,-52]],'#5f9a5c',3);
    for(let j=0;j<6;j++){const a=j/6*TAU;oval(g,Math.cos(a)*14,-60+Math.sin(a)*8,9,6,j%2?'#f0a93c':'#ffcf62');}
    oval(g,0,-60,7,5,'#fff0b0');
  }};
  City.art.vr_moss_stone={box:[190,130,95,105],draw(g,o){
    shadow(g,56);
    poly(g,[[-62,0],[-52,-52],[-18,-82],[22,-76],[58,-44],[66,0]],o.v%2?'#8a9484':'#76826f','#3a4a3c',4);
    poly(g,[[-52,-52],[-18,-82],[22,-76],[58,-44],[30,-50],[-8,-58]],'#9fb09a','#3a4a3c',2);
    for(let j=0;j<5;j++)oval(g,-40+j*20,-48-(j%2)*10,13,6,j%2?'#5fa66c':'#7cc27a');
  }};
})();
