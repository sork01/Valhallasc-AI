"""Connected shaded anatomy for the six Shattered Span enemies."""
import math
from astral_slime_redraw import OUTLINE, WHITE, BONE, PEARL, GOLD, AMBER, PURPLE, TEAL, AZURE, SLATE, BROWN, PINK


def eye(r,x,y,side=1,alive=True,ramp=TEAL):
    r.poly([(x-5,y+3),(x+5,y+1),(x+4,y-3),(x-4,y-2)],OUTLINE)
    if alive:
        r.line([(x-3,y),(x+3,y-1)],ramp[3],2)
        r.ellipse(x+1,y,1,2,OUTLINE)
        r.ellipse(x-2,y+1,.8,.8,WHITE)
    r.line([(x-side*5,y+5),(x+side*5,y+2)],SLATE[0],2)


def hand(r,x,y,closed=False,ramp=BONE):
    r.ball(x,y,4,4,ramp)
    for j in range(3):
        if closed:r.line([(x-3,y+2-j*2),(x+2,y+1-j*2)],ramp[0],1)
        else:r.limb([(x-3+j*3,y-2),(x-4+j*3.5,y-6),(x-2+j*3.5,y-8)],ramp,1.4)
    r.limb([(x+3,y+3),(x+5,y),(x+2,y-2)],ramp,1.5)


def crystal(r,x,y,rx,ry,ramp=TEAL,angle=0):
    dx,dy=math.sin(angle),math.cos(angle)
    ux,uy=dy,-dx
    tip=(x+dx*ry,y+dy*ry);end=(x-dx*ry,y-dy*ry)
    l=(x-ux*rx,y-uy*rx);rr=(x+ux*rx,y+uy*rx)
    r.poly([tip,rr,end,l],ramp[1],OUTLINE)
    r.poly([tip,(x,y),l],ramp[3])
    r.poly([tip,rr,(x,y)],ramp[2])
    r.line([tip,(x,y),end],ramp[4],1)


def lynx(setup,clip,n):
    a,r,w,s,d,ph,b=setup('span_lynx',clip,n,(-3,13),-.40)
    x,y=15*s-8*w,24+b+4*w-10*d
    # Four jointed legs fold under the intact feline as it rolls onto its side.
    for j,(dx,far) in enumerate(((-18,True),(13,True),(-19,False),(15,False))):
        step=math.sin(ph+j*1.8)*5 if clip=='walk' else 0
        hip=(x+dx,y-1)
        knee=(x+dx+step+10*d,12+4*w+5*d)
        paw=(x+dx+step+18*d+(13*s if not far and dx>0 else 0),3+5*w+13*d)
        r.limb([hip,knee,paw],SLATE if far else AZURE,4)
        r.ball(paw[0]+2,paw[1],7,3,AZURE)
        if not far:
            for j in range(2):r.line([(paw[0]+5+j*2,paw[1]+1),(paw[0]+8+j*2,paw[1])],PEARL[4],1)
    r.taper([(x-23,y+1),(x-31,y+6-7*d),(x-36,y+12-10*d+math.sin(ph))],AZURE,5,2)
    crystal(r,x-36,y+13-11*d,3,5,TEAL,1.1*d)
    r.ball(x-4,y,25,12,AZURE)
    r.ball(x+13,y+5,12,14,AZURE)
    r.ball(x+11,y+3,8,9,PEARL)
    for j in range(3):crystal(r,x-17+j*10,y+11,2.5,5-j*.5,TEAL,.15)
    hx,hy=x+22+6*s-4*w,y+15+5*w-4*s-7*d
    r.limb([(x+12,y+8),(hx-7,hy-5)],AZURE,8)
    r.ball(hx,hy,13,11,AZURE)
    for side in (-1,1):
        r.poly([(hx+side*5,hy+6),(hx+side*11-6*d,hy+22-11*d),(hx+side*13,hy+6)],AZURE[2],OUTLINE)
        r.line([(hx+side*10-4*d,hy+18-8*d),(hx+side*12-7*d,hy+27-13*d)],SLATE[0],2)
    # Short feline muzzle and a hinged jaw, rather than the previous hound's long snout.
    r.ball(hx+8,hy-4,8,5,PEARL)
    r.ball(hx+12,hy-2,3,2,SLATE)
    gape=2+8*w+2*s-2*d
    r.limb([(hx+2,hy-7),(hx+8,hy-7-gape),(hx+15,hy-6-gape)],AZURE,2.5)
    for fx in (hx+6,hx+11):crystal(r,fx,hy-9,1.8,4,TEAL)
    eye(r,hx+3,hy+3,alive=d<.6,ramp=AMBER)
    for j in range(2):r.line([(hx-3,hy-4-j*3),(hx-10,hy-5-j*4)],SLATE[1],1)
    return a


