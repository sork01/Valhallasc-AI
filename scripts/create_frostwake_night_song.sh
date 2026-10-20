#!/bin/sh
# Remix the active Frostwake daytime project through the dybase2 MCP.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const project_id='b2ac59239f3ce0e8'; // codex copy of daytime 75951aa438eab92b
const c=new Client({name:'valhallasc-frostwake-night',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args={}){const r=await c.callTool({name,arguments:{project_id,...args}},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
const n=(pitch,beat,beats,velocity=50)=>({pitch,beat,beats,velocity});
const p=await call('open_project');
if(p.project_id!==project_id||!p.tracks.find(t=>t.name==='Ice marimba')||p.bars!==32)throw Error('Wrong Frostwake daytime copy');
await call('rename_project',{name:'Valhalla Frostwake Night - Aurora Beneath the Ice'});
await call('set_tempo',{bpm:84});
for(const t of p.tracks.filter(t=>t.instrument))await call('clear_bars',{track:t.name});
if(p.tracks.some(t=>t.name==='Snow pulse'))await call('remove_track',{track:'Snow pulse'});
for(const [track,instrument,preset] of [
 ['Ice marimba','dexed','MARIMBA'],['Aurora flute','dexed','WHISTLE FLUTE'],
 ['Glacial bells','dexed','GLASS VIBES'],['Snow air','sork60','Mellow Pad'],
 ['Deep ice bass','sorkbass2','Fingered']])await call('set_instrument',{track,instrument,preset});
for(const [track,volume_db,pan] of [
 ['Ice marimba',-13,-.16],['Aurora flute',-22,.12],['Glacial bells',-24,.22],
 ['Snow air',-28,0],['Deep ice bass',0,0]])await call('set_mix',{track,volume_db,pan});
for(const [parameter,value] of [['env.attack',.07],['env.release',.35]])await call('automate',{track:'Snow air',parameter,points:[{bar:1,value},{bar:33,value}]});

// The G–Bb–D–C marimba call comes from the daytime tune. Flute replies are new.
// Each phrase is voiced against its own bar's chord, not copied over the changes.
const sections=[
 ['Gm7','Ebmaj7','Bbmaj7','D7','Gm7','Cm7','Ebmaj7','D7'],
 ['Gm7','Ebmaj7','Cm7','D7','Bbmaj7','Ebmaj7','Cm7','D7'],
 ['Gm7','Fmaj7','Ebmaj7','D7','Gm7','Cm7','Ebmaj7','D7'],
 ['Cm7','Ebmaj7','Bbmaj7','D7','Gm7','Ebmaj7','D7','Gm7']];
const chords=sections.flat();
const roots={Gm7:'G2',Ebmaj7:'Eb2',Bbmaj7:'Bb1',D7:'D2',Cm7:'C2',Fmaj7:'F2'};
const tones={
 Gm7:['G4','Bb4','D5','F5'],Ebmaj7:['Eb4','G4','Bb4','D5'],
 Bbmaj7:['F4','A4','Bb4','D5'],D7:['F#4','A4','C5','D5'],
 Cm7:['Eb4','G4','Bb4','C5'],Fmaj7:['F4','A4','C5','E5']};
const replies={
 Gm7:['D5','Bb4','G4'],Ebmaj7:['Bb4','G4','Eb4'],
 Bbmaj7:['D5','Bb4','A4'],D7:['C5','A4','F#4'],
 Cm7:['Bb4','G4','Eb4'],Fmaj7:['C5','A4','F4']};
await call('write_chords',{track:'Snow air',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:53,velocity:40,name:'Aurora under the shelf'});
const bass=[],marimba=[],flute=[],bells=[];
for(let i=0;i<32;i++){
 const base=i*4,chord=chords[i],t=tones[chord],r=replies[chord],phrase=i%8,section=Math.floor(i/8);
 bass.push(n(roots[chord],base,1.35,i%8===0?59:54),n(roots[chord],base+2.5,.7,43));
 if(i%2===0){
  if(chord==='Gm7')marimba.push(n('G4',base,.42,59),n('Bb4',base+1,.42,56),n('D5',base+1.5,.45,60),n('C5',base+2.5,.4,51));
  else marimba.push(n(t[0],base,.48,53),n(t[1],base+1,.42,50),n(t[2],base+1.5,.5,52),n(t[1],base+2.5,.42,45));
 }else if(phrase===3||phrase===7){
  // A quiet answer twice per section, part of the texture rather than a lead.
  flute.push(n(r[0],base+.5,.48,47),n(r[1],base+1.5,.44,44),n(r[2],base+3,.65,46));
 }
 // Bells mark the return of each four-bar arch instead of repeating an arp.
 if(phrase===0||phrase===4)bells.push(n(t[2],base+3.5,.32,31));
 if(phrase===7)bells.push(n(t[1],base+3,.35,28));
}
for(const [track,notes,name] of [
 ['Deep ice bass',bass,'Slow ice current'],['Ice marimba',marimba,'Lantern call'],
 ['Aurora flute',flute,'Aurora answer'],['Glacial bells',bells,'Blue ice markers']])
 await call('write_notes',{track,start_bar:1,bars:32,notes,name});

if(!p.tracks.some(t=>t.name==='Ice-shelf break'))await call('add_track',{name:'Ice-shelf break',instrument:'axiom8',preset:'Chillhop',volume_db:-5});
else await call('set_instrument',{track:'Ice-shelf break',instrument:'axiom8',preset:'Chillhop'});
const row=(hits,accents=[])=>{const x=Array(16).fill('.');for(const i of hits)x[i]=accents.includes(i)?'X':'x';return x.join('')};
for(let section=0;section<4;section++){
 const hats=[[4,14],[4,10,14],[2,4,10,14],[4,14]][section];
 // Half-time snare on beat 3 (step 8); kick follows both bass attacks (0,10).
 await call('write_drums',{track:'Ice-shelf break',start_bar:section*8+1,bars:8,
  pattern:{kick:row([0,10],[0]),snare:row([8]),hat:row(hats),clap:row([])},
  swing:0,velocity:[45,49,53,47][section],name:['Blue shelf','Lanterns','Aurora','Snowfall'][section]});
}
const a=await call('analyse_song');if(a.problems?.length)throw Error(a.problems.join('; '));
console.log(JSON.stringify({project_id,source:'75951aa438eab92b',bpm:84,bars:32,seconds:32*4*60/84,warnings:a.warnings}));
await c.close();
JS
