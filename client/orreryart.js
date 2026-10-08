'use strict';
// The Orrery's broken rings, dark glass spires and stillpoint shelter.
(() => {
  const {poly,prism}=City.kit,TAU=Math.PI*2,INK='#202130';
  const oval=(g,x,y,rx,ry,fill)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=fill;g.fill();};
  const stroke=(g,p,c,w=3)=>{g.beginPath();p.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineJoin='round';g.stroke();};
  City.art.clockwall={box:[220,300,110,265],draw(g,o){
    oval(g,0,5,42,12,'rgba(9,12,22,.38)');
    prism(g,1.3,1.4,67,'#696371','#444559','#272c3d');
    oval(g,0,-71,25,11,'#bd9264');oval(g,0,-71,16,7,'#403848');
    for(let k=0;k<4;k++)poly(g,[[-32+k*19,-110],[-27+k*19,-122],[-22+k*19,-110]],o.v%2?'#d0aa76':'#a3a0b3',INK);
  }};
  City.art.blackspire={box:[200,330,100,290],draw(g,o){
    oval(g,0,4,33,9,'rgba(7,10,22,.34)');
    poly(g,[[-31,0],[-23,-76],[-2,-134],[21,-79],[31,0]],'#2b3548',INK);
    poly(g,[[-23,-76],[-2,-134],[1,-9],[-31,0]],'#697184',null);
    poly(g,[[21,-79],[31,0],[1,-9],[-2,-134]],o.v%2?'#8d6d79':'#4f6072',null);
    stroke(g,[[-2,-134],[1,-9]],'#e2bc8a',2);
  }};
  City.art.cogstone={box:[150,170,75,140],draw(g,o){
    oval(g,0,3,28,8,'rgba(9,12,22,.3)');
    poly(g,[[-27,-3],[-23,-24],[-6,-35],[20,-26],[29,-4],[7,2]],'#5a596b',INK);
    oval(g,3,-17,11,8,'#c69b6b');oval(g,3,-17,5,4,'#404358');
    if(o.v%2)stroke(g,[[-16,-7],[16,-28]],'#e2c69b',2);
  }};
  City.art.timegrass={box:[120,160,60,130],draw(g,o){
    oval(g,0,2,22,5,'rgba(9,12,22,.2)');
    for(let k=0;k<7;k++){const x=(k-3)*5,h=13+(k*7+o.v*3)%17;
      stroke(g,[[x,0],[x+(k%3-1)*5,-h]],'#777d83',2);
      oval(g,x+(k%3-1)*5,-h,2,2,k%2?'#e8bd7a':'#c9d9d3');}
  }};
  City.art.hourpillar={box:[220,330,110,280],draw(g){
    oval(g,0,4,36,12,'rgba(9,12,22,.4)');
    prism(g,1.1,1.1,80,'#9f948a','#665d68','#394255');
    oval(g,0,-86,24,24,'#d0ae78');oval(g,0,-86,18,18,'#4d4856');
    stroke(g,[[0,-86],[0,-100]],'#e8d7ac',3);stroke(g,[[0,-86],[12,-79]],'#e8d7ac',2);
  }};
  City.art.epoch_crown={box:[400,390,200,350],draw(g){
    oval(g,0,10,85,23,'rgba(8,9,20,.48)');
    for(let k=0;k<9;k++){const a=k*TAU/9,x=Math.cos(a)*60,y=Math.sin(a)*24;
      poly(g,[[x-9,y-9],[x,y-28],[x+9,y-9]],k%2?'#d7a873':'#9b9aaa',INK);}
    oval(g,0,-14,37,18,'#483d4b');oval(g,0,-14,27,13,'#cfab79');
  }};
  City.art.stillpoint={box:[560,410,280,335],draw(g,o){
    oval(g,0,12,126,27,'rgba(7,10,22,.37)');
    prism(g,o.width,o.depth,12,'#8f887f','#6c6872','#46475b');
    for(const x of [-102,102])stroke(g,[[x,2],[x,-130]],'#5d4d49',8);
    poly(g,[[-122,-132],[0,-194],[122,-132],[0,-72]],'#cbb183',INK);
    poly(g,[[0,-194],[122,-132],[0,-72]],'#8f6971',null);
    oval(g,0,-83,15,10,'#f8d99a');
  }};
})();
