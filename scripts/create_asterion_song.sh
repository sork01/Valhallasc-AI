#!/bin/sh
# Compose Asterion's score through dybase2's stdio MCP server. Creates a new editable project.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'EOF'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const client=new Client({name:'valhallasc-asterion-score',version:'1'});
await client.connect(new StdioClientTransport({
  command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'
}));
async function call(name,args={}){
  const r=await client.callTool({name,arguments:args});
  if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
  const data=JSON.parse(r.content[0].text);
  console.log(name,JSON.stringify(data).slice(0,400));
  return data;
}
const project=await call('create_project',{name:'Valhalla Asterion - Seven Rings of Light',bpm:112,time_signature:'4/4',key:'E minor'});
const id=project.project_id;
const A={project_id:id};
for(const t of [
  ['Moon drums','axiom8','Techno',-19],
  ['Deep pulse','sorkbass2','Fingered',-12],
  ['Glass wheel','sork60','Arp Sequence',-18],
  ['City strings','sork60','Juno Strings',-16],
  ['Sky choir','sork60','Swelling Choir',-19],
  ['Brass procession','dexed','BRASS SECT',-13],
  ['Thirteen bells','dexed','TUB BELLS',-20],
]) await call('add_track',{name:t[0],instrument:t[1],preset:t[2],volume_db:t[3],...A});
const harmony=[
  'Em C G D Em C Am B7',
  'Em C G D Em C Am B7',
  'G D Em C G D Am B7',
  'Em C G D Am C B7 Em'
].join(' ');
await call('write_chords',{track:'Deep pulse',start_bar:1,bars:32,progression:harmony,style:'root_fifth',octave:2,velocity:91,...A});
await call('write_chords',{track:'Glass wheel',start_bar:1,bars:32,progression:harmony,style:'arp_updown',register:73,rate:.5,velocity:72,...A});
await call('write_chords',{track:'City strings',start_bar:1,bars:32,progression:harmony,style:'block',register:61,velocity:85,...A});
await call('write_chords',{track:'Sky choir',start_bar:5,bars:28,progression:harmony.split(' ').slice(4).join(' '),style:'block',register:67,velocity:64,...A});
await call('write_chords',{track:'Brass procession',start_bar:9,bars:24,progression:harmony.split(' ').slice(8).join(' '),style:'stabs',register:63,velocity:87,...A});
const motif=[
  [['E5',0,1],['G5',1,1],['B5',2,1.7]],
  [['A5',.5,1],['G5',2,1],['E5',3,1]],
  [['D5',0,1],['G5',1,1],['B5',2,1],['D6',3,.8]],
  [['B5',0,1.5],['A5',2,1],['F#5',3,1]],
  [['E5',0,1],['G5',1,1],['B5',2,1],['E6',3,.9]],
  [['D6',0,1],['B5',1,1],['G5',2,1.8]],
  [['A5',0,1],['C6',1,1],['B5',2,1],['A5',3,.9]],
  [['G5',0,1],['F#5',1,1],['D#5',2,1],['E5',3,.9]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
  const notes=[];
  for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of motif[bar]){
    let p=pitch;
    if(section===2 && bar%2===0)p=({E5:'G5',G5:'B5',B5:'D6',E6:'G6'}[pitch]||pitch);
    notes.push({pitch:p,beat:bar*4+beat,beats,velocity:section===0?68:section===3?107:90});
  }
  await call('write_notes',{track:'Thirteen bells',start_bar:start,bars:8,notes,name:['Glass sunrise','Ring procession','Sky opens','All seven rings'][section],...A});
}
const drum=[
  {kick:'X.......x.......',snare:'........x.......',hat:'..x...x...x...x.'},
  {kick:'X...x...X...x...',snare:'....x.......X...',hat:'x.x.x.x.x.x.x.x.'},
  {kick:'X...x...X...x...',snare:'....X.......X...',hat:'x.x.x.x.x.x.x.x.',tom:'............x.x.'},
  {kick:'X...x...X...x...',snare:'....X.......X...',hat:'x.x.x.x.x.x.x.x.',tom:'........x...x.x.'},
];
for(let i=0;i<4;i++)await call('write_drums',{track:'Moon drums',start_bar:1+8*i,bars:8,pattern:drum[i],velocity:i===0?75:90,...A});
for(const [name,at_bar] of [['The waking glass',1],['The procession',9],['The city sings',17],['Seven rings alight',25]])
  await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'City hall',effect:'sorkverb',...A});
for(const [track,level_db] of [['Thirteen bells',-13],['Sky choir',-17],['Brass procession',-20],['City strings',-22]])
  await call('set_send',{track,fx_return:'City hall',level_db,...A});
await call('analyse_song',A);
const render=await call('render_audio',{path:'/tmp/valhallasc-asterion-dybase2.wav',per_track:false,tail_seconds:2,...A});
console.log('PROJECT_ID='+id);
console.log('WAV='+render.wav);
await client.close();
EOF
