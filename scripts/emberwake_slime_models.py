"""Emberwake connected anatomy, rigid plates, articulated jaws and material deaths."""
import math
from astral_slime_redraw import OUTLINE, WHITE, BONE, GOLD, BROWN
IRON = FIRE = GLASS = CLOTH = SKIN = None


def cooled(d, ramp=None):
    return (ramp or FIRE) if d < .64 else IRON


def plate(r, pts, ramp):
    r.poly(pts, ramp[1], OUTLINE)
    cx=sum(x for x,y in pts)/len(pts);cy=sum(y for x,y in pts)/len(pts)
    r.poly([pts[0],pts[1],(cx,cy)],ramp[3])
    r.poly([pts[-1],pts[0],(cx,cy)],ramp[2])


def links(r, pts, d=0):
    # Contiguous elliptical links share their ends, including both attachment rings.
    for (x,y),(xx,yy) in zip(pts,pts[1:]):
        length=math.hypot(xx-x,yy-y);count=max(1,round(length/6))
        for j in range(count+1):
            t=j/count;px=x+(xx-x)*t;py=y+(yy-y)*t
            r.ball(px,py,3.7,4,IRON)
            r.ellipse(px,py,1.6,2,IRON[0])


def leg(r,x,y,side,step,d,ramp=None):
    ramp=ramp or IRON
    knee=(x+side*(7-3*d),y-13+step+8*d)
    toe=(x+side*(11-8*d)+step,4+20*d)
    r.limb([(x,y),knee,toe],ramp,3.6)
    r.ball(*knee,4.5,4.5,ramp)
    r.ball(toe[0]+2,toe[1],6.4,3.8,ramp)
    for j in range(3):r.line([(toe[0]+1+j*2,toe[1]),(toe[0]+3+j*2,toe[1]-2)],BONE[2],1)


def ashback(setup,clip,n):
    a,r,w,s,d,ph,b=setup('ew_ashback',clip,n,(-5,13),.06)
    x=10*s-6*w;y=23+b+4*w-5*d
    # Long tapered flexible tail belongs to a salamander, not a generic round beast.
    tail=[(x-20,y),(x-34,y-4+math.sin(ph)*2),(x-46-12*w+7*s,y-9+10*w),(x-55-12*w+10*s,y-8+15*w)]
    r.taper(tail,cooled(d),8,1)
    for side in (-1,1):
        for j in range(2):
            step=math.sin(ph+j*math.pi+side)*3 if clip=='walk' else 0
            leg(r,x-17+j*35,y-1,side,step,d,cooled(d))
    r.ball(x-2,y,28,12,cooled(d))
    for j in range(5):
        xx=x-23+j*10;yy=y+10+math.sin(j*.7)*3
        plate(r,[(xx-6,yy-2),(xx-3,yy+9),(xx+4,yy+6),(xx+6,yy-4)],IRON)
    hx=x+26+13*s-4*w;hy=y+4+8*w-3*s
    r.limb([(x+13,y),(hx-6,hy)],cooled(d),8)
    r.ball(hx,hy,14,8,IRON);r.ball(hx+7,hy-3,10,4,cooled(d))
    # Narrow lizard socket, a pin pupil and a heavy overhanging ridge.
    r.poly([(hx-5,hy+5),(hx+7,hy+4),(hx+5,hy),(hx-4,hy+1)],OUTLINE)
    if d<.6:r.line([(hx+1,hy+3),(hx+5,hy+2)],FIRE[4],2)
    r.line([(hx-6,hy+7),(hx+8,hy+5)],IRON[1],3)
    r.line([(hx+4,hy-4),(hx+16,hy-4)],OUTLINE,1)
    r.ellipse(hx+13,hy,1,1,OUTLINE)
    return a


