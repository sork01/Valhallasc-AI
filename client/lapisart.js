'use strict';
// The Lapis Erg: ochre dunes, blue water, date palms, silk caravans and a buried astrolabe.
(() => {
  const {poly}=City.kit,TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const line=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineCap='round';g.lineJoin='round';g.stroke();};
  const shadow=(g,r)=>oval(g,0,5,r,r*.27,'rgba(68,45,37,.25)');
  City.art.lapis_astrolabe={box:[1050,1060,525,970],draw(g,o){
    shadow(g,270);
    // Half of the bronze star machine remains beneath the dune; its iris opens over the stair.
    poly(g,[[-359,0],[-302,-333],[-185,-681],[0,-834],[185,-681],[302,-333],[359,0]],'#c99c69','#72544b',11);
    oval(g,0,-338,264,307,'#705855');oval(g,0,-338,235,282,'#e4bd81');oval(g,0,-338,204,249,'#326a75');
    for(let i=0;i<12;i++){const a=i*TAU/12;const x=Math.cos(a)*222,y=-338+Math.sin(a)*266;
      oval(g,x,y,12,12,i%2?'#f9dfa3':'#87cbd0');line(g,[[x,y],[x*.72,-338+(y+338)*.72]],'#d6ae75',4);}
    oval(g,0,-338,158,195,'#d7bd89');oval(g,0,-338,139,174,'#234e5d');
    for(let i=0;i<8;i++){const a=i*TAU/8;g.save();g.translate(0,-338);g.rotate(a);
      poly(g,[[-22,-153],[22,-153],[61,-27],[0,55],[-61,-27]],i%2?'#bd9469':'#e1bd84','#624e4a',5);g.restore();}
    if(o.open){
      oval(g,0,-338,103,139,'#162f3b');oval(g,0,-338,82,116,'#071c2c');
      for(let i=0;i<7;i++)line(g,[[-71+i*7,-260+i*18],[71-i*7,-260+i*18]],i%2?'#bba277':'#e0c78f',5);
      oval(g,0,-391,22,27,'#87d9da');
    }else{oval(g,0,-338,50,67,'#f8dda1');oval(g,0,-338,27,39,'#79d5d3');}
    for(let side of [-1,1]){poly(g,[[side*310,0],[side*265,-475],[side*220,-677],[side*178,-734],[side*221,-412],[side*245,0]],'#bc8a60','#6b554e',7);
      for(let j=0;j<4;j++)oval(g,side*(253+j*19),-116-j*110,6,10,'#b8e6d4');}
    poly(g,[[-185,-3],[0,62],[185,-3],[0,-66]],'#a47857','#684d43',7);
    for(let j=0;j<9;j++)line(g,[[-110+j*27,24],[-98+j*25,-62]],'#ead3a5',3);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.12+.07*Math.sin(t*1.3);oval(g,sx,sy-334,62,75,'#fff3c2');g.restore();}};
  City.art.lapis_oasis={box:[880,570,440,470],ground:true,draw(g,o){
    shadow(g,270);
    // A long blue pool with lush banks, floating lilies and patterned stone lip.
    oval(g,0,-19,302,151,'#946c4f');oval(g,0,-22,287,143,'#cfaa72');
    // Same isometric circle as the 4.3-tile authoritative water disc.
    oval(g,0,-26,4.3*Math.SQRT2*44,4.3*Math.SQRT2*22,'#399da8');oval(g,0,-29,235,108,o.v===1?'#74c9c4':'#62bfc2');
    for(let j=0;j<14;j++){const x=((j*107+o.v*31)%490)-245,y=-27+Math.sin(j*4)*74;
      oval(g,x,y,14,6,j%3?'#5da977':'#a3ce87');oval(g,x+4,y-4,4,3,j%3?'#f6d79a':'#f1a9b3');}
    for(let i=0;i<8;i++){const a=i*TAU/8;oval(g,Math.cos(a)*280,-20+Math.sin(a)*127,13,6,i%2?'#e8ca8d':'#f5dfae');}
    for(let i=0;i<6;i++)line(g,[[-200+i*66,-48],[-173+i*66,-52]],'rgba(238,250,227,.6)',3);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.21+.12*Math.sin(t*1.7);oval(g,sx+Math.sin(t)*60,sy-17,190,75,'#d7f9e4');g.restore();}};
  City.art.lapis_date_palm={box:[400,560,200,505],occludes:true,draw(g,o){
    shadow(g,96);line(g,[[-5,0],[o.v%2?18:-10,-332]],'#9b7150',18);
    for(let j=0;j<8;j++){const y=-20-j*39;line(g,[[-2+j%2*5,y],[10+j%2*5,y-17]],'#bd8d5e',3);}
    const cx=o.v%2?18:-10,cy=-335;
    for(let i=0;i<9;i++){const a=i*TAU/9,dx=Math.cos(a)*147,dy=Math.sin(a)*67-14;
      line(g,[[cx,cy],[cx+dx*.56,cy+dy-17],[cx+dx,cy+dy+28]],i%2?'#518f63':'#68aa6d',13);
      line(g,[[cx,cy],[cx+dx*.6,cy+dy-19],[cx+dx,cy+dy+22]],'#a5c97b',4);}
    for(let j=0;j<5;j++)oval(g,cx-20+j*10,cy+24+j%2*8,7,10,'#d89954');
  }};
  City.art.lapis_caravan_tent={box:[590,530,295,465],draw(g,o){
    shadow(g,182);poly(g,[[-193,0],[0,71],[193,0],[0,-71]],'#bf915f','#795848',6);
    for(let x of [-143,143])line(g,[[x,0],[x,-192]],'#8d654c',8);
    poly(g,[[-207,-190],[0,-304],[207,-190],[0,-113]],o.v%3===0?'#55a5aa':o.v%3===1?'#e0ad70':'#e8c0a0','#694e50',7);
    for(let j=-4;j<=4;j++)line(g,[[j*39,-171],[j*43,-213]],j%2?'#fbdfa5':'#447e8e',5);
    line(g,[[0,-301],[0,-360]],'#6b574d',5);poly(g,[[0,-360],[48,-346],[0,-328]],'#f3d17e','#6e4f4c',4);
    for(let j=-2;j<=2;j++)oval(g,j*54,-21,15,8,j%2?'#f5dba4':'#71b8a6');
  }};
  City.art.lapis_well={box:[320,360,160,315],draw(g){
    shadow(g,97);oval(g,0,-11,96,45,'#b38b60');oval(g,0,-21,75,35,'#e6c691');oval(g,0,-27,61,27,'#3e98a4');
    for(let side of [-1,1])line(g,[[side*65,-19],[side*65,-196]],'#906b4d',9);
    poly(g,[[-104,-196],[0,-262],[104,-196],[0,-164]],'#61a9a1','#edd0a0',5);
    line(g,[[0,-205],[0,-93]],'#b58b5b',4);oval(g,0,-87,17,11,'#e0b76f');
  }};
  City.art.lapis_mirror={box:[380,370,190,325],draw(g){
    shadow(g,105);oval(g,0,-23,114,68,'#cba475');oval(g,0,-31,94,53,'#a9d9d4');oval(g,0,-35,70,38,'#4f9daa');
    for(let i=0;i<8;i++){const a=i*TAU/8;oval(g,Math.cos(a)*105,-28+Math.sin(a)*57,8,7,'#f2d99f');}
    line(g,[[-25,-45],[30,-70]],'rgba(255,250,225,.65)',4);
  }};
  City.art.lapis_roc_nest={box:[410,330,205,275],draw(g){
    shadow(g,120);for(let i=0;i<9;i++){const y=-13-i*7;oval(g,0,y,125-i*5,36-i*2,i%2?'#a77750':'#ddaf70');}
    for(let x of [-50,0,50])oval(g,x,-78,22,32,'#e3c389');
  }};
  City.art.lapis_salt_arch={box:[430,550,215,500],draw(g){
    shadow(g,132);for(let side of [-1,1])poly(g,[[side*117,0],[side*110,-318],[side*51,-430],[side*81,-277],[side*72,0]],'#d7d4c5','#568e9a',7);
    poly(g,[[-133,-323],[0,-475],[133,-323],[82,-329],[0,-397],[-82,-329]],'#dce5d9','#5c9ba4',6);
    oval(g,0,-408,22,15,'#8bd5d2');
  }};
  City.art.lapis_sandstone={box:[230,190,115,145],draw(g,o){shadow(g,65);poly(g,[[-69,0],[-45,-92],[14,-130],[72,-64],[63,0]],o.v%2?'#c89366':'#dbad77','#966d57',5);}};
  City.art.lapis_salt_spire={box:[205,295,102,255],draw(g,o){shadow(g,56);poly(g,[[-41,0],[-30,-150],[6,-233],[43,-90],[28,0]],o.v%2?'#b5d4cf':'#d8e1d7','#558b96',5);line(g,[[-26,-28],[13,-146]],'#79c3c5',4);}};
  City.art.lapis_dunegrass={box:[145,105,72,78],draw(g,o){for(let j=-2;j<=2;j++)line(g,[[j*9,0],[j*12+o.v*3,-33-j%2*12]],j%2?'#baaa63':'#8c9d64',3);}};
  City.art.lapis_silk_flag={box:[170,230,85,205],draw(g,o){line(g,[[0,0],[0,-153]],'#947257',4);poly(g,[[0,-149],[69,-132],[0,-110]],o.v%2?'#64b5b0':'#db9b73','#6f5f58',3);}};
  City.art.lapis_blue_flower={box:[100,90,50,67],draw(g,o){line(g,[[0,0],[0,-32]],'#608b69',2);for(let i=0;i<5;i++){const a=i*TAU/5;oval(g,Math.cos(a)*9,-37+Math.sin(a)*8,7,5,o.v%2?'#7ac5c4':'#b1d8ba');}oval(g,0,-37,4,4,'#f4d495');}};
})();
