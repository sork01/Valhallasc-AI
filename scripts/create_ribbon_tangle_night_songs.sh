#!/bin/sh
# Arrange the active Ribbonwild and Tanglecrown day scores as editable night remixes.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-ribbon-tangle-night',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args={}) {const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
const note=(pitch,beat,beats,velocity)=>({pitch,beat,beats,velocity});
const specs=[
 {zone:'ribbonwild',id:'5a0f5aed7413939b',source:'702081f8ef8eb02a',title:'Valhalla Ribbonwild Night - Lanterns After the Parade',bpm:96,key:'D major',
  pad:'Silk strings',bass:'Parade bass',keys:'Painted clav',lead:'Festival brass',bell:'Bell garlands',oldDrum:'Drum cart',
  instruments:[['Silk strings','sork60','Mellow Pad'],['Parade bass','sorkbass2','Fingered'],['Painted clav','sork60','Clavinet'],['Festival brass','sork60','Juno Brass'],['Bell garlands','dexed','TUB BELLS']],
  mix:[['Silk strings',-27,0],['Parade bass',-7,0],['Painted clav',-15,-.23],['Festival brass',-19,.1],['Bell garlands',-25,.3]],
  cycles:[['Dmaj7','A7','Bm7','Gmaj7','Dmaj7','Em7','A7','Dmaj7'],['Dmaj7','A7','Bm7','Gmaj7','Em7','Bm7','A7','Dmaj7'],['Bm7','Gmaj7','Dmaj7','A7','Bm7','Gmaj7','Em7','A7'],['Dmaj7','A7','Bm7','Gmaj7','Em7','A7','Dmaj7','Dmaj7']],
  roots:{Dmaj7:'D2',A7:'A1',Bm7:'B1',Gmaj7:'G1',Em7:'E2'},
  tones:{Dmaj7:['D4','F#4','A4','C#5'],A7:['A3','C#4','E4','G4'],Bm7:['B3','D4','F#4','A4'],Gmaj7:['G3','B3','D4','F#4'],Em7:['E4','G4','B4','D5']},
  motifs:{8:[['D5',.5,.5],['F#5',1.5,.5],['A5',2.5,.85]],9:[['G5',.5,.55],['E5',1.75,.5],['C#5',2.75,.7]],16:[['F#5',.5,.65],['D5',1.75,.5],['B4',2.75,.7]],17:[['B4',.5,.6],['D5',1.75,.5],['G5',2.75,.75]]},
  kick:[0,7,11],snare:[4,12],hat:[2,6,10,14],rim:[15],velocity:58,
  markers:['Last parade light','Lantern procession','Painted answer','Market asleep']},
 {zone:'tanglecrown',id:'b9a83443f1d8b949',source:'f7cc1c7e9bc03c07',title:'Valhalla Tanglecrown Night - Rain Under the Leaves',bpm:88,key:'A minor',
  pad:'Rain mist',bass:'Root bass',keys:'Canopy marimba',lead:'River flute',bell:'Leaf glints',oldDrum:'Basin drums',
  instruments:[['Rain mist','sork60','Mellow Pad'],['Root bass','sorkbass2','Fingered'],['Canopy marimba','dexed','MARIMBA'],['River flute','dexed','WHISTLE FLUTE'],['Leaf glints','dexed','GLASS VIBES']],
  mix:[['Rain mist',-26,0],['Root bass',-6,0],['Canopy marimba',-12,-.2],['River flute',-12,.15],['Leaf glints',-25,.28]],
  cycles:[['Am7','Fmaj7','Cmaj7','G7','Am7','Dm7','Fmaj7','G7'],['Am7','Fmaj7','Cmaj7','G7','Dm7','Am7','G7','Am7'],['Cmaj7','Fmaj7','Am7','G7','Dm7','Fmaj7','G7','Am7'],['Am7','Fmaj7','Cmaj7','G7','Dm7','Fmaj7','G7','Am7']],
  roots:{Am7:'A1',Fmaj7:'F2',Cmaj7:'C2',G7:'G1',Dm7:'D2'},
  tones:{Am7:['A4','C5','E5','G5'],Fmaj7:['A4','C5','E5','F5'],Cmaj7:['G4','B4','C5','E5'],G7:['G4','B4','D5','F5'],Dm7:['A4','C5','D5','F5']},
  motifs:{8:[['A5',.5,.55],['C6',1.5,.5],['D6',2.25,.4],['E6',3,.65]],9:[['C6',.5,.6],['A5',1.75,.5],['F5',2.75,.7]],16:[['E5',.5,.65],['C5',1.75,.5],['G4',2.75,.7]],17:[['A4',.5,.6],['C5',1.75,.5],['F5',2.75,.7]]},
  kick:[0,10],snare:[8],hat:[2,6,10,14],rim:[5,13],velocity:56,
  markers:['Leaves close over','River flute','Basin answer','Rain thins']}
];
function row(hits,accent=[]) {const v=Array(16).fill('.');for(const i of hits)v[i]=accent.includes(i)?'X':'x';return v.join('')}
function melody(s,chords,section) {const out=[];for(let b=0;b<8;b++){const i=section*8+b,base=b*4,m=s.motifs[i];if(m){for(const [p,at,d] of m)out.push(note(p,base+at,d,section===1?61:55));continue}const t=s.tones[chords[i]];const phrase=section===0?[[t[0],.5,.5],[t[1],1.75,.5],[t[2],3,.55]]:section===2?[[t[3],.5,.7],[t[2],2,.5],[t[0],3,.6]]:section===3&&b>=6?[[t[2],.5,.55],[t[0],2.5,1]]:b%2?[[t[2],.5,.6],[t[0],2.5,.8]]:[[t[0],.5,.55],[t[1],1.75,.55],[t[2],3,.6]];for(const [p,at,d] of phrase)out.push(note(p,base+at,d,section===0?45:54))}return out}
for(const s of specs){if(process.env.ZONES&&!process.env.ZONES.split(',').includes(s.zone))continue;
 const A={project_id:s.id};const day=await call('open_project',A);if(day.project_id!==s.id)throw Error(`${s.zone}: wrong editable copy`);
 await call('rename_project',{...A,name:s.title});await call('set_tempo',{...A,bpm:s.bpm});await call('set_key',{...A,key:s.key});
 for(const t of day.tracks.filter(t=>t.instrument))await call('clear_bars',{...A,track:t.name});
 if(day.tracks.some(t=>t.name===s.oldDrum))await call('remove_track',{...A,track:s.oldDrum});
 for(const [track,instrument,preset]of s.instruments)if(track!==s.lead)await call('set_instrument',{...A,track,instrument,preset});
 for(const [track,volume_db,pan]of s.mix)if(track!==s.lead)await call('set_mix',{...A,track,volume_db,pan});
 for(const [parameter,value]of [['env.attack',.08],['env.release',.45]])await call('automate',{...A,track:s.pad,parameter,points:[{bar:1,value},{bar:33,value}]});
 const chords=s.cycles.flat();await call('write_chords',{...A,track:s.pad,start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:54,velocity:41,name:'Night harmony'});
 const bass=[],keys=[],bell=[];for(let i=0;i<32;i++){const at=i*4,t=s.tones[chords[i]];bass.push(note(s.roots[chords[i]],at,1.5,i%8===0?59:54),note(s.roots[chords[i]],at+(s.zone==='ribbonwild'?2.75:2.5),.65,41));keys.push(note(t[1],at+.5,.4,49),note(t[2],at+2.5,.45,44));if(i%4===0)bell.push(note(t[3],at,.5,35))}
 for(const [track,notes,name]of [[s.bass,bass,'Night steps'],[s.keys,keys,'After-dark reflections'],[s.bell,bell,'Distant lights']])await call('write_notes',{...A,track,start_bar:1,bars:32,notes,name});
 if(day.tracks.some(t=>t.name===s.lead))await call('remove_track',{...A,track:s.lead});
 if(!day.tracks.some(t=>t.name==='Night breakbeat'))await call('add_track',{...A,name:'Night breakbeat',instrument:'axiom8',preset:'Hip-hop',volume_db:-12});
 else {await call('clear_bars',{...A,track:'Night breakbeat'});await call('set_preset',{...A,track:'Night breakbeat',preset:'Hip-hop'});}
 if(!day.tracks.some(t=>t.name==='Chillhop hi-hat'))await call('add_track',{...A,name:'Chillhop hi-hat',instrument:'axiom8',preset:'Chillhop',volume_db:-10});
 else {await call('clear_bars',{...A,track:'Chillhop hi-hat'});await call('set_preset',{...A,track:'Chillhop hi-hat',preset:'Chillhop'});}
 for(let k=0;k<4;k++){
  const velocity=s.velocity-(k===0?5:k===3?3:0),hats=k===0?s.hat.filter((_,j)=>j%2===0):s.hat;
  await call('write_drums',{...A,track:'Night breakbeat',start_bar:k*8+1,bars:8,pattern:{kick:row([...new Set([...s.kick,s.zone==='ribbonwild'?11:10,s.zone==='ribbonwild'?11:10])],[0]),snare:row(s.snare),clap:row(k===2?s.rim:[])},swing:0,velocity,name:`${s.markers[k]} break`});
  await call('write_drums',{...A,track:'Chillhop hi-hat',start_bar:k*8+1,bars:8,pattern:{hat:row(hats)},swing:0,velocity,name:`${s.markers[k]} Chillhop hats`});
 }
 for(const [k,name]of s.markers.entries())await call('add_marker',{...A,name,at_bar:k*8+1});
 const a=await call('analyse_song',A);if(a.problems?.length)throw Error(`${s.zone}: ${a.problems.join('; ')}`);
 console.log(JSON.stringify({zone:s.zone,id:s.id,source:s.source,title:s.title,bpm:s.bpm,seconds:128*60/s.bpm,warnings:a.warnings}));
}
await c.close();
JS
