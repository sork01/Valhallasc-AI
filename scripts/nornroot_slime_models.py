"""Nornroot's connected articulated creatures: amber, funeral thread, root armour and bone."""
import math
from astral_slime_redraw import OUTLINE, WHITE, BONE, PEARL, GOLD, AMBER, PURPLE, TEAL, BROWN, SLATE


def glare(r, x, y, side=1, ramp=TEAL, alive=True):
    r.poly([(x-5,y+4),(x+5,y+2),(x+4,y-3),(x-4,y-2)], OUTLINE)
    if alive:
        r.ball(x,y,3,2.5,ramp)
        r.ellipse(x+1,y,.8,2,OUTLINE)
        r.ellipse(x-1,y+1,.7,.7,WHITE)
    r.line([(x-side*5,y+6),(x+side*5,y+3)],OUTLINE,2)


def fingers(r, x, y, closed=False, ramp=BONE):
    r.ball(x,y,5,5,ramp)
    if closed:
        for j in range(3): r.line([(x-3,y+3-j*2),(x+3,y+2-j*2)],ramp[0],1)
        r.limb([(x+3,y+4),(x+6,y+1),(x+3,y-2)],ramp,2)
    else:
        for j in range(3):
            r.limb([(x-3+j*3,y-2),(x-5+j*4,y-7),(x-3+j*4,y-9)],ramp,1.6)


def hound(setup, clip, n):
    a,r,w,s,d,ph,b=setup('barrow_hound',clip,n,(-2,11),-.15)
    x,y=13*s-7*w,23+b+4*w-12*d
    # Four attached legs buckle without shortening the bones or melting the fur.
    for j,(dx,depth) in enumerate(((-17,-1),(13,-1),(-19,1),(14,1))):
        step=math.sin(ph+j*1.7)*4 if clip=='walk' else 0
        hip=(x+dx,y-2)
        knee=(x+dx+step+10*d,12+depth*2+5*w)
        paw=(x+dx+step+17*d,3+depth+3*w+12*d)
        r.limb([hip,knee,paw],SLATE if depth<0 else PURPLE,4)
        r.ball(paw[0]+2,paw[1],6,3,PURPLE)
        if depth>0:
            for toe in range(2):r.line([(paw[0]+4+toe*2,paw[1]),(paw[0]+6+toe*2,paw[1]-1)],BONE[3],1)
    r.taper([(x-21,y+2),(x-33,y+9),(x-38,y+16*(1-d)+math.sin(ph)*2)],PURPLE,5,1)
    r.ball(x-4,y,25,11,PURPLE,-.05)
    r.ball(x+12,y+4,12,15,PURPLE)
    for dx in (-14,-3,8):
        r.line([(x+dx-3,y+8),(x+dx+2,y-6)],GOLD[1],2)
        r.line([(x+dx-2,y+9),(x+dx+3,y-5)],GOLD[3],1)
    hx,hy=x+22+8*s-3*w,y+11+8*w-3*s-8*d
    r.limb([(x+10,y+6),(hx-7,hy-4)],PURPLE,8)
    r.ball(hx,hy,12,12,PURPLE)
    for dx in (-7,5):
        r.taper([(hx+dx,hy+7),(hx+dx-3-10*d,hy+20-12*d),(hx+dx-5-15*d,hy+24-18*d)],PURPLE,5,1)
        r.line([(hx+dx-1-4*d,hy+12-5*d),(hx+dx-3-10*d,hy+20-12*d)],PURPLE[0],2)
    # Jaw rotates around its root, so the fangs remain attached through the bite.
    gape=3+9*w+2*s-2*d
    r.ball(hx+8,hy-5,12,5,SLATE)
    r.limb([(hx+1,hy-8),(hx+10,hy-8-gape),(hx+19,hy-7-gape)],PURPLE,3)
    r.ball(hx+17,hy-3,4,3,OUTLINE_RAMP)
    glare(r,hx+4,hy+3,alive=d<.7)
    for j in range(3):
        fx=hx+8+j*4
        r.poly([(fx-1,hy-6),(fx+2,hy-6),(fx,hy-10)],BONE[3])
    r.line([(hx-8,hy-5),(hx-5,hy-10)],GOLD[3],2)
    return a


OUTLINE_RAMP=[OUTLINE,OUTLINE,SLATE[0],SLATE[1],SLATE[2]]


