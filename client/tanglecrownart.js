'use strict';
// Layered jungle trunks, rain-bright waterways and the sealed crown temple.
(() => {
  const {poly}=City.kit,TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const line=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineCap='round';g.lineJoin='round';g.stroke();};
  const shade=(v)=>['#236e55','#328b59','#47a768','#5db875'][((v%4)+4)%4];
  const shadow=(g,r)=>oval(g,0,5,r,r*.24,'rgba(10,48,37,.29)');
  const leaf=(g,x,y,rx,ry,c)=>{oval(g,x,y,rx,ry,c);oval(g,x-rx*.24,y-ry*.25,rx*.45,ry*.25,'rgba(199,236,138,.22)');};
  City.art.kapok_tree={box:[500,600,250,550],draw(g,o){
    shadow(g,112);
    for(const s of [-1,1])poly(g,[[0,-67],[s*18,-129],[s*49,-2],[s*27,0],[s*11,-42]],'#6e6a46','#394d38',3);
    poly(g,[[-29,0],[-22,-205],[-38,-274],[-16,-303],[3,-236],[15,-314],[36,-284],[24,-188],[30,0]],'#8a7750','#45543b',4);
    for(let j=-4;j<=4;j++){const x=j*37,y=-301-Math.cos(j*.35)*50;leaf(g,x,y,81,63,shade(o.v+j));}
    leaf(g,0,-385,102,69,'#3ca66d');
    for(let j=0;j<22;j++){const x=(j*67+o.v*31)%310-155,y=-301-(j*37)%107;oval(g,x,y,5,3,j%3?'#9ed56f':'#e5ce6d');}
    for(let j=-2;j<=2;j++)line(g,[[j*54,-353],[j*56+Math.sin(j)*9,-178]],'#56895d',3);
  }};
  City.art.strangler_fig={box:[440,540,220,490],draw(g,o){
    shadow(g,98);for(let j=-3;j<=3;j++)line(g,[[j*15,0],[j*12,-131],[j*21,-229]],j%2?'#886e4a':'#aa8659',9);
    for(let j=-3;j<=3;j++){const x=j*54,y=-266-Math.cos(j*.45)*43;leaf(g,x,y,81,69,shade(o.v+j+1));}
    leaf(g,0,-345,96,60,'#2f9159');
    for(let j=-3;j<=3;j++){const x=j*40;line(g,[[x,-264],[x+8,-116-j%2*25]],'#7cbf6b',3);}
  }};
  City.art.banana_palm={box:[330,410,165,370],draw(g,o){
    shadow(g,66);line(g,[[0,0],[0,-213]],'#99824e',14);
    for(let j=0;j<7;j++){const a=(j/7)*TAU,x=Math.cos(a)*116,y=-224+Math.sin(a)*47;
      poly(g,[[0,-221],[x*.46,y-38],[x,y],[x*.73,y+28]],j%2?'#51ad60':'#78c46a','#2f7151',2);
      line(g,[[0,-221],[x,y]],'#a5d987',2);
    }
    for(let j=0;j<4;j++)oval(g,15+j*7,-181+j*9,6,13,'#e3bc54');
  }};
  City.art.hanging_vines={box:[165,270,82,250],draw(g,o){
    for(let j=-2;j<=2;j++){const x=j*23;line(g,[[x,-198],[x+Math.sin(j+o.v)*9,-20]],'#4c9455',3);
      for(let i=0;i<5;i++)leaf(g,x+Math.sin(j+i)*8,-46-i*28,9,4,i%2?'#a1d36e':'#73bc5d');}
  }};
  City.art.giant_fern={box:[190,155,95,135],draw(g,o){
    shadow(g,34);for(let side of [-1,1])for(let j=0;j<5;j++){
      const x=side*(22+j*13),y=-25-j*12;line(g,[[0,0],[x,y]],'#34875c',3);
      for(let k=0;k<4;k++)leaf(g,x*(k+1)/5,y*(k+1)/5,10,5,j%2?'#61b774':'#80c66b');}
  }};
  City.art.orchid_cluster={box:[140,120,70,95],draw(g,o){
    for(let j=0;j<7;j++){const x=(j*29+o.v*11)%89-44,y=(j*17)%24;
      line(g,[[x,y],[x+2,y-20-j%3*5]],'#47855d',2);
      const c=['#ff83bb','#f9d57c','#b8a6ed','#fcad88'][j%4];
      for(let k=0;k<5;k++){const a=k*TAU/5;oval(g,x+2+Math.cos(a)*7,y-23-j%3*5+Math.sin(a)*5,4,3,c);}
      oval(g,x+2,y-23-j%3*5,3,3,'#fff2b2');}
  }};
  City.art.glow_mushroom={box:[120,100,60,80],draw(g,o){
    for(let j=0;j<4;j++){const x=j*22-36,y=j%2*9;line(g,[[x,y],[x,-20]],'#d6d3a2',4);oval(g,x,-22,12,7,j%2?'#a8e5ae':'#b7d9ef');oval(g,x-2,-24,4,2,'#f4f8c7');}
  }};
  City.art.jungle_water={box:[155,75,77,55],draw(g,o){
    oval(g,0,0,67,25,'rgba(10,99,116,.45)');oval(g,0,-3,58,19,'#2e9ba8');
    oval(g,-22,-8,23,6,'rgba(153,231,192,.29)');line(g,[[-48,2],[-14,-4],[21,-2],[51,0]],'rgba(194,243,207,.45)',2);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.28+.12*Math.sin(t*2+o.x);g.strokeStyle='#d6f8d8';g.lineWidth=2;g.beginPath();g.ellipse(sx+Math.sin(t+o.y)*14,sy-7,36,10,0,.2,2.8);g.stroke();g.restore();}};
  City.art.jade_pool={box:[335,155,167,135],draw(g){
    shadow(g,112);oval(g,0,-4,129,57,'#136b72');oval(g,0,-11,111,45,'#45b4ac');
    for(let j=0;j<11;j++){const a=j*TAU/11;oval(g,Math.cos(a)*100,Math.sin(a)*41-13,15,8,j%2?'#62b970':'#8acb6c');}
    oval(g,16,-24,29,8,'rgba(198,248,205,.32)');
  }};
  City.art.root_bridge={box:[290,200,145,175],draw(g){
    shadow(g,94);for(let j=-2;j<=2;j++)line(g,[[-106,j*15],[-32,j*11-10],[38,j*8-10],[106,j*12]],j%2?'#9b764a':'#6f603c',10);
    for(let x=-85;x<=85;x+=30)line(g,[[x,-21],[x,-66]],'#6c7944',4);
    line(g,[[-99,-67],[0,-85],[99,-67]],'#a5bd76',5);
  }};
  City.art.banyan_lodge={box:[470,430,235,400],draw(g,o){
    shadow(g,125);for(let x of [-99,-43,43,99])line(g,[[x,0],[x,-143]],'#806d4d',15);
    poly(g,[[-128,-130],[-128,-247],[128,-247],[128,-130]],'#b18b5b','#4f6449',4);
    poly(g,[[-156,-247],[0,-331],[157,-247],[108,-257],[0,-306],[-108,-257]],'#4e9d68','#35543f',5);
    for(let j=-2;j<=2;j++)line(g,[[j*49,-258],[j*43,-160]],j%2?'#9dc466':'#84ad60',5);
    poly(g,[[-28,-130],[-28,-203],[28,-203],[28,-130]],'#3c694e','#d8be81',4);
    for(let j=-3;j<=3;j++)line(g,[[j*39,-130],[j*39,-105]],'#b08b5f',7);
  }};
  City.art.boardwalk_stall={box:[310,260,155,235],draw(g,o){
    shadow(g,75);for(let x of [-70,70])line(g,[[x,0],[x,-132]],'#99784d',10);
    poly(g,[[-96,-131],[0,-204],[96,-131],[66,-144],[0,-183],[-66,-144]],o.v?'#7ebc68':'#64ae86','#456b4a',4);
    line(g,[[-86,-59],[88,-59]],'#c6a46a',13);
    for(let j=-2;j<=2;j++)oval(g,j*31,-66,12,7,j%2?'#f0ce69':'#e7a17e');
  }};
  City.art.jaguar_totem={box:[290,320,145,290],draw(g){
    shadow(g,65);poly(g,[[-64,0],[-42,-170],[43,-170],[63,0]],'#7b8c6e','#36534b',4);
    oval(g,0,-183,54,63,'#b1a377');oval(g,-20,-193,10,12,'#28544b');oval(g,20,-193,10,12,'#28544b');
    poly(g,[[-10,-166],[0,-156],[10,-166]],'#42776b','#36534b',3);
    for(let j=-3;j<=3;j++)line(g,[[j*14,-235],[j*19,-279]],'#4ea772',7);
  }};
  City.art.rain_crown_temple={box:[1080,850,540,795],draw(g){
    shadow(g,385);
    // Broad pyramid terraces, hanging waterfalls and a sealed jaguar-mask door.
    for(let level=0;level<5;level++){
      const w=390-level*56,y=-level*94;
      poly(g,[[-w,y],[w,y],[w-33,y-82],[-w+33,y-82]],level%2?'#7b9c70':'#94aa78','#38594f',6);
      for(let j=-4;j<=4;j++)line(g,[[j*w/5,y-8],[j*w/5-9,y-68]],'#4c7860',3);
    }
    for(const side of [-1,1]){
      poly(g,[[side*322,-8],[side*269,-160],[side*249,-160],[side*279,-5]],'#49bcb3','#daefb5',3);
      for(let j=0;j<6;j++)line(g,[[side*(80+j*47),-458],[side*(97+j*50),-319-j%2*25]],'#4b9c65',5);
    }
    poly(g,[[-101,1],[-92,-259],[-57,-312],[0,-348],[59,-312],[94,-259],[101,1]],'#274c4b','#d7ca7b',8);
    oval(g,0,-274,81,86,'#aab376');
    for(const side of [-1,1]){
      poly(g,[[side*19,-294],[side*59,-304],[side*50,-270],[side*22,-264]],'#2a7167','#d9de89',4);
      poly(g,[[side*80,-336],[side*104,-377],[side*85,-358]],'#689b66','#355745',4);
    }
    poly(g,[[-15,-240],[0,-224],[15,-240]],'#58735a','#385849',3);
    line(g,[[-57,-190],[56,-190]],'#c7b776',11);line(g,[[0,-173],[0,0]],'#8caa70',8);
    for(let j=0;j<8;j++){const x=j*69-244;oval(g,x,-469+Math.sin(j)*8,13,12,j%2?'#f4dd88':'#a4e0ad');}
    leaf(g,0,-512,105,46,'#419367');
    for(let j=-4;j<=4;j++)line(g,[[j*64,-493],[j*71,-320]],'#4e9760',4);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.2+.1*Math.sin(t*1.7);for(let j=0;j<17;j++){const x=sx+Math.sin(j*7+t*.3)*340,y=sy-150-((j*63+t*17)%430);oval(g,x,y,2,4,'#d9f9b4');}g.restore();}};
})();
