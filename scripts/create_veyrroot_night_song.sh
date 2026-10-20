#!/bin/sh
# Remix the active Veyrroot daytime project through the dybase2 MCP.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const project_id='f72407011081b07f';
const c=new Client({name:'valhallasc-veyrroot-night',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args={}){const r=await c.callTool({name,arguments:{project_id,...args}},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
const n=(pitch,beat,beats,velocity=50)=>({pitch,beat,beats,velocity});
const p=await call('open_project');if(p.project_id!==project_id||!p.tracks.find(t=>t.name==='Branch kalimba'))throw Error('Wrong Veyrroot source copy');
await call('rename_project',{name:'Valhalla Veyrroot Night - When the Branches Sleep'});
await call('set_tempo',{bpm:84});await call('set_key',{key:'F major'});
for(const t of p.tracks.filter(t=>t.instrument))await call('clear_bars',{track:t.name});
if(p.tracks.some(t=>t.name==='Leaf drums'))await call('remove_track',{track:'Leaf drums'});
for(const [track,instrument,preset]of [
 ['Branch kalimba','dexed','MARIMBA'],['Amber bells','dexed','GLASS VIBES'],
 ['Heartwood air','sork60','Mellow Pad'],
 ['Living root bass','sorkbass2','Fingered']])await call('set_instrument',{track,instrument,preset});
for(const [track,volume_db,pan]of [
 ['Branch kalimba',-7,-.17],['Amber bells',-30,.25],
 ['Heartwood air',-29,0],['Living root bass',2,0]])await call('set_mix',{track,volume_db,pan});
for(const [parameter,value]of [['env.attack',.08],['env.release',.45]])await call('automate',{track:'Heartwood air',parameter,points:[{bar:1,value},{bar:33,value}]});
const cycles=[
 ['Fmaj7','Cmaj7','Dm7','Bbmaj7','Fmaj7','Gm7','C7','Fmaj7'],
 ['Fmaj7','Cmaj7','Dm7','Bbmaj7','Gm7','Dm7','C7','Fmaj7'],
 ['Dm7','Bbmaj7','Fmaj7','Cmaj7','Gm7','Bbmaj7','C7','Fmaj7'],
 ['Fmaj7','Cmaj7','Dm7','Bbmaj7','Gm7','C7','Fmaj7','Fmaj7']];
const chords=cycles.flat();
const roots={Fmaj7:'F2',Cmaj7:'C2',Dm7:'D2',Bbmaj7:'Bb1',Gm7:'G1',C7:'C2'};
const tones={
 Fmaj7:['F4','A4','C5','E5'],Cmaj7:['E4','G4','B4','C5'],
 Dm7:['F4','A4','C5','D5'],Bbmaj7:['F4','A4','Bb4','D5'],
 Gm7:['F4','G4','Bb4','D5'],C7:['E4','G4','Bb4','C5']};
await call('write_chords',{track:'Heartwood air',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:54,velocity:40,name:'Night tree harmony'});
const bass=[],kalimba=[],bells=[];
for(let i=0;i<32;i++){
 const base=i*4,chord=chords[i],t=tones[chord],group=Math.floor(i/8),b=i%8;
 bass.push(n(roots[chord],base,1.6,i%8===0?58:53),n(roots[chord],base+2.75,.55,39));
 // The daytime flute's F-A-C-D shape becomes a shorter kalimba call at night.
 if(i===8||i===24){kalimba.push(n('F5',base+.5,.48,61),n('A5',base+1.5,.48,59),n('C6',base+2.5,.48,57),n('D6',base+3.25,.38,50));}
 else if(i===16){kalimba.push(n('D5',base+.5,.55,57),n('F5',base+1.5,.48,56),n('A5',base+2.5,.7,55));}
 else if(group===0){kalimba.push(n(t[0],base+.5,.52,47),n(t[2],base+2.5,.55,46));}
 else if(group===3&&b>=6){kalimba.push(n(t[2],base+.5,.5,47),n(t[0],base+2.75,.75,45));}
 else {kalimba.push(n(t[0],base+.5,.5,52),n(t[1],base+1.75,.4,48),n(t[2],base+3,.5,50));}
 // Bell response lands after the kalimba, leaving room for its phrase.
 if(i%2===1)bells.push(n(t[3],base+2,.48,31),n(t[2],base+3.25,.42,27));
}
for(const [track,notes,name]of [['Living root bass',bass,'Root steps'],['Branch kalimba',kalimba,'Branch conversation'],['Amber bells',bells,'Amber replies']])
 await call('write_notes',{track,start_bar:1,bars:32,notes,name});
if(p.tracks.some(t=>t.name==='Canopy flute'))await call('remove_track',{track:'Canopy flute'});
if(!p.tracks.some(t=>t.name==='Leaf-shaker break'))await call('add_track',{name:'Leaf-shaker break',instrument:'axiom8',preset:'Hip-hop',volume_db:-6});
else {await call('clear_bars',{track:'Leaf-shaker break'});await call('set_preset',{track:'Leaf-shaker break',preset:'Hip-hop'});}
if(!p.tracks.some(t=>t.name==='Chillhop hi-hat'))await call('add_track',{name:'Chillhop hi-hat',instrument:'axiom8',preset:'Chillhop',volume_db:-10});
else {await call('clear_bars',{track:'Chillhop hi-hat'});await call('set_preset',{track:'Chillhop hi-hat',preset:'Chillhop'});}
function row(hits,accent=[]){const a=Array(16).fill('.');for(const h of hits)a[h]=accent.includes(h)?'X':'x';return a.join('')}
const names=['Treehouse dusk','Branch lanterns','The amber answer','Before first light'];
for(let section=0;section<4;section++){
 const hats=section===0?[2,10]:section===1?[2,6,10,14]:section===2?[2,10,14]:[6,14];
 const velocity=section===0?50:section===3?52:55;
 await call('write_drums',{track:'Leaf-shaker break',start_bar:section*8+1,bars:8,pattern:{kick:row([0,11],[0]),snare:row([8]),clap:row(section===2?[15]:[])},swing:0,velocity,name:`${names[section]} break`});
 await call('write_drums',{track:'Chillhop hi-hat',start_bar:section*8+1,bars:8,pattern:{hat:row(hats)},swing:0,velocity,name:`${names[section]} Chillhop hats`});
 await call('add_marker',{name:names[section],at_bar:section*8+1});
}
const analysis=await call('analyse_song');if(analysis.problems?.length)throw Error(analysis.problems.join('; '));
console.log(JSON.stringify({project_id,source:'f817d3fb5b57cbb8',bpm:84,bars:32,seconds:32*4*60/84,warnings:analysis.warnings}));
await c.close();
JS