def glasswing(setup,clip,n):
    a,r,w,s,d,ph,b=setup('ew_glasswing',clip,n,(0,45),.85)
    x=8*s-5*w;y=49+b+5*w
    for side in (-1,1):
        hinge=(x+side*5,y+1)
        # Rigid panels rotate at the root; none are scaled into rubber on death.
        angle=side*(.10*math.sin(ph)-.65*w+.95*s+1.05*d)
        def p(u,v):
            return hinge[0]+side*(u*math.cos(angle)-v*math.sin(angle)),hinge[1]+u*math.sin(angle)+v*math.cos(angle)
        panel=[p(0,0),p(28,26),p(37,16),p(32,-17),p(12,-21)]
        plate(r,panel,GLASS)
        for u,v in [(28,26),(37,16),(32,-17)]:r.line([hinge,p(u,v)],IRON[1],2)
        r.line([p(7,1),p(22,12),p(30,7)],cooled(d)[3],1)
        if d>.25:
            r.line([p(13,9),p(20,1),p(16,-7),p(25,-12)],IRON[0],3)
            r.line([p(14,9),p(21,1),p(17,-7)],GLASS[4],1)
        if s>0 and d==0:
            tip=p(37,16)
            r.line([tip,(tip[0]+side*16*s,tip[1]-8*s)],FIRE[2],3)
            plate(r,[(tip[0]+side*12*s,tip[1]-5*s),(tip[0]+side*23*s,tip[1]-10*s),(tip[0]+side*14*s,tip[1]-12*s)],FIRE)
    r.ball(x,y-5,7,19,IRON)
    for j in range(4):r.line([(x-5,y-17+j*6),(x+5,y-17+j*6)],cooled(d)[2],1)
    r.ball(x,y+15,10,10,IRON)
    for side in (-1,1):
        ex=x+side*6
        plate(r,[(ex-side*4,y+21),(ex+side*4,y+21),(ex+side*5,y+13),(ex,y+11)],cooled(d,GLASS))
        if d<.65:
            for j in range(3):r.ellipse(ex+(j%2)*2-1,y+15+j*2,1,1,WHITE)
        r.limb([(x+side*4,y+23),(x+side*10,y+33),(x+side*13,y+31)],IRON,1.3)
        for j in range(3):
            r.limb([(x+side*4,y+6-j*7),(x+side*(12-4*d),y-j*7),(x+side*(17-10*d),y-8-j*7+8*d)],IRON,1.6)
    r.poly([(x-3,y+10),(x,y+3),(x+3,y+10)],BONE[2],OUTLINE)
    return a


def slagjaw(setup,clip,n):
    a,r,w,s,d,ph,b=setup('ew_slagjaw',clip,n,(-4,12),.05)
    x=9*s-5*w;y=23+b+4*w-5*d
    for side in (-1,1):
        for j in range(2):leg(r,x-19+j*32,y,side,math.sin(ph+j*2+side)*3 if clip=='walk' else 0,d)
    r.ball(x-4,y,27,16,IRON)
    for j in range(5):
        xx=x-28+j*10;yy=y+12+math.sin(j*.7)*5
        plate(r,[(xx-5,yy-5),(xx-4,yy+12),(xx+3,yy+18),(xx+9,yy-4)],IRON)
        r.line([(xx,yy),(xx+2,yy+11)],cooled(d)[2],1)
    hx=x+21+16*s-6*w;hy=y-1+11*w
    r.limb([(x+13,y),(hx,hy)],IRON,7)
    plate(r,[(hx-9,hy+9),(hx+7,hy+10),(hx+21,hy+1),(hx+18,hy-5),(hx-9,hy-5)],IRON)
    r.poly([(hx-2,hy+7),(hx+9,hy+4),(hx+8,hy),(hx-1,hy+1)],OUTLINE)
    if d<.65:r.ellipse(hx+4,hy+3,2,1,FIRE[4])
    # Lower jaw rotates about an exact visible rear hinge, teeth move with it.
    angle=-.65*w+.18*s
    def jaw(u,v):return hx-7+u*math.cos(angle)-v*math.sin(angle),hy-4+u*math.sin(angle)+v*math.cos(angle)
    plate(r,[jaw(0,0),jaw(27,0),jaw(25,-6),jaw(1,-7)],cooled(d))
    for j in range(5):r.poly([jaw(5+j*4,0),jaw(8+j*4,0),jaw(7+j*4,4)],BONE[3],OUTLINE)
    r.ball(hx-7,hy-4,4,4,IRON)
    return a


