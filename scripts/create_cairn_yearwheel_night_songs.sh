#!/bin/sh
# Remix the exact Cairnspine and Four Horizons daytime projects in dybase2.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-cairn-yearwheel-night',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(project_id,name,args={}){const r=await c.callTool({name,arguments:{project_id,...args}},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
const n=(pitch,beat,beats,velocity=50)=>({pitch,beat,beats,velocity});
const row=(hits,accent=[])=>{const x=Array(16).fill('.');for(const h of hits)x[h]=accent.includes(h)?'X':'x';return x.join('')};

async function cairn(){
 const id='c6569a18ca3bcc59',p=await call(id,'open_project');
 if(p.project_id!==id||p.bars!==32||!p.tracks.some(t=>t.name==='Stone marimba'))throw Error('Wrong Cairnspine source copy');
 await call(id,'rename_project',{name:'Valhalla Cairnspine Night - Watchfires on the High Pass'});
 await call(id,'set_tempo',{bpm:94});
 for(const t of p.tracks.filter(t=>t.instrument))await call(id,'clear_bars',{track:t.name});
 if(p.tracks.some(t=>t.name==='Footfall drum'))await call(id,'remove_track',{track:'Footfall drum'});
 for(const [track,instrument,preset] of [
  ['Stone marimba','dexed','MARIMBA'],['Highwind flute','dexed','WHISTLE FLUTE'],
  ['Cairn bells','dexed','GLASS VIBES'],['Summit air','sork60','Mellow Pad'],
  ['Stone bass','sorkbass2','Fingered']])await call(id,'set_instrument',{track,instrument,preset});
 for(const [track,volume_db,pan] of [
  ['Stone marimba',-13,-.15],['Highwind flute',-21,.14],['Cairn bells',-24,.22],
  ['Summit air',-28,0],['Stone bass',0,0]])await call(id,'set_mix',{track,volume_db,pan});
 for(const [parameter,value] of [['env.attack',.07],['env.release',.35]])await call(id,'automate',{track:'Summit air',parameter,points:[{bar:1,value},{bar:33,value}]});
 const blocks=[
  ['Em7','Cmaj7','Gmaj7','B7','Em7','Am7','Cmaj7','B7'],
  ['Em7','Gmaj7','Cmaj7','B7','Am7','Cmaj7','D7','B7'],
  ['Em7','Cmaj7','Gmaj7','B7','Am7','Em7','Cmaj7','B7'],
  ['Am7','Cmaj7','Gmaj7','B7','Em7','Cmaj7','B7','Em7']];
 const chords=blocks.flat();
 const roots={Em7:'E2',Cmaj7:'C2',Gmaj7:'G1',B7:'B1',Am7:'A1',D7:'D2'};
 const tones={
  Em7:['E4','G4','B4','D5'],Cmaj7:['E4','G4','B4','C5'],
  Gmaj7:['G4','B4','D5','F#5'],B7:['D#4','F#4','A4','B4'],
  Am7:['E4','G4','A4','C5'],D7:['F#4','A4','C5','D5']};
 const reply={
  Em7:['B4','G4','E4'],Cmaj7:['B4','G4','E4'],
  Gmaj7:['D5','B4','G4'],B7:['A4','F#4','D#4'],
  Am7:['C5','A4','G4'],D7:['C5','A4','F#4']};
 await call(id,'write_chords',{track:'Summit air',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:53,velocity:39,name:'Watchfire harmonies'});
 const bass=[],marimba=[],flute=[],bells=[];
 for(let i=0;i<32;i++){
  const base=i*4,chord=chords[i],t=tones[chord],r=reply[chord],p=i%8,section=Math.floor(i/8);
  bass.push(n(roots[chord],base,1.25,p===0?60:54),n(roots[chord],base+3,.62,44));
  if(i%2===0){
   if(chord==='Em7')marimba.push(n('E4',base,.42,58),n('G4',base+1,.42,54),n('B4',base+1.5,.45,58),n('F#4',base+3,.42,49));
   else marimba.push(n(t[0],base,.45,52),n(t[1],base+1,.4,49),n(t[2],base+2,.42,50));
  }else if(p===3||p===7){
   flute.push(n(r[0],base+.5,.45,46),n(r[1],base+1.5,.45,43),n(r[2],base+3,.6,45));
  }
  if(p===0||p===4)bells.push(n(t[2],base+3.5,.32,30));
  if(p===7)bells.push(n(t[1],base+2.5,.35,28));
 }
 for(const [track,notes,name] of [
  ['Stone bass',bass,'Mountain steps'],['Stone marimba',marimba,'High pass call'],
  ['Highwind flute',flute,'Watchfire reply'],['Cairn bells',bells,'Cairn markers']])
  await call(id,'write_notes',{track,start_bar:1,bars:32,notes,name});
 if(!p.tracks.some(t=>t.name==='Walking-step break'))await call(id,'add_track',{name:'Walking-step break',instrument:'axiom8',preset:'Chillhop',volume_db:-5});
 else await call(id,'set_instrument',{track:'Walking-step break',instrument:'axiom8',preset:'Chillhop'});
 for(let s=0;s<4;s++)await call(id,'write_drums',{track:'Walking-step break',start_bar:s*8+1,bars:8,
  pattern:{kick:row([0,12],[0]),snare:row([8]),hat:row([[4,12],[2,6,10,14],[4,6,12,14],[4,12]][s]),clap:row([])},
  swing:0,velocity:[46,50,53,47][s],name:['High pass','Singing cairn','Whitebark','Thunder gate'][s]});
 const a=await call(id,'analyse_song');if(a.problems?.length)throw Error(a.problems.join('; '));
 console.log(JSON.stringify({zone:27,project_id:id,source:'6132f99b6de18dce',bpm:94,bars:32,seconds:32*4*60/94,warnings:a.warnings}));
}

