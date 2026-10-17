'use strict';
// Three palettes and architectural vocabularies for the Drowned Cathedral's wings.
(() => {
  const { iso, poly, line, ellipse, prism } = City.kit;
  const STYLES = [
    { top:'#b6c3ad', left:'#567b78', right:'#345d61', light:'#88eadb', hue:174, floor:27 },
    { top:'#d3b9bd', left:'#8e6575', right:'#65485e', light:'#ffd1db', hue:329, floor:30 },
    { top:'#9594b6', left:'#4b4669', right:'#2e2d4a', light:'#dbc2ff', hue:253, floor:22 },
  ];
  const isTheme = t => t?.startsWith('cathedral_');
  const style = t => STYLES[t === 'cathedral_right' ? 1 : t === 'cathedral_main' ? 2 : 0];
  const ring = (g,x,y,rx,ry,color,width=2) => { g.beginPath(); g.ellipse(x,y,rx,ry,0,0,Math.PI*2); g.strokeStyle=color; g.lineWidth=width; g.stroke(); };
  const distanceToSegment = (x,y,a,b) => {
    const dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1)));
    return Math.hypot(x-a[0]-t*dx,y-a[1]-t*dy);
  };
  function cloisterSurface(x,y,zone) {
    if (!zone?.paths) return {kind:'water',distance:99};
    const px=x+.5,py=y+.5;
    let distance=Infinity;
    for(const path of zone.paths) for(let i=1;i<path.length;i++)
      distance=Math.min(distance,distanceToSegment(px,py,path[i-1],path[i]));
    const courts=zone.rooms?.slice(0,zone.paths.length+1)||[];
    let altar=Infinity;
    for(const [x0,y0,x1,y1] of courts)
      altar=Math.min(altar,Math.hypot(px-(x0+x1)/2,py-(y0+y1)/2));
    if(altar<6.8) return {kind:'altar',distance:altar};
    if(distance<3.3) return {kind:'walk',distance};
    if(distance<4.5 || (altar>=6.8 && altar<8)) return {kind:'edge',distance:Math.min(distance,altar)};
    return {kind:'water',distance};
  }
  const RELIC_HUES=[43,43,39,321,284,284,17,330,337];
  function reliquarySurface(x,y,zone) {
    if (!zone?.paths) return {kind:'stone',court:0};
    const px=x+.5,py=y+.5;
    let route=Infinity;
    for(const path of zone.paths) for(let i=1;i<path.length;i++)
      route=Math.min(route,distanceToSegment(px,py,path[i-1],path[i]));
    let court=-1,radius=Infinity;
    const count=zone.paths.length+1;
    for(let i=0;i<count;i++) {
      const [x0,y0,x1,y1]=zone.rooms[i],r=Math.hypot(px-(x0+x1)/2,py-(y0+y1)/2);
      if(r<radius){radius=r;court=i;}
    }
    if(radius<5.8) return {kind:'dais',court,radius};
    if(route<3.4) return {kind:'route',court,radius};
    if(radius>6.6 && radius<10.8) return {kind:'pool',court,radius};
    if(radius<11.8 || route<4.5) return {kind:'rim',court,radius};
    return {kind:'stone',court,radius};
  }
  function naveSurface(x,y,zone) {
    if (!zone?.paths) return {kind:'side',court:0,radius:99};
    const px=x+.5,py=y+.5;
    let route=Infinity;
    for(const path of zone.paths) for(let i=1;i<path.length;i++)
      route=Math.min(route,distanceToSegment(px,py,path[i-1],path[i]));
    let court=-1,radius=Infinity;
    for(let i=0;i<zone.paths.length+1;i++) {
      const [x0,y0,x1,y1]=zone.rooms[i],r=Math.hypot(px-(x0+x1)/2,py-(y0+y1)/2);
      if(r<radius){radius=r;court=i;}
    }
    if(court===zone.paths.length && radius<10.5) return {kind:'altar',court,radius};
    if(radius<7.5) return {kind:'court',court,radius};
    if(route<5.1) return {kind:'aisle',court,radius};
    if(route<6.3 || radius<9) return {kind:'border',court,radius};
    return {kind:'side',court,radius};
  }
  function cloisterArch(g,o) {
    const alongX=o.width>=o.depth, length=alongX?o.width:o.depth;
    if(length<2.2) return;
    const span=Math.min(2.25,length*.68), p=(u,z)=>alongX?iso(u,o.depth/2+.02,z):iso(o.width/2+.02,u,z);
    const shape=[p(-span/2,13),p(-span/2,48),p(0,67),p(span/2,48),p(span/2,13)];
    poly(g,shape,'#24494b','#a8c8bd',3);
    const inner=[p(-span*.34,15),p(-span*.34,43),p(0,58),p(span*.34,43),p(span*.34,15)];
    poly(g,inner,'#17383e','rgba(123,203,190,.55)',1.5);
    line(g,[p(-span/2,26),p(span/2,26)],'rgba(132,226,216,.58)',2);
    for(const u of [-span*.31,span*.31]) {
      const c=p(u,19);ellipse(g,c[0],c[1],3,2,'#9fb7a8');
    }
  }
  function reliquaryRelief(g,o) {
    const alongX=o.width>=o.depth,length=alongX?o.width:o.depth;
    if(length<2.2) return;
    const p=(u,z)=>alongX?iso(u,o.depth/2+.03,z):iso(o.width/2+.03,u,z),half=length/2;
    line(g,[p(-half,70),p(half,70)],'#e8c6b6',4);
    line(g,[p(-half,16),p(half,16)],'rgba(255,205,193,.68)',3);
    const branches=[
      [[0,12],[-.34,37],[-.52,62]],[[0,12],[.28,34],[.52,58]],
      [[0,20],[-.1,44],[.06,67]],[[.28,34],[.5,40],[.66,49]],
      [[-.34,37],[-.57,43],[-.69,54]],
    ];
    for(const b of branches) line(g,b.map(([u,z])=>p(u*half,z)),'#e89ca8',4);
    for(const [u,z] of [[-.52,62],[.52,58],[.06,67],[.66,49],[-.69,54]]) {
      const c=p(u*half,z);ellipse(g,c[0],c[1],3.7,3,'#ffd6cf','#aa6a83');
    }
    const pearl=p(0,42);ellipse(g,pearl[0],pearl[1],8,12,'#f6e9cf','#bd93ab');
    ellipse(g,pearl[0]-2,pearl[1]-3,2.3,3.6,'#fffdf0');
  }
  function naveWindow(g,o) {
    const alongX=o.width>=o.depth,length=alongX?o.width:o.depth;
    if(length<2.2) return;
    const span=Math.min(2.55,length*.7),p=(u,z)=>alongX?iso(u,o.depth/2+.03,z):iso(o.width/2+.03,u,z);
    poly(g,[p(-span/2,19),p(-span/2,71),p(0,94),p(span/2,71),p(span/2,19)],'#121b3d','#c3af80',3);
    const colors=['#6a8db3','#9c78bd','#db9b9c'];
    for(let k=0;k<3;k++) {
      const l=-span*.38+k*span*.25,r=l+span*.24;
      poly(g,[p(l,27),p(l,67),p((l+r)/2,80+(k===1?7:0)),p(r,67),p(r,27)],colors[k],'rgba(233,218,176,.63)',1.2);
    }
    line(g,[p(0,21),p(0,86)],'#e1c788',2.4);
    line(g,[p(-span*.39,49),p(span*.39,49)],'#d8c28e',2);
    const gem=p(0,55);ellipse(g,gem[0],gem[1],4.5,6,'#f4e5c4');
  }
  City.art.cathedralwall = {
    box:[440,520,220,410],
    draw(g,o) {
      const s=STYLES[o.v], w=o.width,d=o.depth,h=o.v===2?112:82;
      prism(g,w,d,h,s.top,s.left,s.right);
      for(let z=18;z<h;z+=18) {
        const a=iso(-w/2,d/2,z), b=iso(w/2,d/2,z), c=iso(w/2,-d/2,z);
        line(g,[a,b,c],'rgba(12,20,32,.5)',1.5);
      }
      if(o.v===0) {
        cloisterArch(g,o);
        const alongX=w>=d, p=(u,z)=>alongX?iso(u,d/2+.03,z):iso(w/2+.03,u,z), half=(alongX?w:d)/2;
        line(g,[p(-half,15),p(half,15)],'rgba(116,224,211,.66)',2);
        for(const u of [-half*.58,half*.54]) line(g,[p(u,14),p(u+.12,8)],'rgba(31,105,83,.72)',3);
      }
      if(o.v===1) reliquaryRelief(g,o);
      if(o.v===2) naveWindow(g,o);
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
      if(o.v===0) {
        ring(g,0,-47,18,7,'#a2c2b2',4);ring(g,0,-101,17,7,'#a2c2b2',4);
        line(g,[[-16,-30],[0,-39],[16,-30]],'rgba(114,227,211,.72)',2);
      }
      if(o.v===1) {
        ring(g,0,-45,14,7,'#f1b6c4',5);ring(g,0,-82,14,7,'#f1b6c4',5);
        for(const k of [-1,1]) {
          line(g,[[k*12,-18],[k*23,-49],[k*29,-68]],'#e58ca4',5);
          line(g,[[k*21,-44],[k*37,-51]],'#f4a8b9',3);
          ellipse(g,k*29,-69,3.5,3.5,'#ffd9d2');
        }
        ellipse(g,0,-78,8,11,'#f8e5d4','#b87d9f');
      }
      if(o.v===2) {
        for(const z of [24,66,108,146]) ring(g,0,-z,15,7,'#b9a875',3);
        for(const k of [-1,1]) {
          line(g,[[k*9,-29],[k*14,-80],[k*12,-138]],'#8999ae',3);
          line(g,[[k*13,-110],[k*27,-132],[k*34,-150]],'#c8b27d',2.4);
        }
        ellipse(g,0,-116,7,12,'#bed9e6','#ad9f86');
      }
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
    draw(g,o) {
      prism(g,1.5,.8,28,'#e1c9c5','#9e7189','#674f6c');
      for(const k of [-1,1]) {
        line(g,[[k*34,-15],[k*38,-36],[k*29,-56]],'#e989a2',5);
        line(g,[[k*38,-36],[k*47,-43]],'#f7b8bd',3);
        ellipse(g,k*29,-57,4,4,'#ffe0d2');
      }
      poly(g,[[-39,-29],[-23,-48],[0,-61],[23,-48],[39,-29],[0,-8]],'rgba(157,237,234,.3)','#f6d4d6',2.5);
      ellipse(g,0,-33,12,10,'#fff0d8','#e4a7c2');
      ellipse(g,-3,-37,3.5,3,'#ffffff');
      ring(g,0,-33,19,11,'rgba(255,216,226,.8)',2);
    },
  };
  City.art.navepew = {
    box:[260,260,130,210],
    draw(g) {
      prism(g,1.8,.65,20,'#706b81','#3c3c60','#252840');
      g.save();g.translate(-12,-24);prism(g,1.8,.16,48,'#a8a2ae','#56516d','#34334d');g.restore();
      line(g,[[-44,-66],[40,-25]],'#d9bf88',3);
      for(const x of [-28,0,28]) {ellipse(g,x,-48,5,8,'#788db1','#d9c18e');line(g,[[x,-40],[x,-31]],'#d9c18e',2);}
    },
  };
  function ground(theme,x,y,tone,alt,zone) {
    const s=style(theme);
    if(theme==='cathedral_left') {
      const surface=cloisterSurface(x,y,zone);
      if(surface.kind==='altar') return `hsl(${42+tone*5},24%,${48+tone*5+alt*.5+((x+y)&1?2:-2)}%)`;
      if(surface.kind==='walk') return `hsl(${41+tone*6},18%,${43+tone*5+alt*.5+((x+y)&1?1:-1)}%)`;
      if(surface.kind==='edge') return `hsl(${168+tone*6},27%,${39+tone*6+alt*.5}%)`;
      return `hsl(${190+tone*8},48%,${23+tone*7+alt*.5+((x*3+y)&3)}%)`;
    }
    if(theme==='cathedral_right') {
      const surface=reliquarySurface(x,y,zone),h=RELIC_HUES[surface.court]||329;
      if(surface.kind==='dais') return `hsl(${h+tone*4},30%,${54+tone*4+alt*.5+((x+y)&1?2:-2)}%)`;
      if(surface.kind==='route') return `hsl(${33+tone*5},20%,${48+tone*5+alt*.5+((x+y)&1?1:-1)}%)`;
      if(surface.kind==='pool') return `hsl(${190+tone*8},47%,${26+tone*7+alt*.5+((x+y)&1?1:-1)}%)`;
      if(surface.kind==='rim') return `hsl(${h+tone*5},34%,${43+tone*6+alt*.5}%)`;
      return `hsl(${327+tone*9},22%,${31+tone*8+alt*.5+((x+y)&1?2:-2)}%)`;
    }
    const surface=naveSurface(x,y,zone);
    if(surface.kind==='altar') return `hsl(${surface.radius<4?43:249},${surface.radius<4?43:30}%,${(surface.radius<4?52:38)+tone*4+alt*.5}%)`;
    if(surface.kind==='court') return `hsl(${surface.court%2?222:251},27%,${36+tone*5+alt*.5+((x+y)&1?1:-1)}%)`;
    if(surface.kind==='aisle') return `hsl(${228+tone*5},20%,${39+tone*5+alt*.5+((x+y)&1?2:-1)}%)`;
    if(surface.kind==='border') return `hsl(${41+tone*4},38%,${44+tone*5+alt*.5}%)`;
    return `hsl(${246+tone*8},20%,${21+tone*7+alt*.5+((x+y)&1?2:-1)}%)`;
  }
  function detail(g,theme,px,py,x,y,TW,TH,zone) {
    const s=style(theme);
    if(theme==='cathedral_left') {
      const surface=cloisterSurface(x,y,zone),cy=py+TH/2;
      if(surface.kind==='water') {
        g.strokeStyle='rgba(100,207,202,.24)';g.lineWidth=1;
        g.beginPath();g.moveTo(px-TW/2+4,cy);g.lineTo(px,py+3);g.lineTo(px+TW/2-4,cy);g.stroke();
        if((x*7+y*3)%5===0) {ring(g,px-4,cy+3,17,5,'rgba(158,240,225,.43)',1.4);ring(g,px-4,cy+3,8,2.4,'rgba(208,255,241,.26)',1);}
        if((x*3+y*11)%13===0) {line(g,[[px-10,cy+6],[px+5,cy-1],[px+17,cy+1]],'rgba(213,250,216,.32)',2);}
      } else {
        g.strokeStyle=surface.kind==='edge'?'rgba(167,244,225,.74)':'rgba(63,79,71,.59)';g.lineWidth=surface.kind==='edge'?2.5:1.2;
        g.beginPath();g.moveTo(px-TW/2,cy);g.lineTo(px,py);g.lineTo(px+TW/2,cy);g.stroke();
        if(surface.kind==='altar' && (x+y)%5===0) {
          g.strokeStyle='rgba(237,225,185,.56)';g.lineWidth=2;
          g.beginPath();g.moveTo(px-9,cy);g.lineTo(px+9,cy);g.moveTo(px,cy-7);g.lineTo(px,cy+7);g.stroke();
        }
        if(surface.kind==='walk' && (x*5+y)%7===0) ring(g,px,cy,7,3,'rgba(60,107,103,.46)',1.5);
      }
      return;
    }
    if(theme==='cathedral_right') {
      const surface=reliquarySurface(x,y,zone),cy=py+TH/2;
      g.strokeStyle=surface.kind==='pool'?'rgba(81,198,203,.34)':'rgba(67,36,53,.44)';g.lineWidth=1.2;
      g.beginPath();g.moveTo(px-TW/2,cy);g.lineTo(px,py);g.lineTo(px+TW/2,cy);g.stroke();
      if(surface.kind==='pool') {
        if((x*7+y*3)%4===0) {ring(g,px,cy,15,4,'rgba(145,242,233,.53)',1.5);ring(g,px,cy,7,2,'rgba(223,255,246,.42)',1);}
        if((x+y*2)%11===0) ellipse(g,px-11,cy+4,3,2,'rgba(255,207,218,.69)');
      } else if(surface.kind==='rim') {
        g.strokeStyle='rgba(255,185,197,.55)';g.lineWidth=2;
        g.beginPath();g.moveTo(px-11,cy+6);g.lineTo(px,cy-5);g.lineTo(px+11,cy+6);g.stroke();
        if((x*3+y)%5===0) {
          line(g,[[px-8,cy+3],[px-8,cy-6],[px-15,cy-10]],'#f0a1aa',2.5);
          line(g,[[px-8,cy-5],[px-1,cy-10]],'#f8c7bd',2);
        }
      } else if(surface.kind==='dais') {
        if((x+y)%3===0) {
          ring(g,px,cy,12,6,'rgba(255,235,202,.49)',1.4);
          ellipse(g,px,cy,2.6,2,'#fff4dc');
        }
      } else if(surface.kind==='route' && (x*5+y)%6===0) {
        line(g,[[px-9,cy],[px,cy-6],[px+9,cy]],'rgba(238,209,187,.49)',2);
      } else if(surface.kind==='stone' && (x*7+y)%4===0) {
        g.strokeStyle='rgba(236,148,177,.42)';g.lineWidth=2;
        g.beginPath();g.moveTo(px-10,cy+6);g.lineTo(px-3,cy-4);g.lineTo(px+6,cy+2);g.stroke();
      }
      return;
    }
    if(theme==='cathedral_main') {
      const surface=naveSurface(x,y,zone),cy=py+TH/2;
      g.strokeStyle=surface.kind==='side'?'rgba(96,108,146,.36)':'rgba(9,15,36,.55)';g.lineWidth=1.3;
      g.beginPath();g.moveTo(px-TW/2,cy);g.lineTo(px,py);g.lineTo(px+TW/2,cy);g.stroke();
      if(surface.kind==='altar') {
        if(surface.radius>3.3) {
          g.strokeStyle='rgba(230,207,147,.74)';g.lineWidth=2.5;
          g.beginPath();g.moveTo(px-13,cy);g.lineTo(px,cy-8);g.lineTo(px+13,cy);g.moveTo(px,cy-8);g.lineTo(px,cy+9);g.stroke();
        } else {
          ring(g,px,cy,15,7,'rgba(255,237,190,.65)',2);
          ellipse(g,px,cy,3.5,3,'#fff4cf');
        }
      } else if(surface.kind==='court' && (x*3+y)%5===0) {
        ring(g,px,cy,9,4,'rgba(177,202,236,.35)',1.5);
      } else if(surface.kind==='aisle' && (x+y)%4===0) {
        line(g,[[px-12,cy+4],[px,cy-4],[px+12,cy+4]],'rgba(196,207,230,.36)',2);
      } else if(surface.kind==='border') {
        line(g,[[px-13,cy],[px,cy-8],[px+13,cy]],'rgba(238,210,150,.66)',2.3);
      } else if((x*7+y*3)%11===0) {
        g.strokeStyle='rgba(157,169,210,.27)';g.lineWidth=1.3;
        g.beginPath();g.moveTo(px-6,cy);g.lineTo(px+6,cy);g.moveTo(px,cy-5);g.lineTo(px,cy+5);g.stroke();
      }
      return;
    }
    g.strokeStyle='rgba(7,12,25,.5)';g.lineWidth=1;
    g.beginPath();g.moveTo(px-TW/2,py+TH/2);g.lineTo(px,py);g.lineTo(px+TW/2,py+TH/2);g.stroke();
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
