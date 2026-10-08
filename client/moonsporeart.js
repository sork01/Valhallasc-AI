'use strict';
// Fallen-moon forest scenery: luminous gills, slate roots, and a safe lamp court.
(() => {
  const {poly,prism}=City.kit,TAU=Math.PI*2,INK='#182b30';
  const oval=(g,x,y,rx,ry,fill)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=fill;g.fill();};
  const stroke=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineJoin='round';g.stroke();};
  City.art.mooncaps={box:[190,260,95,225],draw(g,o){
    oval(g,0,2,42,11,'rgba(4,18,24,.36)');
    for(let j=-1;j<=1;j++){
      const x=j*23,h=58+(j+1)*10;
      poly(g,[[x-7,0],[x-5,-h],[x+5,-h],[x+8,0]],'#62736e',INK);
      oval(g,x,-h,26,11,o.v%2?'#a3dec6':'#bee9ad');
      oval(g,x,-h+4,21,5,'#4b7279');
      for(let k=-2;k<=2;k++)stroke(g,[[x+k*7,-h+4],[x+k*5,-h+8]],'#d7f9cf',1);
    }
  }};
  City.art.gloomstalk={box:[185,360,92,310],draw(g,o){
    oval(g,0,4,32,8,'rgba(3,20,22,.28)');
    poly(g,[[-12,0],[-8,-79],[-22,-106],[-15,-136],[0,-113],[14,-140],[23,-110],[9,-72],[13,0]],'#45594f',INK);
    stroke(g,[[-2,-8],[1,-108]],'#84997b',3);
    for(let j=-2;j<=2;j++){
      const x=j*12,y=-85+(j%2)*12;
      oval(g,x,y,9,4,o.v%2?'#87bdad':'#adb9a3');
    }
  }};
  City.art.moonstone={box:[145,155,73,128],draw(g,o){
    oval(g,0,3,28,7,'rgba(6,18,24,.27)');
    poly(g,[[-23,0],[-19,-23],[-2,-46],[20,-19],[25,0]],o.v%2?'#7a8a8f':'#62797f',INK);
    poly(g,[[-19,-23],[-2,-46],[3,-4],[-23,0]],'#acbbc0',null);
    stroke(g,[[-2,-46],[3,-4]],'#d4f3cd',2);
  }};
  City.art.sporefern={box:[100,150,50,130],draw(g,o){
    for(let j=-2;j<=2;j++){
      const x=j*8,h=17+(j*7+o.v*3+20)%15;
      stroke(g,[[0,0],[x,-h]],'#587564',2);
      oval(g,x-4,-h+4,6,3,'#83bd9e');oval(g,x+4,-h-1,6,3,'#bce5ba');
    }
  }};
  City.art.glowmoss={box:[90,70,45,55],draw(g,o){
    oval(g,0,0,20,7,'#315647');for(let j=0;j<7;j++)oval(g,(j-3)*5,-3-(j+o.v)%4,2,2,j%2?'#c5f4ae':'#8fddb4');
  }};
  City.art.sporelamp={box:[110,260,55,220],draw(g){
    oval(g,0,3,24,7,'rgba(5,25,25,.32)');
    prism(g,.65,.9,45,'#778e80','#465e5c','#2a4a4c');
    stroke(g,[[0,-48],[0,-84]],'#7b8c7e',4);
    oval(g,0,-94,14,14,'#c9f5ba');oval(g,0,-94,8,8,'#ecffe0');
  }};
  City.art.lamphouse={box:[310,360,155,315],draw(g){
    oval(g,0,5,73,17,'rgba(4,21,20,.4)');
    poly(g,[[-65,0],[-65,-73],[65,-73],[65,0]],'#566660',INK);
    poly(g,[[-76,-70],[-34,-118],[32,-118],[78,-70]],'#547469',INK);
    poly(g,[[-76,-70],[0,-110],[78,-70]],'#9ac3a7',null);
    poly(g,[[-13,0],[-13,-54],[13,-54],[13,0]],'#243b40','#aac7b1');
    oval(g,-43,-42,12,15,'#d8f5b8');oval(g,43,-42,12,15,'#d8f5b8');
  }};
  City.art.moonwell={box:[150,170,75,145],draw(g){
    oval(g,0,3,33,10,'rgba(4,21,20,.3)');
    prism(g,.9,.48,28,'#899e8f','#5e7770','#2d5152');
    oval(g,0,-30,25,10,'#b7d8b9');oval(g,0,-30,18,6,'#3a767b');
    oval(g,0,-31,9,4,'#c4f5c2');
  }};
  City.art.moonaltar={box:[230,320,115,275],draw(g){
    oval(g,0,5,41,11,'rgba(5,21,23,.4)');
    prism(g,1.1,.65,30,'#7e8e87','#4f6968','#2e5055');
    poly(g,[[-24,-36],[-11,-95],[0,-121],[12,-92],[24,-36]],'#94ab9d',INK);
    oval(g,0,-97,10,15,'#d6f3af');oval(g,0,-97,5,8,'#fffddd');
  }};
})();
