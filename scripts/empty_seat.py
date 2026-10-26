#!/usr/bin/env python3
"""The Empty Seat: persistent, additive campaign overlay. Reapplied by sync-world."""
import json
import math
import sys
from collections import deque
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'es'
TEXT = {}
def tr(en, sv):
    TEXT[en] = sv
    return en

def content():
    """Zone, level, giver, title, lead, action, revelation. English and Swedish are authored together."""
    return [
(0, 2, 'smith', tr('Ash in the Bread', 'Aska i brödet'),
 tr('Bram found warm ash inside a loaf baked in a cold oven. Follow the ember print north of Alderhaven. Stand still in its circle and listen. Something beneath the meadow is remembering a name.', 'Bram fann varm aska i ett bröd bakat i en kall ugn. Följ glödspåret norr om Alderhaven. Stå stilla i cirkeln och lyssna. Något under ängen minns ett namn.'), 'memory',
 tr('A giant hand cups a tiny flame against a blizzard. A voice says: Not the children. Take my winter instead. The ash spells ELDMARR, then cools.', 'En jättes hand skyddar en liten låga mot snöstormen. En röst säger: Inte barnen. Ta min vinter i stället. Askan skriver ELDMARR och svalnar.')),
(1, 7, 'crags_scout', tr('The Cinder That Followed You', 'Glöden som följde dig'),
 tr('The ash has crawled into a discarded forge mould. Step into the ember circle to draw out the Cinder Without a Hearth and defeat it. Kael thinks it is tracking old hammer marks, not people.', 'Askan har krupit in i en kasserad gjutform. Gå in i glödcirkeln för att locka fram Glöden utan härd och besegra den. Kael tror att den följer gamla hammarmärken, inte människor.'), 'echo',
 tr('Cinder Without a Hearth', 'Glöden utan härd')),
(2, 12, 'rime_loremaster', tr('A Warmth Older Than Spring', 'En värme äldre än våren'),
 tr('Ylva knows a lullaby about a winter that never ended. Listen at the thaw mark without moving or fighting. The gods are named in every verse except the one that explains who lit the fire.', 'Ylva kan en vaggvisa om en vinter som aldrig tog slut. Lyssna vid tömärket utan att röra dig eller slåss. Gudarna nämns i varje vers utom den som berättar vem som tände elden.'), 'memory',
 tr('The ice remembers roots wrapped in a giant\'s burning hands. Above him, the first houses rise. A child asks his name. The singer has been taught to leave that part silent.', 'Isen minns rötter omslutna av en jättes brinnande händer. Ovanför honom byggs de första husen. Ett barn frågar vad han heter. Sångaren har lärt sig att vara tyst just där.')),
(3, 17, 'fen_lamplighter', tr('The Name in the Drowned Ledger', 'Namnet i den dränkta liggaren'),
 tr('A drowned ledger lists nine captains receiving seats in a distant hall. Black water eats the name beneath theirs. Call the Oath-Eater from the circle and recover what it is swallowing.', 'En dränkt liggare listar nio kaptener som får platser i en avlägsen hall. Svart vatten äter namnet under deras. Kalla fram Edsätaren ur cirkeln och återta det den slukar.'), 'echo',
 tr('Oath-Eater', 'Edsätaren')),
(4, 20, 'city_herald', tr('The Tenth Place Setting', 'Den tionde dukningen'),
 tr('Bran found a banquet inventory: ten cups, nine chairs. Visit the old setting and listen to the missing toast. The captains were paid before their master ever reached the door.', 'Bran hittade en festförteckning: tio bägare, nio stolar. Besök den gamla dukningen och lyssna till den saknade skålen. Kaptenerna fick sin lön innan deras mästare ens nådde dörren.'), 'memory',
 tr('Nine cups ring. The tenth is turned upside down. A herald rehearses: The forge has gone out. Behind the wall, a hammer answers once.', 'Nio bägare klingar. Den tionde vänds upp och ned. En härold övar: Smedjan har slocknat. Bakom väggen svarar en hammare en gång.')),
(6, 25, 'wyrd_wright', tr('Keep One Root Alive', 'Håll en rot vid liv'),
 tr('Hallveig has found a root hot enough to blister bark. Hold the marked circle for twenty seconds while the sootlings attack. The root carries the same warmth as Bram\'s ash. This time you must use it to save something.', 'Hallveig har hittat en rot så het att barken spricker. Håll den markerade cirkeln i tjugo sekunder medan sotvarelserna anfaller. Roten bär samma värme som Brams aska. Den här gången måste du använda den för att rädda något.'), 'hold',
 tr('Root-Sootling', 'Rotsotling')),
(7, 32, 'sky_veleda', tr('An Invitation With No Door', 'En inbjudan utan dörr'),
 tr('Veleda hears three notes trapped in the wind. Ring all three oath bells within thirty seconds to unfold an invitation addressed to the First Keeper of the Forge. Nobody delivered it.', 'Veleda hör tre toner fångade i vinden. Ring alla tre edsklockor inom trettio sekunder för att veckla ut en inbjudan till Smedjans förste väktare. Ingen lämnade fram den.'), 'chime',
 tr('The invitation bears Eldmarr\'s name. Its seal says: A seat beside the fire you gave us. On the back, a later hand has written: Do not admit.', 'Inbjudan bär Eldmarrs namn. Sigillet säger: En plats vid elden du gav oss. På baksidan har en senare hand skrivit: Släpp inte in honom.')),
(8, 37, 'deep_halla', tr('The First Shadow', 'Den första skuggan'),
 tr('Halla hauled up a chain link that casts a shadow against the current. Enter its circle and defeat the Shade of Eldmarr. It is a memory wearing anger, a fraction of the giant far beneath Asterion.', 'Halla drog upp en kedjelänk som kastar sin skugga mot strömmen. Gå in i cirkeln och besegra Eldmarrs skugga. Det är ett minne klätt i vrede, en spillra av jätten långt under Asterion.'), 'echo',
 tr('Shade of Eldmarr', 'Eldmarrs skugga')),
(9, 40, 'nacre_archivist', tr('What the Archive Was Paid to Forget', 'Vad arkivet fick betalt för att glömma'),
 tr('Vaela found a receipt for scraping a name from the Pearl Archive. Hold still beside the erased inscription. Read the empty space: the lie was purchased, copied and taught to children.', 'Vaela hittade ett kvitto på att skrapa bort ett namn ur Pärlarkivet. Stå stilla vid den utplånade inskriften. Läs tomrummet: lögnen köptes, kopierades och lärdes ut till barn.'), 'memory',
 tr('The receipt pays nine shares for one silence. The erased line returns: Eldmarr kept the roots alive through the Long Winter. The hall was built upon his gift.', 'Kvittot betalar nio andelar för en enda tystnad. Den utplånade raden återkommer: Eldmarr höll rötterna vid liv genom den långa vintern. Hallen byggdes på hans gåva.')),
(13, 43, 'astral_scholar', tr('A Constellation With One Star Missing', 'En stjärnbild med en stjärna som saknas'),
 tr('Vey charted nine bright stars around a dark tenth. Listen at the fallen star. Its light left the sky on the night the captains accepted their new titles: Wardens.', 'Vey kartlade nio ljusa stjärnor kring en mörk tionde. Lyssna vid den fallna stjärnan. Dess ljus lämnade himlen den natt kaptenerna tog emot sina nya titlar: väktare.'), 'memory',
 tr('Nine shadows bow to a shining hall. Below them, the tenth star is hammered into a ring. Each Warden is given one end of a chain and told never to listen.', 'Nio skuggor bugar mot en lysande hall. Under dem hamras den tionde stjärnan till en ring. Varje väktare får en kedjeände och befalls att aldrig lyssna.')),
(14, 48, 'prism_scholar', tr('Break the Beautiful Lie', 'Krossa den vackra lögnen'),
 tr('Asha\'s lens shows Eldmarr as a monster before the first chain touched him. Call out the Gilded Witness and break the false reflection. Someone made the betrayal look like a rescue.', 'Ashas lins visar Eldmarr som ett monster redan innan den första kedjan rörde honom. Kalla fram Det förgyllda vittnet och krossa den falska spegelbilden. Någon fick sveket att se ut som en räddning.'), 'echo',
 tr('Gilded Witness', 'Det förgyllda vittnet')),
(15, 53, 'orrery_scholar', tr('The Clock That Counts Downward', 'Klockan som räknar nedåt'),
 tr('Edda\'s buried clock has never measured hours. Stand in its measuring circle and hear what it counts. Every turn belongs to the fire trapped beneath the world.', 'Eddas begravda klocka har aldrig mätt timmar. Stå i mätcirkeln och hör vad den räknar. Varje varv tillhör elden som fångats under världen.'), 'memory',
 tr('The hands count chain fractures. A hundred years of heat press against nine failing links. The roots have begun carrying the pressure outward. This is not a future war. It has already started under your feet.', 'Visarna räknar sprickor i kedjorna. Hundra års hetta pressar mot nio sviktande länkar. Rötterna har börjat föra trycket utåt. Det här är inget framtida krig. Det har redan börjat under dina fötter.')),
(16, 58, 'moonspore_scholar', tr('Borrow a Dream That Is Not Yours', 'Låna en dröm som inte är din'),
 tr('Odo has grown a memory in a lantern cap. Keep still in the spore circle until it opens. It remembers a much younger Eldmarr, and it knows a way to let you walk through his last free night in Asterion.', 'Odo har odlat ett minne i en lyktsvamp. Stå stilla i sporcirkeln tills det öppnas. Det minns en mycket yngre Eldmarr och vet hur du kan vandra genom hans sista fria natt i Asterion.'), 'memory',
 tr('A giant kneels to warm a seedling. The dream asks you to bring three things to Asterion: the hand that gave, the promise that was made, and the hand that closed the chain. You carry them as memories.', 'En jätte knäböjer för att värma en planta. Drömmen ber dig föra tre ting till Asterion: handen som gav, löftet som gavs och handen som slöt kedjan. Du bär dem som minnen.')),
(17, 60, 'asterion_archon', tr('Before the Nine Chains', 'Före de nio kedjorna'),
 tr('Seraphine will open the city\'s buried memory. Walk through its three circles in order: the First Hearth, the Promised Table and the Closing Chain. Stand still at each to witness the Long Winter, the bargain and the betrayal. You remain yourself inside the vision; you can leave and return.', 'Seraphine öppnar stadens begravda minne. Gå genom dess tre cirklar i ordning: Den första härden, Det utlovade bordet och Kedjan som sluts. Stå stilla vid varje cirkel för att bevittna den långa vintern, avtalet och sveket. Du förblir dig själv i synen och kan lämna den och återvända.'), 'flashback', ''),
(19, 63, 'stormglass_scholar', tr('The Sea Cannot Swallow This Fire', 'Havet kan inte svälja denna eld'),
 tr('Orrin found salt boiling on a cold shore. Hold the cooling circle for twenty seconds against escaped furnace sparks. The sea is not putting out Eldmarr\'s fire; his heat is travelling through the world\'s roots beneath it.', 'Orrin fann salt som kokade på en kall strand. Håll kylcirkeln i tjugo sekunder mot förrymda ugnsgnistor. Havet släcker inte Eldmarrs eld; hans hetta färdas genom världens rötter under det.'), 'hold',
 tr('Furnace Spark', 'Ugnsgnista')),
(20, 68, 'sun_miller', tr('The Harvest of Tomorrow', 'Morgondagens skörd'),
 tr('Ada planted tomorrow\'s seed and harvested yesterday\'s ash. Read the ember furrow. Eldmarr is no longer sending memories by accident. He is offering you a warning, and a choice.', 'Ada sådde morgondagens frö och skördade gårdagens aska. Läs glödfåran. Eldmarr sänder inte längre minnen av misstag. Han erbjuder dig en varning och ett val.'), 'memory',
 tr('Eldmarr speaks through the grain: I warmed their cradle. They built a throne on my back. Stand aside when I rise. Beside the voice, a real wheat stalk turns to ash. His road upward runs through living homes.', 'Eldmarr talar genom säden: Jag värmde deras vagga. De byggde en tron på min rygg. Stig åt sidan när jag reser mig. Bredvid rösten blir ett riktigt veteax till aska. Hans väg upp går genom levande hem.')),
(21, 73, 'ribbon_host', tr('A Mask for the Man He Was', 'En mask för den han var'),
 tr('Mira\'s dancers remember the forge keeper as a gentle festival giant. An angry memory has stolen their masks. Enter the circle and defeat the Uninvited Guest before its borrowed face becomes the only version anyone remembers.', 'Miras dansare minns smedjans väktare som en vänlig festjätte. Ett vredgat minne har stulit deras masker. Gå in i cirkeln och besegra Den objudne gästen innan dess lånade ansikte blir den enda bild någon minns.'), 'echo',
 tr('The Uninvited Guest', 'Den objudne gästen')),
(22, 78, 'tangle_botanist', tr('The Root That Refused the Order', 'Roten som vägrade lyda'),
 tr('Tavi found one root growing against the others. Hold its circle for twenty seconds while chain thorns try to turn it back. Eldmarr has begun ordering the roots toward the pillars of the gods\' hall. Help this one keep feeding the forest.', 'Tavi hittade en rot som växer mot alla andra. Håll dess cirkel i tjugo sekunder medan kedjetörnen försöker vända den. Eldmarr har börjat styra rötterna mot pelarna under gudarnas hall. Hjälp denna rot att fortsätta ge skogen näring.'), 'hold',
 tr('Chain Thorn', 'Kedjetörne')),
(23, 80, 'heart_matriarch', tr('Count the Windows, Not the Thrones', 'Räkna fönstren, inte tronerna'),
 tr('Iria asks you to listen where the canopy homes meet the great root. You have learned why Eldmarr hates the hall. Now listen to the people who will fall with it.', 'Iria ber dig lyssna där trädkronans hem möter den stora roten. Du har lärt dig varför Eldmarr hatar hallen. Lyssna nu till människorna som faller med den.'), 'memory',
 tr('Supper bowls. A child practising a song. A carpenter promising to mend a window tomorrow. The root holds every voice at once. Eldmarr\'s revenge cannot choose only the guilty.', 'Kvällsmatsskålar. Ett barn som övar en sång. En snickare som lovar att laga ett fönster i morgon. Roten bär alla röster samtidigt. Eldmarrs hämnd kan inte välja bara de skyldiga.')),
(24, 80, 'heart_oracle', tr('A Third Answer', 'Ett tredje svar'),
 tr('Veya has heard two endings: leave the giant chained until the roots burn, or let him rise and melt them. Listen at the Living Pith for a third. Saving the world must not require calling the betrayal just.', 'Veya har hört två slut: lämna jätten fjättrad tills rötterna brinner eller låt honom resa sig och smälta dem. Lyssna vid Den levande märgen efter ett tredje. Att rädda världen får inte kräva att sveket kallas rättvist.'), 'memory',
 tr('The pith answers: Break the jailers. End the hand that would burn us. Keep the name they buried. We can carry the old warmth without carrying his wrath. One small green shoot opens in your palm.', 'Märgen svarar: Bryt fångvaktarna. Stoppa handen som vill bränna oss. Bevara namnet de begravde. Vi kan bära den gamla värmen utan hans vrede. Ett litet grönt skott öppnar sig i din hand.')),
(25, 83, 'lapis_cartographer', tr('The Route Beneath Every Map', 'Vägen under varje karta'),
 tr('Ivo sees the old forge roads reflected under the sand. Tune all three survey bells within thirty seconds. Their joined note will show where the failing chains are sending their heat.', 'Ivo ser de gamla smidesvägarna speglas under sanden. Stäm alla tre mätklockor inom trettio sekunder. Deras gemensamma ton visar vart de sviktande kedjorna sänder sin hetta.'), 'chime',
 tr('Every buried road points toward Asterion. The heat does not spread at random: Eldmarr is testing which root will carry him closest to the hall.', 'Varje begravd väg pekar mot Asterion. Hettan sprids inte slumpmässigt: Eldmarr prövar vilken rot som bär honom närmast hallen.')),
(26, 88, 'frostwake_bellkeeper', tr('An Apology Made of Ice', 'En ursäkt av is'),
 tr('Ylva caught a Warden\'s abandoned apology inside an ice bell. Call out the Penitent Chain and break it. The Wardens were offered places at the table. Each told himself that one more winter of silence would hurt nobody.', 'Ylva fångade en väktares övergivna ursäkt i en isklocka. Kalla fram Den botfärdiga kedjan och bryt den. Väktarna erbjöds platser vid bordet. Var och en intalade sig att ännu en tyst vinter inte skulle skada någon.'), 'echo',
 tr('Penitent Chain', 'Den botfärdiga kedjan')),
(27, 93, 'cairn_stonesinger', tr('Teach the Mountain His Name', 'Lär berget hans namn'),
 tr('Edda has carved the keeper\'s true name into three singing stones. Ring them together within thirty seconds. The mountain must remember who held it up before you ask it to survive his fall.', 'Edda har ristat väktarens sanna namn i tre sjungande stenar. Låt dem klinga tillsammans inom trettio sekunder. Berget måste minnas vem som bar det innan du ber det överleva hans fall.'), 'chime',
 tr('The stones answer: Eldmarr, First Keeper. Not the gods\' furnace. Not the world\'s enemy from the beginning. A rescuer who now chooses to become its destroyer.', 'Stenarna svarar: Eldmarr, den förste väktaren. Inte gudarnas ugn. Inte världens fiende från början. En räddare som nu väljer att bli dess förgörare.')),
(28, 97, 'yr_wi_lead', tr('One Year the Fire Cannot Have', 'Ett år elden inte får ta'),
 tr('Ysra asks you to gather four promises from the Yearwheel: a spring that grows, a summer that feeds, an autumn that shares and a winter that shelters. Listen in each circle. These are the futures you carry into the Forge.', 'Ysra ber dig samla fyra löften från Årshjulet: en vår som gror, en sommar som föder, en höst som delar och en vinter som skyddar. Lyssna i varje cirkel. Det är dessa framtider du bär in i Smedjan.'), 'seasons', ''),
(45, 99, 'ew_guide', tr('The Guest at the Last Door', 'Gästen vid den sista dörren'),
 tr('Svala says your memories have reached the Nine-Chain Door ahead of you. Eldmarr wants to hear your answer himself. Enter the marked circle and defeat the Shade of the Unbound King. Its power is only an echo; the giant beyond the door is still waiting.', 'Svala säger att dina minnen nådde Nio kedjornas port före dig. Eldmarr vill själv höra ditt svar. Gå in i den markerade cirkeln och besegra Den obundne kungens skugga. Dess kraft är bara ett eko; jätten bortom porten väntar ännu.'), 'echo',
 tr('Shade of the Unbound King', 'Den obundne kungens skugga')),
(45, 99, 'ew_keeper', tr('A Place for the Living', 'En plats för de levande'),
 tr('Hedda will carry your answer to the sealed court. Stand at the offered seat and refuse the bargain: you will break the Wardens, but you will not give Eldmarr the roots to burn. Afterwards, prepare your Ember Key and ten fighters for the Chained Forge.', 'Hedda för ditt svar till den förseglade salen. Stå vid den erbjudna stolen och avvisa avtalet: du bryter väktarna men ger inte Eldmarr rötterna att bränna. Förbered sedan din Glödnyckel och tio kämpar för Den fjättrade smedjan.'), 'memory',
 tr('You set a green shoot on the empty seat. Eldmarr answers: They promised me a place. You answer: And you promised the roots another spring. The door shakes. For a moment, the fire sounds like grief.', 'Du lägger ett grönt skott på den tomma stolen. Eldmarr svarar: De lovade mig en plats. Du svarar: Och du lovade rötterna ännu en vår. Porten skakar. För ett ögonblick låter elden som sorg.')),
(45, 99, 'ew_guide', tr('The Table He Was Promised', 'Bordet han blev lovad'),
 tr('Enter the Chained Forge with your Ember Key and ten fighters. Defeat Eldmarr, the Ember-Lord. This is the real giant, not a summoned shade. The captains\' betrayal was real; so are the homes above his furnace. Stop him before he melts the roots that hold them.', 'Gå in i Den fjättrade smedjan med din Glödnyckel och tio kämpar. Besegra Eldmarr, Glödherren. Det här är den verkliga jätten, inte en framkallad skugga. Kaptenernas svek var verkligt; det är också hemmen ovanför hans ugn. Stoppa honom innan han smälter rötterna som bär dem.'), 'raid', ''),
(0, 99, 'smith', tr('Leave One Chair Empty', 'Lämna en stol tom'),
 tr('Return to Bram Emberforge in Alderhaven. Tell him the true name of the one who warmed the first hearth. Then listen at the meadow memorial. The world needs a story that remembers both his gift and his last terrible choice.', 'Återvänd till Bram Emberforge i Alderhaven. Berätta det sanna namnet på den som värmde den första härden. Lyssna sedan vid ängens minnesplats. Världen behöver en berättelse som minns både hans gåva och hans sista förfärliga val.'), 'epilogue',
 tr('Bram leaves one chair empty beside the village hearth. No crown. No chains. Just a name: Eldmarr, who kept the first fire. Outside, the children plant a tree. The ground is warm enough for spring.', 'Bram lämnar en stol tom vid byns härd. Ingen krona. Inga kedjor. Bara ett namn: Eldmarr, som vaktade den första elden. Utanför planterar barnen ett träd. Marken är varm nog för våren.')),
]

