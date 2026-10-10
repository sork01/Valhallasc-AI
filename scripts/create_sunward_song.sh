#!/bin/sh
# Compose an editable pastoral score through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'EOF'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const client=new Client({name:'valhallasc-sunward-score',version:'1'});
await client.connect(new StdioClientTransport({
  command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'
}));
async function call(name,args={}){
  const r=await client.callTool({name,arguments:args});
  if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
  const data=JSON.parse(r.content[0].text);
  console.log(name,JSON.stringify(data).slice(0,250));
  return data;
}
const project=await call('create_project',{name:'Valhalla Sunward Vale - Along the Millstream',bpm:104,time_signature:'4/4',key:'G major'});
const A={project_id:project.project_id};
console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
  ['Hillside flute','dexed','WHISTLE FLUTE',-13],
  ['Plucked strings','dexed','HARPSICHORD',-18],
  ['Millwheel marimba','dexed','MARIMBA',-21],
  ['Warm strings','dexed','STRING ENS',-21],
  ['Walking bass','sorkbass2','Fingered',-17],
  ['Wooden hand drum','dexed','LOG DRUM',-23],
])await call('add_track',{name,instrument,preset,volume_db,...A});
const harmony=[
  'G D Em C G Am D7 G',
  'G D Em C Am D7 G G',
  'C G Am Em C G D7 D7',
  'G D Em C Am D7 G G',
].join(' ');
await call('write_chords',{track:'Walking bass',start_bar:1,bars:32,progression:harmony,style:'root_fifth',octave:2,velocity:71,...A});
await call('write_chords',{track:'Plucked strings',start_bar:1,bars:32,progression:harmony,style:'arp_updown',register:68,rate:.5,velocity:60,...A});
await call('write_chords',{track:'Warm strings',start_bar:1,bars:32,progression:harmony,style:'block',register:57,velocity:60,...A});
await call('write_chords',{track:'Millwheel marimba',start_bar:9,bars:24,progression:harmony.split(' ').slice(8).join(' '),style:'stabs',register:65,velocity:54,...A});
const tune=[
  [['G5',0,.75],['B5',1,.75],['D6',2,1.5]],
  [['A5',.5,.75],['G5',1.5,.75],['F#5',2.5,1]],
  [['E5',0,.75],['G5',1,.75],['B5',2,1.5]],
  [['C6',0,1],['B5',1.5,.75],['G5',2.5,1]],
  [['D6',0,.75],['B5',1,.75],['G5',2,1.5]],
  [['A5',0,.75],['C6',1,.75],['B5',2,1.5]],
  [['A5',0,.75],['F#5',1,.75],['D6',2,1.5]],
  [['B5',0,1],['A5',1.5,.75],['G5',2.5,1]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
  const notes=[];
  for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar]){
    const raised=section===2&&bar%2===0?({G5:'B5',B5:'D6',D6:'G6'}[pitch]||pitch):pitch;
    notes.push({pitch:raised,beat:bar*4+beat,beats,velocity:section===0?67:section===3?87:76});
  }
  await call('write_notes',{track:'Hillside flute',start_bar:start,bars:8,notes,
    name:['First light on the river','The orchard path','Under the old oaks','Home by the mill'][section],...A});
}
const beats=[];
for(let bar=0;bar<32;bar++){
  beats.push({pitch:'G2',beat:bar*4,beats:.38,velocity:bar%8===0?71:57});
  beats.push({pitch:'D3',beat:bar*4+2.5,beats:.25,velocity:48});
}
await call('write_notes',{track:'Wooden hand drum',start_bar:1,bars:32,notes:beats,name:'Quiet wood pulse',...A});
for(const [name,at_bar] of [['Millbridge morning',1],['Across the orchard',9],['Oakwood clearing',17],['The Elder Hollow',25]])
  await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Open valley air',effect:'sorkverb',...A});
for(const [track,level_db] of [['Hillside flute',-19],['Warm strings',-24],['Millwheel marimba',-25]])
  await call('set_send',{track,fx_return:'Open valley air',level_db,...A});
await call('analyse_song',A);
try{
  const render=await call('render_audio',{path:'/tmp/valhallasc-sunward-dybase2.wav',per_track:false,tail_seconds:2,...A});
  console.log('WAV='+render.wav);
}catch(error){
  console.error('Render request timed out; check the requested WAV before retrying:',error.message);
}
await client.close();
EOF
