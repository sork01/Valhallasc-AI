'use strict';
// Asterion's glass-roof homes, lunar obelisks and central astrolabe. Drawn into the normal City.art cache.
(() => {
  const {iso,poly,line,ellipse,prism}=City.kit;
  const rx=62.225,ry=31.112;
  const tint=(hex,n)=>{
    const x=parseInt(hex.slice(1),16), target=n<0?0:255, f=Math.abs(n);
    return '#'+[x>>16,(x>>8)&255,x&255].map(v=>Math.round(v+(target-v)*f).toString(16).padStart(2,'0')).join('');
  };
  const ring=(g,r,z,color,width=2)=>{g.strokeStyle=color;g.lineWidth=width;g.beginPath();g.ellipse(0,-z,r*rx,r*ry,0,0,Math.PI*2);g.stroke();};
  City.art.aetherhouse={
    box:[430,510,215,440],
    draw(g,o){
      const w=o.width||3.3,d=o.depth||3.1,c=o.color||'#b9e4dc';
      g.fillStyle='rgba(35,21,57,.25)';g.beginPath();g.ellipse(12,14,155,66,0,0,Math.PI*2);g.fill();
      prism(g,w,d,110,'#efe7db','#d8d4d2','#b9afba');
      // Four pitched glass petals bloom over the flat stone rooms.
      const peak=iso(0,0,215),nw=iso(-w/2,-d/2,110),ne=iso(w/2,-d/2,110),se=iso(w/2,d/2,110),sw=iso(-w/2,d/2,110);
      poly(g,[nw,ne,peak],tint(c,.32),'#4b536d',3);poly(g,[ne,se,peak],c,'#4b536d',3);
      poly(g,[se,sw,peak],tint(c,-.22),'#4b536d',3);poly(g,[sw,nw,peak],tint(c,.12),'#4b536d',3);
      for(const a of [nw,ne,se,sw])line(g,[a,peak],'rgba(255,247,218,.7)',3);
      for(let row=0;row<2;row++)for(let col=0;col<3;col++){
        const z=42+row*37,x=-w*.28+col*w*.28,p=iso(x,d/2+.02,z);
        poly(g,[[p[0]-12,p[1]-13],[p[0]+12,p[1]-13],[p[0]+12,p[1]+10],[p[0]-12,p[1]+10]],
             '#6c9da8','#e9d9ad',2);line(g,[[p[0],p[1]-13],[p[0],p[1]+10]],'#e9d9ad',1);
      }
      const door=iso(0,d/2+.04,0);
      poly(g,[[door[0]-14,door[1]],[door[0]-14,door[1]-45],[door[0]+14,door[1]-45],[door[0]+14,door[1]]],
           '#433e5f','#ecc998',2);
      g.fillStyle='#f9edc2';g.beginPath();g.arc(door[0]+8,door[1]-20,2,0,Math.PI*2);g.fill();
      for(const side of [-1,1]){
        const p=iso(side*w*.42,d*.38,103);line(g,[[p[0],p[1]],[p[0],p[1]+27]],'#665679',2);
        ellipse(g,p[0],p[1]+33,6,9,'#fff0ae','#aa7e54',1.5);
      }
    }
  };
  City.art.astrolabe={
    box:[780,780,390,640],
    draw(g){
      ellipse(g,0,12,235,112,'#293654','#a3b3c4',5);
      for(let r=1.1;r<3.9;r+=.8)ring(g,r,8,r%2?'#8b96b6':'#c6d5df',4);
      prism(g,1.5,1.5,170,'#ddd9cf','#b9c3ce','#7d8294');
      ellipse(g,0,-184,92,42,'#424b6f','#c8d1df',5);
      ellipse(g,0,-185,44,19,'#f3e6a8','#7769a1',3);
      for(let i=0;i<12;i++){
        const a=i*Math.PI/6,x=Math.cos(a)*194,y=Math.sin(a)*94;
        line(g,[[x,y],[x*.77,y*.77-18]],'#e7d3a3',6);
        ellipse(g,x,y-6,8,9,'#b8eaf0','#7290ad',2);
      }
    },
    animate(g,o,sx,sy,t){
      g.save();g.translate(sx,sy-211);
      for(let j=0;j<3;j++){
        g.save();g.rotate(t*(j%2?-0.17:0.12)+j*.9);g.scale(1,j===1?.48:.75);
        g.strokeStyle=['#a8eff1','#f4d49e','#dfb7f1'][j];g.lineWidth=5-j;
        g.shadowColor=g.strokeStyle;g.shadowBlur=18;g.beginPath();g.ellipse(0,0,72+j*31,72+j*31,0,0,Math.PI*2);g.stroke();
        for(let i=0;i<8;i++){const a=i*Math.PI/4,gx=Math.cos(a)*(72+j*31),gy=Math.sin(a)*(72+j*31);
          g.fillStyle='#fff3ce';g.beginPath();g.arc(gx,gy,4,0,Math.PI*2);g.fill();}
        g.restore();
      }
      g.restore();
    }
  };
  City.art.moonobelisk={
    box:[300,520,150,445],
    draw(g){
      ellipse(g,0,6,75,31,'#34364e','#aab6c6',3);
      prism(g,.95,.95,198,'#dbe4dc','#c2c5d8','#8896ad');
      poly(g,[[-42,-192],[0,-276],[42,-192],[0,-157]],'#b6eef1','#6e829f',4);
      poly(g,[[-24,-195],[0,-253],[24,-195],[0,-176]],'#f4e8b6',null);
      for(let i=0;i<6;i++)ring(g,.26+i*.085,29+i*22,'rgba(112,236,248,.55)',2);
    },
    animate(g,o,sx,sy,t){g.save();g.translate(sx,sy-212);g.globalAlpha=.6+.25*Math.sin(t*2.3);g.fillStyle='#d4faff';
      g.shadowColor='#74e5ff';g.shadowBlur=35;g.beginPath();g.arc(0,-18,19,0,Math.PI*2);g.fill();g.restore();}
  };
  City.art.glasslamp={
    box:[150,280,75,235],
    draw(g){line(g,[[0,0],[0,-133]],'#625676',7);ellipse(g,0,-142,15,19,'#fff2b0','#8a6e86',2);
      poly(g,[[-20,-143],[0,-178],[20,-143],[0,-128]],'#90cfda','#4f6587',2);},
    animate(g,o,sx,sy,t){g.save();g.translate(sx,sy-143);g.fillStyle='#fff2b0';g.globalAlpha=.28+.14*Math.sin(t*2+o.x);
      g.shadowColor='#fff2b0';g.shadowBlur=25;g.beginPath();g.arc(0,0,15,0,Math.PI*2);g.fill();g.restore();}
  };
})();
