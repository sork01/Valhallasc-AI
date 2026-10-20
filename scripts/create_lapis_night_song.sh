#!/bin/sh
# Remix the active Lapis Erg daytime project through the dybase2 MCP.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const project_id='fdff01002b905c49';
const c=new Client({name:'valhallasc-lapis-night',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args={}){const r=await c.callTool({name,arguments:{project_id,...args}},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
const n=(pitch,beat,beats,velocity=50)=>({pitch,beat,beats,velocity});
const p=await call('open_project');if(p.project_id!==project_id||!p.tracks.find(t=>t.name==='Caravan pluck'))throw Error('Wrong Lapis Erg source copy');
await call('rename_project',{name:'Valhalla Lapis Erg Night - Caravan Under the Stars'});
await call('set_tempo',{bpm:86});await call('set_key',{key:'D minor'});
for(const t of p.tracks.filter(t=>t.instrument))await call('clear_bars',{track:t.name});
for(const dead of ['Sand drums','Desert flute'])if(p.tracks.some(t=>t.name===dead))await call('remove_track',{track:dead});
for(const [track,instrument,preset]of [
 ['Caravan pluck','dexed','MARIMBA'],
 ['Blue-glass bells','dexed','GLASS VIBES'],['Oasis air','sork60','Mellow Pad'],
 ['Caravan bass','sorkbass2','Fingered']])await call('set_instrument',{track,instrument,preset});
for(const [track,volume_db,pan]of [
 ['Caravan pluck',-7,-.18],['Blue-glass bells',-14,.22],
 ['Oasis air',-29,0],['Caravan bass',2,0]])await call('set_mix',{track,volume_db,pan});
for(const [parameter,value]of [['env.attack',.08],['env.release',.45]])await call('automate',{track:'Oasis air',parameter,points:[{bar:1,value},{bar:33,value}]});
const cycles=[
 ['Dm7','Bbmaj7','Gm7','A7','Dm7','Fmaj7','Gm7','A7'],
 ['Dm7','Bbmaj7','Fmaj7','A7','Gm7','Bbmaj7','A7','Dm7'],
 ['Bbmaj7','Fmaj7','Gm7','Dm7','Bbmaj7','Gm7','A7','Dm7'],
 ['Dm7','Bbmaj7','Gm7','A7','Gm7','A7','Dm7','Dm7']];
const chords=cycles.flat();
const roots={Dm7:'D2',Bbmaj7:'Bb1',Gm7:'G1',A7:'A1',Fmaj7:'F2'};
const tones={
 Dm7:['D4','F4','A4','C5'],Bbmaj7:['D4','F4','A4','Bb4'],
 Gm7:['D4','F4','G4','Bb4'],A7:['C#4','E4','G4','A4'],Fmaj7:['C4','E4','F4','A4']};
const bellTones={
 Dm7:['D5','F5','A5','C6'],Bbmaj7:['D5','F5','A5','Bb5'],
 Gm7:['D5','G5','Bb5','D6'],A7:['C#5','E5','G5','A5'],Fmaj7:['C5','F5','A5','C6']};
await call('write_chords',{track:'Oasis air',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:53,velocity:41,name:'Night oasis harmony'});
const bass=[],pluck=[],bells=[];
for(let i=0;i<32;i++){
 const base=i*4,chord=chords[i],t=tones[chord],bt=bellTones[chord],group=Math.floor(i/8),b=i%8;
 bass.push(n(roots[chord],base,1.5,i%8===0?58:53),n(roots[chord],base+2.5,.65,41));
 // Caravan pluck carries the D4-F4-G4-A4 motif and answers over the night chords without a separate lead.
 if(i===8||i===24){pluck.push(n('D4',base+.5,.5,60),n('F4',base+1.5,.5,58),n('G4',base+2.5,.45,56),n('A4',base+3,.6,61));}
 else if(i===16){pluck.push(n('F4',base+.5,.55,58),n('D4',base+1.5,.5,56),n('Bb4',base+2.5,.7,55));}
 else if(group===0){pluck.push(n(t[0],base+.5,.52,48),n(t[2],base+2.5,.55,46));}
 else if(group===3&&b>=6){pluck.push(n(t[2],base+.5,.5,48),n(t[0],base+2.5,.75,46));}
 else {pluck.push(n(t[0],base+.5,.5,53),n(t[1],base+1.5,.45,49),n(t[2],base+2.5,.55,51));}
 // Blue-glass bells answer in odd bars after the pluck phrase.
 if(i%2===1)bells.push(n(bt[2],base+2,.48,34),n(bt[1],base+3.25,.42,30));
}
for(const [track,notes,name]of [
 ['Caravan bass',bass,'Caravan steps'],['Caravan pluck',pluck,'Resting caravan pluck'],
 ['Blue-glass bells',bells,'Blue-glass starlight']])
 await call('write_notes',{track,start_bar:1,bars:32,notes,name});
if(!p.tracks.some(t=>t.name==='Sand-brush break'))await call('add_track',{name:'Sand-brush break',instrument:'axiom8',preset:'Chillhop',volume_db:-2});
else {await call('clear_bars',{track:'Sand-brush break'});await call('set_instrument',{track:'Sand-brush break',instrument:'axiom8',preset:'Chillhop'});await call('set_mix',{track:'Sand-brush break',volume_db:-2});}
function row(hits,accent=[]){const a=Array(16).fill('.');for(const h of hits)a[h]=accent.includes(h)?'X':'x';return a.join('')}
const names=['Campfire in the dunes','Wells under Orion','The mirage replies','Before the sun rises'];
for(let section=0;section<4;section++){
 // Dry sand-brush Chillhop break with deliberate rests on beat 2; kick locks to bass at 0 and 10 (beat 2.5), snare anchors beat 3 (step 8).
 const hats=section===0?[2,10]:section===1?[2,8,10,14]:section===2?[2,6,10,14]:[2,14];
 await call('write_drums',{track:'Sand-brush break',start_bar:section*8+1,bars:8,pattern:{kick:row([0,10],[0]),snare:row([8]),hat:row(hats),clap:row(section===2?[15]:[])},swing:0,velocity:section===0?50:section===3?52:56,name:`${names[section]} break`});
 await call('add_marker',{name:names[section],at_bar:section*8+1});
}
const analysis=await call('analyse_song');if(analysis.problems?.length)throw Error(analysis.problems.join('; '));
console.log(JSON.stringify({project_id,source:'b1a0de52aae84cfb',bpm:86,bars:32,seconds:32*4*60/86,warnings:analysis.warnings}));
await c.close();
JS
