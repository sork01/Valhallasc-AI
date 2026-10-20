#!/bin/sh
# Make night arrangements on dybase2 copies of the Wyrdwood and Bifrost scores.
# Daytime source ids: 75b165ad74a360fb and 0c009f9d39d87dc3.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const c=new Client({name:'valhallasc-wyrd-sky-night-remixes',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args){const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);return JSON.parse(r.content[0].text)}
const n=(pitch,beat,beats,velocity=55)=>({pitch,beat,beats,velocity});
const at=(bars,meter,offset)=>bars.flatMap((bar,i)=>bar.map(([pitch,beat,beats,velocity])=>n(pitch,(i+offset)*meter+beat,beats,velocity)));

// Wyrdwood: the A-C-E daytime flute rise now appears as a restrained night
// call. The walking six-note arpeggio becomes three separated waltz steps.
{
  const project_id='a2ac7b7ae8fa8ad8',A={project_id};
  await call('open_project',A);
  await call('rename_project',{name:'Valhalla Wyrdwood Night - Lanterns Under the Ash',...A});
  await call('set_tempo',{bpm:82,...A});
  await call('set_key',{key:'A minor',...A});
  try { await call('remove_track',{track:'Drums',...A}); } catch { /* already removed on a resumed run */ }
  for(const track of ['Arp','Pad','Bass','Flute','Strings','Bells'])await call('clear_bars',{track,from_bar:1,bars:32,...A});
  for(const [track,preset] of [['Pad','Mellow Pad'],['Flute','Unison Lead'],['Strings','Juno Strings']])await call('set_instrument',{track,instrument:'sork60',preset,...A});
  for(const [track,volume_db,pan] of [['Arp',-11,-.2],['Pad',-26,0],['Bass',2,0],['Flute',-23,.12],['Strings',-13,-.15],['Bells',-16,.25]])await call('set_mix',{track,volume_db,pan,...A});
  const chords=('Am7 G6 Fmaj7 E7 Am7 Cmaj7 Dm7 E7 '+
                'Am7 Fmaj7 Cmaj7 G6 Dm7 Am7 E7 Am7 '+
                'Fmaj7 Cmaj7 Dm7 E7 Am7 G6 Fmaj7 E7 '+
                'Am7 G6 Fmaj7 Cmaj7 Dm7 E7 Am7 Am7').split(' ');
  await call('write_chords',{track:'Pad',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:54,velocity:42,name:'Roots beneath the ash',...A});
  const roots={Am7:'A1',G6:'G1',Fmaj7:'F1',E7:'E2',Cmaj7:'C2',Dm7:'D2'};
  const tones={Am7:['A3','C4','E4'],G6:['G3','B3','E4'],Fmaj7:['F3','A3','C4'],E7:['E3','G#3','D4'],Cmaj7:['C4','E4','G4'],Dm7:['D4','F4','A4']};
  const bass=[],arp=[],bells=[],strings=[];
  chords.forEach((chord,i)=>{const b=i*3,t=tones[chord];
    bass.push(n(roots[chord],b,2.45,i%8===0?57:47));
    arp.push(n(t[0],b+.1,.55,53),n(t[2],b+1.15,.38,44),n(t[1],b+2.15,.38,42));
    if(i>=8&&i<28&&i%4===3)bells.push(n(i%8===3?'E5':'A4',b+2.15,.5,31));
    if(i>=16&&i<28)strings.push(n(t[1],b+.25,2.2,36));
  });
  for(const [track,notes,name] of [['Bass',bass,'Slow forest steps'],['Arp',arp,'Three ash leaves'],['Bells',bells,'Distant lanterns'],['Strings',strings,'Canopy at rest']])await call('write_notes',{track,start_bar:1,bars:32,notes,name,...A});
  const theme=[
    [['A4',.35,.65,61],['C5',1.3,.55,55],['E5',2.1,.68,64]],
    [['D5',.45,.85,56],['B4',1.85,.7,52]],
    [['C5',.4,.65,57],['A4',1.45,.5,51],['F4',2.2,.65,53]],
    [['G#4',.4,.65,54],['B4',1.4,.55,55],['E5',2.2,.55,59]],
    [['A4',.35,1.2,60],['E5',2.05,.7,56]],
    [['G4',.4,.6,52],['C5',1.35,.65,56],['E5',2.25,.5,58]],
    [['F5',.4,.75,58],['D5',1.55,.7,52]],
    [['B4',.4,.6,55],['G#4',1.4,.55,50],['A4',2.2,.65,59]],
  ];
  const answer=[
    [['C5',.4,.75,58],['A4',1.75,.85,52]],
    [['B4',.4,.65,54],['G4',1.55,.7,51]],
    [['A4',.4,.65,55],['C5',1.4,.55,56],['F5',2.2,.55,58]],
    [['E5',.4,.8,58],['B4',1.85,.75,52]],
    [['E5',.4,.65,57],['C5',1.5,.8,53]],
    [['D5',.4,.65,54],['B4',1.5,.75,51]],
    [['C5',.4,.65,55],['A4',1.5,.75,52]],
    [['A4',.4,2.2,59]],
  ];
  await call('write_notes',{track:'Flute',start_bar:1,bars:32,notes:[...at(theme,3,8),...at(answer,3,16),...at(theme.slice(0,4),3,24),...at([[['C5',.4,.8,54]],[['B4',.4,.8,51]],[['G#4',.4,.7,52]],[['A4',.4,2.1,58]]],3,28)],name:'Wanderer call and lantern answer',...A});
  for(const [name,at_bar] of [['Ash leaves',1],['The old path',9],['Lantern answer',17],['Forest settles',25]])await call('add_marker',{name,at_bar,...A});
  const a=await call('analyse_song',A);console.log('WYRD',JSON.stringify({project_id,length:a.length,problems:a.problems,warnings:a.warnings}));
}

