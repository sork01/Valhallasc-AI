"""Connected Longship anatomy, hinged shell/wood/metal, and maritime crew rigs."""
import math
from astral_slime_redraw import OUTLINE, WHITE, BONE, PEARL, GOLD, TEAL, AMBER, CORAL

# Added by longship_slime_redraw before these rigs are called.
COPPER = NAVY = SEA = WOOD = None


def hand(r,x,y,d=0):
    r.ball(x,y,4,4,SEA)
    for j in range(3):r.line([(x-3,y+2-j*2),(x+2+d*2,y+1-j*2)],SEA[0],1)
    r.limb([(x+3,y+3),(x+5,y),(x+2,y-2)],SEA,1.4)


def hook(r,x,y,angle=0,size=1):
    dx,dy=math.sin(angle),math.cos(angle);ux,uy=dy,-dx
    def pt(u,v):return x+size*(ux*u+dx*v),y+size*(uy*u+dy*v)
    r.limb([pt(0,15),pt(0,-3),pt(4,-9),pt(11,-10),pt(16,-4),pt(14,3)],COPPER,2.5)
    r.poly([pt(14,3),pt(8,1),pt(14,8)],COPPER[3],OUTLINE)
    r.line([pt(-2,14),pt(2,14)],BONE[3],2)


def crab(setup,clip,n):
    a,r,w,s,d,ph,b=setup('keel_crab',clip,n,(0,10),-.28)
    x,y=15*s-8*w,22+b+3*w-7*d
    for side in (-1,1):
        for j in range(3):
            step=math.sin(ph+j*1.9+side)*5 if clip=='walk' else 0
            hip=(x+side*15,y-3+j*3)
            knee=(x+side*(28-7*d),y-9+j*4+step)
            foot=(x+side*(37-8*d)+step,3+j*2+15*d)
            r.limb([hip,knee,foot],TEAL,3)
            r.line([knee,foot],COPPER[2],1)
    r.ball(x,y,23,16,TEAL)
    r.ball(x-1,y+4,19,12,COPPER)
    for j in range(3):r.line([(x-12+j*10,y+12),(x-15+j*10,y-4)],COPPER[0],1)
    r.line([(x-16,y+6),(x+13,y+6)],COPPER[4],1)
    for side in (-1,1):
        wrist=(x+side*(27+7*s-4*w-7*d)+8*s,y+10+15*w-9*s-13*d)
        r.limb([(x+side*17,y+1),(x+side*25,y+5+9*w),wrist],TEAL,4)
        r.ball(*wrist,8,10,COPPER,side*1.4*d)
        def cp(dx,dy):
            angle=-side*1.4*d
            return wrist[0]+dx*math.cos(angle)-dy*math.sin(angle),wrist[1]+dx*math.sin(angle)+dy*math.cos(angle)
        gape=3+11*w-2*s-2*d
        r.limb([wrist,cp(side*7,9),cp(side*(2+gape),17)],COPPER,3)
        r.limb([wrist,cp(-side*6,8),cp(side*(2-gape),16)],COPPER,3)
        ex=x+side*9;ey=y+22-17*d
        r.limb([(x+side*8,y+8),(ex,ey)],TEAL,2.5)
        r.ball(ex,ey,5,5,COPPER)
        if d<.65:
            r.poly([(ex-4,ey+2),(ex+4,ey+1),(ex+3,ey-2),(ex-3,ey-2)],OUTLINE)
            r.line([(ex-2,ey),(ex+2,ey)],AMBER[3],1)
            r.ellipse(ex-1,ey+1,.8,.8,WHITE)
        r.line([(ex-side*4,ey+5),(ex+side*4,ey+2)],COPPER[0],2)
    r.poly([(x-8,y-3),(x+8,y-3),(x+5,y-9),(x,y-7),(x-5,y-9)],OUTLINE)
    for side in (-1,1):r.poly([(x+side*5,y-3),(x+side*2,y-7),(x+side,y-3)],BONE[3])
    return a


