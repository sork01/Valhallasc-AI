'use strict';
// Three palettes and architectural vocabularies for the Drowned Cathedral's wings.
(() => {
  const { iso, poly, line, ellipse, prism } = City.kit;
  const STYLES = [
    { top:'#7ba4a0', left:'#386c69', right:'#284d54', light:'#75ead9', hue:174, floor:27 },
    { top:'#c2a8b6', left:'#795565', right:'#543b54', light:'#ffb0d4', hue:329, floor:30 },
    { top:'#9594b6', left:'#4b4669', right:'#2e2d4a', light:'#dbc2ff', hue:253, floor:22 },
  ];
  const isTheme = t => t?.startsWith('cathedral_');
  const style = t => STYLES[t === 'cathedral_right' ? 1 : t === 'cathedral_main' ? 2 : 0];
  const ring = (g,x,y,rx,ry,color,width=2) => { g.beginPath(); g.ellipse(x,y,rx,ry,0,0,Math.PI*2); g.strokeStyle=color; g.lineWidth=width; g.stroke(); };
  City.art.cathedralwall = {
    box:[440,520,220,410],
    draw(g,o) {
      const s=STYLES[o.v], w=o.width,d=o.depth,h=o.v===2?112:82;
      prism(g,w,d,h,s.top,s.left,s.right);
      for(let z=18;z<h;z+=18) {
        const a=iso(-w/2,d/2,z), b=iso(w/2,d/2,z), c=iso(w/2,-d/2,z);
        line(g,[a,b,c],'rgba(12,20,32,.5)',1.5);
      }
      if(o.v===1) {
        for(let k=0;k<3;k++) { const a=iso((k-1)*w/4,d/2,35); line(g,[a,[a[0]+4,a[1]-28],[a[0]+14,a[1]-44]],'#d381a0',3); }
      }
      if(o.v===2) { const a=iso(0,d/2,58); ring(g,a[0],a[1],12,18,'#c0b082'); }
    },
  };
  City.art.cathedralcolumn = {
    box:[200,300,100,250],
    draw(g,o) {
      const s=STYLES[o.v], h=o.v===2?164:119;
      prism(g,1.3,1.3,12,s.top,s.left,s.right);
      prism(g,.62,.62,h,s.top,s.left,s.right);
      g.save();g.translate(0,-h);prism(g,1.1,1.1,12,s.top,s.left,s.right);g.restore();
      if(o.v===0) for(let k=0;k<4;k++) { line(g,[[-12+k*6,-28],[Math.sin(k)*12,-62],[Math.cos(k)*13,-96]],'#2d8f71',3); }
      if(o.v===1) { ring(g,0,-45,14,7,'#ecabc8');ring(g,0,-82,14,7,'#ecabc8'); }
      if(o.v===2) { ring(g,0,-90,12,16,'#d3bd7c');line(g,[[0,-76],[0,-104]],'#d3bd7c',2); }
    },
  };
  City.art.cathedrallamp = {
    box:[180,230,90,180],
    draw(g,o) { const s=STYLES[o.v]; prism(g,.35,.35,65,s.top,s.left,s.right); ring(g,0,-72,13,17,s.light,4); ellipse(g,0,-72,5,9,s.light); },
    animate(g,o,t) { const s=STYLES[o.v];g.save();g.shadowColor=s.light;g.shadowBlur=12+3*Math.sin(t*2);ellipse(g,0,-72,4,7,s.light);g.restore(); },
  };
  City.art.cloisterbed = {
    box:[260,230,130,180],
    draw(g,o) { prism(g,1.5,1,12,'#427e75','#28564e','#193f40');for(let k=0;k<7;k++)line(g,[[(k-3)*10,0],[Math.sin(k)*30,-25],[Math.sin(k+o.v)*35,-56-k*3]],k%2?'#419e73':'#64b592',4); },
  };
  City.art.reliccase = {
    box:[260,230,130,180],
    draw(g,o) { prism(g,1.5,.8,28,'#d7bfd2','#9b6c86','#684859');poly(g,[[-42,-30],[0,-50],[42,-30],[0,-10]],'rgba(180,225,244,.35)','#d6b4ce',2);ellipse(g,0,-32,10,6,'#ffe4bd');ring(g,0,-32,16,8,'#ffb9d6'); },
  };
  City.art.navepew = {
    box:[260,260,130,210],
    draw(g) { prism(g,1.8,.65,20,'#77708b','#494057','#302c43');g.save();g.translate(-12,-24);prism(g,1.8,.16,42,'#bdb3a0','#6d6272','#493f59');g.restore();line(g,[[-42,-65],[40,-23]],'#d1b987',2); },
  };
  function ground(theme,x,y,tone,alt) {
    const s=style(theme);
    if(theme==='cathedral_left') return `hsl(${174+tone*12},28%,${s.floor+tone*9+alt*.6}%)`;
    if(theme==='cathedral_right') return `hsl(${323+tone*12},19%,${s.floor+tone*9+((x+y)&1?3:-3)}%)`;
    return `hsl(${248+tone*10},18%,${s.floor+tone*6+((x+y)&1?4:-2)}%)`;
  }
  function detail(g,theme,px,py,x,y,TW,TH) {
    const s=style(theme);
    g.strokeStyle='rgba(7,12,25,.5)';g.lineWidth=1;
    g.beginPath();g.moveTo(px-TW/2,py+TH/2);g.lineTo(px,py);g.lineTo(px+TW/2,py+TH/2);g.stroke();
    if(theme==='cathedral_left' && (x*7+y*3)%9===0) { ellipse(g,px,py+TH/2,18,6,'rgba(92,218,193,.12)');ring(g,px,py+TH/2,14,4,'rgba(135,245,218,.23)',1); }
    if(theme==='cathedral_right' && (x+y)%3===0) poly(g,[[px,py+7],[px+10,py+TH/2],[px,py+TH-7],[px-10,py+TH/2]],'rgba(231,182,204,.22)',s.light,1);
    if(theme==='cathedral_main' && (x*3+y)%7===0) { line(g,[[px-8,py+TH/2],[px+8,py+TH/2]],'#ae996955',1.5);line(g,[[px,py+TH/2-6],[px,py+TH/2+6]],'#ae996955',1.5); }
  }
  function weather(g,theme,t,w,h) {
    const s=style(theme);g.save();g.globalAlpha=.11;g.fillStyle=s.light;
    for(let k=0;k<9;k++) { const x=(k*193+Math.sin(t*.25+k)*60)%w;poly(g,[[x,0],[x+45,0],[x+280,h],[x+120,h]],s.light); }
    g.globalAlpha=.3;for(let k=0;k<28;k++) { const x=(k*137+t*(theme==='cathedral_right'?5:2))%w,y=(h+k*79-t*(theme==='cathedral_left'?14:5))%h;ring(g,x,y,k%3+1,k%3+1,s.light,1); }g.restore();
  }
  function portal(g,p,sx,sy,t,dest) {
    const s=style(dest.theme);
    g.save();g.translate(sx,sy);
    poly(g,[[-48,0],[-48,-75],[-30,-118],[0,-144],[30,-118],[48,-75],[48,0]],s.left,s.top,5);
    const grd=g.createRadialGradient(0,-56,3,0,-56,57);grd.addColorStop(0,s.light);grd.addColorStop(1,'#102c45');
    ellipse(g,0,-55,34,58,grd);ring(g,0,-55,26+Math.sin(t*2)*3,46,s.light,2);
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#0b1228';g.lineWidth=4;g.fillStyle=s.light;
    const label=p.name;g.strokeText(label,0,-157);g.fillText(label,0,-157);g.restore();
  }
  window.CathedralArt={isTheme,style,ground,detail,weather,portal};
})();