// Bifrost: preserve the daytime A-F#-A ascent and D lydian's raised fourth,
// but replace constant eighths and the storm bridge with a floating 4/4 pulse.
{
  const project_id='f8d95f2b7456bee1',A={project_id};
  await call('open_project',A);
  await call('rename_project',{name:'Valhalla Bifrost Night - Stars Above the Rift',...A});
  await call('set_tempo',{bpm:76,...A});
  await call('set_key',{key:'D lydian',...A});
  for(const track of ['Arp','Pad','Sparkle','Flute','Bass','Strings','Drums'])await call('clear_bars',{track,from_bar:1,bars:32,...A});
  for(const [track,preset] of [['Pad','Mellow Pad'],['Flute','Unison Lead'],['Strings','Juno Strings']])await call('set_instrument',{track,instrument:'sork60',preset,...A});
  for(const [track,volume_db,pan] of [['Arp',-16,-.2],['Pad',-27,0],['Sparkle',-15,.25],['Flute',-24,.12],['Bass',1,0],['Strings',-15,-.15],['Drums',-2,0]])await call('set_mix',{track,volume_db,pan,...A});
  const chords=('Dmaj7 E6 Bm7 Amaj7 Dmaj7 E6 F#m7 Bm7 '+
                'Dmaj7 Amaj7 E6 Bm7 F#m7 E6 Bm7 Dmaj7 '+
                'Bm7 F#m7 E6 Amaj7 Dmaj7 E6 F#m7 Bm7 '+
                'Dmaj7 E6 Bm7 Amaj7 F#m7 E6 Dmaj7 Dmaj7').split(' ');
  await call('write_chords',{track:'Pad',start_bar:1,bars:32,progression:chords.join(' '),style:'block',register:57,velocity:42,name:'Skyglass harmony',...A});
  const roots={Dmaj7:'D2',E6:'E2',Bm7:'B1',Amaj7:'A1','F#m7':'F#2'};
  const tones={Dmaj7:['D4','F#4','A4','C#5'],E6:['E4','G#4','B4','C#5'],Bm7:['B3','D4','F#4','A4'],Amaj7:['A3','C#4','E4','G#4'],'F#m7':['F#3','A3','C#4','E4']};
  const bass=[],arp=[],sparkle=[],strings=[],drums=[];
  chords.forEach((chord,i)=>{const b=i*4,t=tones[chord];
    bass.push(n(roots[chord],b,2.6,i%8===0?57:46));
    arp.push(n(t[0],b+.5,.45,52),n(t[2],b+2,.45,45),n(t[3],b+3.25,.38,42));
    if(i>=8&&i<28&&i%4===3)sparkle.push(n(i%8===3?'G#5':'C#6',b+3,.5,31));
    if(i>=16&&i<28)strings.push(n(t[1],b+.35,3,36));
    if(i>=8&&i<28){drums.push(n(36,b,.12,35),n(38,b+2,.12,23));for(const beat of [1.5,3.5])drums.push(n(42,b+beat,.08,20));}
  });
  for(const [track,notes,name] of [['Bass',bass,'Rift below'],['Arp',arp,'Three floating shards'],['Sparkle',sparkle,'High stars'],['Strings',strings,'Sky after the storm'],['Drums',drums,'Soft faraway pulse']])await call('write_notes',{track,start_bar:1,bars:32,notes,name,...A});
  const theme=[
    [['A4',.45,.75,59],['F#5',1.65,.65,55],['A5',2.8,.8,62]],
    [['G#5',.55,.9,58],['E5',2.2,1.1,54]],
    [['F#5',.5,.8,57],['D5',1.8,.65,52],['B4',2.9,.75,54]],
    [['C#5',.5,.8,54],['E5',1.8,.65,56],['G#5',2.9,.75,59]],
    [['A5',.45,1.1,61],['F#5',2.3,.85,54]],
    [['G#5',.5,.75,57],['E5',1.7,.65,52],['C#5',2.8,.8,53]],
    [['F#5',.5,.85,57],['D5',2.1,.8,52]],
    [['A4',.5,2.6,58]],
  ];
  const answer=[
    [['F#5',.5,.8,57],['A5',1.85,.75,59],['C#6',3,.7,60]],
    [['A5',.55,.95,56],['F#5',2.2,1,53]],
    [['G#5',.5,.8,57],['E5',1.8,.7,52],['B4',3,.65,52]],
    [['C#5',.5,.8,54],['E5',1.8,.7,56],['G#5',3,.65,58]],
    [['A5',.5,1.1,59],['F#5',2.3,.9,53]],
    [['G#5',.5,.8,55],['E5',2.1,.9,52]],
    [['F#5',.5,.8,56],['C#5',2.1,.9,51]],
    [['D5',.5,2.5,58]],
  ];
  await call('write_notes',{track:'Flute',start_bar:1,bars:32,notes:[...at(theme,4,8),...at(answer,4,16),...at(theme.slice(0,4),4,24),...at([[['F#5',.5,.9,55]],[['E5',.5,.9,53]],[['C#5',.5,.9,51]],[['D5',.5,2.4,57]]],4,28)],name:'The old ascent over a quieter sky',...A});
  for(const [name,at_bar] of [['Stars in the glass',1],['The old ascent',9],['Rift answers',17],['Night sky clears',25]])await call('add_marker',{name,at_bar,...A});
  const a=await call('analyse_song',A);console.log('SKY',JSON.stringify({project_id,length:a.length,problems:a.problems,warnings:a.warnings}));
}
await c.close();
JS