def cinderhorn(setup,clip,n):
    a,r,w,s,d,ph,b=setup('ew_cinderhorn',clip,n,(-4,14),.05)
    x=13*s-7*w;y=32+b-3*d
    for side in (-1,1):
        for j in range(2):leg(r,x-19+j*33,y-4,side,math.sin(ph+j*2+side)*4 if clip=='walk' else 0,d)
    r.ball(x-6,y,25,16,IRON);r.ball(x+8,y+7,15,20,IRON)
    r.taper([(x-28,y+5),(x-35,y+12),(x-38,y+9)],cooled(d),4,1)
    hx=x+23+11*s-5*w;hy=y+15+14*w-16*s
    r.limb([(x+8,y+6),(hx-5,hy-4)],cooled(d),9)
    r.ball(hx,hy,12,14,cooled(d));r.ball(hx+6,hy-9,9,7,IRON)
    # True spiral iron horns with a bright outer ridge, attached to the head.
    for side in (-1,1):
        cx=hx-8+side*9;cy=hy+10
        pts=[(cx+math.cos(t)*rr,cy+math.sin(t)*rr) for t,rr in [(j*.30,12-j*.44) for j in range(20)]]
        r.limb(pts,IRON,3)
        r.line(pts[:10],GOLD[2],1)
    r.poly([(hx+1,hy+3),(hx+10,hy+3),(hx+9,hy-1),(hx+2,hy-1)],OUTLINE)
    if d<.65:
        r.poly([(hx+3,hy+2),(hx+9,hy+2),(hx+9,hy),(hx+3,hy)],GOLD[3])
        r.line([(hx+5,hy+2),(hx+5,hy)],OUTLINE,1)
    r.line([(hx,hy+6),(hx+10,hy+4)],IRON[0],3)
    r.poly([(hx-5,hy-15),(hx+3,hy-15),(hx-1,hy-26)],IRON[1],OUTLINE)
    r.ellipse(hx+12,hy-8,2,1,OUTLINE)
    return a


def chainmaw(setup,clip,n):
    a,r,w,s,d,ph,b=setup('ew_chainmaw',clip,n,(-5,13),.04)
    x=10*s-6*w;y=29+b+5*w-6*d
    for side in (-1,1):
        for j in range(2):leg(r,x-20+j*35,y-3,side,math.sin(ph+j*2+side)*3 if clip=='walk' else 0,d)
    r.ball(x-6,y,28,20,IRON)
    for j in range(3):
        xx=x-23+j*12
        r.line([(xx-4,y-8),(xx+2,y+9),(xx-2,y+17)],cooled(d)[2],2)
    hx=x+23+13*s-5*w;hy=y+2+13*w-10*s
    r.limb([(x+9,y+4),(hx-5,hy)],IRON,11)
    plate(r,[(hx-14,hy+15),(hx+11,hy+17),(hx+23,hy+4),(hx+22,hy-7),(hx-12,hy-6)],IRON)
    # One scarred gouge rather than the ram's horizontal pupil or lizard socket.
    r.poly([(hx-1,hy+10),(hx+12,hy+9),(hx+9,hy+1),(hx+2,hy+2)],OUTLINE)
    if d<.65:r.line([(hx+5,hy+8),(hx+7,hy+3)],FIRE[4],2)
    r.line([(hx+11,hy+16),(hx+5,hy+5),(hx+1,hy-1)],IRON[0],2)
    angle=-.58*w+.15*s
    def jaw(u,v):return hx-8+u*math.cos(angle)-v*math.sin(angle),hy-6+u*math.sin(angle)+v*math.cos(angle)
    plate(r,[jaw(0,0),jaw(30,0),jaw(27,-9),jaw(2,-8)],IRON)
    for j in range(4):r.poly([jaw(6+j*6,0),jaw(10+j*6,0),jaw(9+j*6,6)],GOLD[3],OUTLINE)
    # Bridle starts at a collar rivet and ends at the transformed jaw ring.
    end=jaw(17,-6);start=(x+3,y+16)
    links(r,[start,(x+6,y-11+7*d),end],d)
    links(r,[(x-23,y+14),(x-32,y-2),(x-27+8*d,y-18+10*d)],d)
    r.ball(*jaw(0,-1),4,4,IRON)
    return a


