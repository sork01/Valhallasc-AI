'use strict';
// Millbridge's real trees and fields; only the old oak at the far end is uncanny.
(() => {
  const {poly}=City.kit, TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const stroke=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineCap='round';g.lineJoin='round';g.stroke();};
  const leaf=(g,x,y,rx,ry,shade)=>{
    oval(g,x+2,y+7,rx+5,ry+5,'#315b2c');oval(g,x,y,rx,ry,shade);
    oval(g,x-rx*.28,y-ry*.3,rx*.55,ry*.42,'rgba(217,238,133,.23)');
  };
  const seed=(i,v)=>((i*127.1+v*37.7)*.61803398875)%1;
  const shadow=g=>oval(g,0,4,62,15,'rgba(25,49,19,.25)');

  City.art.oak_tree={box:[390,410,195,365],occludes:true,draw(g,o){
    shadow(g);poly(g,[[-20,0],[-15,-119],[-34,-176],[-22,-183],[-4,-137],[4,-195],[17,-188],[13,-121],[28,0]],'#805236','#433f2b');
    stroke(g,[[-4,-14],[2,-124],[6,-166]],'#b17b49',5);
    for(const [x,y,rx,ry,c] of [[-71,-184,75,62,'#497c3a'],[59,-188,77,65,'#4f863c'],[-17,-231,91,76,'#598f3e'],[7,-190,111,64,'#619c45']])leaf(g,x,y,rx,ry,c);
    for(let i=0;i<27;i++){const x=(seed(i+1,o.v)-.5)*182,y=-160-seed(i+31,o.v)*104;oval(g,x,y,3.4,2.3,i%3?'#9fbd59':'#c8d77b');}
  }};
  City.art.birch_tree={box:[270,390,135,350],occludes:true,draw(g,o){
    oval(g,0,3,33,10,'rgba(22,48,19,.2)');
    poly(g,[[-8,0],[-11,-145],[-16,-200],[-3,-227],[11,-200],[8,-139],[11,0]],'#efead4','#474b3e');
    for(const [x,y] of [[-8,-40],[8,-66],[-10,-107],[10,-140],[-9,-181]])stroke(g,[[x,y],[x+(x<0?13:-12),y-5]],'#65705c',3);
    stroke(g,[[-2,-165],[-45,-223]],'#827a5d',5);stroke(g,[[4,-182],[42,-245]],'#827a5d',4);
    leaf(g,-38,-236,48,57,'#8ab550');leaf(g,40,-232,47,56,'#7eae4d');leaf(g,0,-266,54,54,'#a2c667');
    for(let i=0;i<13;i++){const x=(seed(i,o.v)-.5)*90,y=-222-seed(i+19,o.v)*73;oval(g,x,y,3,2,'#cbd783');}
  }};
  City.art.apple_tree={box:[330,330,165,285],occludes:true,draw(g,o){
    oval(g,0,3,39,11,'rgba(28,47,18,.24)');
    poly(g,[[-13,0],[-11,-92],[-37,-130],[-26,-136],[-1,-107],[14,-146],[28,-139],[13,-86],[14,0]],'#885336','#59452e');
    leaf(g,-44,-147,54,45,'#568936');leaf(g,43,-145,52,45,'#61943c');leaf(g,0,-183,65,53,'#69a144');
    for(let i=0;i<16;i++){const x=(seed(i+2,o.v)-.5)*122,y=-122-seed(i*5+18,o.v)*94;oval(g,x,y,5,5,i%4?'#c93f32':'#e1bd48');oval(g,x-2,y-2,2,2,'#f6bf84');}
  }};
  City.art.willow_tree={box:[390,400,195,365],occludes:true,draw(g,o){
    shadow(g);poly(g,[[-17,0],[-14,-127],[-48,-178],[-30,-182],[0,-148],[29,-198],[43,-190],[13,-111],[18,0]],'#896546','#4b593b');
    leaf(g,-55,-192,60,47,'#749b43');leaf(g,53,-196,63,46,'#759d49');leaf(g,0,-236,82,58,'#86aa52');
    for(let i=-6;i<=6;i++){const x=i*19,top=-197-Math.cos(i*.36)*31;stroke(g,[[x,top],[x+(i%2?5:-5),-110-(i%3)*13]],i%2?'#6b9647':'#8ab057',4);}
  }};
  City.art.hawthorn_bush={box:[150,120,75,95],draw(g,o){
    oval(g,0,3,29,7,'rgba(25,44,15,.18)');
    for(const [x,y,rx,ry] of [[-23,-26,27,23],[17,-28,27,24],[0,-44,28,27]])leaf(g,x,y,rx,ry,o.v%2?'#54833a':'#678d40');
    for(let i=0;i<6;i++)oval(g,(seed(i,o.v)-.5)*47,-22-seed(i+11,o.v)*38,2.4,2.4,'#dfc989');
  }};
  City.art.wildflowers={box:[120,100,60,80],draw(g,o){
    for(let i=0;i<10;i++){const x=(seed(i,o.v)-.5)*66,y=seed(i+13,o.v)*18;
      stroke(g,[[x,y],[x+2,y-15-seed(i+23,o.v)*11]],'#528f35',2);
      const c=['#fff4cd','#edb2d3','#a3c7e8','#f3db73'][i%4];
      oval(g,x+2,y-17-seed(i+23,o.v)*11,4,3,c);
    }
  }};
  City.art.haystack={box:[150,110,75,90],draw(g,o){
    oval(g,0,5,46,10,'rgba(50,39,15,.18)');
    poly(g,[[-45,0],[-38,-35],[-15,-58],[18,-54],[43,-28],[47,0]],'#d8aa57','#8d703d');
    for(let i=-3;i<=3;i++)stroke(g,[[i*10,-8],[i*10+8,-36+Math.abs(i)*3]],i%2?'#eaca70':'#af8542',2);
  }};
  City.art.vale_cottage={box:[450,380,225,335],draw(g,o){
    oval(g,0,9,111,24,'rgba(32,43,22,.26)');
    poly(g,[[-94,0],[-94,-93],[92,-93],[92,0]],'#eadab4','#765c48');
    poly(g,[[-112,-93],[0,-168],[111,-93],[91,-101],[0,-147],[-92,-101]],o.v%3===1?'#9b543d':'#a96a48','#583f38');
    poly(g,[[-18,0],[-18,-65],[20,-65],[20,0]],'#5b493a','#e4b179');
    for(const x of [-65,63]){poly(g,[[x-19,-77],[x+19,-77],[x+19,-35],[x-19,-35]],'#b4d8ce','#845e43');stroke(g,[[x,-77],[x,-35]],'#f4e0b4',3);}
    poly(g,[[60,-122],[60,-173],[81,-173],[81,-110]],'#d5bd94','#674c3c');
    for(let i=0;i<6;i++)oval(g,-85+i*34,4,9,5,i%2?'#e6b0bc':'#f2d269');
  }};
  City.art.watermill={box:[570,480,285,430],draw(g){
    oval(g,0,13,133,26,'rgba(28,43,21,.24)');
    poly(g,[[-119,0],[-119,-142],[91,-142],[91,0]],'#e3d4ac','#6e6044');
    poly(g,[[-145,-142],[-7,-234],[117,-142],[88,-151],[-7,-213],[-119,-151]],'#a66342','#674535');
    poly(g,[[-25,0],[-25,-82],[18,-82],[18,0]],'#665039','#efc99b');
    poly(g,[[-93,-118],[-52,-118],[-52,-69],[-93,-69]],'#9ec8c3','#694e3b');
    oval(g,114,-61,65,65,'#6b5237');oval(g,114,-61,47,47,'#a47a4a');oval(g,114,-61,12,12,'#59442d');
    for(let i=0;i<10;i++){const a=i*TAU/10;stroke(g,[[114+Math.cos(a)*14,-61+Math.sin(a)*14],[114+Math.cos(a)*60,-61+Math.sin(a)*60]],'#574329',7);}
    stroke(g,[[50,-172],[64,-213]],'#d7a86d',4);
  }};
  City.art.stone_bridge={box:[470,240,235,175],draw(g){
    oval(g,0,15,124,20,'rgba(22,41,28,.2)');
    poly(g,[[-125,-8],[-100,-40],[100,-40],[125,-8],[110,12],[-110,12]],'#c6b991','#6d765e');
    for(let x=-87;x<=87;x+=29)stroke(g,[[x,-34],[x+1,3]],'#8d8968',3);
    for(const x of [-107,106]){poly(g,[[x-8,-9],[x-8,-59],[x+8,-59],[x+8,-9]],'#d9c99e','#6a765f');oval(g,x,-60,12,7,'#e9d4a3');}
  }};
  City.art.wild_hive={box:[220,260,110,220],draw(g){
    oval(g,0,8,49,14,'rgba(38,47,19,.21)');
    poly(g,[[-25,0],[-17,-87],[12,-89],[25,0]],'#795239','#463b2e');
    oval(g,6,-104,36,29,'#a87940');
    for(let i=-2;i<=2;i++)stroke(g,[[-24,-104+i*9],[35,-104+i*9]],'#d9a653',3);
    oval(g,7,-100,8,6,'#473428');
  }};
  City.art.wicker_post={box:[190,290,95,245],draw(g){
    oval(g,0,5,40,10,'rgba(28,42,20,.22)');stroke(g,[[0,0],[0,-184]],'#654634',11);
    stroke(g,[[-55,-127],[55,-127]],'#806043',9);poly(g,[[-23,-143],[-11,-171],[14,-171],[27,-143]],'#b58a53','#745338');
    poly(g,[[-40,-169],[0,-205],[41,-169]],'#705142','#403d32');
    for(const x of [-34,-17,1,19,35])stroke(g,[[x,-122],[x+4,-79]],'#cfab67',3);
  }};

  // The Elder Hollow's door, drawn isometric (owner rule: gates are never a flat front elevation): a stepped stone plinth, two split oak trunks standing on the long sides of the footprint
  // (o.width x o.depth, the door on the +y wall) with a root arch between them over a dark stair, a root lintel and a leafy crown.
  City.art.elder_hollow_gate={box:[920,760,460,695],draw(g,o,K){
    const {iso,prism}=K;
    oval(g,0,17,254,49,'rgba(24,47,24,.38)');
    g.save();g.translate(...iso(0,0));prism(g,9.4,4.4,12,'#b7b08f','#8d8870','#76735f');g.restore();
    g.save();g.translate(...iso(0,.3));prism(g,6.6,3.2,8,'#c7bf9b','#9b957a','#85826a',12);g.restore();
    g.save();g.translate(...iso(0,.5));prism(g,4.8,2.4,8,'#d6ceaa','#a8a186','#918e76',20);g.restore();
    // the dark stair under the arch, on the +y wall
    g.save();g.translate(...iso(0,1.55,12));g.transform(1,.5,0,1,0,0);
    poly(g,[[-96,0],[-96,-150],[-70,-220],[0,-252],[70,-220],[96,-150],[96,0]],'#14261f','#e0cb92',6);
    poly(g,[[-70,0],[-70,-140],[-48,-196],[0,-222],[48,-196],[70,-140],[70,0]],'rgba(170,219,138,.22)');
    for(let i=0;i<5;i++)stroke(g,[[-70+i*4,-8-i*14],[70-i*4,-8-i*14]],'#ccb891',4);
    g.restore();
    for(const side of [-1,1]){
      g.save();g.translate(...iso(side*3.05,0,12));prism(g,1.9,2.2,250,'#8a6a46','#5f4630','#4a3624');g.restore();
      const [rx,ry]=iso(side*3.05,1.2,12);
      for(let k=0;k<4;k++)stroke(g,[[rx+side*(8+k*14),ry+k*2],[rx+side*(34+k*16),ry-26+k*6],[rx+side*(52+k*14),ry-8+k*3]],'#7a5a3a',10-k*2);
      for(let i=0;i<4;i++){const [bx,by]=iso(side*3.05,1.1,40+i*52);stroke(g,[[bx-9,by],[bx-4,by-18]],'#bb8e5d',3);}
    }
    g.save();g.translate(...iso(0,0,262));prism(g,9,2.4,34,'#9a7a54','#6b5238','#584330');g.restore();
    const [cx,cy]=iso(0,0,296);
    for(const side of [-1,1]){
      stroke(g,[[cx+side*120,cy+40],[cx+side*190,cy-70],[cx+side*290,cy-120]],'#735436',22);
      stroke(g,[[cx+side*90,cy+10],[cx+side*40,cy-120],[cx,cy-170]],'#765638',18);
      leaf(g,cx+side*230,cy-110,116,79,'#4e8139');leaf(g,cx+side*110,cy-160,115,81,'#5a923f');
    }
    leaf(g,cx,cy-205,169,91,'#639c44');
    for(let i=0;i<52;i++){const x=(seed(i,2)-.5)*530,y=cy-150-seed(i+59,1)*150;oval(g,x,y,4,2.3,i%5?'#9bbd59':'#d1db7d');}
    for(const x of [-4.2,4.2]){g.save();g.translate(...iso(x,1.6,12));prism(g,.4,.4,48,'#a69670','#7d7255','#6b6149');g.restore();const [lx,ly]=iso(x,1.6,66);oval(g,lx,ly,13,13,'#ffe0a0');}
  },animate(g,o,sx,sy,t){
    g.save();g.globalAlpha=.22+.12*Math.sin(t*.6);g.fillStyle='#fff2b4';
    for(let i=0;i<18;i++){const x=sx+Math.sin(i*18.1+t*.34)*155,
      y=sy-250-((i*61+t*(12+i%4*4))%370);
      oval(g,x,y,2.1,3.2,'#fff0b1');}
    g.restore();
  }};
})();
