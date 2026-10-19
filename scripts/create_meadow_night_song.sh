#!/bin/sh
# Copy Greenmeadow Wander through dybase2's MCP and turn its two passes into a nocturne.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const client=new Client({name:'valhallasc-meadow-night-remix',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args={}) {
  const result=await client.callTool({name,arguments:args},undefined,{timeout:300000});
  if(result.isError) throw Error(`${name}: ${result.content.map(x=>x.text).join('\n')}`);
  const data=JSON.parse(result.content[0].text);
  console.log(name,JSON.stringify(data).slice(0,240));
  return data;
}
const source='e2041a0c18b333d3'; // Valhalla Meadow - Greenmeadow Wander
const copy=await call('open_project',{project_id:source});
if(copy.copied_from?.id!==source) throw Error('The daytime meadow project was not copied; refusing to edit it');
const project_id=copy.project_id;
console.log('PROJECT_ID='+project_id);
const A={project_id};
await call('rename_project',{name:'Valhalla Greenmeadow Night - Fireflies on the Path',...A});
await call('set_tempo',{bpm:100,...A});
for(const [track,preset] of [
  ['Kantele','Clavinet'],
  ['Harp','Clavinet'],
  ['Strings','Mellow Pad'],
]) await call('set_instrument',{track,instrument:'sork60',preset,...A});
await call('set_instrument',{track:'Flute',instrument:'dexed',preset:'WHISTLE FLUTE',...A});
for(const [track,volume_db,pan] of [
  ['Kantele',3,.1],
  ['Flute',-22,.1],
  ['Harp',0,-.3],
  ['Bass',-7,0],
  ['Strings',-34,-.1],
]) await call('set_mix',{track,volume_db,pan,...A});
await call('remove_track',{track:'Hand Drum',...A});
for(const [track,level_db] of [
  ['Kantele',-14],['Flute',-14],['Harp',-17],['Strings',-15],
]) await call('set_send',{track,fx_return:'Reverb',level_db,...A});
await call('add_marker',{name:'Fireflies at the edge of town',at_bar:1,...A});
await call('add_marker',{name:'Under the old trees',at_bar:17,...A});
// Relative-minor reharmonization, with new offbeat pulses and call/response.
const chords=[
  'Em7 Cmaj7 Gadd9 Dsus2 Em7 Cmaj7 Am7 D7',
  'Cmaj7 Gmaj7 Bm7 Em7 Cmaj7 Am7 Dsus4 D7',
  'Em7 Cmaj7 Gadd9 D6 Am7 Cmaj7 Dsus4 Gmaj7',
  'Cmaj7 Gmaj7 Em7 Bm7 Am7 D7 Gmaj7 G',
].join(' ').split(' ');
await call('write_chords',{track:'Strings',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:55,velocity:46,name:'Moonlit chord bed',...A});
const root={Em7:'E2',Cmaj7:'C2',Gadd9:'G2',Dsus2:'D2',Am7:'A2',D7:'D2',Gmaj7:'G2',Bm7:'B2',Dsus4:'D2',D6:'D2',G:'G2'};
await call('write_notes',{track:'Bass',start_bar:1,bars:32,notes:chords.map((c,i)=>({pitch:root[c],beat:i*3,beats:2.3,velocity:i%8===0?62:51})),name:'One slow tide per bar',...A});
const tones={Em7:['E4','G4','B4'],Cmaj7:['C4','E4','B4'],Gadd9:['G3','D4','A4'],Dsus2:['D4','E4','A4'],Am7:['A3','C4','G4'],D7:['D4','F#4','C5'],Gmaj7:['G3','D4','F#4'],Bm7:['B3','D4','A4'],Dsus4:['D4','G4','A4'],D6:['D4','F#4','B4'],G:['G3','B3','D4']};
const harp=[];
for(let bar=0;bar<32;bar++) for(const [i,beat] of [.75,1.5,2.25].entries())
  harp.push({pitch:tones[chords[bar]][i],beat:bar*3+beat,beats:.42,velocity:i===0?47:39});
await call('write_notes',{track:'Harp',start_bar:1,bars:32,notes:harp,name:'Offbeat firefly pulses',...A});
// The G-B-D shape recalls Greenmeadow Wander, but rests and endings now answer
// the Em/C night harmony instead of replaying the daytime two-pass tune.
const leadA=[
  [['G4',.5,.5],['B4',1.25,.5],['D5',2,.75]],
  [['B4',.5,.5],['A4',1.25,1]],
  [['E5',.25,.75],['D5',1.25,.5],['B4',2,.75]],
  [['G4',.75,1.5]],
  [['B4',.5,.5],['D5',1.25,.5],['G5',2,.75]],
  [['F#5',.25,.75],['E5',1.25,.5],['D5',2,.75]],
  [['C5',.5,.5],['B4',1.25,.5],['A4',2,.75]],
  [['G4',.5,1.5]],
  [['E5',0,1],['B4',1.5,.5],['G4',2.25,.5]],
  [['B4',.5,.75],['A4',1.5,.75]],
  [['D5',.25,.5],['F#5',1.25,.5],['D5',2,.75]],
  [['E5',.5,1],['B4',2,.5]],
  [['G4',.25,.5],['B4',1,.5],['D5',1.75,.75]],
  [['C5',.75,.75],['B4',1.75,.75]],
  [['A4',.5,.5],['G4',1.25,.5],['F#4',2,.75]],
  [['G4',.5,1.5]],
];
const leadB=[
  [['B4',.5,.5],['D5',1.25,.5],['G5',2,.75]],
  [['G5',.25,.75],['E5',1.25,.5],['D5',2,.75]],
  [['D5',.5,.5],['B4',1.25,.5],['G4',2,.75]],
  [['A4',.5,1.5]],
  [['C5',.5,.5],['E5',1.25,.5],['G5',2,.75]],
  [['B4',.5,.5],['G4',1.25,.5],['E4',2,.75]],
  [['A4',.5,.5],['B4',1.25,.5],['D5',2,.75]],
  [['G4',.5,1.5]],
  [['G4',.5,.5],['B4',1.25,.5],['D5',2,.75]],
  [['F#5',.5,.5],['E5',1.25,.5],['D5',2,.75]],
  [['B4',.5,.5],['D5',1.25,.5],['E5',2,.75]],
  [['F#5',.5,1.5]],
  [['E5',.5,.5],['C5',1.25,.5],['B4',2,.75]],
  [['A4',.5,.5],['G4',1.25,.5],['F#4',2,.75]],
  [['G4',.5,1.5]],
  [['G4',.25,2.5]],
];
const part=phrase=>phrase.flatMap((bar,i)=>bar.map(([pitch,beat,beats])=>({pitch,beat:i*3+beat,beats,velocity:i%8===0?63:54})));
await call('write_notes',{track:'Kantele',start_bar:1,bars:16,notes:part(leadA),name:'Firefly call',...A});
await call('write_notes',{track:'Flute',start_bar:17,bars:16,notes:part(leadB),name:'Moonlit answer and return',...A});
await call('write_notes',{track:'Kantele',start_bar:17,bars:16,notes:[
  {pitch:'G4',beat:11.25,beats:.5,velocity:40},
  {pitch:'E4',beat:23.25,beats:.5,velocity:40},
  {pitch:'D4',beat:35.25,beats:.5,velocity:40},
  {pitch:'G4',beat:47.25,beats:.5,velocity:40},
],name:'Distant kantele answers',...A});
await call('analyse_song',A);
await client.close();
JS