def bellows(setup,clip,n):
    a,r,w,s,d,ph,b=setup('ew_bellows',clip,n,(0,12),-1.35)
    x=5*s-4*w;y=37+b-9*d
    for j,side in enumerate((-1,1)):
        step=math.sin(ph+j*math.pi)*4 if clip=='walk' else 0
        leg(r,x+side*9,y-14,side,step,d)
    plate(r,[(x-18,y+17),(x+17,y+17),(x+23,y-22),(x-23,y-22)],CLOTH)
    r.poly([(x-9,y+12),(x+9,y+12),(x+10,y-15),(x-10,y-15)],IRON[1],OUTLINE)
    for j in range(4):r.line([(x-7,y+8-j*5),(x+7,y+8-j*5)],cooled(d)[2],1)
    hx=x;hy=y+32
    r.ball(hx,hy,12,14,SKIN)
    r.poly([(hx+1,hy+12),(hx+9,hy+9),(hx+11,hy-3),(hx+3,hy-12)],SKIN[1])
    for side in (-1,1):
        ex=hx+side*5
        r.poly([(ex+side*5,hy+6),(ex-side*3,hy+2),(ex,hy-2)],OUTLINE)
        if d<.65:r.line([(ex+side*2,hy+3),(ex-side,hy+1)],GLASS[4],1)
    r.line([(hx-4,hy-8),(hx+5,hy-7)],OUTLINE,2)
    plate(r,[(hx-13,hy+10),(hx-16,hy+23),(hx-5,hy+17),(hx+1,hy+26),(hx+7,hy+16),(hx+15,hy+23),(hx+12,hy+10)],IRON)
    for side in (-1,1):
        elbow=(x+side*(26+8*w-12*d),y+8+8*w)
        start=(elbow[0],elbow[1]-5)
        length=21+17*w-11*s
        end=(start[0]+side*(7+14*s-4*d),start[1]-length+18*s+10*d)
        r.limb([(x+side*16,y+14),elbow,start],SKIN,4)
        # Accordion folds span the exact elbow-to-nozzle segment.
        for j in range(7):
            t=j/6;px=start[0]+(end[0]-start[0])*t;py=start[1]+(end[1]-start[1])*t
            r.ball(px,py,8 if j%2==0 else 6,3.5,IRON if j%2==0 else CLOTH)
        r.ball(*end,9,5,IRON)
        r.ellipse(end[0]+side*3,end[1]+1,4,2,IRON[0])
        if s>0 and d==0:
            r.taper([end,(end[0]+side*13*s,end[1]+7*s),(end[0]+side*27*s,end[1]+3*s)],FIRE,7*s,1)
    return a


def crown(setup,clip,n):
    a,r,w,s,d,ph,b=setup('ew_crown',clip,n,(0,12),-.98)
    x=7*s-4*w;y=39+b+4*w-10*s-10*d
    for j,side in enumerate((-1,1)):leg(r,x+side*12,y-16,side,math.sin(ph+j*math.pi)*4 if clip=='walk' else 0,d)
    r.ball(x,y,23,28,IRON)
    for side in (-1,1):
        r.ball(x+side*20,y+18,12,12,IRON)
        hand=(x+side*(32+8*s-6*w-15*d),y-5+30*w-15*s+13*d)
        r.limb([(x+side*20,y+15),(x+side*31,y+8+14*w),hand],IRON,6)
        r.ball(*hand,11,13,cooled(d))
        for j in range(3):r.line([(hand[0]-5+j*4,hand[1]+6),(hand[0]-5+j*4,hand[1]-7)],IRON[0],1)
    r.ball(x,y-1,10,14,cooled(d))
    r.line([(x-8,y+16),(x+3,y+7),(x-2,y-11)],cooled(d)[3],3)
    hx=x;hy=y+31
    r.ball(hx,hy,16,17,IRON)
    # Asymmetric volcanic fissures and a split furnace mouth.
    r.poly([(hx-13,hy+7),(hx-2,hy+3),(hx-5,hy-3),(hx-12,hy)],OUTLINE)
    r.poly([(hx+3,hy+7),(hx+13,hy+10),(hx+11,hy-2),(hx+4,hy-3)],OUTLINE)
    if d<.64:
        r.line([(hx-10,hy+4),(hx-5,hy+2)],FIRE[4],2)
        r.line([(hx+9,hy+7),(hx+7,hy)],FIRE[3],2)
    r.poly([(hx-8,hy-8),(hx-3,hy-6),(hx+1,hy-9),(hx+9,hy-7),(hx+6,hy-14),(hx-5,hy-15)],cooled(d)[2],OUTLINE)
    # Separate broken crown drops onto the ground beside the fallen stone body.
    cr=r if d<.5 else type(r)(a,0,0,0)
    cx=hx if d<.5 else 20+24*d
    cy=hy+27 if d<.5 else (hy+27)*(1-d)-3*d
    plate(cr,[(cx-18,cy),(cx-20,cy+15),(cx-10,cy+8),(cx-6,cy+18),(cx-2,cy+3),(cx+6,cy),(cx+10,cy+13),(cx+14,cy+6),(cx+19,cy+14),(cx+17,cy-2)],GOLD)
    return a
