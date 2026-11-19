const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),mode=process.env.FISH_COAST_MUTATION;
if(process.argv.includes('--mutations')) {
 const {spawnSync}=require('node:child_process');
 for(const [name,message] of Object.entries({disabled:'ordinary sea coastline is fishable',border:'seams are not ocean water',floor:'painted land is not sea',range:'distant sea is out of reach'})) {
  const r=spawnSync(process.execPath,[__filename],{cwd:root,encoding:'utf8',env:{...process.env,FISH_COAST_MUTATION:name}});
  assert(r.status!==0&&(r.stdout+r.stderr).includes(message),name+': '+r.stdout+r.stderr);console.log('Caught coast client mutation:',name);
 }process.exit(0);
}
const read=fs.readFileSync.bind(fs),controlled={...fs,readFileSync(file,...args){let s=read(file,...args);if(String(file).endsWith('/client/fishing.js')&&typeof s==='string'){
 if(mode==='disabled')s=s.replace('if (!lava && !onDock && map.shapeFloor && map.shapeEdge)', 'if (false && !lava && !onDock && map.shapeFloor && map.shapeEdge)');
 if(mode==='border')s=s.replace("map.shapeEdge[Math.floor(p.y)]?.[Math.floor(p.x)] === 'c'", "map.shapeEdge[Math.floor(p.y)]?.[Math.floor(p.x)] !== ' '");
 if(mode==='floor')s=s.replace("map.shapeFloor[Math.floor(p.y)]?.[Math.floor(p.x)] === ' ' && ",'');
 if(mode==='range')s=s.replace('if (distance > 4) return false','if (distance > 6) return false');
}return s;}};
const prefix=read(path.join(__dirname,'fishing-client.cjs'),'utf8').split('const f=fixture(),')[0];
const fixture=new Function('require','__dirname',prefix+'\nreturn fixture;')(name=>name==='node:fs'?controlled:require(name),__dirname),f=fixture();
const items=JSON.parse(read(path.join(root,'world/items.txt'))),rod=items.find(i=>i.id==='rod_twig_rod');
const hero={id:'coast',zone:0,x:8,y:10.5,fx:1,fy:0,level:99,inventory:[{item:rod.id,quantity:1}]};
const map={objects:[],shapeFloor:Array(20).fill('##########          '),shapeEdge:Array(20).fill('          cccccccccc')};let count=0;
const check=(ok,message)=>{assert(ok,message);count++;};
check(f.ctx.Fishing.shore(hero,map),'ordinary sea coastline is fishable');
check(!f.ctx.Fishing.shore({...hero,fx:-1},map),'facing land cannot cast into the sea');
check(!f.ctx.Fishing.shore({...hero,x:5},map),'distant sea is out of reach');
check(!f.ctx.Fishing.shore({...hero,x:12},map),'cannot stand in the sea to fish');
check(!f.ctx.Fishing.shore({...hero,inventory:[]},map),'coast still needs a rod');
check(f.ctx.Fishing.shore({...hero,inventory:[{item:'rod_emberline_rod',quantity:1}]},map),'Platinum line keeps sea fishing');
check(!f.ctx.Fishing.shore(hero,{...map,shapeEdge:Array(20).fill('          AAAAAAAAAA')}),'seams are not ocean water');
check(!f.ctx.Fishing.shore(hero,{...map,shapeEdge:Array(20).fill('          llllllllll')}),'cliffs are not ocean water');
check(!f.ctx.Fishing.shore(hero,{...map,shapeFloor:Array(20).fill('####################')}),'painted land is not sea');
check(!f.ctx.Fishing.shore(hero,{...map,shapeEdge:undefined}),'old maps without a sea mask are unchanged');
console.log(`Coast client: ${count} focused checks pass.`);