def sentinel(setup,clip,n):
    a,r,w,s,d,ph,b=setup('span_sentinel',clip,n,(0,9),-1.48)
    x,y=12*s-5*w,32+b+3*w-10*d
    # Thick articulated gold shins, segmented rigid breastplate, one recessed visor.
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        xx=x+side*10+step
        r.limb([(x+side*9,y-9),(xx,14),(xx+side*5*d,4+8*d)],SLATE,5)
        r.ball(xx,12,7,8,GOLD)
        r.ball(xx+side*5*d,4+8*d,9,4,AMBER)
    r.ball(x,y,20,23,GOLD)
    r.ball(x-2,y+4,14,16,AMBER)
    for j in range(3):r.line([(x-13,y+10-j*8),(x+13,y+8-j*8)],GOLD[0],2)
    crystal(r,x,y+5,5,8,TEAL)
    r.ball(x,y+31,14,12,GOLD)
    r.poly([(x-12,y+34),(x+12,y+34),(x+9,y+26),(x-9,y+26)],OUTLINE)
    if d<.7:r.line([(x-6,y+30),(x+7,y+30)],TEAL[3],2)
    for side in (-1,1):
        r.ball(x+side*(20-7*d),y+15,9,10,AMBER)
        elbow=(x+side*(26+5*w-18*d),y-1+13*w)
        fist=(x+side*(29+8*s-3*w-20*d),y-16+36*w-10*s)
        r.limb([(x+side*(19-7*d),y+16),elbow,fist],SLATE,5)
        crystal(r,fist[0],fist[1]+4,7,16,AMBER,side*(.15+1.1*s-.7*w))
        if d>.2:
            r.line([(x+side*13,y+9),(x+side*16,y+1),(x+side*12,y-8)],OUTLINE,2)
    return a


def caster(setup,clip,n):
    a,r,w,s,d,ph,b=setup('span_caster',clip,n,(0,25))
    x,y=14*s-6*w,53+b+5*w
    f=1-d
    # The violet spirit unravels; the tangible prism rings fall independently.
    if d<.92:
        r.ball(x,y+10*d,13*f,18*f,PURPLE)
        r.poly([(x-12*f,y+6),(x,y+28*f),(x+10*f,y+7),(x+7*f,y-13)],PURPLE[2],OUTLINE)
        r.ball(x-1,y+9+10*d,9*f,12*f,PURPLE)
        for side in (-1,1):eye(r,x+side*5*f,y+12+10*d,side,alive=d<.65,ramp=PINK)
        r.poly([(x-3,y+3+10*d),(x+3,y+3+10*d),(x,y-3+10*d)],OUTLINE)
        for j in range(4):
            r.taper([(x-10+j*7,y-5),(x-13+j*8,y-13),(x-12+j*8+math.sin(ph+j)*4,y-23+8*d)],PURPLE,3*f,.4)
        for side in (-1,1):
            grip=(x+side*(20+20*s-6*w),y-2+16*w-6*s)
            r.limb([(x+side*9,y+6),(x+side*18,y+2),grip],PURPLE,3*f)
            crystal(r,*grip,4*f,9*f,TEAL,side*(.4+s))
            r.line([(x+side*10,y+17),grip],PINK[2],1)
    for side in (-1,1):
        xx=x+side*(5*w-5*s+25*d)
        yy=(y+side*22)*(1-d)+(5+side)*d
        r.ball(xx,yy,19,4,GOLD,side*(.12+.5*w-.6*s)*(1-d)+side*.3*d)
        r.line([(xx-13,yy),(xx+13,yy)],AMBER[1],1)
        crystal(r,xx+side*15,yy,2.5,5,TEAL,.5*d)
    return a


