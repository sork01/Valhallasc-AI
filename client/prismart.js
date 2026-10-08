'use strict';
// Shattered mirrors, salt plants and the canvas refuge of the Prismwaste.
(() => {
  const { poly, prism } = City.kit;
  const OL='#30243a', TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,fill,stroke=null)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=fill;g.fill();if(stroke){g.strokeStyle=stroke;g.lineWidth=3;g.stroke();}};
  const stroke=(g,points,col,w=3)=>{g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=col;g.lineWidth=w;g.lineJoin='round';g.stroke();};
  function shard(g,x,y,w,h,v=0){
    const palettes=[['#f8e4bb','#b19bc9','#6d6596'],['#d8f4ee','#8dbccf','#536e9f'],['#f5c6ca','#bd8ba9','#76537c'],['#ffe9ba','#e4ad83','#985e7c']];
    const p=palettes[v%4];
    poly(g,[[x-w,y],[x-w*.65,y-h*.7],[x+3,y-h],[x+w*.8,y-h*.53],[x+w,y]],p[1],OL,3);
    poly(g,[[x-w,y],[x-w*.65,y-h*.7],[x+3,y-h],[x,y]],p[0],null);
    poly(g,[[x+3,y-h],[x+w*.8,y-h*.53],[x+w,y],[x,y]],p[2],null);
    stroke(g,[[x+3,y-h],[x,y]],'rgba(255,255,235,.7)',2);
  }
  City.art.mirrorwall={box:[170,270,85,225],draw(g,o){
    oval(g,0,3,38,12,'rgba(30,18,35,.33)');
    shard(g,0,-4,27,93+(o.v%3)*12,o.v);
    for(const s of [-1,1])shard(g,s*24,-3,9,35,o.v+1);
  }};
  City.art.sunspire={box:[220,350,110,300],draw(g,o){
    oval(g,2,4,39,13,'rgba(38,19,39,.32)');
    shard(g,-10,-3,21,118+(o.v%4)*10,o.v+3);
    shard(g,21,-3,12,66,o.v);
  }};
  City.art.glassstone={box:[150,160,75,125],draw(g,o){
    oval(g,0,3,29,8,'rgba(38,19,39,.3)');
    poly(g,[[-27,-2],[-24,-27],[-6,-38],[15,-29],[28,-5],[13,2]],'#69586b',OL,3);
    poly(g,[[-24,-27],[-6,-38],[3,-17],[-16,-4]],'#c7bac4',null);
    shard(g,13,-11,8,26,o.v);
  }};
  City.art.saltbrush={box:[150,160,75,132],draw(g,o){
    oval(g,0,3,24,6,'rgba(38,19,39,.22)');
    for(let k=0;k<8;k++){
      const x=(k-3.5)*6,h=13+((k*11+o.v*7)%18);
      stroke(g,[[x,0],[x+((k%3)-1)*7,-h]],'#786d74',3);
      oval(g,x+((k%3)-1)*7,-h,3,2,k%2?'#fff2d0':'#edc8df');
    }
  }};
  City.art.lens_pillar={box:[200,320,100,275],draw(g,o){
    oval(g,0,4,31,9,'rgba(30,18,35,.36)');
    prism(g,.9,.9,82,'#f7d7b4','#a890a1','#5f667e');
    shard(g,0,-84,13,43,o.v);
  }};
  City.art.broken_crown={box:[370,380,185,330],draw(g){
    oval(g,0,8,75,23,'rgba(28,17,32,.45)');
    for(let k=0;k<7;k++){
      const a=k*TAU/7,x=Math.cos(a)*58,y=Math.sin(a)*20;
      shard(g,x,y,12,k%2?110:70,k);
    }
    oval(g,0,-8,28,9,'#5e466e','#e7c09d');
  }};
  City.art.shade_tent={box:[610,400,305,326],draw(g,o){
    const w=o.width,d=o.depth;
    oval(g,0,15,135,30,'rgba(26,16,32,.32)');
    prism(g,w,d,12,'#a89b9a','#796b77','#5d5268');
    for(const x of [-116,116])stroke(g,[[x,5],[x,-135]],'#4a3b4b',9);
    poly(g,[[-135,-134],[0,-204],[135,-134],[0,-72]],'#e8ba8a',OL,4);
    poly(g,[[0,-204],[135,-134],[0,-72]],'#a5798f',null);
    for(let k=-4;k<=4;k++)stroke(g,[[k*25,-132-Math.abs(k)*5],[k*25,-78-Math.abs(k)*2]],'#bd8e81',2);
    oval(g,0,-82,16,10,'#fff1cc','#e3b772');
  }};
})();
