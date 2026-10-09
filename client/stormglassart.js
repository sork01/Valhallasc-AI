'use strict';
// Black sand, salt-white cliffs and lamps driven into the stormglass shore.
(() => {
  const {poly,prism}=City.kit, TAU=Math.PI*2, INK='#142336';
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const stroke=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineJoin='round';g.stroke();};
  City.art.saltpillar={box:[175,235,88,200],draw(g,o){
    oval(g,0,3,31,9,'rgba(5,17,29,.35)');
    poly(g,[[-21,0],[-15,-75],[-8,-106],[11,-84],[22,0]],o.v%2?'#81959c':'#657d8a',INK);
    poly(g,[[-15,-75],[-8,-106],[11,-84],[0,-51]],'#d0ded9');
    stroke(g,[[0,-51],[4,-24],[15,-8]],'#9fe7e8',2);
  }};
  City.art.blackpebble={box:[105,90,52,73],draw(g,o){
    oval(g,0,3,29,9,'rgba(4,17,28,.25)');
    poly(g,[[-27,0],[-20,-16],[-2,-27],[20,-17],[27,0]],o.v%2?'#283d50':'#344759',INK);
    stroke(g,[[-20,-16],[-2,-27],[3,-3]],'#7997a4',2);
  }};
  City.art.seafoam={box:[105,70,52,54],draw(g,o){
    oval(g,0,0,28,5,'#386e76');
    for(let j=-2;j<=2;j++)oval(g,j*10,-3-(j+o.v)%3,5,2,j%2?'#d5f4e7':'#90d9df');
  }};
  City.art.stormreed={box:[105,160,52,137],draw(g,o){
    for(let j=-2;j<=2;j++){
      const x=j*9,h=30+(j*7+o.v*3+35)%23;
      stroke(g,[[0,0],[x,-h]],'#526f74',3);
      oval(g,x,-h,4,7,j%2?'#b8d7cf':'#83b8bd');
    }
  }};
  City.art.stormglass_spire={box:[175,285,88,250],draw(g){
    oval(g,0,4,36,10,'rgba(5,16,30,.37)');
    poly(g,[[-27,0],[-23,-49],[-7,-118],[5,-86],[23,0]],'#36536b',INK);
    poly(g,[[-7,-118],[5,-86],[23,0],[5,-15]],'#82b5ba');
    stroke(g,[[-4,-105],[3,-54],[14,-21]],'#b7eff0',3);
  }};
  City.art.stormlamp={box:[115,260,57,226],draw(g){
    oval(g,0,4,23,7,'rgba(4,16,29,.32)');
    prism(g,.55,.8,43,'#70899a','#3e566b','#263949');
    stroke(g,[[0,-43],[0,-84]],'#839ca5',5);
    oval(g,0,-98,13,17,'#73bed0');oval(g,0,-98,7,10,'#e3ffed');
  }};
  City.art.breakwater_hut={box:[340,325,170,287],draw(g){
    oval(g,0,5,80,17,'rgba(4,16,27,.42)');
    poly(g,[[-75,0],[-75,-69],[75,-69],[75,0]],'#607985',INK);
    poly(g,[[-88,-68],[-37,-108],[31,-108],[88,-68]],'#31495b',INK);
    poly(g,[[-88,-68],[0,-104],[88,-68]],'#97b5b7');
    poly(g,[[-14,0],[-14,-49],[14,-49],[14,0]],'#1e3447','#a2d6d4');
    oval(g,-46,-43,10,12,'#a6dfe1');oval(g,46,-43,10,12,'#a6dfe1');
  }};
  City.art.tide_bell={box:[180,235,90,204],draw(g){
    prism(g,.95,.52,29,'#849da5','#536977','#293e51');
    stroke(g,[[-32,-30],[-32,-83],[32,-83],[32,-30]],'#8399a4',7);
    oval(g,0,-66,17,22,'#c2d6d4');oval(g,0,-62,10,14,'#648c99');
    oval(g,0,-40,5,6,'#e8fbde');
  }};
  City.art.eye_arch={box:[520,510,260,462],draw(g){
    oval(g,0,8,130,28,'rgba(3,12,29,.48)');
    poly(g,[[-125,0],[-115,-150],[-65,-232],[-30,-205],[-57,-122],[-55,0]],'#344d62',INK);
    poly(g,[[125,0],[115,-150],[65,-232],[30,-205],[57,-122],[55,0]],'#344d62',INK);
    poly(g,[[-66,-225],[-34,-255],[34,-255],[66,-225],[47,-204],[-47,-204]],'#7797a2',INK);
    oval(g,0,-120,51,70,'#142039');oval(g,0,-120,36,55,'#385977');
    oval(g,0,-120,24,43,'#8dc8d0');oval(g,0,-120,11,34,'#17233d');
    stroke(g,[[-45,-192],[0,-216],[45,-192]],'#c9eeeb',4);
    for(let j=-1;j<=1;j++)oval(g,j*55,-151,6,10,'#a8e7e5');
  }};
})();