def face(r,x,y,d,angular=False,weaver=False):
    r.ball(x,y,12,15,BONE)
    r.ball(x-2,y+2,8,11,BONE)
    for side in (-1,1):eye(r,x+side*5,y+3,side,alive=d<.65,ramp=TEAL if angular else PINK if weaver else AMBER)
    r.line([(x,y+3),(x-2,y-3),(x+1,y-4)],BONE[0],1)
    r.line([(x-4,y-8),(x+4,y-8)],OUTLINE,1)
    if angular:
        r.poly([(x-11,y-1),(x-6,y-13),(x+5,y-14),(x+11,y-1)],AZURE[1],OUTLINE)
        r.line([(x-5,y-5),(x+5,y-5)],SLATE[0],1)


def legs(r,x,y,ph,clip,d,ramp=SLATE):
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        xx=x+side*10+step
        r.limb([(x+side*9,y-12),(xx,13),(xx+side*5*d,4)],ramp,5)
        r.ball(xx+side*5*d,4,8,4,ramp)


def warden(setup,clip,n):
    a,r,w,s,d,ph,b=setup('span_warden',clip,n,(0,8),-1.25)
    x,y=10*s-5*w,32+b+4*w-12*d
    legs(r,x,y,ph,clip,d)
    r.ball(x,y+4,20,23,GOLD)
    r.ball(x-2,y+7,14,16,AMBER)
    for j in range(3):r.line([(x-13,y+10-j*7),(x+13,y+8-j*7)],GOLD[0],2)
    for side in (-1,1):r.ball(x+side*20,y+19,10,9,GOLD)
    face(r,x,y+38,d)
    r.poly([(x-13,y+39),(x-14,y+53),(x,y+60),(x+14,y+53),(x+13,y+39),(x+8,y+47),(x-8,y+47)],GOLD[2],OUTLINE)
    for side in (-1,1):crystal(r,x+side*16,y+51,4,12,TEAL,side*.7)
    shield=(x-28-3*w,y+4)
    r.limb([(x-16,y+18),shield],SLATE,5)
    r.ball(*shield,13,23,GOLD)
    crystal(r,*shield,10,20,AZURE)
    r.line([(shield[0],shield[1]+16),(shield[0],shield[1]-15)],GOLD[3],2)
    grip=(x+24+15*s-8*w,y+3+22*w-7*s)
    r.limb([(x+17,y+20),(x+25-5*w,y+12+12*w),grip],SLATE,5)
    angle=-.3-1.1*w+1.4*s
    dx,dy=math.sin(angle),math.cos(angle)
    tip=(grip[0]+dx*35,grip[1]+dy*35)
    r.line([(grip[0]-dx*13,grip[1]-dy*13),tip],BROWN[1],4)
    r.line([(grip[0]-dx*10,grip[1]-dy*10),tip],GOLD[2],1)
    crystal(r,*tip,7,12,TEAL,angle)
    r.poly([tip,(tip[0]+dy*13,tip[1]-dx*13),(tip[0]+dy*8-dx*9,tip[1]-dx*8-dy*9)],GOLD[2],OUTLINE)
    hand(r,*grip,closed=d<.6)
    return a


