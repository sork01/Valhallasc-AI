#!/bin/sh
# Rewrite copies of the two daytime dybase2 projects as distinct night arrangements.
# Sources: Ashfall Run 7cb1d78917291ca2; Rimeveil Spiral cce5d9367601343c.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const c=new Client({name:'valhallasc-two-night-remixes',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args) {
  const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});
  if(r.isError) throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
  const d=JSON.parse(r.content[0].text);
  if(name==='analyse_song') console.log(name,JSON.stringify({project_id:d.project_id,length:d.length,harmony:d.harmony?.slice(0,8),problems:d.problems,warnings:d.warnings}));
  return d;
}
const note=(pitch,beat,beats,velocity=58)=>({pitch,beat,beats,velocity});
const flatten=(bars,beatsPerBar,offset=0)=>bars.flatMap((bar,i)=>bar.map(([pitch,at,length,velocity])=>note(pitch,(i+offset)*beatsPerBar+at,length,velocity)));

// Emberfall: the original's E-G-E-D-E and F/E friction remain, but the fast
// gallop becomes a half-time ember pulse with new Em/F/C/B7 harmony and phrases.
{
  const project_id='90d3be446ee5a58f', A={project_id};
  await call('open_project',A);
  await call('rename_project',{name:'Valhalla Crags Night - Embers Beneath the Ridge',...A});
  await call('set_tempo',{bpm:92,...A});
  await call('set_key',{key:'E phrygian',...A});
  try { await call('remove_track',{track:'Echo',...A}); } catch { /* already removed on a resumed run */ }
  for(const [track,preset] of [['Lead','Unison Lead'],['Lead Snarl','Bell Tine'],['Arp','Bell Tine'],['Stabs','Clavinet'],['Pad','Mellow Pad']])
    await call('set_instrument',{track,instrument:'sork60',preset,...A});
  for(const [track,volume_db,pan] of [['Drums',-6,0],['Bass',-15,0],['Arp',-10,-.25],['Lead',-25,.1],['Lead Snarl',-3,.2],['Stabs',1,-.2],['Pad',-28,0]])
    await call('set_mix',{track,volume_db,pan,...A});
  const chords=[
    'Em7 Fmaj7 Cmaj7 B7 Em7 Gmaj7 Am7 B7',
    'Em7 Fmaj7 Cmaj7 D7 Gmaj7 Fmaj7 B7 Em7',
    'Em7 Cmaj7 Fmaj7 B7 Em7 Gmaj7 Am7 B7',
    'Cmaj7 Fmaj7 Em7 D7 Cmaj7 B7 Em7 Em7',
  ].join(' ').split(' ');
  await call('write_chords',{track:'Pad',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:55,velocity:46,name:'Ridge afterglow',...A});
  const roots={Em7:'E2',Fmaj7:'F2',Cmaj7:'C2',B7:'B1',Gmaj7:'G2',Am7:'A2',D7:'D2'};
  const tones={Em7:['E4','G4','B4'],Fmaj7:['F4','A4','C5'],Cmaj7:['C4','E4','B4'],B7:['B3','D#4','A4'],Gmaj7:['G3','B3','F#4'],Am7:['A3','C4','G4'],D7:['D4','F#4','C5']};
  const bass=[],pluck=[],keys=[],drums=[];
  chords.forEach((chord,i)=>{
    const b=i*4, triad=tones[chord];
    bass.push(note(roots[chord],b,1.65,65),note(roots[chord],b+2.5,.9,48));
    for(const [j,at] of [.75,1.75,3.25].entries()) pluck.push(note(triad[(j+i)%3],b+at,.4,j===0?54:43));
    if(i>=8 && i<28) for(const at of [1.5,3.5]) for(const p of [triad[1],triad[2]]) keys.push(note(p,b+at,.25,35));
    if(i<24) {
      drums.push(note(36,b,.12,48),note(38,b+2,.12,29));
      if(i%2===0) drums.push(note(36,b+2.75,.12,29));
      for(const at of [.5,1.5,2.5,3.5]) drums.push(note(42,b+at,.09,23));
    }
  });
  for(const [track,notes,name] of [['Bass',bass,'Slow coal steps'],['Arp',pluck,'Offbeat sparks'],['Stabs',keys,'Quiet chord replies'],['Drums',drums,'Half-time ash pulse']])
    await call('write_notes',{track,start_bar:1,bars:32,notes,name,...A});
  const motif=[
    [['E5',.5,.75,68],['G5',1.5,.4,56],['F5',2.25,.4,53],['E5',3,.75,62]],
    [['C5',.75,.8,59],['A4',2,.5,52],['C5',3,.5,55]],
    [['G4',.5,.5,57],['B4',1.5,.7,61],['E5',2.75,.8,64]],
    [['D#5',.5,.5,53],['B4',1.25,.6,60],['A4',2.25,.5,49],['B4',3,.75,58]],
    [['E5',.25,1,65],['D5',1.75,.5,52],['B4',2.75,.75,56]],
    [['G4',.75,.5,54],['B4',1.5,.5,58],['D5',2.5,1,61]],
    [['C5',.5,.65,58],['B4',1.5,.5,52],['A4',2.5,1,56]],
    [['B4',.5,.5,59],['D#5',1.5,.5,54],['E5',2.5,1,64]],
  ];
  const answer=[
    [['B4',.25,.75,57],['D5',1.5,.5,55],['E5',2.5,1,63]],
    [['E5',.5,.5,57],['C5',1.5,.75,51],['G4',2.75,.8,55]],
    [['F5',.5,.75,58],['E5',1.75,.5,52],['C5',2.75,.8,54]],
    [['B4',.5,.75,58],['A4',1.75,.5,50],['F#4',2.75,.75,56]],
    [['G4',.5,.5,54],['B4',1.5,.5,58],['E5',2.5,1,62]],
    [['D5',.5,1,60],['B4',2,.5,53],['G4',3,.5,50]],
    [['C5',.5,.5,54],['E5',1.5,.75,60],['G5',2.75,.8,58]],
    [['F5',.5,.5,55],['D#5',1.5,.5,53],['B4',2.5,1,60]],
  ];
  await call('write_notes',{track:'Lead',start_bar:1,bars:32,notes:[...flatten(motif,4,8),...flatten(motif.map((bar,i)=>i===7?[['E5',.5,2,63]]:bar),4,24)],name:'Ember motif, reshaped',...A});
  await call('write_notes',{track:'Lead Snarl',start_bar:1,bars:32,notes:flatten(answer,4,16),name:'Night response',...A});
  for(const [name,at_bar] of [['Coals under the ridge',1],['A distant trail',9],['Embers answer',17],['The fire settles',25]]) await call('add_marker',{name,at_bar,...A});
  await call('analyse_song',A);
  console.log('CRAGS_NIGHT_PROJECT_ID='+project_id);
}

