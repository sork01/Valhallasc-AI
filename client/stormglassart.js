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
  // A hut on its w x d footprint in the game's 2:1 projection: walls, a gabled roof (ridge along x), a door and windows on the +y wall and a window on the +x wall.
  const hut=(g,o,P)=>{
    const K=City.kit,{iso,poly,prism,wallPlane}=K,w=o.width||4.5,d=o.depth||3.5,z0=8,zt=z0+P.h;
    const fill=(x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,6.2832);g.fillStyle=c;g.fill();};
    fill(0,6,(w+d)*25,(w+d)*10,'rgba(5,16,30,.38)');
    prism(g,w+.3,d+.3,z0,...P.base);
    prism(g,w,d,P.h,...P.wall,z0);
    const onWall=(side,fn)=>{g.save();wallPlane(g,...(side==='y'?iso(0,d/2+.02,z0):iso(w/2+.02,0,z0)),side);fn();g.restore();};
    onWall('y',()=>{
      poly(g,[[-24,0],[-24,-P.h*.74],[24,-P.h*.74],[24,0]],P.door,P.trim,3);
      for(const x of [-w*13,w*13]){fill(x,-P.h*.58,12,15,P.glow);}
    });
    onWall('x',()=>fill(0,-P.h*.58,12,15,P.glow));
    const rw=w+.7,rd=d+.7,rise=P.rise;
    const a=iso(-rw/2,-rd/2,zt),b=iso(rw/2,-rd/2,zt),c=iso(rw/2,rd/2,zt),e=iso(-rw/2,rd/2,zt),r0=iso(-rw/2,0,zt+rise),r1=iso(rw/2,0,zt+rise);
    poly(g,[a,b,r1,r0],P.roof,P.line,3);
    poly(g,[b,c,r1],P.gable,P.line,3);
    poly(g,[r0,r1,c,e],P.roof,P.line,3);
    for(let row=1;row<6;row++){const t=row/6;K.line(g,[iso(-rw/2,rd/2*t,zt+rise*(1-t)),iso(rw/2,rd/2*t,zt+rise*(1-t))],P.course,1.6);}
    K.line(g,[r0,r1],P.ridge||P.line,5);
    return {top:iso(0,0,zt+rise)};
  };
  City.art.breakwater_hut={box:[440,320,220,200],draw(g,o){
    hut(g,o,{h:68,rise:46,base:['#aab7b3','#7d8f95','#617079'],wall:['#8aa3ab','#607985','#4a6370'],door:'#1e3447',trim:'#a2d6d4',glow:'#a6dfe1',roof:'#31495b',gable:'#97b5b7',line:INK,course:'rgba(151,181,183,.3)'});
  }};
  City.art.tide_bell={box:[180,235,90,204],draw(g){
    prism(g,.95,.52,29,'#849da5','#536977','#293e51');
    stroke(g,[[-32,-30],[-32,-83],[32,-83],[32,-30]],'#8399a4',7);
    oval(g,0,-66,17,22,'#c2d6d4');oval(g,0,-62,10,14,'#648c99');
    oval(g,0,-40,5,6,'#e8fbde');
  }};
  City.art.eye_arch={box:[440,390,220,300],draw(g,o){
    // A thick stone gate wall with the eye in its dark doorway (on the +y face) and a lighter crest on top.
    const {iso,wallPlane}=City.kit,w=o.width||6;
    oval(g,0,8,150,38,'rgba(3,12,29,.48)');
    prism(g,w,2,200,'#4d6a80','#344d62','#243847');
    g.save();wallPlane(g,...iso(0,1+.02,0),'y');
    const door=(k,c)=>{g.beginPath();g.moveTo(-90*k,0);g.lineTo(-90*k,-110*k);g.quadraticCurveTo(-90*k,-170*k,0,-176*k);g.quadraticCurveTo(90*k,-170*k,90*k,-110*k);g.lineTo(90*k,0);g.closePath();g.fillStyle=c;g.fill();};
    door(1,'#142039');g.strokeStyle='#7797a2';g.lineWidth=6;g.lineJoin='round';g.stroke();
    oval(g,0,-96,52,66,'#385977');oval(g,0,-96,36,50,'#8dc8d0');oval(g,0,-96,15,40,'#17233d');
    stroke(g,[[-52,-146],[0,-168],[52,-146]],'#c9eeeb',4);
    for(let j=-1;j<=1;j+=2)oval(g,j*70,-60,6,10,'#a8e7e5');
    g.restore();
    prism(g,w-1.4,1.5,32,'#9bb7c0','#7797a2','#58767f',200);
  }};
})();
