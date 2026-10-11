'use strict';
// Veyrroot is one living tree: open crown galleries outside and rooms cut into the heartwood.
(() => {
  const {poly}=City.kit,TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const line=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineCap='round';g.lineJoin='round';g.stroke();};
  const leaf=(g,x,y,r,c)=>{oval(g,x,y,r,r*.53,c);oval(g,x-r*.22,y-r*.18,r*.35,r*.15,'rgba(239,246,173,.25)');};
  const shadow=(g,r)=>oval(g,0,4,r,r*.25,'rgba(13,47,40,.3)');
  City.art.worldheart_trunk={box:[1880,1580,940,1450],draw(g){
    shadow(g,410);
    // Buttresses, bark windows, looping balconies and the vast split crown.
    for(let side of [-1,1]){
      poly(g,[[side*45,-210],[side*156,-90],[side*299,0],[side*179,-9],[side*82,-139]],'#836b49','#345544',8);
      poly(g,[[side*90,-340],[side*277,-515],[side*460,-570],[side*299,-523],[side*83,-395]],'#846f4d','#355343',8);
    }
    poly(g,[[-132,0],[-109,-673],[-93,-898],[-15,-1051],[78,-949],[116,-655],[132,0]],'#8b7050','#314d3d',10);
    for(let j=-4;j<=4;j++)line(g,[[j*22,-5],[j*14,-575],[j*27,-768]],j%2?'#aa8a5d':'#5f5b45',6);
    for(let y of [-95,-235,-375,-515]){
      oval(g,0,y,172,31,'#b79a69');oval(g,0,y-7,151,23,'#6c9164');
      for(let x=-120;x<=120;x+=30){line(g,[[x,y-12],[x,y+17]],'#3a5f4a',3);oval(g,x,y-13,4,3,'#f8df87');}
    }
    for(let y of [-165,-315,-465])for(let x of [-66,0,66]){
      oval(g,x,y,24,39,'#304f42');oval(g,x,y,16,30,'#e5b974');oval(g,x,y,9,22,'#f5e7aa');
    }
    const crowns=[[-400,-1055,245],[-190,-1165,260],[80,-1220,260],[329,-1090,247],[-15,-1030,340]];
    for(let i=0;i<crowns.length;i++){const [x,y,r]=crowns[i];leaf(g,x,y,r,['#2f9165','#39a56a','#56b979','#45aa73','#287f5b'][i]);}
    for(let j=0;j<42;j++){const x=((j*131)%1050)-525,y=-1150-((j*67)%260);oval(g,x,y,7+(j%3)*2,4,j%4?'#b9d984':'#f6d37d');}
    for(let side of [-1,1])for(let j=0;j<7;j++)line(g,[[side*(120+j*44),-1160],[side*(130+j*46),-660-j%2*46]],'#72ae69',4);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.2+.1*Math.sin(t*1.2);for(let j=0;j<11;j++)oval(g,sx+Math.sin(j*7+t)*240,sy-280-(j*57+t*13)%520,3,5,'#f9e8a0');g.restore();}};
  City.art.hollow_arch={box:[530,680,265,620],draw(g){
    shadow(g,155);
    poly(g,[[-150,0],[-136,-315],[-105,-465],[-47,-560],[48,-560],[105,-465],[136,-315],[150,0]],'#866d4b','#344e3e',9);
    poly(g,[[-77,0],[-75,-225],[-44,-294],[0,-317],[44,-294],[75,-225],[77,0]],'#244a43','#d4bd77',8);
    poly(g,[[-51,-11],[-52,-212],[-26,-261],[0,-274],[26,-261],[52,-212],[51,-11]],'#3c6d53','#b7d28a',5);
    for(let side of [-1,1]){
      line(g,[[side*94,-70],[side*91,-360],[side*45,-495]],'#5b8d58',9);
      for(let j=0;j<5;j++)leaf(g,side*(118+j%2*12),-120-j*75,35,j%2?'#66b777':'#87c874');
    }
    oval(g,0,-301,20,16,'#fae9a7');
  }};
  City.art.canopy_market={box:[480,420,240,365],draw(g,o){
    shadow(g,140);poly(g,[[-156,0],[0,57],[156,0],[0,-57]],'#ab8355','#38543d',5);
    for(let x of [-111,111])line(g,[[x,-10],[x,-180]],'#765e43',8);
    poly(g,[[-164,-179],[0,-259],[164,-179],[0,-111]],o.v?'#e9b66f':'#a3cd82','#4d7656',6);
    for(let j=-3;j<=3;j++)leaf(g,j*39,-172,20,j%2?'#6cb971':'#e5d078');
    line(g,[[-95,-38],[95,-38]],'#edd3a2',12);
  }};
  City.art.sunleaf_observatory={box:[500,570,250,510],draw(g){
    shadow(g,155);poly(g,[[-156,0],[0,65],[156,0],[0,-65]],'#bb9a65','#365645',5);
    for(let x of [-118,118])line(g,[[x,-4],[x,-281]],'#8e704e',10);
    poly(g,[[-158,-279],[0,-405],[158,-279],[0,-213]],'#6ba578','#e4dc9b',6);
    oval(g,0,-263,58,51,'#d7d8a4');oval(g,0,-263,42,39,'#75c0a3');
    for(let j=-2;j<=2;j++)line(g,[[j*50,-18],[j*50,-97]],'#e4d39e',4);
    oval(g,0,-410,30,16,'#ffe3a2');
  }};
  City.art.suspended_garden={box:[370,340,185,290],draw(g,o){
    shadow(g,100);poly(g,[[-114,0],[0,45],[114,0],[0,-45]],'#9c794e','#345e45',5);
    for(let j=0;j<9;j++){const x=((j*39+o.v*17)%174)-87,y=-30-j%3*10;leaf(g,x,y,25,j%3?'#6dba78':'#a7d787');}
    for(let x of [-90,90])line(g,[[x,0],[x,-92]],'#b99b6b',5);
  }};
  City.art.buttress_root={box:[270,210,135,165],draw(g,o){shadow(g,75);poly(g,[[-91,0],[-23,-91],[30,-143],[17,-83],[102,0],[61,-15],[3,-64],[-55,-3]],o.v%2?'#9e8058':'#816c4b','#39563f',5);}};
  City.art.hanging_pod={box:[280,390,140,340],draw(g,o){
    shadow(g,75);line(g,[[0,-335],[0,-188]],'#629c65',6);
    oval(g,0,-124,69,88,o.v%2?'#c99f63':'#9db974');oval(g,0,-126,42,58,'#476d58');
    oval(g,0,-134,29,39,'#f3d79b');for(let side of [-1,1])leaf(g,side*45,-195,39,'#66ae71');
  }};
  City.art.leaf_lantern={box:[110,180,55,155],draw(g,o){line(g,[[0,0],[0,-101]],'#658a59',3);oval(g,0,-106,13,17,o.v%2?'#f5d97c':'#f5eaa4');leaf(g,0,-131,21,'#5aaa70');}};
  City.art.epiphyte_garden={box:[150,130,75,100],draw(g,o){
    for(let j=0;j<5;j++){const x=j*28-56;leaf(g,x,-19-j%2*9,23,j%2?'#74c87a':'#a0d78d');oval(g,x+4,-33-j%2*8,5,4,j%2?'#ffb3c6':'#f5dd87');}
  }};
  City.art.branch_rail={box:[170,125,85,95],draw(g,o){line(g,[[-64,0],[-64,-48],[-27,-61],[28,-61],[64,-48],[64,0]],'#806346',7);for(let x of [-35,0,35])leaf(g,x,-59,17,'#64ac6a');}};
  City.art.heartwood_vault={box:[960,1040,480,950],draw(g){
    shadow(g,260);
    // A sealed iris of overlapping living bark petals, with amber seams.
    for(let side of [-1,1])poly(g,[[side*300,0],[side*270,-552],[side*199,-730],[side*110,-870],[side*149,-557],[side*184,0]],'#785a43','#354b3c',9);
    oval(g,0,-423,256,345,'#3a5b4b');oval(g,0,-423,224,306,'#d2b777');oval(g,0,-423,203,282,'#315f51');
    for(let i=0;i<8;i++){const a=i*TAU/8;g.save();g.translate(0,-423);g.rotate(a);
      poly(g,[[-28,-196],[25,-196],[82,-30],[10,63],[-73,-30]],i%2?'#8cad6f':'#6f9763','#d7bf81',5);g.restore();}
    oval(g,0,-423,58,76,'#f4d99b');oval(g,0,-423,39,56,'#a8e0ad');
    for(let j=-5;j<=5;j++){const x=j*48;line(g,[[x,-700],[x+Math.sin(j)*12,-190]],'#568c62',4);leaf(g,x,-730,22,j%2?'#7fbf78':'#abd983');}
    for(let side of [-1,1])for(let j=0;j<4;j++)oval(g,side*(218+j*25),-161-j*124,7,12,'#f1cf7c');
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.16+.09*Math.sin(t*1.4);oval(g,sx,sy-430,69,81,'#fff0a8');g.restore();}};
  City.art.heartwood_core={box:[550,560,275,510],draw(g){
    shadow(g,170);for(let r of [173,145,117,90]){g.beginPath();g.ellipse(0,-45,r,r*.55,0,0,TAU);g.strokeStyle=r%2?'#c79d68':'#d5bd80';g.lineWidth=12;g.stroke();}
    oval(g,0,-70,74,31,'#93d9a4');oval(g,0,-82,38,21,'#f2dea2');
    for(let j=0;j<10;j++){const a=j*TAU/10;leaf(g,Math.cos(a)*152,-83+Math.sin(a)*66,35,j%2?'#76b977':'#a2d486');}
  }};
  City.art.hollow_lift={box:[330,400,165,355],draw(g){
    shadow(g,110);oval(g,0,-16,97,35,'#c6a474');oval(g,0,-27,75,25,'#518a68');
    for(let x of [-80,80])line(g,[[x,-24],[x,-262]],'#947851',9);
    poly(g,[[-104,-263],[0,-350],[104,-263],[0,-220]],'#a8c77f','#3f7355',5);
  }};
  City.art.amber_library={box:[530,470,265,420],draw(g){
    shadow(g,150);poly(g,[[-167,0],[0,59],[167,0],[0,-59]],'#a77c52','#365541',5);
    for(let x of [-112,-38,38,112]){poly(g,[[x-24,-44],[x+24,-44],[x+24,-230],[x-24,-230]],'#765741','#d6b778',4);
      for(let j=0;j<4;j++)oval(g,x,-75-j*35,14,7,j%2?'#f6da91':'#80b992');}
    poly(g,[[-180,-229],[0,-316],[180,-229],[0,-177]],'#9db779','#e9d294',5);
  }};
  City.art.pith_forge={box:[410,390,205,350],draw(g){shadow(g,125);poly(g,[[-137,0],[0,54],[137,0],[0,-54]],'#8f704c','#3e5d48',4);
    oval(g,0,-94,72,52,'#8e7050');oval(g,0,-99,45,30,'#f3cf82');oval(g,0,-111,22,15,'#a2e0aa');
    for(let x of [-98,98])line(g,[[x,0],[x,-191]],'#947553',8);
    poly(g,[[-135,-192],[0,-266],[135,-192],[0,-147]],'#a2ba78','#d5c388',4);
  }};
  City.art.root_loom={box:[320,320,160,280],draw(g){shadow(g,99);for(let x of [-81,81])line(g,[[x,0],[x,-205]],'#8b6b4d',9);
    line(g,[[-88,-191],[88,-191]],'#b59565',8);for(let j=-4;j<=4;j++)line(g,[[j*19,-185],[j*15,-29]],j%2?'#cfaa79':'#77b68b',4);
  }};
  City.art.seed_chapel={box:[420,460,210,405],draw(g){shadow(g,117);
    for(let side of [-1,1])poly(g,[[side*110,0],[side*77,-240],[0,-343],[side*14,-177],[side*40,0]],'#9f8259','#3e5944',5);
    oval(g,0,-215,61,90,'#5e9775');oval(g,0,-225,43,64,'#f5dfaa');leaf(g,0,-318,46,'#78bc78');
  }};
  City.art.heartwood_column={box:[150,295,75,260],draw(g,o){shadow(g,37);poly(g,[[-26,0],[-21,-215],[-7,-246],[16,-217],[25,0]],o.v%2?'#a88a60':'#81684c','#3f5e49',4);leaf(g,0,-242,38,'#70ad71');}};
  City.art.glow_sconce={box:[90,140,45,115],draw(g,o){line(g,[[0,0],[0,-69]],'#886b4b',4);oval(g,0,-75,14,21,o.v%2?'#f7dea3':'#a8e0ad');}};
  City.art.amber_window={box:[100,130,50,105],draw(g){oval(g,0,-51,27,44,'#926d4e');oval(g,0,-51,19,36,'#edcf8c');oval(g,0,-51,9,22,'#f8e9b4');}};
  City.art.root_bench={box:[180,135,90,110],draw(g){shadow(g,63);line(g,[[-56,-15],[56,-15]],'#a28359',15);for(let x of [-46,46])line(g,[[x,-11],[x,3]],'#654e3b',7);}};
})();
