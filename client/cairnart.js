'use strict';
// The Cairnspine: ochre switchbacks cut through blue slate and a leafless alpine forest.
(() => {
  const {poly,iso,prism}=City.kit,T=Math.PI*2;
  const oval=(g,x,y,a,b,c)=>{g.fillStyle=c;g.beginPath();g.ellipse(x,y,a,b,0,0,T);g.fill();};
  const line=(g,p,c,w=3)=>{g.strokeStyle=c;g.lineWidth=w;g.lineCap='round';g.lineJoin='round';g.beginPath();p.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.stroke();};
  const shade=(g,r)=>oval(g,0,7,r,r*.27,'rgba(30,37,48,.27)');
  City.art.cairn_boulder={box:[350,260,175,230],draw(g,o){shade(g,130);const v=o.v||0;poly(g,[[-123,0],[-130,-46],[-75,-147],[18,-174],[116,-112],[134,-33],[86,9]],v%2?'#6d7279':'#787c7f','#303946',6);poly(g,[[-75,-147],[18,-174],[116,-112],[65,-95],[-20,-79]],'#aa9f8e');poly(g,[[-123,0],[-130,-46],[-75,-147],[-20,-79],[-22,-5]],'#555d68');for(let i=0;i<5;i++)line(g,[[-72+i*29,-32-i%2*12],[-52+i*24,-42-i%3*16]],'#c4b08f',2);}};
  City.art.cairn_dead_tree={box:[310,590,155,550],draw(g,o){shade(g,65);const v=o.v||0;line(g,[[0,0],[v*3-8,-170],[0,-340]],'#303c44',24);line(g,[[4,-15],[3,-190],[5,-342]],'#cfccbb',15);for(const s of [-1,1]){line(g,[[0,-170],[s*70,-260],[s*105,-352]],'#d6d2c4',9);line(g,[[s*66,-260],[s*129,-279]],'#bebbad',5);line(g,[[s*13,-285],[s*52,-398]],'#e4ded1',6);line(g,[[s*40,-363],[s*78,-387]],'#d7d2c5',4);}}};
  City.art.cairn_slate_spire={box:[240,420,120,380],draw(g,o){shade(g,60);poly(g,[[-61,0],[-39,-230],[9,-350],[54,-167],[66,0]],o.v%2?'#5e6670':'#777b7c','#343c49',6);poly(g,[[-38,-228],[9,-350],[18,-198],[-14,-13]],'#aca797');line(g,[[-39,-230],[9,-350],[54,-167]],'#c2baa5',3);}};
  City.art.cairn_pebble={box:[100,65,50,50],draw(g,o){oval(g,0,-4,32+o.v*3,16,o.v%2?'#7f8180':'#a29684');oval(g,-8,-10,17,6,'#b8ad96');}};
  City.art.cairn_windbanner={box:[180,340,90,310],draw(g,o){shade(g,25);line(g,[[0,0],[0,-250]],'#4a4542',9);poly(g,[[0,-241],[87,-219],[28,-186],[0,-198]],o.v%2?'#9e7560':'#b3915f','#4a3c3c',4);line(g,[[5,-235],[75,-219]],'#e2c69e',3);}};
  City.art.cairn_watchhall={box:[620,570,310,480],draw(g,o){shade(g,215);poly(g,[[-205,-16],[0,65],[205,-16],[0,-102]],'#8a7869','#403f45',6);poly(g,[[-170,-21],[-170,-227],[0,-309],[170,-227],[170,-21],[0,48]],'#68656a','#343942',7);poly(g,[[-191,-221],[0,-374],[191,-221],[0,-135]],o.v%2?'#3d5058':'#455963','#242d36',8);for(let i=-3;i<=3;i++)line(g,[[i*50,-239],[i*49,-183]],'#b4aa91',4);poly(g,[[-30,23],[-30,-153],[0,-169],[30,-153],[30,24]],'#302f3c','#c3aa7e',4);oval(g,0,-94,14,25,'#e1a65b');}};
  City.art.cairn_signal={box:[260,440,130,400],draw(g){shade(g,67);line(g,[[0,0],[0,-310]],'#655c56',12);poly(g,[[-70,-296],[0,-374],[70,-296]],'#c0b39d','#343c47',6);oval(g,0,-292,31,43,'#efbc73');oval(g,0,-293,13,29,'#ffe4ad');}};
  City.art.cairn_stonecircle={box:[460,330,230,300],draw(g){shade(g,165);for(let i=0;i<9;i++){const a=i*T/9,x=Math.cos(a)*142,y=Math.sin(a)*55;poly(g,[[x-16,y],[x-14,y-105],[x+7,y-132],[x+18,y-5]],i%2?'#6d7178':'#969489','#3d424b',4);}oval(g,0,-9,79,31,'#9b856d');}};
  City.art.cairn_whitegrove={box:[590,570,295,530],draw(g){shade(g,170);for(let i=-2;i<=2;i++){let x=i*70,y=Math.abs(i)*10;line(g,[[x,y],[x+12,-180],[x-6,-310]],'#dedaca',17);for(let s of [-1,1]){line(g,[[x+10,-167],[x+s*56,-241],[x+s*74,-341]],'#ebe7d6',7);line(g,[[x+s*45,-246],[x+s*96,-264]],'#d7d6cb',4);}}}};
  City.art.cairn_eyrie={box:[420,390,210,350],draw(g){shade(g,150);poly(g,[[-169,0],[-124,-202],[-25,-297],[79,-242],[158,-58],[139,8]],'#59616a','#303946',7);poly(g,[[-25,-297],[79,-242],[11,-130],[-69,-132]],'#aba38f');for(let i=0;i<5;i++)line(g,[[-115+i*51,-31],[-61+i*36,-121]],'#c3b594',6);}};
  City.art.cairn_boulder_altar={box:[430,390,215,350],draw(g){shade(g,130);for(let i=-2;i<=2;i++)poly(g,[[i*66-35,0],[i*66-29,-96-i%2*20],[i*66+26,-108],[i*66+36,2]],i%2?'#777a7b':'#929084','#353b44',4);line(g,[[-128,-139],[0,-203],[132,-142]],'#d9be83',9);oval(g,0,-206,22,29,'#e8b663');}};
  // The Thunderheart Gate, drawn isometric (owner rule 2026-11-09: gates are never a flat front elevation): a slate plinth, two square slate pillars with bronze bands on the x axis, a lintel across
  // them, and the stormlight ring standing in the wall plane between the pillars (the opening runs along the y axis; the ring is sheared like a house door).
  const ring=(g,rx,ry,cy,c)=>{g.beginPath();g.ellipse(0,cy,rx,ry,0,0,T);g.fillStyle=c;g.fill();};
  City.art.cairn_thunder_gate={box:[900,920,450,865],draw(g,o){
    shade(g,365);
    g.save();g.translate(...iso(0,0));prism(g,7.4,3,16,'#8a8d94','#5c616c','#464b57');g.restore();
    g.save();g.translate(...iso(0,.6));g.transform(1,.5,0,1,0,0);
    ring(g,112,172,-258,'#172937');ring(g,76,148,-258,o.open?'#84d4ed':'#2d5360');
    for(let i=0;i<13;i++){const a=i*T/13;oval(g,Math.cos(a)*134,-258+Math.sin(a)*190,9,13,i%2?'#f4d99a':'#91d6cf');}
    g.restore();
    for(const x of [-2.6,2.6]){
      g.save();g.translate(...iso(x,0));prism(g,1.5,1.5,430,'#8d9199','#5d6370','#474d5a',16);g.restore();
      for(const z of [150,300]){g.save();g.translate(...iso(x,0));prism(g,1.7,1.7,22,'#e0b87a','#a98450','#8a6a3e',16+z);g.restore();}
    }
    g.save();g.translate(...iso(0,0));prism(g,7.4,1.7,80,'#9c9fa5','#676c78','#505663',446);g.restore();
    const [kx,ky]=iso(0,.85,560);poly(g,[[kx-34,ky+2],[kx,ky-52],[kx+34,ky+2],[kx,ky+26]],'#ddb87b','#5f5650',5);
  },animate(g,o,sx,sy,t){g.save();g.translate(sx,sy);g.transform(1,.5,0,1,0,0);g.globalAlpha=.1+.06*Math.sin(t*1.7);oval(g,0,-258,136,206,'#7bbec0');g.restore();}};
  City.art.cairn_stack={box:[130,170,65,150],draw(g,o){shade(g,34);const v=o.v||0;[[0,-2,38,13,'#6f747c'],[1,-22,31,11,'#8a8f93'],[-1,-39,23,9,'#767b80'],[0,-54,15,7,'#9a9a96']].forEach(([x,y,a,b,c],i)=>{oval(g,x+(v%2?2:-2)*(i%2),y,a,b,c);oval(g,x-a*.2,y-b*.35,a*.5,b*.3,'rgba(214,214,205,.28)');});}};
  City.art.cairn_lichen_rock={box:[180,120,90,100],draw(g,o){shade(g,50);const v=o.v||0;poly(g,[[-54,0],[-48,-36],[-16,-68],[26,-62],[54,-30],[58,0]],v%2?'#667079':'#7a8088','#303946',5);poly(g,[[-48,-36],[-16,-68],[26,-62],[54,-30],[24,-36],[-12,-44]],'#9aa0a2');for(let k=0;k<6;k++)oval(g,-34+k*14+(v%3)*2,-24-(k%3)*12,5+(k%2)*3,3+(k%2),k%2?'#d99a3c':'#e8c15a');}};
})();