// Rimeveil: the daytime A-C#-F# ascent is heard in 6/8, answered by a new
// falling figure. Long chords and three sparse bell steps replace the spiral's
// constant eighth notes; drums are absent and the bass moves only once a bar.
{
  const project_id='4091d2184af5bf68', A={project_id};
  await call('open_project',A);
  await call('rename_project',{name:'Valhalla Rimeveil Night - Stars Beneath the Ice',...A});
  await call('set_tempo',{bpm:88,...A});
  await call('set_time_signature',{numerator:6,denominator:8,...A});
  await call('set_key',{key:'F# dorian',...A});
  try { await call('remove_track',{track:'Drums',...A}); } catch { /* already removed on a resumed run */ }
  for(const track of ['Bells','Pad','Bass','Sparkle','Lead','Strings'])
    await call('clear_bars',{track,from_bar:33,bars:12,...A});
  for(const [track,preset] of [['Pad','Glass Pad'],['Lead','Whistle'],['Strings','Juno Strings']])
    await call('set_instrument',{track,instrument:'sork60',preset,...A});
  for(const [track,volume_db,pan] of [['Bells',-18,-.25],['Pad',-22,0],['Bass',-14,0],['Sparkle',-20,.3],['Lead',-22,.1],['Strings',-20,-.1]])
    await call('set_mix',{track,volume_db,pan,...A});
  const chords=[
    'F#m7 Dmaj7 Bm7 Eadd9 F#m7 Amaj7 Bm7 C#m7',
    'Dmaj7 Amaj7 Eadd9 C#m7 Bm7 Dmaj7 Eadd9 F#m7',
    'F#m7 Bm7 Dmaj7 Amaj7 F#m7 Eadd9 C#m7 Bm7',
    'Dmaj7 Eadd9 F#m7 C#m7 Bm7 Eadd9 F#m7 F#m7',
  ].join(' ').split(' ');
  await call('write_chords',{track:'Pad',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:56,velocity:42,name:'Blue ice chords',...A});
  const roots={ 'F#m7':'F#2','Dmaj7':'D2','Bm7':'B1','Eadd9':'E2','Amaj7':'A1','C#m7':'C#2' };
  const tones={ 'F#m7':['F#4','A4','C#5'],'Dmaj7':['D4','F#4','A4'],'Bm7':['B3','D4','F#4'],'Eadd9':['E4','G#4','B4'],'Amaj7':['A3','C#4','E4'],'C#m7':['C#4','E4','G#4'] };
  const bells=[],bass=[],sparkle=[],strings=[];
  chords.forEach((chord,i)=>{
    const b=i*3,t=tones[chord];
    bass.push(note(roots[chord],b,2.35,i%8===0?55:45));
    bells.push(note(t[2],b+.25,.42,57),note(t[1],b+1.25,.42,46),note(t[0],b+2.25,.42,49));
    if(i%4===3) sparkle.push(note(i%8===3?'F#6':'C#6',b+2,.6,35));
    if(i>=16 && i<28) strings.push(note(t[1],b,2.5,39));
  });
  for(const [track,notes,name] of [['Bass',bass,'One breath per ring'],['Bells',bells,'Falling ice steps'],['Sparkle',sparkle,'Far stars'],['Strings',strings,'Aurora answer']])
    await call('write_notes',{track,start_bar:1,bars:32,notes,name,...A});
  const rising=[
    [['A4',.5,.6,63],['C#5',1.35,.45,55],['F#5',2,.8,66]],
    [['E5',.5,.5,55],['D5',1.4,1.2,57]],
    [['F#4',.5,.5,53],['B4',1.3,.5,58],['D5',2.1,.75,60]],
    [['C#5',.35,.6,58],['B4',1.3,.5,52],['G#4',2.1,.75,54]],
    [['A4',.4,.5,56],['C#5',1.25,.5,58],['E5',2.1,.7,62]],
    [['F#5',.5,1,62],['E5',2,.6,55]],
    [['D5',.5,.55,57],['C#5',1.35,.5,52],['B4',2.15,.65,55]],
    [['C#5',.5,.75,57],['F#4',1.75,1.1,58]],
  ];
  const falling=[
    [['F#5',.45,.85,61],['C#5',1.75,.5,54],['A4',2.4,.45,51]],
    [['D5',.5,.65,56],['B4',1.55,.9,53]],
    [['A4',.5,.5,54],['C#5',1.35,.5,57],['F#5',2.1,.75,62]],
    [['E5',.5,1.1,60],['C#5',2,.6,53]],
    [['B4',.5,.5,53],['D5',1.35,.55,58],['F#5',2.15,.7,60]],
    [['E5',.5,.55,58],['C#5',1.35,.5,52],['A4',2.1,.7,53]],
    [['G#4',.5,.5,54],['B4',1.35,.5,57],['C#5',2.1,.75,58]],
    [['F#4',.5,2.2,59]],
  ];
  await call('write_notes',{track:'Lead',start_bar:1,bars:32,notes:[...flatten(rising,3,4),...flatten(falling,3,12),...flatten(rising,3,20),...flatten(falling.slice(0,4),3,28)],name:'Climbing stars and falling answer',...A});
  for(const [name,at_bar] of [['Ice settles',1],['The old ascent',5],['Stars answer',13],['Aurora opens',21],['Snow returns',29]]) await call('add_marker',{name,at_bar,...A});
  await call('analyse_song',A);
  console.log('RIME_NIGHT_PROJECT_ID='+project_id);
}
await c.close();
JS