FLASH = [
(tr('The First Hearth', 'Den första härden'), tr('Long before the chains. Snow buries the last village. Eldmarr tears open his own furnace ribs and lays his fire beneath the roots. A small voice asks if it hurts. He says: Only until spring.', 'Långt före kedjorna. Snön begraver den sista byn. Eldmarr sliter upp sina egna ugnsrevben och lägger elden under rötterna. En liten röst frågar om det gör ont. Han säger: Bara tills våren kommer.'), 'hearth'),
(tr('The Promised Table', 'Det utlovade bordet'), tr('The hall rises on the rescued roots. A messenger promises Eldmarr a seat beside its fire. He forges ten cups, one for each captain and one for himself. For the first time, the keeper lets his hammer rest.', 'Hallen reser sig på de räddade rötterna. En budbärare lovar Eldmarr en plats vid dess eld. Han smider tio bägare, en åt varje kapten och en åt sig själv. För första gången låter väktaren hammaren vila.'), 'table'),
(tr('The Closing Chain', 'Kedjan som sluts'), tr('Nine captains enter wearing new gold. They lower chains instead of a chair. Eldmarr asks: Did you leave no place for me? One captain looks away. A hundred winters later, that question is still burning.', 'Nio kaptener kommer in klädda i nytt guld. De sänker kedjor i stället för en stol. Eldmarr frågar: Lämnade ni ingen plats åt mig? En kapten ser bort. Hundra vintrar senare brinner frågan fortfarande.'), 'chains')]
SEASONS = [
(72,319,tr('A Spring That Grows','En vår som gror'),tr('A seed breaks its shell. The world does not owe the old hall another year, but the seed has done nothing to deserve a fire.','Ett frö bryter sitt skal. Världen är inte skyldig den gamla hallen ännu ett år, men fröet har inte förtjänat någon eld.')),
(316,311,tr('A Summer That Feeds','En sommar som föder'),tr('Hands pass bread across a crowded table. There is room because someone brings another chair.','Händer skickar bröd över ett fullt bord. Det finns plats eftersom någon hämtar ännu en stol.')),
(319,100,tr('An Autumn That Shares','En höst som delar'),tr('An old farmer leaves the last apples for strangers. A gift can outlive the person who gave it.','En gammal bonde lämnar de sista äpplena åt främlingar. En gåva kan överleva den som gav den.')),
(69,100,tr('A Winter That Shelters','En vinter som skyddar'),tr('A child closes a door against the snow, then opens it again for a traveller. This is the winter Eldmarr once wanted to save.','Ett barn stänger dörren mot snön och öppnar den sedan igen för en vandrare. Det är denna vinter Eldmarr en gång ville rädda.'))]