def cargomaw(setup,clip,n):
    a,r,w,s,d,ph,b=setup('keel_cargomaw',clip,n,(0,10),-.83)
    x,y=18*s-8*w,27+b+4*w-9*d
    for side in (-1,1):
        for j in range(3):
            step=math.sin(ph+j*1.8+side)*4 if clip=='walk' else 0
            r.limb([(x+side*22,y-4+j*4),(x+side*(34-6*d),y-8+j*4+step),(x+side*(43-9*d)+step,3+j*2+12*d)],TEAL,3.5)
    # Deep wooden chest body: rounded bevels, separate side plane, copper bands.
    r.ball(x,y,28,20,WOOD)
    r.poly([(x-27,y+10),(x+21,y+10),(x+28,y+3),(x+28,y-16),(x-25,y-17)],WOOD[2],OUTLINE)
    r.poly([(x+21,y+10),(x+28,y+3),(x+28,y-16),(x+21,y-10)],WOOD[0])
    for j in range(3):r.line([(x-23,y+5-j*7),(x+20,y+5-j*7)],WOOD[0],1)
    for xx in (x-17,x+15):
        r.limb([(xx,y+13),(xx,y-14)],COPPER,3)
        for yy in (y+7,y-8):r.ellipse(xx,yy,1,1,BONE[2])
    # Lid is hinged at rear corners; the maw opens between base and lid, never disconnects.
    gape=(5+20*w+7*s)*(1-.95*d)
    ly=y+13+gape
    r.poly([(x-24,y+10),(x-25,ly),(x+23,ly),(x+25,y+10)],OUTLINE)
    for side in (-1,1):
        r.limb([(x+side*24,y+10),(x+side*26,y+12+gape*.5),(x+side*24,ly)],COPPER,2.5)
        r.ball(x+side*26,y+12+gape*.5,3,3,COPPER)
    r.ball(x,ly+3,28,11,WOOD)
    r.line([(x-24,ly),(x+24,ly)],COPPER[3],3)
    for xx in (x-17,x+15):r.limb([(xx,ly+10),(xx,ly-1)],COPPER,2.5)
    for j in range(7):
        xx=x-19+j*6
        r.poly([(xx-2,ly-1),(xx+2,ly-1),(xx,ly-7-j%2*2)],BONE[3],OUTLINE)
        r.poly([(xx-2,y+10),(xx+2,y+10),(xx,y+16+j%2*2)],BONE[3],OUTLINE)
    # Asymmetric keyhole sockets sit in the lid, rather than shared crab eye stalks.
    for side in (-1,1):
        ex=x+side*11;ey=ly+5+side
        r.ellipse(ex,ey,4,3,OUTLINE)
        r.poly([(ex-1,ey),(ex+1,ey),(ex+2,ey-6),(ex-2,ey-6)],OUTLINE)
        if d<.7:r.line([(ex-2,ey+1),(ex+2,ey)],TEAL[3],1)
    r.ball(x,y-2,6,7,COPPER)
    r.ellipse(x,y-1,2,3,OUTLINE)
    r.line([(x-1,y-3),(x+1,y-3)],GOLD[3],1)
    return a


