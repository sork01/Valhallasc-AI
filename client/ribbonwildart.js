'use strict';
// The Ribbonwild's silk architecture, painted gardens and colossal sealed big top.
(() => {
  const {poly}=City.kit,TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const line=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineJoin='round';g.lineCap='round';g.stroke();};
  const COLORS=['#ef6998','#f4c65e','#58c5d0','#aa7dda'];
  const shade=(i)=>COLORS[(i+4)%4];
  const shadow=(g,r)=>oval(g,0,6,r,r*.23,'rgba(40,31,57,.23)');
  const stripe=(g,x,y,w,h,i)=>poly(g,[[x,y],[x+w,y],[x+w*.75,y+h],[x+w*.22,y+h]],shade(i),'#6f496f',2);

  City.art.fan_topiary={box:[300,310,150,275],draw(g,o){
    shadow(g,55);poly(g,[[-9,0],[-10,-109],[10,-109],[9,0]],'#9b6c5c','#694a51');
    for(let j=-3;j<=3;j++){
      const a=j*.34,x=Math.sin(a)*81,y=-134-Math.cos(a)*32;
      oval(g,x,y,38,49,shade(o.v+j));oval(g,x-8,y-13,17,13,'rgba(255,248,215,.28)');
    }
    oval(g,0,-158,25,29,'#f9db7e');oval(g,-5,-166,8,7,'#fff2cb');
  }};
  City.art.ribbon_pole={box:[170,330,85,290],draw(g,o){
    shadow(g,25);line(g,[[0,0],[0,-210]],'#f3d49b',9);
    oval(g,0,-219,13,13,'#f9df86');
    for(let j=0;j<3;j++){
      const y=-185+j*56,s=j%2?1:-1;
      poly(g,[[0,y],[s*65,y-17],[s*46,y+9],[s*74,y+22],[0,y+13]],shade(o.v+j),'#fbeac0',2);
    }
  },animate(g,o,sx,sy,t){
    g.save();g.globalAlpha=.42;g.strokeStyle=shade(o.v);g.lineWidth=2;
    g.beginPath();g.moveTo(sx,sy-144);g.quadraticCurveTo(sx+20+Math.sin(t*2+o.x)*12,sy-150,sx+48,sy-136);g.stroke();g.restore();
  }};
  City.art.pinwheel={box:[135,180,67,150],draw(g,o){
    shadow(g,20);line(g,[[0,0],[0,-105]],'#f4d696',6);
    for(let j=0;j<4;j++){const a=j*TAU/4;
      const x=Math.cos(a)*35,y=-111+Math.sin(a)*35;
      poly(g,[[0,-111],[x,y],[x-Math.sin(a)*20,y+Math.cos(a)*20]],shade(o.v+j),'#fff0ce',2);
    }
    oval(g,0,-111,8,8,'#fff3c8');
  }};
  City.art.festival_bloom={box:[120,100,60,75],draw(g,o){
    for(let j=0;j<7;j++){const x=(j*31+o.v*9)%76-38,y=(j*17+o.v*11)%27;
      line(g,[[x,y],[x+2,y-16-j%3*4]],'#4f9c6d',2);
      for(let k=0;k<5;k++){const a=k*TAU/5;oval(g,x+2+Math.cos(a)*5,y-18-j%3*4+Math.sin(a)*4,3,2,shade(o.v+j));}
      oval(g,x+2,y-18-j%3*4,2,2,'#ffeb9e');
    }
  }};
  City.art.confetti_lantern={box:[150,250,75,220],draw(g,o){
    shadow(g,24);line(g,[[0,0],[0,-160]],'#98716c',6);line(g,[[-38,-145],[38,-145]],'#98716c',5);
    for(const s of [-1,1]){
      oval(g,s*34,-134,16,22,shade(o.v+(s+1)/2));
      oval(g,s*34,-134,9,14,'rgba(255,248,212,.56)');
      line(g,[[s*34,-112],[s*34,-100]],'#f7e4a2',2);
    }
  }};
  City.art.silk_pavilion={box:[510,450,255,400],draw(g,o){
    shadow(g,128);poly(g,[[-107,0],[-107,-143],[108,-143],[108,0]],'#f7dfaf','#7f596c',3);
    poly(g,[[-146,-141],[-72,-202],[0,-276],[72,-202],[145,-141],[101,-149],[0,-255],[-101,-149]],'#f7d36f','#754d67',4);
    for(let j=-3;j<=2;j++)stripe(g,j*39,-147,43,139,o.v+j);
    poly(g,[[-28,0],[-28,-109],[27,-109],[27,0]],'#665078','#e5c9a4',4);
    for(const x of [-106,107])line(g,[[x,0],[x,-150]],'#ecd297',8);
    oval(g,0,-276,15,15,'#fff0ac');
    for(let j=-3;j<=3;j++)oval(g,j*35,-135,5,6,'#ffefb0');
  }};
  City.art.painted_stall={box:[330,280,165,250],draw(g,o){
    shadow(g,92);poly(g,[[-80,0],[-80,-92],[80,-92],[80,0]],'#f2dfb5','#78546b',3);
    poly(g,[[-104,-93],[-82,-143],[83,-143],[104,-93]],shade(o.v),'#694c6e',3);
    for(let j=-2;j<=2;j++)stripe(g,j*37,-143,35,50,o.v+j);
    line(g,[[-78,-44],[78,-44]],'#9a6a74',10);
    for(let j=-2;j<=2;j++)oval(g,j*27,-50,11,6,['#ffe189','#9ad9e0','#f2a0bc'][((j+2)+o.v)%3]);
  }};
  City.art.parade_standard={box:[240,390,120,350],draw(g){
    shadow(g,41);line(g,[[0,0],[0,-273]],'#f1d69d',12);
    poly(g,[[-87,-219],[-8,-259],[72,-219],[47,-162],[-6,-183],[-53,-162]],'#ec77a5','#653f74',4);
    for(let j=-2;j<=2;j++)line(g,[[j*22,-219],[j*16,-176]],['#ffe589','#68cbd2','#b89aeb'][((j+2)%3)],6);
    oval(g,0,-281,18,18,'#fff2a8');
  }};
  City.art.mask_dais={box:[340,230,170,195],draw(g){
    shadow(g,98);poly(g,[[-116,0],[-83,-39],[87,-39],[118,0]],'#ddbc89','#795f77',4);
    poly(g,[[-71,-39],[-62,-89],[62,-89],[72,-39]],'#a685b9','#5d5478',3);
    oval(g,0,-106,34,41,'#f6d88e');
    oval(g,-14,-109,8,11,'#5d4770');oval(g,14,-109,8,11,'#5d4770');
    line(g,[[-15,-85],[0,-77],[15,-85]],'#8c4c77',4);
    for(let j=-2;j<=2;j++)line(g,[[j*13,-139],[j*18,-164]],shade(j),5);
  }};
  City.art.mosaic_disc={box:[530,240,265,195],draw(g){
    oval(g,0,0,190,91,'rgba(81,74,128,.20)');
    for(let j=0;j<12;j++){const a=j*TAU/12;
      oval(g,Math.cos(a)*150,Math.sin(a)*66,21,10,shade(j));}
    oval(g,0,0,31,15,'#fff0b9');
  }};
  City.art.grand_pavilion_gate={box:[980,760,490,704],draw(g){
    shadow(g,292);
    // Three immense peaks are tied to one stage. The mask door is visibly sealed.
    poly(g,[[-268,4],[-258,-247],[260,-247],[271,4]],'#f5dba8','#5b4668',6);
    poly(g,[[-310,-247],[-177,-330],[0,-544],[180,-330],[310,-247],[225,-262],[0,-506],[-225,-262]],'#f7c96c','#70466b',7);
    for(let j=-5;j<=4;j++)stripe(g,j*55,-246,58,247,j);
    for(const s of [-1,1]){
      poly(g,[[s*140,-274],[s*183,-358],[s*211,-273]],shade(s+1),'#70466b',3);
      line(g,[[s*241,2],[s*241,-261]],'#fce1a1',14);
      oval(g,s*241,-275,24,24,'#ffe5a3');
      line(g,[[s*207,-229],[s*281,-181]],'#fbe7ad',4);
      for(let j=0;j<4;j++)oval(g,s*(248+j*9),-201+j*11,6,8,shade(j));
    }
    poly(g,[[-87,4],[-87,-204],[-54,-256],[0,-279],[55,-256],[88,-204],[88,4]],'#4a315e','#fbe7ac',7);
    oval(g,0,-162,65,83,'#ffe9ab');
    oval(g,-25,-182,17,25,'#503957');oval(g,25,-182,17,25,'#503957');
    poly(g,[[-14,-135],[0,-124],[14,-135]],'#dc799b','#8b5b82',3);
    line(g,[[-46,-84],[46,-84]],'#87537c',12);
    line(g,[[0,-68],[0,2]],'#9e7293',7);
    for(let j=-5;j<=5;j++){
      const x=j*38;
      line(g,[[x,-260],[x+Math.sin(j)*12,-297]],'#e6bb73',3);
      oval(g,x+Math.sin(j)*12,-300,6,6,shade(j));
    }
    line(g,[[0,-542],[0,-610]],'#f4d891',8);
    poly(g,[[0,-611],[107,-583],[0,-558]],'#f77ca3','#ffe5ab',4);
    oval(g,0,-547,20,20,'#fff1b5');
  },animate(g,o,sx,sy,t){
    g.save();g.globalAlpha=.22+.13*Math.sin(t*1.2);g.fillStyle='#fff2be';
    for(let i=0;i<26;i++){
      const x=sx+Math.sin(i*9.7+t*.8)*265,y=sy-165-((i*79+t*(21+i%4*3))%410);
      oval(g,x,y,2.5,4,'#fff0bd');
    }
    g.restore();
  }};
})();