def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')

def install():
    import generate_gloamfen as geo
    world = json.loads((ROOT/'world/map.txt').read_text())
    zones = [world]+world['zones']
    levels = json.loads((ROOT/'world/levels.txt').read_text())
    while len(levels)<99: levels.append(levels[-1]+2300)
    chapters = content()
    items = json.loads((ROOT/'world/items.txt').read_text())
    for z in zones:
        z['quests'] = [q for q in z.get('quests',[]) if not q['id'].startswith('es_')]
        z['places'] = [p for p in z.get('places',[]) if not p['id'].startswith('es_')]
        z['slimes'] = [s for s in z['slimes'] if not s['kind'].startswith('es_')]
    scenes, enemies, used, flood = [], [], {}, {}
    def site(zone, near, hostile=False):
        z=zones[zone]
        if zone not in flood: flood[zone],_=geo.flood(z,(z['spawn']['x'],z['spawn']['y']))
        seen=flood[zone]
        def city(x,y):
            return any(c['x0']-3<x<c['x1']+3 and c['y0']-3<y<c['y1']+3 for c in [z.get('city')]+z.get('camps',[]) if c)
        # The collision grid already expands solids by the player's radius. Prefer clear paths near the local story giver.
        candidates=[]
        grid = sorted(((x,y) for y in range(4,z['size']-4) for x in range(4,z['size']-4)), key=lambda p: ((p[0]-near[0])**2+(p[1]-near[1])**2,p[1],p[0]))
        for x,y in grid:
            if not seen[int(y/.5),int(x/.5)] or hostile and city(x,y): continue
            if any(math.hypot(x-a,y-b)<7 for a,b in used.get(zone,[])): continue
            if any(math.hypot(x-p['x'],y-p['y'])<p['r']+6 for p in z.get('portals',[])): continue
            if any(math.hypot(x-p['tx'],y-p['ty'])<8 for source in zones for p in source.get('portals',[]) if p['to']==zone): continue
            if any(math.hypot(x-c['x'],y-c['y'])<6 for c in z.get('crosses',[])): continue
            if any(math.hypot(x-s['x'],y-s['y'])<12 for s in z['slimes'] if not s.get('ambush')): continue
            if hostile and any(math.hypot(x-n['x'],y-n['y'])<9 for n in z.get('npcs',[])): continue
            # A clear small ring and a clear adjacent summon location.
            if not all(seen[int((y+dy)/.5),int((x+dx)/.5)] for dx,dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1),(2,0)]): continue
            d=math.hypot(x-near[0],y-near[1])
            if not hostile and math.hypot(x-giver['x'],y-giver['y'])<5: continue
            candidates.append((d,y,x))
            break
        assert candidates, (zone,'no clear story site')
        _,y,x=min(candidates);used.setdefault(zone,[]).append((x,y));return x,y
    def add_place(zone,pid,name,near,hostile=False):
        x,y=site(zone,near,hostile)
        p=dict(id=pid,name=name,x=x,y=y,r=2.1)
        zones[zone]['places'].append(p)
        return p
    for i,(zone,level,npc,title,desc,mode,reveal) in enumerate(chapters,1):
        qid=f'es_{i:02}'
        z=zones[zone];giver=next(n for n in z['npcs'] if n['id']==npc)
        anchors = {
            1:(38,53), 2:(35,66), 3:(64,94), 4:(22,45), 5:(80,28),
            6:(44,184), 7:(66,142), 8:(26,140), 9:(144,72), 10:(87,87),
            11:(64,69), 12:(72,72), 13:(70,62), 15:(87,54), 16:(38,43),
            17:(73,30), 18:(64,68), 19:(76,87), 20:(48,53), 21:(67,72),
            22:(79,74), 23:(55,74), 25:(125,39), 26:(126,31), 28:(38,62),
        }
        base=anchors.get(i,(giver['x'],giver['y']))
        objectives=[];recaps=[]
        def obj(kind,target,label,count=1):
            objectives.append(dict(kind=kind,target=target,label=label,count=count))
        def memory(suffix,name,text,near,visual='ember'):
            p=add_place(zone,f'{qid}_{suffix}',name,near)
            scenes.append(dict(id=p['id'],quest=qid,zone=zone,seconds=18 if mode=='flashback' else 14,label=name,description=text,visual=visual))
            obj('memory',p['id'],name);recaps.append(text)
        if mode=='flashback':
            for j,(name,text,visual) in enumerate(FLASH): memory(str(j),name,text,(base[0]+(j-1)*9,base[1]-8),visual)
        elif mode=='seasons':
            for j,(x,y,name,text) in enumerate(SEASONS): memory(str(j),name,text,(x,y),'root')
        elif mode in ('memory','epilogue'):
            if mode=='epilogue': obj('talk',npc,tr('Tell Bram the keeper\'s true name','Berätta väktarens sanna namn för Bram'))
            memory('m',title,reveal,base,'table' if i in (5,26,28) else 'ember')
        elif mode=='raid':
            obj('kill','cf_eldmarr',tr('Defeat Eldmarr in the Chained Forge','Besegra Eldmarr i Den fjättrade smedjan'))
        elif mode=='chime':
            chain=f'{qid}_bells'
            for j in range(3):
                name=tr(f'Oath Bell {j+1}',f'Edsklocka {j+1}')
                p=add_place(zone,f'{qid}_{j}',name,(base[0]+(j-1)*10,base[1]-12))
                p.update(chain=chain,burn=30)
            obj('chime',chain,tr('Ring the three oath bells together','Ring de tre edsklockorna tillsammans'),3)
            recaps.append(reveal)
        else:
            p=add_place(zone,f'{qid}_m',title,base,True)
            kind=f'es_foe_{i:02}'
            tag='empty-seat:'+p['id']
            art='cf_eldmarr' if 'Shade' in reveal else 'cf_kettil'
            # Story encounters use ordinary solo scale, not raid or elite rewards. Owner evaluates fight timing.
            hp=120+level*level*1.5
            damage=8+level*3
            enemies.append(dict(kind=kind,name=reveal,level=level,stats=[round(hp),damage,2.6,1.4],profile=[.7,1.4,7,12],boss=False,elite=True,outdoor=True,add=True,gold=0,material='slime_gel',lootSource=None,ranged=None,slam=0,melee=1,color='#a5cddd',artFrom=art))
            count=2 if mode=='hold' else 1
            for k in range(count):
                z['slimes'].append(dict(kind=kind,x=p['x']+2,y=p['y'],ambush=tag))
            if mode=='hold':
                p['waves']=[dict(at=1,tag=tag)]
                obj('hold',p['id'],tr('Keep the root circle alive','Håll rotcirkeln vid liv'),20)
            else:
                scenes.append(dict(id=p['id'],quest=qid,zone=zone,seconds=0,label=title,description=desc,visual='shade',enemy=kind))
                obj('echo',p['id'],reveal)
        next_text=''
        if i<len(chapters):
            nz,nl,nn,nt,*_=chapters[i]
            ng=next(n for n in zones[nz]['npcs'] if n['id']==nn)
            next_text=tr(f'Next chapter: {nt}. Speak to {ng["name"]} in {zones[nz]["name"]} at level {nl}.',f'Nästa kapitel: {TEXT[nt]}. Tala med {ng["name"]} i {zones[nz]["name"]} på nivå {nl}.')
        q=dict(id=qid,title=title,npc=npc,description=desc,objectives=objectives,level=level,minLevel=level,rewardXp=levels[level-1]//10,rewardGold=level*12,requires=f'es_{i-1:02}' if i>1 else None,repeatable=False,story=dict(title=tr('The Empty Seat','Den tomma stolen'),chapter=i,recap=recaps,next=next_text))
        rarity = 'epic' if mode == 'memory' and i == len(chapters)-2 else 'rare' if i % 5 == 0 else 'uncommon'
        slots = ['weapon', 'armor', 'headgear', 'shoulders', 'gloves']
        q['rewardChoices'] = {}
        for cls in ['warrior', 'mage', 'assassin', 'priest', 'hunter']:
            rewards = []
            for slot in (slots[(i-1)%5], slots[i%5]):
                pool = [it for it in items if it.get('class')==cls and it['rarity']==rarity and it['kind']==slot and it.get('requiredLevel',1)<=level and not it.get('starter')]
                assert pool, (qid,cls,slot,rarity)
                tier = max(it.get('requiredLevel',1) for it in pool)
                rewards.append(min((it for it in pool if it.get('requiredLevel',1)==tier), key=lambda it:(len(it['id']),it['id']))['id'])
            q['rewardChoices'][cls] = rewards
        z['quests'].append(q)
    dump(ROOT/'world/map.txt',world)
    dump(ROOT/'world/empty-seat-scenes.txt',scenes)
    dump(ROOT/'world/empty-seat-enemies.txt',enemies)
    for filename,default in [('elite-power',[1,1]),('enrage',[240,120])]:
        p=ROOT/f'world/{filename}.txt';d=json.loads(p.read_text())
        for e in enemies:d[e['kind']]=default
        dump(p,d)
    svpath=ROOT/'scripts/sv-translations.txt';sv=json.loads(svpath.read_text());sv.update(TEXT);dump(svpath,sv)
    print(f'The Empty Seat: {len(chapters)} chapters, {len(scenes)} memories/echoes, {len(enemies)} summoned enemy kinds; no new zones')
def check_map():
    """Read-only reachability/timing checks against authored collision, including the sky islands."""
    import generate_gloamfen as geo
    w=json.loads((ROOT/'world/map.txt').read_text());zones=[w]+w['zones']
    total=0
    for z in zones:
        places=[p for p in z.get('places',[]) if p['id'].startswith('es_')]
        if not places: continue
        seen,blocked=geo.flood(z,(z['spawn']['x'],z['spawn']['y']))
        for p in places:
            assert seen[int(p['y']*2),int(p['x']*2)], (p['id'],'unreachable')
            total+=1
        def distance(a,b):
            start=(int(a['x']*2),int(a['y']*2));end=(int(b['x']*2),int(b['y']*2))
            todo=deque([(start,0)]);visited={start};n=len(blocked)
            while todo:
                (x,y),d=todo.popleft()
                if (x,y)==end:return d*.5
                for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    at=(x+dx,y+dy)
                    if 0<=at[0]<n and 0<=at[1]<n and at not in visited and not blocked[at[1],at[0]]:
                        visited.add(at);todo.append((at,d+1))
            raise AssertionError((a['id'],b['id'],'disconnected'))
        for chain in {p['chain'] for p in places if p.get('chain')}:
            bells=[p for p in places if p.get('chain')==chain]
            seconds=sum(distance(a,b) for a,b in zip(bells,bells[1:]))/5.2
            assert len(bells)==3 and seconds<25, (chain,'bell route too slow',seconds)
    print(f'Empty Seat: {total} reachable sites; all three bell routes fit within 25 of their 30 seconds')

if __name__=='__main__':
    if '--check' not in sys.argv:install()
    check_map()