def lantern(setup,clip,n):
    a,r,w,s,d,ph,b=setup('keel_lantern',clip,n,(0,38),-1.38)
    x,y=11*s-6*w,58+b+5*w
    # Rigid cage and chained handle rotate as one object. Only the flame diminishes.
    r.limb([(x-7,y+23),(x-8,y+34),(x+8,y+34),(x+7,y+23)],COPPER,2)
    r.ball(x,y+21,14,5,NAVY)
    r.ball(x,y,14,22,COPPER)
    r.ball(x,y,10,18,NAVY)
    f=1-d
    if f>.03:
        fy=y-5+6*s+8*d
        r.ball(x,fy,8*f+2*s*f,13*f,TEAL)
        r.poly([(x-7*f,fy),(x-9*f,fy+16*f),(x-2*f,fy+10*f),(x+2*f,fy+23*f),(x+8*f,fy+6*f),(x+5*f,fy-7*f)],TEAL[2])
        r.ball(x-1,fy-1,4*f,8*f,PEARL)
        # Cruel angular holes are cut into the flame; its face differs from crew and crabs.
        for side in (-1,1):
            ex=x+side*4;ey=fy+3
            r.poly([(ex-side*3,ey+3),(ex+side*3,ey),(ex,ey-3)],OUTLINE)
        r.poly([(x-4,fy-5),(x,fy-2),(x+4,fy-5),(x,fy-9)],OUTLINE)
    for xx in (x-11,x+11):r.limb([(xx,y-16),(xx,y+18)],COPPER,2)
    r.ball(x,y-21,17,4,COPPER)
    r.poly([(x-16,y+19),(x-11,y+28),(x+11,y+28),(x+16,y+19)],NAVY[2],OUTLINE)
    r.line([(x-13,y+20),(x+13,y+20)],COPPER[3],2)
    for side in (-1,1):r.limb([(x+side*9,y-22),(x+side*12,y-29)],COPPER,2)
    # A connected pressure tongue makes the spell attack reach outside the cage.
    if s>0 and d==0:
        r.taper([(x+5,y),(x+14+12*s,y+4),(x+18+29*s,y+9*s)],TEAL,5*s,.6)
    return a


def legs(r,x,y,ph,clip,d):
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        foot=(x+side*8+step+side*4*d,3+7*d)
        r.limb([(x+side*7,y-11),(x+side*(9-4*d)+step,13+6*d),foot],NAVY,4)
        r.ball(foot[0]+2,foot[1],7,4,NAVY)
        r.line([(foot[0]-3,foot[1]+1),(foot[0]+5,foot[1]+1)],COPPER[2],1)


def crew_body(r,x,y,ph,clip,d,broad=False,captain=False):
    legs(r,x,y,ph,clip,d)
    if captain:
        for side in (-1,1):
            r.poly([(x+side*5,y+18),(x+side*18,y+18),(x+side*(24-8*d),y-23),(x+side*8,y-17)],NAVY[1],OUTLINE)
            r.line([(x+side*16,y+14),(x+side*17,y-17)],COPPER[2],2)
    wid=19 if broad else 14
    r.ball(x,y, wid,19,NAVY)
    r.ball(x-2,y+3,wid-5,14,NAVY)
    for side in (-1,1):r.line([(x+side*8,y+15),(x+side*4,y-4)],COPPER[2],1)
    r.ball(x,y-10,wid,4,WOOD)
    r.ball(x+1,y-10,4,4,COPPER)
    r.line([(x-2,y-10),(x+3,y-10)],BONE[3],1)