def scarab(setup, clip, n):
    a,r,w,s,d,ph,b=setup('barrow_scarab',clip,n,(-4,17),-.72)
    x,y=10*s-5*w,23+b+8*w-8*d
    # Six jointed legs curl beneath an intact, rigid pair of amber elytra.
    for side in (-1,1):
        for j in range(3):
            dx=-19+j*15
            step=math.sin(ph+j*1.7+side)*3 if clip=='walk' else 0
            root=(x+dx,y-4)
            joint=(x+dx+side*(8-5*d),12+step+8*d)
            tip=(x+dx+side*(13-11*d),3+step+15*d)
            r.limb([root,joint,tip],BROWN,2.5)
    r.ball(x-5,y+2,26,17,AMBER)
    r.ball(x-9,y+7,19,12,GOLD,-.12)
    r.line([(x-23,y+12),(x-7,y+4),(x+13,y-7)],BROWN[0],2)
    for j in range(3):
        xx=x-22+j*11
        r.line([(xx,y+11),(xx+3,y+3)],AMBER[1],2)
    r.ball(x+21,y-1+2*s,12,11,AMBER)
    for side in (-1,1):
        glare(r,x+20+side*6,y+3,side,alive=d<.6)
        # Open mandibles hinge on the face and snap together on the strike.
        root=(x+28,y-3+side*3)
        gap=side*(6+8*w-4*s-3*d)
        r.taper([root,(x+38+6*s-5*d,y-4+gap),(x+40+5*s-7*d,y-7+side*2)],BROWN,4,1)
        r.taper([(x+20+side*4,y+8),(x+24+side*7-4*d,y+19-13*d),(x+29+side*7-8*d,y+22-18*d)],AMBER,2,1)
    r.poly([(x-10,y+11),(x-6,y+16),(x-2,y+11),(x-6,y+7)],TEAL[2],OUTLINE)
    return a


def spindle(r,x,y,scale=1,tilt=0):
    # Tangible wooden spindle with separate flanges, rather than a magic floating glyph.
    dx,dy=math.sin(tilt),math.cos(tilt)
    r.line([(x-dx*15*scale,y-dy*15*scale),(x+dx*15*scale,y+dy*15*scale)],BROWN[1],max(1,round(4*scale)))
    for sign in (-1,1):
        cx,cy=x+dx*sign*13*scale,y+dy*sign*13*scale
        r.ball(cx,cy,9*scale,3*scale,GOLD,tilt)
    for j in range(4):
        cy=y+(-6+j*4)*scale
        r.line([(x-5*scale,cy),(x+5*scale,cy+1)],GOLD[3],max(1,round(scale)))


def spinner(setup,clip,n):
    a,r,w,s,d,ph,b=setup('barrow_spinner',clip,n,(0,25))
    x,y=12*s-6*w,54+b+6*w
    fade=1-d
    # The spectral face unravels; the amber spindle ends remain solid and fall.
    if d<.92:
        r.ball(x,y+16*d,15*fade,18*fade,TEAL)
        r.ball(x,y+13+16*d,12*fade,12*fade,TEAL)
        for side in (-1,1):
            glare(r,x+side*5*fade,y+16+16*d,side,alive=d<.65)
        r.poly([(x-5,y+6+16*d),(x,y+2+16*d),(x+6,y+6+16*d)],OUTLINE)
        for j in range(5):
            xx=x-12+j*6+math.sin(ph+j)*2
            r.taper([(xx,y),(xx+3*math.sin(ph+j),y-14),(xx+side_wave(j,ph),y-25+10*d)],TEAL,2.4*fade,.5)
        hand=(x+22+30*s-8*w,y-3+16*w)
        r.limb([(x+10,y+5),(x+17,y+1),hand],TEAL,3*fade)
        r.ball(*hand,4*fade,4*fade,TEAL)
        tip=(hand[0]+7+13*s,hand[1]+19-14*s)
        r.line([hand,tip],GOLD[3],2)
        r.poly([(tip[0]-2,tip[1]),(tip[0]+5,tip[1]+7),(tip[0]+2,tip[1]-3)],BONE[3])
        # Thread remains visibly connected from spool through hand to needle.
        r.line([(x-13,y+17),(x-25,y+7-7*w),(x-21,y-11),(x+7,y-13),hand],GOLD[2],1)
    for side in (-1,1):
        xx=x+side*19*d
        yy=(y+side*23)*(1-d)+(8+side*2)*d
        r.ball(xx,yy,19,4,GOLD,side*.5*d)
        r.line([(xx-15,yy),(xx+14,yy)],AMBER[1],1)
    if d>0:
        for j in range(4):
            if j<round(4*fade):r.taper([(x-15+j*8,y+25*d),(x-19+j*10,y+15+28*d)],TEAL,2*fade,.5)
        r.line([(x-28*d,8+10*(1-d)),(x+5,5),(x+28*d,10)],GOLD[2],1)
    return a


def side_wave(j,ph):return math.sin(ph+j*.8)*5


