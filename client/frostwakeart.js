'use strict';
// Frostwake Shelf: calved ice, aurora lanterns and a camp lashed to the snow.
(() => {
  const {poly}=City.kit,TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const line=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineCap='round';g.lineJoin='round';g.stroke();};
  const shadow=(g,r)=>oval(g,0,6,r,r*.25,'rgba(26,60,91,.25)');
  City.art.frostwake_crevasse={box:[570,260,285,220],draw(g,o){
    const v=o.v||0;shadow(g,165);
    poly(g,[[-245,-23],[-141,-68],[-47,-35],[34,-74],[142,-49],[251,-82],[234,23],[114,36],[26,0],[-67,53],[-155,18]],'#569fbd','#e3f9fb',7);
    poly(g,[[-213,-12],[-142,-46],[-34,-14],[42,-52],[148,-28],[218,-59],[201,-11],[101,10],[12,-21],[-73,28],[-147,0]],v%2?'#153f67':'#225b79');
    line(g,[[-158,-29],[-33,0],[42,-41],[143,-13]],'#89dbe8',4);
    for(let j=0;j<5;j++)line(g,[[-192+j*95,-15],[-162+j*93,1]],'rgba(224,255,255,.7)',2);
  }};
  City.art.frostwake_frozen_pool={box:[600,310,300,260],draw(g,o){
    shadow(g,195);oval(g,0,-15,215,102,'#9fc7d6');oval(g,0,-19,201,92,o.v?'#70b2cc':'#5c9cb9');
    for(let j=0;j<9;j++){const a=j*TAU/9;line(g,[[0,-19],[Math.cos(a)*180,Math.sin(a)*73-19]],'rgba(224,253,255,.72)',2);}
    for(let j=0;j<6;j++)oval(g,-150+j*58,-18+Math.sin(j*3)*35,9,4,'rgba(239,255,255,.65)');
  }};
  City.art.frostwake_snow_pine={box:[350,550,175,505],draw(g,o){
    shadow(g,84);line(g,[[0,0],[0,-345]],'#4b6877',17);
    for(let j=0;j<4;j++){const y=-85-j*66,w=94-j*19;
      poly(g,[[-w,y],[0,y-146],[w,y]],o.v%2?'#416f81':'#3d7989','#254e67',5);
      line(g,[[-w+9,y-12],[0,y-129],[w-9,y-12]],'#d9f3f4',9);}
    oval(g,0,-381,12,7,'#f4fbf7');
  }};
  City.art.frostwake_ice_spire={box:[260,420,130,375],draw(g,o){
    shadow(g,75);poly(g,[[-54,0],[-43,-209],[5,-340],[48,-155],[57,0]],o.v%2?'#78b9d1':'#9ad9e4','#357592',7);
    poly(g,[[-28,-11],[-22,-185],[4,-312],[17,-162],[20,-10]],'#daf7f7');
    line(g,[[-42,-201],[4,-311],[47,-155]],'#eefdf9',5);
  }};
  City.art.frostwake_camp={box:[550,480,275,435],draw(g,o){
    shadow(g,180);poly(g,[[-187,0],[0,54],[187,0],[0,-54]],'#b7cbd1','#58758a',6);
    for(let x of [-136,136])line(g,[[x,0],[x,-187]],'#59738b',8);
    poly(g,[[-200,-182],[0,-313],[200,-182],[0,-112]],o.v%2?'#6297ae':'#7085a5','#315b78',7);
    for(let j=-3;j<=3;j++)line(g,[[j*49,-182],[j*41,-245]],'#d9eff1',5);
    line(g,[[0,-310],[0,-364]],'#5a7690',5);poly(g,[[0,-363],[56,-344],[0,-324]],'#7be4d4','#2c6783',4);
    for(let j=-2;j<=2;j++)oval(g,j*52,-14,16,7,'#e9f9f8');
  }};
  City.art.frostwake_hearth={box:[360,390,180,340],draw(g){
    shadow(g,100);oval(g,0,-9,104,58,'#7d9aa5');oval(g,0,-18,77,42,'#d0e1dd');
    for(let i=0;i<9;i++){const a=i*TAU/9;oval(g,Math.cos(a)*72,Math.sin(a)*38-19,18,10,i%2?'#6f8795':'#a9c8cc');}
    poly(g,[[-24,-31],[0,-146],[23,-34],[0,-66]],'#ffd49a','#d68e61',4);oval(g,0,-72,15,25,'#fff3ca');
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.08+.06*Math.sin(t*2);oval(g,sx,sy-98,76,107,'#ffda9b');g.restore();}};
  City.art.frostwake_signal={box:[230,350,115,315],draw(g){
    shadow(g,56);line(g,[[0,0],[0,-232]],'#4f6d85',10);poly(g,[[-37,-238],[0,-283],[37,-238]],'#dceeee','#5c879e',5);
    oval(g,0,-219,28,40,'#7bd9d7');oval(g,0,-219,13,26,'#e5ffea');
  }};
  City.art.frostwake_lantern={box:[150,220,75,180],draw(g){line(g,[[0,0],[0,-153]],'#5d758a',5);poly(g,[[-17,-157],[0,-188],[17,-157]],'#e5f7f2');oval(g,0,-146,13,23,'#8cddd9');oval(g,0,-145,5,15,'#edfff3');}};
  City.art.frostwake_obelisk={box:[640,810,320,750],draw(g){
    shadow(g,210);poly(g,[[-147,0],[-119,-463],[-13,-695],[112,-464],[146,0]],'#3b7ca4','#d5f7f3',11);
    poly(g,[[-76,-37],[-61,-442],[-9,-609],[44,-436],[65,-36]],'#9cdedc');
    poly(g,[[-10,-590],[36,-435],[-10,-291],[-57,-435]],'#b8f7de','#567db0',5);
    for(let side of [-1,1]){line(g,[[side*170,0],[side*167,-292],[side*95,-416]],'#477d98',18);oval(g,side*108,-430,31,24,'#a4f0d8');}
    for(let j=0;j<7;j++){const a=j*TAU/7;oval(g,Math.cos(a)*130,-330+Math.sin(a)*119,11,12,j%2?'#bdf9d6':'#d2ecff');}
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.13+.09*Math.sin(t*.9);oval(g,sx,sy-430,190,305,'#8bf9cd');g.restore();}};
  City.art.frostwake_fossil={box:[440,300,220,260],draw(g){shadow(g,130);line(g,[[-150,-10],[143,-37]],'#e6ecdb',19);for(let i=0;i<7;i++){let x=-127+i*42;line(g,[[x,-14],[x-20,-112+i%3*15]],'#d6e0d7',9);}}};
  City.art.frostwake_mammoth_bells={box:[280,280,140,240],draw(g){shadow(g,85);line(g,[[-83,0],[-83,-172]],'#63798a',9);line(g,[[83,0],[83,-172]],'#63798a',9);line(g,[[-88,-171],[88,-171]],'#63798a',7);for(let x of [-48,0,48]){line(g,[[x,-171],[x,-125]],'#ad9f82',4);oval(g,x,-114,17,22,'#d4bd8c');}}};
  City.art.frostwake_leviathan_rib={box:[460,390,230,335],draw(g){shadow(g,132);for(let j=-2;j<=2;j++)line(g,[[j*52,0],[j*55,-172-Math.cos(j)*90],[j*48,-258-Math.cos(j)*35]],'#cde5e5',13);line(g,[[-150,-10],[150,-10]],'#a7cbd2',17);}};
  City.art.frostwake_snowdrift={box:[200,100,100,70],draw(g,o){oval(g,0,-7,65+o.v*6,23,'#d7eff3');oval(g,-11,-12,50,14,'#f4fbf7');}};
  City.art.frostwake_iceflower={box:[110,120,55,95],draw(g,o){line(g,[[0,0],[0,-48]],'#7dabb5',3);for(let i=0;i<6;i++){let a=i*TAU/6;oval(g,Math.cos(a)*11,-55+Math.sin(a)*11,7,4,o.v%2?'#9cf2e1':'#c5dfff');}oval(g,0,-55,4,4,'#fff7c9');}};
})();