def deckhand(setup,clip,n):
    a,r,w,s,d,ph,b=setup('keel_deckhand',clip,n,(0,8),-1.43)
    x,y=13*s-6*w,29+b+4*w-10*d
    crew_body(r,x,y,ph,clip,d)
    hx,hy=x,y+30
    r.limb([(x,y+15),(hx,hy-7)],SEA,5)
    r.ball(hx,hy,11,12,SEA)
    r.ball(hx-2,hy+1,7,9,SEA)
    # Deep hollow unequal eyes, exposed pale cheekbone and a jagged tooth snarl.
    for side in (-1,1):
        ex=hx+side*5;ey=hy+2
        r.poly([(ex-4,ey+3),(ex+3,ey+1),(ex+3,ey-3),(ex-3,ey-2)],OUTLINE)
        if d<.7:r.line([(ex-2,ey),(ex+1,ey)],PEARL[3],1)
        r.line([(ex-side*4,ey+5),(ex+side*3,ey+2)],SEA[0],2)
    r.poly([(hx-6,hy-5),(hx+6,hy-4),(hx+4,hy-9),(hx-5,hy-8)],OUTLINE)
    for j in range(4):r.line([(hx-4+j*3,hy-5),(hx-3+j*3,hy-7)],BONE[3],1)
    r.ball(hx,hy+12,14,4,NAVY)
    r.poly([(hx-12,hy+12),(hx-10,hy+22),(hx+9,hy+21),(hx+12,hy+11)],NAVY[2],OUTLINE)
    r.line([(hx-10,hy+13),(hx+11,hy+13)],BONE[2],2)
    free=(x-21+10*d,y-4+12*w)
    r.limb([(x-12,y+12),(x-20+12*d,y+4),free],NAVY,4);hand(r,*free,d)
    grip=(x+20+19*s-8*w-10*d,y+1+19*w-10*s)
    r.limb([(x+12,y+13),(x+22-5*w,y+7+10*w),grip],NAVY,4)
    angle=-.2-1.25*w+1.8*s+.8*d;dx,dy=math.sin(angle),math.cos(angle);ux,uy=dy,-dx
    r.limb([(grip[0]-dx*7,grip[1]-dy*7),(grip[0]+dx*25,grip[1]+dy*25)],WOOD,2)
    tip=(grip[0]+dx*24,grip[1]+dy*24)
    r.poly([(grip[0]+dx*5,grip[1]+dy*5),(tip[0],tip[1]),(tip[0]+ux*10,tip[1]+uy*10),(grip[0]+dx*7+ux*8,grip[1]+dy*7+uy*8)],COPPER[2],OUTLINE)
    r.line([tip,(tip[0]+ux*10,tip[1]+uy*10)],COPPER[4],2)
    hand(r,*grip,d)
    return a


def bosun(setup,clip,n):
    a,r,w,s,d,ph,b=setup('keel_bosun',clip,n,(0,8),-1.35)
    x,y=8*s-5*w,31+b+4*w-11*d
    crew_body(r,x,y,ph,clip,d,broad=True)
    hx,hy=x,y+32
    r.limb([(x,y+18),(hx,hy-6)],SEA,6)
    r.ball(hx,hy,13,13,SEA)
    r.ball(hx-2,hy+1,8,10,SEA)
    # One squinting eye, a dark patch and a thick broken brow distinguish Brinehook.
    r.poly([(hx-10,hy+3),(hx-2,hy+5),(hx-2,hy-2),(hx-9,hy-3)],NAVY[0],OUTLINE)
    r.line([(hx-11,hy+7),(hx+10,hy-4)],WOOD[1],1)
    r.line([(hx+2,hy+5),(hx+10,hy+2)],SEA[0],3)
    if d<.65:r.line([(hx+3,hy+1),(hx+8,hy+1)],AMBER[3],1)
    r.ball(hx+2,hy-3,3,4,SEA)
    r.line([(hx-6,hy-8),(hx+6,hy-9)],OUTLINE,2)
    r.line([(hx-1,hy-8),(hx+2,hy-8)],BONE[3],2)
    r.poly([(hx-13,hy+7),(hx-11,hy+18),(hx+10,hy+19),(hx+14,hy+7)],CORAL[1],OUTLINE)
    r.line([(hx-11,hy+9),(hx+12,hy+9)],CORAL[3],2)
    r.poly([(hx-12,hy+10),(hx-23,hy+13),(hx-18,hy+2),(hx-10,hy+4)],CORAL[2],OUTLINE)
    # A real rope coil stays attached to the off hand throughout the cast.
    coil=(x-24+10*d,y+3)
    r.limb([(x-16,y+15),(x-23+10*d,y+12),coil],NAVY,5)
    r.ball(*coil,10,14,BONE);r.ball(*coil,5,8,WOOD)
    for j in range(3):r.line([(coil[0]-7+j*2,coil[1]+10),(coil[0]-9+j*2,coil[1]-8)],BONE[0],1)
    hand(r,coil[0]+2,coil[1]+7,d)
    grip=(x+22+16*s-8*w-10*d,y+2+18*w-8*s)
    r.limb([(x+17,y+15),(x+24-7*w,y+10+7*w),grip],NAVY,5)
    hx2,hy2=grip[0]+26*s,grip[1]+7*s
    hook_angle=-.15+1.45*s-.75*w
    hook_eye=(hx2+math.sin(hook_angle)*15,hy2+math.cos(hook_angle)*15)
    r.line([coil,(x,y-1),grip,hook_eye],BONE[0],3)
    r.line([coil,(x,y-1),grip,hook_eye],BONE[3],1)
    hook(r,hx2,hy2,hook_angle,1.0)
    hand(r,*grip,d)
    return a