def doorward(setup,clip,n):
    a,r,w,s,d,ph,b=setup('barrow_doorward',clip,n,(0,7),-1.14)
    x,y=11*s-6*w,31+b+5*w-14*d
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        foot=(x+side*11+step+side*3*d,4)
        r.limb([(x+side*9,y-10),(foot[0],14),foot],BROWN,6)
        r.ball(*foot,9,4,AMBER)
    r.ball(x,y+7,20,24,AMBER)
    r.ball(x-2,y+9,15,17,GOLD)
    for side in (-1,1):
        r.ball(x+side*20,y+20,10,9,BROWN)
        r.line([(x+side*16,y+25),(x+side*22,y+15)],GOLD[2],2)
    r.line([(x,y+23),(x,y-5)],BROWN[0],3)
    r.ball(x,y+38,15,17,AMBER)
    r.poly([(x-15,y+39),(x-12,y+54),(x,y+61),(x+13,y+53),(x+15,y+39)],AMBER[1],OUTLINE)
    r.poly([(x-12,y+43),(x+12,y+43),(x+9,y+34),(x-9,y+34)],OUTLINE)
    if d<.75:
        for side in (-1,1):r.line([(x+side*3,y+39),(x+side*9,y+40)],TEAL[3],2)
    r.line([(x-3,y+30),(x+4,y+30)],BROWN[0],2)
    shield=(x-27-3*w,y+5)
    r.limb([(x-17,y+20),shield],BROWN,5)
    r.ball(*shield,14,23,BROWN)
    r.ball(shield[0]-1,shield[1]+1,11,20,GOLD)
    r.poly([(shield[0],shield[1]+14),(shield[0]+6,shield[1]),(shield[0],shield[1]-14),(shield[0]-6,shield[1])],AMBER[2],OUTLINE)
    r.line([(shield[0],shield[1]+12),(shield[0],shield[1]-12)],GOLD[3],2)
    hand=(x+23+16*s-8*w,y+5+17*w-5*s)
    r.limb([(x+18,y+19),(x+24-5*w,y+13+8*w),hand],BROWN,6)
    # The mace follows the hand, swinging about the grip through a broad arc.
    angle=-.2-1.05*w+1.35*s
    dx,dy=math.sin(angle),math.cos(angle)
    tip=(hand[0]+dx*29,hand[1]+dy*29)
    r.line([(hand[0]-dx*9,hand[1]-dy*9),tip],BROWN[1],4)
    spindle(r,*tip,.85,angle)
    fingers(r,*hand,closed=True,ramp=BROWN)
    return a


def robe(r,x,y,ph,d=0):
    # Rounded chest, pinched waist and overlapping hanging folds, shaded in five bands.
    r.ball(x,y+8,14,17,PURPLE)
    r.ball(x,y-6,10,10,PURPLE)
    r.ball(x,y-19,16,13,PURPLE)
    for j,dx in enumerate((-11,-4,4,12)):
        flow=math.sin(ph+j*.6)*1.1
        r.taper([(x+dx*.55,y-9),(x+dx+flow,y-20),(x+dx+flow*.5,y-34+abs(dx)*.3)],PURPLE,5.5,1.3)
    for dx in (-8,3,10):
        r.line([(x+dx*.5,y-12),(x+dx,y-25)],PURPLE[0],1)
        r.line([(x+(dx-2)*.5,y-13),(x+dx-2,y-24)],PURPLE[3],1)
    for side in (-1,1):
        r.poly([(x+side*11,y+20),(x+side*5,y+14),(x,y+4),(x+side*8,y+9)],SLATE[1],OUTLINE)
        r.line([(x+side*10,y+18),(x+side*4,y+12)],GOLD[2],1)
    r.ball(x,y+2,3,3,GOLD)


def threadkeeper(setup,clip,n):
    a,r,w,s,d,ph,b=setup('barrow_threadkeeper',clip,n,(0,6),-1.37)
    x,y=10*s-5*w,38+b+5*w-6*d
    robe(r,x,y,ph,d)
    hx,hy=x,y+32
    # The hood sits behind an exposed severe face.
    r.ball(hx,hy+3,16,20,SLATE)
    r.poly([(hx-15,hy+7),(hx-5,hy+27),(hx+9,hy+21),(hx+16,hy+4)],PURPLE[1],OUTLINE)
    r.ball(hx,hy-1,10,13,BONE)
    for side in (-1,1):glare(r,hx+side*5,hy+2,side,alive=d<.7)
    r.poly([(hx,hy),(hx+3,hy-5),(hx,hy-6)],BONE[0])
    r.line([(hx-4,hy-10),(hx,hy-8),(hx+4,hy-9)],OUTLINE,2)
    # Wooden thread frame and near shuttle each have an actual gripping hand.
    far=(x-24-3*w,y+1+12*w-4*s)
    r.limb([(x-12,y+16),(x-19,y+10),far],PURPLE,5)
    spindle(r,far[0]-1,far[1]+3,1.1,-.12)
    fingers(r,*far,closed=True)
    hand=(x+23+29*s-9*w,y+2+18*w-5*s)
    r.limb([(x+12,y+16),(hand[0]-9,hand[1]+3),hand],PURPLE,5)
    # Shuttle is a small shaded spindle with a needle tip, attached throughout the cast.
    r.ball(hand[0]+3,hand[1]+4,10,4,GOLD,-.6+1.0*s)
    r.poly([(hand[0]+9,hand[1]+7),(hand[0]+16+7*s,hand[1]+8-6*s),(hand[0]+8,hand[1])],BONE[2],OUTLINE)
    fingers(r,*hand,closed=True)
    r.line([(far[0]+2,far[1]+12),(x-8,y+17),(x+8,y+10),(hand[0],hand[1]+2)],GOLD[3],1)
    return a


