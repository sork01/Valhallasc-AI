'use strict';
// Nacrehold's original canvas art: shell homes, nautilus inn, tide palace and the sealed Cathedral.
(() => {
  const { iso, prism, poly, wallPlane } = City.kit;
  const OUT = '#133d55';
  const ellipse = (g, x, y, rx, ry, c, stroke = OUT) => {
    g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); g.fillStyle = c; g.fill();
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = 2; g.stroke(); }
  };
  const line = (g, pts, c, w = 2) => { g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(...p) : g.moveTo(...p)); g.strokeStyle = c; g.lineWidth = w; g.stroke(); };
  function shell(g, x, y, rx, ry, color, variant = 0) {
    const gr = g.createLinearGradient(x - rx, y - ry, x + rx, y);
    gr.addColorStop(0, '#f7f6e4'); gr.addColorStop(.35, color); gr.addColorStop(1, '#506c94');
    g.fillStyle = gr; g.strokeStyle = OUT; g.lineWidth = 3;
    g.beginPath(); g.moveTo(x - rx, y); g.bezierCurveTo(x - rx * 1.15, y - ry * .75, x - rx * .5, y - ry * 1.12, x, y - ry);
    g.bezierCurveTo(x + rx * .75, y - ry * 1.08, x + rx * 1.15, y - ry * .65, x + rx, y);
    g.quadraticCurveTo(x, y + ry * .25, x - rx, y); g.closePath(); g.fill(); g.stroke();
    for (let i = -4; i <= 4; i++) {
      const f = i / 4, tx = x + rx * f * .88, ty = y - ry * Math.sqrt(1 - f * f * .8);
      g.beginPath(); g.moveTo(x + f * rx * .5, y + ry * .04); g.quadraticCurveTo(x + f * rx * .8, y - ry * .55, tx, ty);
      g.strokeStyle = 'rgba(25,58,80,.35)'; g.lineWidth = 4; g.stroke();
      g.strokeStyle = 'rgba(255,250,245,.55)'; g.lineWidth = 1.5; g.stroke();
      if (variant % 2) ellipse(g, tx, ty + 8, 3, 3, '#fbf7dd', null);
    }
    if (variant === 3) { // a spiral shell ridge
      const pts = []; for (let a = 0; a < 14; a += .15) { const r = 3 + a * 2; pts.push([x + Math.cos(a) * r, y - ry * .53 + Math.sin(a) * r * .7]); }
      line(g, pts, 'rgba(255,255,255,.6)', 2);
    }
  }
  const tone=(hex,k)=>'#'+[1,3,5].map(i=>Math.round(parseInt(hex.slice(i,i+2),16)*k).toString(16).padStart(2,'0')).join('');
  // A ribbed barrel-shell roof: every point uses the same world axes as the walls.
  function shellRoof(g,w,d,z,rise,color,variant=0){
    const n=24,front=d/2,back=-d/2,point=(i,y)=>{const a=Math.PI*i/n;return iso(-w/2*Math.cos(a),y,z+rise*Math.sin(a));};
    // The curved surface is extruded through the actual building depth.
    for(let i=0;i<n;i++)poly(g,[point(i,back),point(i+1,back),point(i+1,front),point(i,front)],tone(color,.68+.27*Math.sin(Math.PI*(i+.5)/n)),OUT,1);
    const hinge=iso(0,front,z);
    for(let i=0;i<n;i++)poly(g,[hinge,point(i,front),point(i+1,front)],tone(color,.81+(i%3)*.075),OUT,1);
    for(let i=0;i<=n;i+=2)line(g,[hinge,point(i,front)],i%4?'#f5f2df':'#6b8e9c',1.6);
    line(g,Array.from({length:n+1},(_,i)=>point(i,front)),'#e5eee1',3);
    // The front lip overlaps the wall top, rather than hovering above its ceiling.
    poly(g,[iso(-w/2,front,z),iso(w/2,front,z),iso(w/2,front,z-5),iso(-w/2,front,z-5)],'#a3bfc0',OUT,1.5);
    if(variant===3){
      g.save();wallPlane(g,...iso(0,front,z+rise*.43));const pts=[];
      for(let a=0;a<14;a+=.15){const r=1+a*1.5;pts.push([Math.cos(a)*r,Math.sin(a)*r*.8]);}line(g,pts,'#f4e8cf',2);g.restore();
    }
  }
  function column(g,x,y,z,h,color,cap=true){
    const sides=12,ring=(r,height)=>Array.from({length:sides},(_,i)=>iso(x+Math.cos(i*Math.PI*2/sides)*r,y+Math.sin(i*Math.PI*2/sides)*r,height));
    const drum=(r0,r1,low,high)=>{
      const a=ring(r0,low),b=ring(r1,high),faces=[];
      for(let i=0;i<sides;i++){const j=(i+1)%sides,angle=(i+.5)*Math.PI*2/sides;if(Math.cos(angle)+Math.sin(angle)>0)faces.push({i,j,depth:Math.cos(angle)+Math.sin(angle)});}
      faces.sort((a,b)=>a.depth-b.depth);for(const {i,j}of faces)poly(g,[a[i],a[j],b[j],b[i]],tone(color,.68+.22*Math.sin((i+.5)*Math.PI*2/sides)),OUT,1.4);
      poly(g,b,'#e0eee4',OUT,1.5);
    };
    drum(.43,.43,z,z+9);drum(.27,.19,z+9,z+h-9);drum(.38,.38,z+h-9,z+h);
    for(const angle of [0,Math.PI/4,Math.PI/2])line(g,[iso(x+Math.cos(angle)*.27,y+Math.sin(angle)*.27,z+12),iso(x+Math.cos(angle)*.19,y+Math.sin(angle)*.19,z+h-12)],'#eef8e7',1.5);
    if(cap){g.save();g.translate(...iso(x,y));shellRoof(g,.9,.72,z+h,37,color,1);g.restore();}
  }
  function windowAt(g, x, y, r = 13, side = 'y') {
    g.save();wallPlane(g,x,y,side);
    ellipse(g, 0, 0, r, r * 1.15, '#256781');
    ellipse(g, -1, -1, r * .74, r * .9, '#b6f4dd', '#6999a0');
    line(g, [[0, -r], [0, r]], '#ebeee0');
    line(g, [[-r, 0], [r, 0]], '#ebeee0');g.restore();
  }
  function home(g, o, grand = false) {
    const w = o.width, d = o.depth, h = grand ? 150 : 90, color = o.color || '#9bd5df';
    const rx = (w + d) * 22 + 8;
    ellipse(g, 5, 10, rx, rx * .3, 'rgba(4,29,50,.25)', null);
    prism(g, w + .2, d + .2, 10, '#dcebe2', '#82aaa9', '#54818e');
    prism(g, w, d, h, '#d0e4e1', '#c1ddd6', '#80b4bd', 10);
    shellRoof(g,w+.28,d+.28,h+10,grand?132:80+o.v*8,color,o.v);
    for (const side of [0, 1]) {
      const pt = side ? iso(w / 2 + .01, -.55, 65) : iso(-.8, d / 2 + .01, 65);
      windowAt(g, ...pt, grand ? 19 : 13, side ? 'x' : 'y');
    }
    const p = iso(.35, d / 2 + .03, 24);
    g.save();wallPlane(g,...p);
    ellipse(g, 0, -11, 17, 29, '#194958', '#ecedd2');
    ellipse(g, 7, -8, 2.5, 2.5, '#f8daa1', null);
    line(g, [[-12, 19], [13, 19]], '#f0eee0', 4);g.restore();
    // Coral growing from the house's far corner; three shapes share cached sprites.
    const c = iso(-w / 2, d / 2, 13);
    for (let i = 0; i < 3; i++) {
      const tx = c[0] + (i - 1) * 9, ty = c[1] - 24 - i * 5;
      line(g, [[c[0], c[1]], [tx, ty]], '#548aa0', 5);
      ellipse(g, tx, ty, 4, 5, color, null);
    }
  }
  City.art.nacrehouse = { box: [660, 580, 330, 440], draw: (g, o) => home(g, o) };
  City.art.nacreinn = { box: [850, 740, 425, 590], draw(g, o) {
    home(g, { ...o, color: '#dda8ca', v: 3 }, true);
    line(g, [[-12, -43], [-12, -82], [32, -82]], '#eef4df', 3);
    ellipse(g, 33, -79, 21, 18, '#eccda1');
    const pts = []; for (let a = 0; a < 15; a += .2) { const r = 1 + a; pts.push([33 + Math.cos(a) * r, -79 + Math.sin(a) * r * .8]); } line(g, pts, '#6c6890', 2);
  } };
  City.art.nacrestall = { box: [420, 420, 210, 320], draw(g, o) {
    prism(g, o.width, o.depth, 50, '#e4e8d6', '#b8cacc', '#719da9');
    for(const x of [-o.width/2,o.width/2]){g.save();g.translate(...iso(x,o.depth/2));prism(g,.14,.14,130,'#e1f0e6','#b8d4d1','#78a5b0');g.restore();}
    shellRoof(g,o.width+.45,o.depth+.45,130,55,o.color,1);
    for (let i = 0; i < 5; i++) ellipse(g, -48 + i * 23, -49 - Math.abs(i - 2) * 4, 9, 6, ['#eee6c9', '#cb9aba', '#96dfbe'][i % 3]);
  } };
  City.art.nacrepalace = { box: [1180, 1040, 590, 850], draw(g, o) {
    home(g, { ...o, color: '#afd9e5', v: 1 }, true);
    for(const x of [-o.width/2+.15,o.width/2-.15])column(g,x,o.depth/2+.12,10,210,'#b9d9df');
    ellipse(g, ...iso(0,0,316), 24, 24, '#e3fff4', '#96babc');
  } };
  City.art.nacrearchive = { box: [880, 700, 440, 540], draw(g, o) {
    home(g, { ...o, color: '#b0b4ed', v: 2 }, true);
    for (let i = 0; i < 3; i++) windowAt(g, ...iso(o.width / 2 + .02, -.8 + i * .65, 125), 6, 'x');
  } };
  City.art.nacregarden = { box: [640, 470, 320, 360], draw(g) {
    ellipse(g, 0, -12, 170, 64, '#397e7b', '#b1dacc');
    const posts=Array.from({length:9},(_,i)=>({x:Math.cos(i*2.4)*2,y:Math.sin(i*2.4)*2,i})).sort((a,b)=>a.x+a.y-b.x-b.y);
    for(const {x,y,i}of posts)column(g,x,y,12,30+i%3*12,['#e5a5ca','#95d9cd','#beb8e5'][i%3]);
  }, animate(g, o, sx, sy, t) {
    g.save(); g.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 12; i++) { const x = sx + Math.cos(t * .25 + i * 2.3) * 122, y = sy - 45 + Math.sin(t * .38 + i) * 42; ellipse(g, x, y, 3, 2, '#aaffdd', null); }
    g.restore();
  } };
  City.art.nacrememorial = { box: [420, 480, 210, 370], draw(g) {
    prism(g, 2.3, 1.7, 16, '#e0dfd3', '#98b7b5', '#668c9c');
    g.save();wallPlane(g,...iso(0,.65,16));shell(g,0,-20,65,160,'#c5bde2',2);
    for(let i=0;i<4;i++)line(g,[[-20,-90-i*14],[22,-90-i*14]],'#e7f1e1',2);g.restore();
  } };
  City.art.nacrefountain = { box: [780, 900, 390, 720], draw(g) {
    ellipse(g, 0, -12, 174, 67, '#d7ede0'); ellipse(g, 0, -18, 151, 52, '#41959e');
    column(g,0,0,10,165,'#c5dce0',false);
    shellRoof(g,2.4,1.8,175,84,'#a4dbd6',1);
    ellipse(g, 0, -282, 23, 23, '#dffff0', '#9dbbb8');
  }, animate(g, o, sx, sy, t) {
    g.save(); g.globalCompositeOperation = 'lighter';
    const halo = g.createRadialGradient(sx, sy - 282, 5, sx, sy - 282, 110); halo.addColorStop(0, 'rgba(190,255,230,.35)'); halo.addColorStop(1, 'rgba(80,240,220,0)'); g.fillStyle = halo; g.fillRect(sx - 110, sy - 392, 220, 220);
    for (let i = 0; i < 14; i++) { const f = (t * .14 + i / 14) % 1, x = sx + Math.sin(i * 2.4 + f * 3) * 68, y = sy - 18 - f * 250; g.globalAlpha = Math.sin(f * Math.PI) * .6; ellipse(g, x, y, 3 + f * 3, 3 + f * 3, 'rgba(160,255,240,.1)', '#c4fff0'); }
    g.restore();
  } };
  City.art.nacrecathedral = { box: [1200, 1180, 600, 980], draw(g, o) {
    const w = o.width, d = o.depth;
    ellipse(g, 0, 6, 264, 84, 'rgba(2,15,38,.5)', null);
    prism(g, w + .3, d + .3, 18, '#adb7c5', '#668493', '#3e5d78');
    prism(g, w, d, 175, '#647a9b', '#69869c', '#405779', 18);
    shellRoof(g,w+.3,d+.3,193,165,'#9996be',2);
    for(const x of [-w/2+.15,w/2-.15])column(g,x,d/2+.12,18,280,'#a6bbd0');
    // Huge locked arch. The seal is visible, and the NPC states that the instance is forthcoming.
    const p = iso(0, d / 2 + .02, 0);
    g.save();wallPlane(g,...p);
    ellipse(g, 0, -93, 64, 105, '#09192f', '#b0c5ce');
    for (let i = -2; i <= 2; i++) line(g, [[i * 22, -173], [i * 22, -10]], '#6aa7b5', 4);
    ellipse(g, 0, -80, 37, 37, '#1a465e', '#8eefe2');
    poly(g, [[0, -111], [21, -80], [0, -49], [-21, -80]], '#8fe7dc', OUT, 2);g.restore();
    // Silent bell in the rose window.
    g.save();wallPlane(g,...iso(0,(d+.3)/2,193+165*.58));
    ellipse(g,0,0,34,34,'#21446b','#bdd0d9');
    line(g,[[0,-29],[0,29]],'#8dbbc7',3);line(g,[[-29,0],[29,0]],'#8dbbc7',3);g.restore();
  }, animate(g, o, sx, sy, t) {
    const p = iso(0, o.depth / 2 + .02, 0);
    g.save();wallPlane(g,sx + p[0],sy + p[1]); g.globalAlpha = .6 + Math.sin(t * .8) * .15; g.strokeStyle = '#a0fff1'; g.lineWidth = 2;
    g.beginPath(); g.arc(0, -80, 42, 0, Math.PI * 2); g.stroke(); g.restore();
    g.font = '17px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 5; g.strokeStyle = '#071a30';
    const text = 'The Drowned Cathedral · Sealed'; g.strokeText(text, sx, sy + 100); g.fillStyle = '#bdeee8'; g.fillText(text, sx, sy + 100);
  } };
  // Merfolk share the authoritative NPC position/route system, with a visible scaled tail instead of legs.
  window.NacreArt = { merfolk(g, n, t) {
    const L = n.look, tail = L.tail || n.color, skin = L.skin, hair = L.hair, sway = Math.sin(t * 2.1 + n.x) * (n.moving ? 8 : 3);
    g.save(); g.lineJoin = g.lineCap = 'round';
    const gr = g.createLinearGradient(-18, -60, 25, 0); gr.addColorStop(0, '#c4f0e1'); gr.addColorStop(.4, tail); gr.addColorStop(1, '#315b84');
    g.fillStyle = gr; g.strokeStyle = OUT; g.lineWidth = 2;
    g.beginPath(); g.moveTo(-13, -50); g.quadraticCurveTo(-18, -25, 5 + sway, -14); g.quadraticCurveTo(16 + sway, -8, 22 + sway, -10); g.quadraticCurveTo(4 + sway, -23, 13, -50); g.closePath(); g.fill(); g.stroke();
    poly(g, [[19 + sway, -11], [39 + sway, -20], [33 + sway, -3], [46 + sway, 4], [24 + sway, 0], [17 + sway, -9]], tail, OUT, 2);
    for (let i = 0; i < 5; i++) { const y = -43 + i * 5; line(g, [[-8 + i * 2, y], [-3 + i * 2, y + 2], [2 + i * 2, y]], 'rgba(230,255,240,.45)', 1); }
    if (L.female) poly(g, [[-17, -104], [16, -104], [23, -63], [-23, -63]], hair, OUT, 2);
    poly(g, [[-13, -78], [13, -78], [13, -50], [-13, -50]], skin, OUT, 2);
    if (L.female) { shell(g, -7, -65, 8, 9, tail, 0); shell(g, 7, -65, 8, 9, tail, 0); }
    else line(g, [[-12, -74], [12, -62]], '#eedebb', 3);
    for (const s of [-1, 1]) { line(g, [[s * 13, -74], [s * 23, -54], [s * 25, -46]], skin, 8); ellipse(g, s * 25, -46, 4, 5, skin); }
    ellipse(g, 0, -94, 17, 19, skin);
    poly(g, [[-18, -96], [-16, -109], [-4, -115], [13, -111], [18, -98], [6, -105], [-7, -98]], hair, OUT, 1.5);
    for (const s of [-1, 1]) poly(g, [[s * 16, -95], [s * 26, -104], [s * 22, -88], [s * 16, -86]], tail, OUT, 1);
    ellipse(g, -6, -94, 2, 3, '#193950', null); ellipse(g, 6, -94, 2, 3, '#193950', null);
    line(g, [[-4, -85], [0, -83], [4, -85]], '#608786', 1.5);
    line(g, [[-12, -106], [0, -111], [12, -106]], '#ede9ca', 2); ellipse(g, 0, -110, 3, 3, '#f5fff0', null);
    g.restore();
  } };
})();