def captain(setup,clip,n):
    a,r,w,s,d,ph,b=setup('keel_captain',clip,n,(0,8),-1.4)
    x,y=10*s-7*w,30+b+4*w-10*d
    crew_body(r,x,y,ph,clip,d,captain=True)
    for side in (-1,1):r.ball(x+side*15,y+16,7,6,COPPER)
    hx,hy=x,y+32
    r.limb([(x,y+16),(hx,hy-9)],SEA,4)
    # Exposed angular cheekbones, stern almond eyes and individually shaded ivory braids.
    r.ball(hx,hy,10,13,SEA)
    r.poly([(hx-9,hy+2),(hx-5,hy-9),(hx+2,hy-12),(hx+9,hy-5),(hx+9,hy+5)],SEA[2])
    for side in (-1,1):
        ex=hx+side*4;ey=hy+3
        r.poly([(ex-side*4,ey+2),(ex+side*3,ey),(ex+side*2,ey-2),(ex-side*2,ey-2)],OUTLINE)
        if d<.65:r.line([(ex-side*2,ey),(ex+side,ey)],TEAL[4],1)
        r.line([(ex-side*4,ey+5),(ex+side*3,ey+2)],SEA[0],2)
        for j in range(6):r.ball(hx+side*(10+j*.2),hy+5-j*4,2.4,3,BONE)
        r.ball(hx+side*11,hy-17,2,2,COPPER)
    r.line([(hx,hy+3),(hx-1,hy-3),(hx+2,hy-4)],SEA[0],1)
    r.line([(hx-4,hy-8),(hx+4,hy-8)],OUTLINE,1)
    r.poly([(hx-16,hy+10),(hx-23,hy+23),(hx-9,hy+19),(hx,hy+30),(hx+8,hy+19),(hx+23,hy+23),(hx+16,hy+10)],NAVY[1],OUTLINE)
    r.line([(hx-21,hy+22),(hx-8,hy+17),(hx,hy+27),(hx+8,hy+17),(hx+21,hy+22)],COPPER[3],2)
    r.ball(hx,hy+17,3,4,CORAL)
    angle=-.16-1.4*w+1.9*s+.95*d;dx,dy=math.sin(angle),math.cos(angle);ux,uy=dy,-dx
    grip=(x+22+17*s-9*w-11*d,y+6+23*w-8*s)
    low=(grip[0]-dx*13,grip[1]-dy*13)
    def pt(u,v):return grip[0]+ux*u+dx*v,grip[1]+uy*u+dy*v
    # Ring, stock, shank and twin curved flukes make an anchor at every angle.
    r.limb([pt(0,-18),pt(0,30)],COPPER,3)
    r.ball(*pt(0,34),5,5,COPPER);r.ellipse(*pt(0,34),2,2,OUTLINE)
    r.limb([pt(-12,17),pt(12,17)],COPPER,2.5)
    r.limb([pt(-17,-8),pt(-12,-18),pt(0,-23),pt(12,-18),pt(17,-8)],COPPER,3.5)
    for side in (-1,1):r.poly([pt(side*17,-8),pt(side*11,-11),pt(side*18,0)],COPPER[3],OUTLINE)
    for side,point in ((-1,low),(1,grip)):
        r.limb([(x+side*13,y+17),(x+side*(21-8*d)-4*w,y+10+10*w),point],NAVY,4)
        hand(r,*point,d)
    return a