def weaver(setup,clip,n):
    a,r,w,s,d,ph,b=setup('span_weaver',clip,n,(0,8),-1.2)
    x,y=10*s-5*w,34+b+3*w-12*d
    # Shaded ribcage, fitted waist and overlapping skirt panels remain volumetric.
    r.ball(x,y-14,19,17,PURPLE)
    for j in range(5):
        xx=x-14+j*7
        r.limb([(x+(j-2)*4,y-1),(xx,y-15),(xx+2*math.sin(ph+j),y-29)],PURPLE,4)
        r.line([(xx,y-9),(xx+2,y-25)],PURPLE[0],1)
    r.ball(x,y+7,15,21,PURPLE)
    r.ball(x-2,y+8,10,15,PURPLE)
    r.ball(x,y-4,11,5,GOLD)
    for side in (-1,1):
        r.line([(x+side*10,y+24),(x+side*5,y+2),(x+side*7,y-5)],GOLD[2],2)
        r.ball(x+side*16,y+19,8,9,PURPLE)
    face(r,x,y+38,d,weaver=True)
    for side in (-1,1):
        r.limb([(x+side*10,y+47),(x+side*12,y+36),(x+side*11,y+28)],PEARL,2)
    r.poly([(x-13,y+35),(x-16,y+54),(x,y+67),(x+16,y+54),(x+13,y+35),(x+8,y+48),(x-8,y+48)],PURPLE[1],OUTLINE)
    r.line([(x-13,y+53),(x,y+62),(x+13,y+53)],GOLD[2],2)
    crystal(r,x,y+58,3,6,TEAL)
    grips=[]
    for side in (-1,1):
        grip=(x+side*(24+13*w)+24*s,y+3+18*w+side*8*s-14*d)
        r.limb([(x+side*14,y+20),(x+side*23,y+12+7*w),grip],PURPLE,5)
        hand(r,*grip,closed=False)
        grips.append(grip)
    if d<.92:
        left,right=grips
        for j,ramp in enumerate((TEAL,PINK,GOLD)):
            r.line([left,(x-2,y+9+9*w-j*6),(x+12+16*s,y+4-j*6),right],ramp[3],1)
        for side,grip in zip((-1,1),grips):crystal(r,grip[0]+side*5,grip[1]+9,3,7,TEAL,side*.4)
    else:
        crystal(r,x-25,y-22,4,7,TEAL,1.3)
        crystal(r,x+25,y-23,3,6,TEAL,-1.1)
    return a


def archon(setup,clip,n):
    a,r,w,s,d,ph,b=setup('span_archon',clip,n,(0,8),-1.32)
    x,y=12*s-7*w,34+b+4*w-13*d
    # Split winglike cape belongs to the shoulders and folds beneath the fallen plate.
    for side in (-1,1):
        r.poly([(x+side*8,y+26),(x+side*31,y+30),(x+side*(32-6*d),y-24+8*d),(x+side*14,y-19)],SLATE[1],OUTLINE)
        r.poly([(x+side*14,y+22),(x+side*26,y+23),(x+side*23,y-17)],AZURE[1])
        r.line([(x+side*16,y+20),(x+side*26,y-13)],TEAL[2],2)
    legs(r,x,y,ph,clip,d,AZURE)
    r.ball(x,y+6,20,25,AZURE)
    r.ball(x-2,y+8,14,18,AZURE)
    r.line([(x,y+26),(x-3,y+7),(x,y-8)],GOLD[2],2)
    for side in (-1,1):
        r.ball(x+side*20,y+22,10,10,AZURE)
        crystal(r,x+side*22,y+28,4,8,TEAL,side*.6)
    face(r,x,y+42,d,angular=True)
    crownx,crowny=x-8*d,y+56+5*d
    r.poly([(crownx-14,crowny-6),(crownx-17,crowny+12),(crownx-7,crowny+4),(crownx,crowny+20),(crownx+7,crowny+4),(crownx+17,crowny+12),(crownx+14,crowny-6)],GOLD[2],OUTLINE)
    r.line([(crownx-12,crowny-3),(crownx+12,crowny-3)],GOLD[4],2)
    crystal(r,crownx,crowny+5,3,6,TEAL)
    # Both grips are derived along the shaft before the arms are drawn.
    angle=-.25-1.05*w+1.75*s+.8*d
    dx,dy=math.sin(angle),math.cos(angle)
    grip=(x+22+13*s-10*w,y+9+20*w-5*s-9*d)
    low=(grip[0]-dx*14,grip[1]-dy*14)
    tip=(grip[0]+dx*34,grip[1]+dy*34)
    r.line([(low[0]-dx*15,low[1]-dy*15),tip],SLATE[1],4)
    r.line([(low[0]-dx*14,low[1]-dy*14),tip],GOLD[3],1)
    crystal(r,*tip,8,16,TEAL,angle)
    r.line([(tip[0]-dy*11,tip[1]+dx*11),(tip[0]+dy*11,tip[1]-dx*11)],GOLD[2],3)
    for side,pt in ((-1,low),(1,grip)):
        wrist=(pt[0]-side*4*d,pt[1]-3*d)
        r.limb([(x+side*17,y+24),(x+side*23-7*w,y+10+12*w),wrist],AZURE,5)
        hand(r,*wrist,closed=d<.6)
    return a