async function yearwheel(){
 const id='e99e8712f13cb78a',p=await call(id,'open_project');
 if(p.project_id!==id||p.bars!==64||!p.tracks.some(t=>t.name==='Horizon strings')||!p.name.includes('Four Horizons'))throw Error('Wrong Yearwheel source copy');
 await call(id,'rename_project',{name:'Valhalla Yearwheel Night - Four Horizons After Dark'});
 await call(id,'set_tempo',{bpm:96});
 for(const t of p.tracks.filter(t=>t.instrument))await call(id,'clear_bars',{track:t.name});
 if(p.tracks.some(t=>t.name==='Deep drum'))await call(id,'remove_track',{track:'Deep drum'});
 for(const [track,instrument,preset] of [
  ['Horizon strings','sork60','Mellow Pad'],['Distant choir','sork60','Juno Strings'],
  ['Earth bass','sorkbass2','Fingered'],['Far horns','sork60','Soft Horn Section'],
  ['Rain notes','dexed','TINE PIANO']])await call(id,'set_instrument',{track,instrument,preset});
 for(const [track,volume_db,pan] of [
  ['Horizon strings',-30,0],['Distant choir',-30,.12],['Earth bass',-1,0],
  ['Far horns',-18,-.12],['Rain notes',-12,.18]])await call(id,'set_mix',{track,volume_db,pan});
 for(const [parameter,value] of [['env.attack',.07],['env.release',.4]])await call(id,'automate',{track:'Horizon strings',parameter,points:[{bar:1,value},{bar:65,value}]});
 const sections=[
  {name:'Dusk crossing',chords:['Em7','Am7','Cmaj7','D7','Em7','Cmaj7','Am7','D7']},
  {name:'Spring road',chords:['Gmaj7','D7','Em7','D7','Gmaj7','Cmaj7','Am7','D7'],motif:'spring'},
  {name:'Spring opens',chords:['Gmaj7','D7','Em7','D7','Am7','Gmaj7','Cmaj7','D7'],motif:'spring'},
  {name:'Summer horizon',chords:['Cmaj7','D7','Em7','D7','Cmaj7','Gmaj7','Am7','D7'],motif:'summer'},
  {name:'Wide sky',chords:['Gmaj7','D7','Em7','D7','Gmaj7','Bm7','Cmaj7','D7'],motif:'spring'},
  {name:'Amber evening',chords:['Em7','Cmaj7','Am7','B7','Em7','Cmaj7','Am7','B7']},
  {name:'Winter stars',chords:['Bm7','A7','F#m7','Em7','Bm7','Gmaj7','Em7','A7'],motif:'winter'},
  {name:'Four horizons',chords:['Cmaj7','D7','Em7','D7','Cmaj7','D7','Gmaj7','Gmaj7'],motif:'summer'}];
 const chords=sections.flatMap(s=>s.chords);
 const roots={Em7:'E2',Am7:'A1',Cmaj7:'C2',D7:'D2',Gmaj7:'G1',Bm7:'B1',B7:'B1',A7:'A1','F#m7':'F#1'};
 const tones={
  Em7:['E4','G4','B4','D5'],Am7:['E4','G4','A4','C5'],
  Cmaj7:['E4','G4','B4','C5'],D7:['F#4','A4','C5','D5'],
  Gmaj7:['G4','B4','D5','F#5'],Bm7:['F#4','A4','B4','D5'],
  B7:['D#4','F#4','A4','B4'],A7:['E4','G4','A4','C#5'],
  'F#m7':['F#4','A4','C#5','E5']};
 const bass=[],horns=[],piano=[];
 for(let i=0;i<64;i++){
  const bar=i+1,base=i*4,chord=chords[i],t=tones[chord],s=Math.floor(i/8),b=i%8;
  bass.push(n(roots[chord],base,1.3,b===0?58:52),n(roots[chord],base+2.5,.7,42));
  if(b===4||b===6||s===0&&b%2===0||s===5&&b%2===0)piano.push(n(t[0],base+.5,.4,39),n(t[2],base+2.5,.42,35));
  if(b===7)piano.push(n(t[1],base+3,.45,38));
 }
 // Exact G–D–A–B–G–D source contour returns in spring and the wide sky;
 // its C–E and B–F# source variants remain audible in summer and winter.
 const motif={spring:['G4','D5','A4','B4','G4','D5'],summer:['C5','E5','D5','E5','B4','D5'],winter:['B4','F#5','E5','F#5','C#5','E5']};
 for(let s=0;s<8;s++){
  const variant=sections[s].motif;if(!variant)continue;
  const start=s*8*4,p=motif[variant],v=s===6?43:46;
  for(const [pitch,offset,dur] of [[p[0],0,1],[p[1],2,.7],[p[2],4,.85],
   [p[3],8.5,.75],[p[4],10,.7],[p[5],12,1]])horns.push(n(pitch,start+offset,dur,v));
  // The quiet piano answers in the second half of the phrase using chord tones.
  for(const b of [4,6]){const bar=s*8+b,chord=chords[bar],t=tones[chord],base=bar*4;
   piano.push(n(t[2],base+1,.42,42),n(t[0],base+3,.5,39));}
 }
 for(let s=0;s<8;s++){
  const {name,chords:barChords}=sections[s];
  await call(id,'write_chords',{track:'Horizon strings',start_bar:s*8+1,bars:8,progression:barChords.join(' '),style:'block',register:53,velocity:s===6?35:39,name:`${name} air`});
  if([2,3,4,6,7].includes(s))await call(id,'write_chords',{track:'Distant choir',start_bar:s*8+1,bars:8,progression:barChords.join(' '),style:'block',register:49,velocity:30,name:`${name} distance`});
 }
 for(const [track,notes,name] of [
  ['Earth bass',bass,'Wheel below'],['Far horns',horns,'Distant horizon calls'],
  ['Rain notes',piano,'Seasonal answers']])await call(id,'write_notes',{track,start_bar:1,bars:64,notes,name});
 if(!p.tracks.some(t=>t.name==='Wheel break'))await call(id,'add_track',{name:'Wheel break',instrument:'axiom8',preset:'Chillhop',volume_db:-4});
 else {await call(id,'set_instrument',{track:'Wheel break',instrument:'axiom8',preset:'Chillhop'});await call(id,'set_mix',{track:'Wheel break',volume_db:-4});}
 const hats=[[4,12],[4,10,14],[2,6,10,14],[2,4,10,14],
  [4,10,14],[4,12],[4,10],[2,6,10,14]];
 for(let s=0;s<8;s++)await call(id,'write_drums',{track:'Wheel break',start_bar:s*8+1,bars:8,
  pattern:{kick:row([0,10],[0]),snare:row([8]),hat:row(hats[s]),clap:row([])},
  swing:0,velocity:[43,46,49,52,48,44,42,47][s],name:`${sections[s].name} break`});
 const a=await call(id,'analyse_song');if(a.problems?.length)throw Error(a.problems.join('; '));
 console.log(JSON.stringify({zone:28,project_id:id,source:'c7ab959e2d451253',bpm:96,bars:64,seconds:64*4*60/96,warnings:a.warnings}));
}

if(!process.env.ZONES||process.env.ZONES.split(',').includes('27'))await cairn();
if(!process.env.ZONES||process.env.ZONES.split(',').includes('28'))await yearwheel();
await c.close();
JS
