// Mount picker and real depth compositor without a browser or private game process.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const cp = require('node:child_process');
const root = path.resolve(__dirname, '..');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');
class Node {
  constructor() { this.children = []; this.dataset = {}; this.events = {}; this.textContent = ''; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  addEventListener(name, fn) { this.events[name] = fn; }
  setAttribute(name, value) { this[name] = value; }
  get childElementCount() { return this.children.length; }
}
const sent = [], host = new Node();
const ctx = { document: { createElement: () => new Node(), getElementById: () => host }, Money: { text: String }, Keys: { label: () => 'H' }, Online: { connected: true, send: v => sent.push(v) } };
ctx.window = ctx; vm.createContext(ctx);
let source = read('client/mounts.js');
if (process.env.MUTATE === 'picker') source = source.replace(/    \{id:'seahorse'.*\n/, '');
vm.runInContext(source, ctx);
const def = ctx.Mounts.MOUNTS.find(m => m.id === 'seahorse');
assert(def); assert.equal(def.level, 35); assert(def.route.includes('Brynja')); assert(def.cost.includes('Underwater only'));
ctx.Mounts.update({ mounts: [], mount: '', level: 35 });
assert.equal(host.children.filter(n => n.dataset.mount).length, 12);
let card = host.children.find(n => n.dataset.mount === 'seahorse');
assert.equal(card.dataset.owned, false); assert.equal(card.children.length, 1);
ctx.Mounts.update({ mounts: ['horse', 'seahorse'], mount: 'horse', level: 35 });
card = host.children.find(n => n.dataset.mount === 'seahorse');
assert.equal(card.dataset.owned, true); assert.equal(card.dataset.selected, false);
assert(card.children[0].children.some(n=>n.textContent==='Underwater only · 160% movement speed'));
card.children[1].events.click(); assert.equal(JSON.stringify(sent.at(-1)), JSON.stringify({type:'select_mount',mount:'seahorse'}));
ctx.Mounts.update({ mounts: ['horse', 'seahorse'], mount: 'seahorse', level: 35 });
card = host.children.find(n => n.dataset.mount === 'seahorse'); assert(card.children[1].disabled);
const meta = JSON.parse(read('client/assets/mounts_sprites.txt'));
// Decode the actual PNG files through Pillow, then supply those pixels to the production JS compositor.
function pixels(file, row0) {
  const out = cp.execFileSync('python3', ['-c', 'from PIL import Image; import sys; im=Image.open(sys.argv[1]).convert("RGBA"); im=im.crop((0,int(sys.argv[2])*160,im.width,(int(sys.argv[2])+8)*160)) if len(sys.argv)>2 else im; sys.stdout.buffer.write(im.tobytes())', path.join(root, 'client/assets', file), ...(row0 === undefined ? [] : [String(row0)])], { maxBuffer: 24 * 1024 * 1024 });
  return new Uint8ClampedArray(out);
}
const images = new Map();
for (const file of [meta.mounts.seahorse.png, meta.mounts.seahorse.depth]) images.set('assets/' + file, pixels(file));
class Image {
  set src(url) { this.data = images.get(url); assert(this.data, url); this.width = 1280; this.height = 2560; queueMicrotask(() => this.onload()); }
}
class Canvas {
  getContext() { return { drawImage: img => this.data = img.data, getImageData: () => ({data:this.data}), putImageData: out => this.data = out.data }; }
}
const art = { Image, ImageData: class { constructor(w,h) { this.data = new Uint8ClampedArray(w*h*4); } }, document: { createElement: () => new Canvas() }, fetch: async () => ({json:async () => meta}) };
art.window=art; vm.createContext(art); vm.runInContext(read('client/mountart.js'), art);
(async () => {
  art.MountArt.preload('seahorse');
  for (let n=0; n<10 && !art.MountArt.ready('seahorse'); n++) await new Promise(resolve => setImmediate(resolve));
  assert(art.MountArt.ready('seahorse'));
  if (process.env.MUTATE === 'depth') meta.mounts.seahorse.cut = 1000;
  // A real class/body colour+depth frame for every rig; the shared compositor must preserve visible rider pixels.
  for (const rig of ['warrior_layered','warrior_layered_f','mage','mage_f','assassin','assassin_f','priest','priest_f','hunter','hunter_f']) {
    const m=JSON.parse(read(`client/assets/${rig}_sprites.txt`));
    const body=m.parts.body; const rgba=pixels(body.png,m.clips.idle.row0), depth=pixels(body.png.replace('.png','_depth.png'),m.clips.idle.row0);
    const width=1280; // All ten class sheets use eight 160 px columns.
    for (let dir=0;dir<8;dir++) {
      const rider={_px:new Uint8ClampedArray(160*160*4),_z:new Uint16Array(160*160)};
      for(let y=0;y<160;y++)for(let x=0;x<160;x++) {
        const src=(dir*160*width+y*width+x)*4, dst=y*160+x;
        rider._px.set(rgba.subarray(src,src+4),dst*4); rider._z[dst]=depth[src]*256+depth[src+1];
      }
      const bare={_px:new Uint8ClampedArray(160*160*4),_z:new Uint16Array(160*160)};
      for(const clip of ['idle','run']) {
        const hashes=new Set();
        for(let i=0;i<meta.mounts.seahorse.clips[clip].n;i++) {
          const mounted=art.MountArt.compose(rider,'seahorse',clip,dir,i,0).data;
          const animal=art.MountArt.compose(bare,'seahorse',clip,dir,i,0).data;
          let visible=0; for(let p=0;p<mounted.length;p+=4) if(mounted[p+3] && (mounted[p]!==animal[p]||mounted[p+1]!==animal[p+1]||mounted[p+2]!==animal[p+2])) visible++;
          assert(visible>100,`${rig} ${dir} ${clip} ${i}: visible rider (${visible})`);
          hashes.add(require('node:crypto').createHash('sha256').update(mounted).digest('hex'));
        }
        assert(hashes.size>1,`${rig} ${dir} ${clip}: animated`);
      }
    }
  }
  console.log('Seahorse client: picker, selection and 960 real colour/depth rider composites across ten class/body rigs pass');
})().catch(e=>{console.error(e);process.exitCode=1;});
