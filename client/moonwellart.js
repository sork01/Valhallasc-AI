'use strict';
// Separate garden props: no baked backdrop, so each is independently placed and animated.
(() => {
  const {line,ellipse,poly}=City.kit;
  City.art.moonlily={
    box:[110,110,55,90],
    draw(g,o){
      ellipse(g,0,0,39,16,'#245d69','#102f48',3);
      for(let i=0;i<(o.petals||6);i++){
        const a=i*6.283/(o.petals||6),x=Math.cos(a)*19,y=Math.sin(a)*8-16;
        g.save();g.translate(x,y);g.rotate(a*.38);
        ellipse(g,0,-9,10,20,i%2?'#c7e5d1':'#e2d8ec','#6a799e',2);g.restore();
      }
      ellipse(g,0,-19,9,8,'#f8e8ad','#b3a27a',2);
    },
    animate(g,o,sx,sy,t){g.save();g.globalAlpha=.25+.12*Math.sin(t*1.6+o.x);g.fillStyle='#dcfff1';
      g.shadowColor='#9af2d7';g.shadowBlur=26;g.beginPath();g.ellipse(sx,sy-18,13,10,0,0,6.283);g.fill();g.restore();}
  };
  City.art.moonreed={
    box:[85,180,42,150],
    draw(g){for(let i=-2;i<=2;i++){
      line(g,[[i*8,0],[i*9+4,-55-Math.abs(i)*8],[i*10,-101-Math.abs(i)*9]],i%2?'#79b8b2':'#a8d5cf',3);
      ellipse(g,i*10,-102-Math.abs(i)*9,5,12,'#f8e8ad','#637895',1);
    }},
    animate(g,o,sx,sy,t){g.save();g.globalAlpha=.22+.1*Math.sin(t*2+o.y);g.fillStyle='#f8e8ad';g.shadowColor='#f8e8ad';g.shadowBlur=18;g.beginPath();g.arc(sx,sy-109,6,0,6.283);g.fill();g.restore();}
  };
  City.art.moonmirror={
    box:[185,120,92,95],
    draw(g){ellipse(g,0,2,76,30,'#214f65','#0b2f4a',4);ellipse(g,0,-2,60,20,'#8cb8c4','#4c779b',2);
      poly(g,[[-35,-4],[-10,-13],[20,-7],[47,0],[10,8]],'rgba(244,238,208,.5)');
      for(let i=-2;i<=2;i++)ellipse(g,i*17,10+(i%2)*3,5,2,'#a8e5d9');},
    animate(g,o,sx,sy,t){g.save();g.strokeStyle=`rgba(218,253,239,${.3+.15*Math.sin(t*2+o.x)})`;g.lineWidth=2;
      g.beginPath();g.ellipse(sx,sy,61+4*Math.sin(t*1.3),21,0,0,6.283);g.stroke();g.restore();}
  };
})();