def crown(r,x,y,drop=0):
    r.ball(x,y,15,4,GOLD)
    for side in (-1,1):
        r.taper([(x+side*10,y),(x+side*17,y+13),(x+side*20,y+22)],BROWN,4,1)
        r.taper([(x+side*16,y+11),(x+side*25,y+15)],GOLD,3,1)
        r.taper([(x+side*16,y+11),(x+side*11,y+20)],GOLD,2,1)
    r.poly([(x-6,y+1),(x,y+19),(x+6,y+1)],GOLD[2],OUTLINE)
    r.ball(x,y+4,3,4,TEAL)


def king(setup,clip,n):
    a,r,w,s,d,ph,b=setup('barrow_fatebound',clip,n,(0,7),-1.4)
    x,y=6*s-6*w,32+b+4*w-11*d
    # Knees fold; shoulder plates and bones separate as rigid pieces.
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        knee=(x+side*(11+8*d)+step,16-5*d)
        foot=(x+side*(12+13*d)+step,4)
        r.limb([(x+side*8,y-7),knee,foot],BONE,4)
        r.ball(*foot,9,4,BROWN)
    for side in (-1,1):
        r.taper([(x+side*14,y+24),(x+side*27,y+10),(x+side*24,y-19)],SLATE,10,3)
        r.line([(x+side*18,y+17),(x+side*23,y-13)],GOLD[2],1)
    r.ball(x,y+9,17,22,BROWN)
    r.ball(x,y+13,13,15,GOLD)
    for j in range(3):
        r.line([(x-9,y+18-j*6),(x,y+14-j*6),(x+10,y+18-j*6)],BONE[2],2)
    for side in (-1,1):r.ball(x+side*(19+10*d),y+23-6*d,10,8,AMBER)
    hx,hy=x,y+43-8*d
    r.ball(hx,hy,13,16,BONE)
    for side in (-1,1):
        r.ball(hx+side*8,hy+2,5,6,OUTLINE_RAMP)
        if d<.65:
            r.ellipse(hx+side*8,hy+3,2,3 if side<0 else 1.7,TEAL[3])
            r.ellipse(hx+side*8,hy+4,.6,.6,WHITE)
        r.line([(hx+side*3,hy+8),(hx+side*12,hy+12)],BROWN[0],2)
    r.poly([(hx,hy+1),(hx-3,hy-5),(hx+3,hy-5)],OUTLINE)
    r.ball(hx,hy-10,8,5,BONE)
    for j in range(4):r.line([(hx-5+j*3,hy-8),(hx-5+j*3,hy-13)],BROWN[0],1)
    # Crown separates from the skull on death and lands as an identifiable relic.
    crown(r,hx-20*d,hy+16-25*d,d)
    hand=(x+22+12*s-9*w,y+8+20*w-6*s)
    angle=-.25-1.1*w+1.40*s
    dx,dy=math.sin(angle),math.cos(angle)
    other=(hand[0]-dx*11,hand[1]-dy*11)
    r.limb([(x+16,y+20),(x+23,y+13),hand],BONE,4)
    r.limb([(x-15,y+20),(x-6,y+7),other],BONE,4)
    angle=-.25-1.1*w+1.40*s
    dx,dy=math.sin(angle),math.cos(angle)
    r.line([(hand[0]-dx*20,hand[1]-dy*20),(hand[0]+dx*37,hand[1]+dy*37)],BROWN[1],4)
    tip=(hand[0]+dx*26,hand[1]+dy*26)
    spindle(r,*tip,1.0,angle)
    r.poly([(tip[0]+dx*12-3,tip[1]+dy*12),(tip[0]+dx*16,tip[1]+dy*16),(tip[0]+dx*12+3,tip[1]+dy*12)],BONE[3],OUTLINE)
    fingers(r,*hand,closed=True)
    fingers(r,*other,closed=True)
    return a
