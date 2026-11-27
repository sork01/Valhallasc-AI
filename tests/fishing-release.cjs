// Release packaging must retain the independent manual test and matching fishing data.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),read=p=>fs.readFileSync(path.join(root,p),'utf8'),load=p=>JSON.parse(read(p));
const version=read('client/index.html').match(/class="version">([^<]+)</)[1];
assert.match(version,/^\d+\.\d+\.\d+$/);assert(load('scripts/sv-keep.txt').includes(version));
assert.equal(load('client/release-notes.txt')[0].version,version);
let config=read('deploy/apache.conf');
if(process.env.MUTATE==='route')config=config.replace(/^ProxyPass \/ValhallaFishing\/ .*\n/m,'');
for(const [route,port] of [['Valhalla',8080],['ValhallaFishing',8082]]){
 const ws=`ProxyPass /${route}/ws ws://172.18.0.1:${port}/ws`,http=`ProxyPass /${route}/ http://172.18.0.1:${port}/`;
 assert(config.includes(http),`${route} retains its independent HTTP route`);
 assert(config.indexOf(ws)>=0&&config.indexOf(ws)<config.indexOf(http),'WebSocket route precedes HTTP');
 assert(config.includes(`ProxyPassReverse /${route}/ http://172.18.0.1:${port}/`));
}
assert(config.includes('<Location "/ValhallaFishing/">')&&config.includes('Header always set Cache-Control "no-store"'));
const context={window:{}};vm.createContext(context);vm.runInContext(read('client/items.js'),context);
const items=load('world/items.txt'),clientItems=context.window.WORLD_ITEMS||context.WORLD_ITEMS;
assert(clientItems,'generated client item catalogue loads');
for(const i of items.filter(i=>i.kind==='fish'||i.kind==='rod'||i.foodBonus)){
 const generated=clientItems.find(j=>j.id===i.id);assert(generated,`${i.id} ships in both catalogues`);
 for(const key of ['name','kind','requiredLevel','fishing','foodBonus'])assert.equal(JSON.stringify(generated[key]),JSON.stringify(i[key]),`${i.id} ${key} matches`);
}
assert.equal(items.filter(i=>i.kind==='fish').length,92);assert.equal(items.filter(i=>i.kind==='rod').length,10);
assert.deepEqual(load('world/rods.txt').map(r=>r.name),['Twig Rod','Platinum Rod','Willow Rod','Reedglass Rod','Silverline Rod','Tempered Platinum Rod','Starcatch Rod','Worldwire Rod','Rootbraid Rod','Cairnsteel Rod']);
console.log('Fishing release: version/notes, separate public/manual routes, stable 92 species/ten cumulative rods and matching generated catalogues pass.');
