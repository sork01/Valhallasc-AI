#!/bin/sh
# Enter the Python-rendered daytime scores as editable dybase2 source projects.
# The note, chord and entry tables come from make_nacre_music.py and
# make_astral_music.py; the shipped daytime MP3s remain the original renders.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-python-score-transcription',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'valhallasc_source'}}));
async function call(name,args){const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content[0].text}`);return JSON.parse(r.content[0].text)}
const n=(pitch,beat,beats,velocity=58)=>({pitch,beat,beats,velocity});

// Waterglass Lullaby: two-bar chords and the exact eight-bar A-C / G-E melody.
{
  const p=await call('create_project',{name:'Valhalla Nacrehold Daytime Source - Waterglass Lullaby',bpm:64,time_signature:'4/4',key:'F major'}),A={project_id:p.project_id};
  for(const [name,instrument,preset,volume_db] of [['Pad','sork60','Mellow Pad',-25],['Keys','sork60','Hiphop Chorus Keys',-15],['Bass','sorkbass2','Fingered',-3],['Melody','sork60','Bell Tine',-17]])await call('add_track',{name,instrument,preset,volume_db,...A});
  const chords=[[53,57,60,64],[48,55,59,62],[50,57,60,65],[46,53,57,60],[53,57,60,64],[55,58,62,65],[48,55,59,62],[53,57,60,67]];
  const theme=[[[69,0,2],[72,2.5,1]],[[67,0,2],[64,2.5,1]],[[65,.5,1.5],[69,2.5,1]],[[65,0,3]],[[69,0,1.5],[67,2,1]],[[65,.5,2],[62,3,.75]],[[64,0,2],[62,2.5,1]],[[60,0,3]]];
  const pad=[],keys=[],bass=[],melody=[];
  for(let bar=0;bar<32;bar++){
    const chord=chords[Math.floor(bar/2)%8],b=bar*4;
    if(bar%2===0){for(const pitch of chord)pad.push(n(pitch,b,7.3,42));bass.push(n(chord[0]-12,b,5,52));}
    if(bar>=4&&bar<28)for(let i=0;i<3;i++)keys.push(n(chord[i+1]+12,b+.5+i,1.2,43));
    if((bar>=8&&bar<24)||bar>=28)for(const [pitch,offset,length] of theme[bar%8])melody.push(n(pitch,b+offset,length,bar<24?63:48));
  }
  for(const [track,notes] of [['Pad',pad],['Keys',keys],['Bass',bass],['Melody',melody]])await call('write_notes',{track,start_bar:1,bars:32,notes,name:'Transcribed daytime '+track,...A});
  await call('add_marker',{name:'Pearl streets',at_bar:1,...A});
  await call('add_marker',{name:'Waterglass theme',at_bar:9,...A});
  const a=await call('analyse_song',A);
  console.log('NACRE_DAY_SOURCE',JSON.stringify({id:p.project_id,open_in_app:p.open_in_app,length:a.length,problems:a.problems}));
}

// The Falling Garden: the original Python 5/4 voicings, five-step wood part,
// and C#-E-F# melodic cell are entered as notes; timbres are editable proxies.
{
  const p=await call('create_project',{name:'Valhalla Astralhollow Daytime Source - The Falling Garden',bpm:108,time_signature:'5/4',key:'F# minor'}),A={project_id:p.project_id};
  for(const [name,instrument,preset,volume_db] of [['Strings','sork60','Juno Strings',-18],['Bass','sorkbass2','Fingered',-5],['Wood','dexed','MARIMBA',-15],['Melody','sork60','Unison Lead',-24],['Glass','dexed','GLASS VIBES',-19]])await call('add_track',{name,instrument,preset,volume_db,...A});
  const chords=[[42,49,57,61,68],[38,45,54,57,61],[47,54,59,61,66],[40,47,56,59,64],[37,44,54,59,64],[42,49,57,61,66],[45,52,57,61,64],[37,44,53,59,64]];
  const theme=[[[73,0,.9],[76,1,1],[78,2,1.8],[76,4,.8]],[[74,0,1.7],[73,2,.9],[71,3,1.8]],[[71,.5,.8],[73,1.5,.9],[78,2.5,1.3],[76,4,.8]],[[68,0,1.7],[71,2,1],[73,3,1.5]],[[73,0,1],[71,1,1],[68,2,1],[66,3,1.7]],[[69,0,1.8],[73,2,.9],[76,3,1.8]],[[73,.5,1],[76,2,1],[78,3,1.7]],[[76,0,1],[73,1,1],[68,2,1],[66,3,1.8]]];
  const strings=[],bass=[],wood=[],melody=[],glass=[];
  for(let bar=0;bar<32;bar++){
    const b=bar*5,chord=chords[bar%8],section=Math.floor(bar/8);
    for(const pitch of chord.slice(1))strings.push(n(pitch,b,4.9,section===0?34:43));
    for(const [offset,pitch] of [[0,chord[0]],[3,chord[0]+12]])bass.push(n(pitch,b+offset,1.8,section===1||section===2?54:43));
    const pattern=section===2?[3,null,2,4,1]:[1,3,null,2,4];
    pattern.forEach((k,j)=>{if(k!==null)wood.push(n(chord[k]+12,b+j,.48,section===0?38:49));});
    if(bar>=4)for(const [pitch,offset,length] of theme[bar%8])melody.push(n(pitch+(section===2&&offset===2?12:0),b+offset,length,section===0||section===3?58:49));
    if(bar>=12&&bar<28&&bar%2===0){glass.push(n(chord[2]+12,b+1.5,1.25,47),n(chord[3]+12,b+3.5,1.25,42));}
  }
  for(const [track,notes] of [['Strings',strings],['Bass',bass],['Wood',wood],['Melody',melody],['Glass',glass]])await call('write_notes',{track,start_bar:1,bars:32,notes,name:'Transcribed daytime '+track,...A});
  for(const [name,at_bar] of [['Falling starglass',1],['Garden theme',9],['Bright bridge',17],['Homeward',25]])await call('add_marker',{name,at_bar,...A});
  const a=await call('analyse_song',A);
  console.log('ASTRAL_DAY_SOURCE',JSON.stringify({id:p.project_id,open_in_app:p.open_in_app,length:a.length,problems:a.problems}));
}
await c.close();
JS
