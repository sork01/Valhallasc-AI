"""Seven distinct native rigs. Rigid anatomy rotates; only flames/petals dissipate."""
import math
from astral_slime_redraw import OUTLINE, WHITE, EYE_WHITE, BONE, GOLD, BROWN, LEAF, SLATE, AMBER, CRIMSON, PEARL, PINK, VIOLET
from lapis_slime_redraw import Rig


class Socket(Rig):
    """A prop expressed relative to a world-space wrist, inheriting its rotation."""
    def __init__(self,a,x,y,phi):
        super().__init__(a,0,0,phi);self.ox,self.oy=x,y
    def t(self,x,y):
        u,v=super().t(x,y);return u+self.ox,v+self.oy


def plate(r, points, ramp):
    r.poly(points,ramp[1],OUTLINE)
    x=sum(p[0] for p in points)/len(points);y=sum(p[1] for p in points)/len(points)
    r.poly([points[0],points[1],(x,y)],ramp[3])
    r.line(points[:2],ramp[4],1)


def flame(r,x,y,h,phase,death=0):
    h*=max(0,1-death*1.7)
    if h<1:return
    for j in range(3):
        xx=x+(j-1)*h*.13;top=y+h*(.66+.25*math.sin(phase+j*.9)**2)
        r.poly([(xx-h*.22,y),(xx-h*.14,y+h*.5),(xx+math.sin(phase+j)*h*.10,top),(xx+h*.19,y+h*.3),(xx+h*.20,y)],AMBER[1],OUTLINE)
        r.poly([(xx-h*.1,y),(xx,y+h*.65),(xx+h*.12,y)],AMBER[4])


def feet(r,d,phase,walk,ramp,width=5,hip=26):
    for side in (-1,1):
        step=math.sin(phase+(side+1)*math.pi/2)*4 if walk else 0
        x=side*8
        r.limb([(x,hip),(x+side*5*d,14-6*d),(x+side*8*d+step,5+5*d)],ramp,width)
        r.ball(x+side*8*d+step+2,4+5*d,7,4,ramp)


def leaf(r,x,y,ang,ramp=LEAF,size=6):
    dx,dy=math.cos(ang)*size,math.sin(ang)*size
    r.poly([(x-dx,y-dy),(x-dy*.45,y+dx*.45),(x+dx,y+dy),(x+dy*.45,y-dx*.45)],ramp[2],ramp[0])
    r.line([(x-dx*.8,y-dy*.8),(x+dx*.8,y+dy*.8)],ramp[4],1)


def ember_firelord(setup,clip,n):
    a,r,w,s,d,ph,b=setup('ember_firelord',clip,n,(0,12),-.25)
    b-=24*d
    cool=BASALT if d>.55 else AMBER
    # A compact basalt giant, broken cross-shaped crown, no Eldmarr cleaver/chain regalia.
    feet(r,d,ph,clip=='walk',BASALT,7,22)
    r.ball(0,30+b,25,18,BASALT);r.ball(-20,41+b,14,10,BASALT);r.ball(20,41+b,14,10,BASALT)
    for dx in (-11,0,11):
        r.line([(dx-3,39+b),(dx+2,31+b),(dx-2,23+b)],cool[3],2)
    left=(-30-9*w+18*s,22+20*w+8*s+b)
    right=(29-12*w+28*s,28+15*w-14*s+b)
    for sh,hand in [((-22,41+b),left),((22,41+b),right)]:
        mid=((sh[0]+hand[0])/2,hand[1]+9)
        r.limb([sh,mid,hand],BASALT,7);r.ball(*hand,9,8,BASALT)
        if d<.6:flame(r,hand[0],hand[1]+4,10+11*s,ph,d)
    # The heavy skull rolls down beside the buckling torso on death.
    h=Socket(a,*r.t(18*d,54+b-14*d),r.phi-1.2*d)
    h.ball(0,0,19,13,BASALT)
    for side in (-1,1):
        x=side*8
        h.poly([(x-side*6,4),(x+side*7,7),(x+side*5,-1),(x-side*4,-2)],OUTLINE)
        if d<.6:h.line([(x-side*3,1),(x+side*3,3)],AMBER[4],2)
        h.line([(side*2,5),(side*17,10)],BASALT[0],3)
        plate(h,[(side*13,7),(side*26,18),(side*22,4)],BASALT)
    h.poly([(-12,-5),(-6,-3),(0,-6),(7,-4),(13,-7),(5,-11),(-6,-10)],OUTLINE)
    for x in (-8,-1,6):h.poly([(x,-6),(x+3,-6),(x+1,-10)],cool[3])
    for j in range(3):flame(h,(j-1)*9,7,17-j%2*4,ph+j,d)
    if d:
        # Separate rigid chips settle near the cooled giant, rather than squash.
        ground=Rig(a,0,0,0)
        for j in range(4):
            x=-27+j*18+d*5;y=2+(1-d)*(17+j*2)
            plate(ground,[(x-3,y),(x,y+4),(x+4,y+1),(x+2,y-2)],BASALT)
    return a


def hollow_rider(setup,clip,n):
    a,_,w,s,d,ph,b=setup('hollow_rider',clip,n,(0,15),0)
    horse=Rig(a,0,15,-.18*d)
    # Four jointed horse legs fold individually under an intact barrel.
    for back in (True,False):
        for side in (-1,1):
            x=side*17+(3 if back else 0);step=math.sin(ph+(side+1)*1.57+(2 if back else 0))*5 if clip=='walk' else 0
            horse.limb([(x,33),(x+step+side*7*d,18+21*d),(x-step-side*8*d,4+40*d)],BASALT,3 if back else 4)
            horse.ball(x-step-side*8*d,3+40*d,5,3,BASALT)
    horse.ball(0,34+b,24,12,BASALT)
    horse.limb([(16,36+b),(21,49+b-17*d),(29,51+b-23*d)],BASALT,7)
    horse.ball(29,50+b-23*d,8,10,BASALT);horse.ball(35,45+b-23*d,9,5,BASALT)
    horse.poly([(24,57+b-23*d),(25,68+b-23*d),(29,58+b-23*d)],BASALT[2],OUTLINE)
    horse.poly([(31,57+b-23*d),(35,65+b-23*d),(35,55+b-23*d)],BASALT[2],OUTLINE)
    horse.line([(30,52+b-23*d),(34,53+b-23*d)],AMBER[4] if d<.65 else OUTLINE,2)
    horse.line([(30,49+b-23*d),(35,44+b-23*d)],BASALT[4],2)
    horse.ellipse(39,44+b-23*d,1.4,1.1,OUTLINE)
    horse.limb([(-20,39+b),(-30,33+b),(-34,23+b)],BASALT,3)
    flame(horse,-31,23+b,15,ph,d)
    for x in (17,23):flame(horse,x,48+b,12,ph+x,d)
    rider=Rig(a,-4,39,-1.04*d)
    rider.poly([(-14,64+b),(-18,39+b),(6,38+b),(5,65+b)],VIOLET[1],OUTLINE)
    rider.ball(-5,62+b,10,13,SLATE)
    # Open neck: the lantern is held beside the rider, never attached as a head.
    rider.ellipse(-5,76+b,6,2,OUTLINE);rider.line([(-10,77+b),(0,77+b)],GOLD[2],2)
    rider.limb([(-12,64+b),(-19-8*w,56+12*w+b),(-17-10*w+25*s,68+10*w-18*s+b)],SLATE,3)
    hand=(-17-10*w+25*s,68+10*w-18*s+b)
    angle=.1-1.85*w+1.2*s
    reach=27+9*max(w,s)
    tip=(hand[0]+math.sin(angle)*reach,hand[1]+math.cos(angle)*reach)
    rider.line([(hand[0]-math.sin(angle)*12,hand[1]-math.cos(angle)*12),tip],GOLD[2],2)
    sc=Socket(a,*rider.t(*tip),rider.phi-angle)
    plate(sc,[(0,0),(15,-1),(23,-8),(25,-18),(18,-10),(7,-6)],PEARL)
    rider.limb([(3,66+b),(15,61+b),(17,64+b)],SLATE,3)
    pumpkin=Rig(a,0,0,0) if d>.55 else rider
    px,py=(30+6*d,10+(1-d)*30) if d>.55 else (21,64+b)
    pumpkin.ball(px,py,9,8,AMBER)
    for dx in (-4,4):pumpkin.poly([(px+dx-2,py+3),(px+dx+2,py+4),(px+dx+1,py)],OUTLINE)
    pumpkin.line([(px-5,py-3),(px,py-5),(px+5,py-2)],OUTLINE,2)
    pumpkin.line([(px,py+7),(px+2,py+11)],LEAF[1],2)
    return a


def grinch(setup,clip,n):
    a,r,w,s,d,ph,b=setup('grinch',clip,n,(0,13),-1.38)
    feet(r,d,ph,clip=='walk',LEAF,3,22)
    r.ball(0,33+b,13,21,CRIMSON);r.ball(0,48+b,10,11,CRIMSON)
    r.ball(0,16+b,13,3,PEARL);r.ball(0,51+b,11,3,PEARL)
    # A sack tied to the swinging wrist keeps its full volume when it lands.
    hand=(-15-25*w+62*s,36+34*w+5*s+b)
    r.limb([(-8,49+b),(-18-14*w+22*s,46+20*w+b),hand],CRIMSON,4)
    r.ball(*hand,4,4,LEAF)
    r.line([hand,(hand[0]-4,hand[1]-9)],GOLD[2],2)
    r.ball(hand[0]-7,hand[1]-18,10,13,SACK)
    r.poly([(hand[0]-12,hand[1]-8),(hand[0]-9,hand[1]-3),(hand[0]-3,hand[1]-5),(hand[0]-1,hand[1]-10)],SACK[2],SACK[0])
    for j in range(3):r.line([(hand[0]-10+j*3,hand[1]-10),(hand[0]-13+j*5,hand[1]-20)],SACK[0],1)
    r.line([(hand[0]-14,hand[1]-9),(hand[0]-1,hand[1]-9)],GOLD[2],2)
    # A stolen parcel is tucked into the sack, with attached ribbon.
    plate(r,[(hand[0]-13,hand[1]-12),(hand[0]-5,hand[1]-11),(hand[0]-4,hand[1]-19),(hand[0]-12,hand[1]-20)],CRIMSON)
    r.line([(hand[0]-8,hand[1]-11),(hand[0]-8,hand[1]-20)],GOLD[3],1)
    r.limb([(9,48+b),(16,38+b),(18,31+b)],CRIMSON,3)
    for j in range(3):r.limb([(18+j,31+b),(20+j*2,25-j+b)],LEAF,1)
    r.ball(0,67+b,14,13,LEAF);r.ball(4,61+b,13,7,LEAF)
    for side in (-1,1):
        ex=side*6
        r.poly([(ex-side*5,70+b),(ex+side*4,72+b),(ex+side*4,66+b),(ex-side*4,66+b)],GOLD[3],OUTLINE)
        if d<.5:r.line([(ex+1,70+b),(ex+1,66+b)],OUTLINE,2)
        r.line([(side*2,72+b),(side*13,76+b)],LEAF[0],3)
        r.poly([(side*11,65+b),(side*21,66+b),(side*13,59+b)],LEAF[2],OUTLINE)
    r.ball(4,65+b,4,3,LEAF)
    r.line([(-8,60+b),(-3,56+b),(7,57+b),(13,61+b)],OUTLINE,2)
    r.line([(-1,57+b),(4,57+b)],BONE[4],1)
    r.ball(0,79+b,14,3,PEARL)
    plate(r,[(-13,80+b),(4,100+b),(16,93+b),(12,82+b),(7,89+b),(1,81+b)],CRIMSON)
    r.ball(14+3*d,82+b-8*d,4,4,PEARL)
    return a


def bloomwarden(setup,clip,n):
    a,r,w,s,d,ph,b=setup('bloomwarden',clip,n,(0,12),-1.27)
    feet(r,d,ph,clip=='walk',BROWN,4,25)
    r.ball(0,37+b,15,21,LEAF)
    for side in (-1,1):
        # Broad decorated egg pauldrons, unlike Birchcrown's tall trunk.
        r.ball(side*14,51+b,8,11,PEARL)
        r.line([(side*14-5,52+b),(side*14,48+b),(side*14+5,52+b)],PINK[3],2)
        if d>.2:r.line([(side*14-1,59+b),(side*14+2,53+b),(side*14-2,48+b)],OUTLINE,1)
    for dx in (-7,0,7):
        r.ball(dx,32+b,4,6,PEARL);r.line([(dx-3,32+b),(dx+3,32+b)],PINK[2],1)
    hand=(20-10*w+19*s,36+22*w-16*s+b)
    r.limb([(14,49+b),(24-9*w,47+17*w+b),hand],BROWN,3)
    r.limb([(-14,49+b),(-22,39+b),(-20,31+b)],BROWN,4)
    r.ball(-20,31+b,5,6,LEAF)
    # Staff is a single rigid transform about the attached wrist.
    tool=Socket(a,*r.t(*hand),r.phi-.25+1.05*w-.9*s)
    tool.line([(0,-24),(0,34)],BROWN[2],3)
    for j in range(6):
        an=j*math.tau/6
        tool.ball(math.cos(an)*5,34+math.sin(an)*5,3,5,PINK,an)
    tool.ball(0,34,4,4,GOLD)
    r.ball(0,66+b,13,12,LEAF)
    for side in (-1,1):
        ex=side*5
        r.poly([(ex-side*4,69+b),(ex+side*4,72+b),(ex+side*2,63+b)],GOLD[3],OUTLINE)
        if d<.55:r.line([(ex,69+b),(ex+1,65+b)],OUTLINE,1)
    r.line([(-5,59+b),(0,57+b),(6,60+b)],LEAF[0],2)
    for j in range(7):
        an=.1+j*math.pi/6
        x,y=math.cos(an)*12,71+b+math.sin(an)*9
        r.ball(x,y,4,6,PINK,an)
    if d>.2:
        ground=Rig(a,0,0,0)
        for j in range(4):
            x=-25+j*17;y=3+(1-d)*23
            plate(ground,[(x-3,y),(x+1,y+4),(x+5,y)],PEARL)
            leaf(ground,x+4,5+(1-d)*36,j,PINK,4)
    return a


def birchcrown(setup,clip,n):
    a,r,w,s,d,ph,b=setup('birchcrown',clip,n,(0,11),-1.4)
    feet(r,d,ph,clip=='walk',BIRCH,4,25)
    # Tall pale tree trunk, sloped shoulders and long antler branches.
    r.ball(0,39+b,10,26,BIRCH)
    for j in range(6):r.line([(-7+3*(j%2),22+j*7+b),(3+3*(j%3),23+j*7+b)],OUTLINE,1)
    hands=[]
    for side in (-1,1):
        hand=(side*15-12*w+22*s,39+17*w-7*s+b)
        r.limb([(side*8,56+b),(side*19-5*w+12*s,49+12*w+b),hand],BIRCH,3)
        r.ball(*hand,4,5,LEAF);hands.append(hand)
        for j in range(3):leaf(r,side*(12+j*4),59+j*2+b,side*(.3+j*.6),size=5)
    # A two-handed branch staff: both grips lie on its rigid line.
    x0,y0=hands[0];x1,y1=hands[1];dx,dy=x1-x0,y1-y0
    r.line([(x0-dx*.65,y0-dy*.65),(x1+dx*.7,y1+dy*.7)],BROWN[2],3)
    r.line([(x1+dx*.4,y1+dy*.4),(x1+dx*.65,y1+dy*.4+10)],BROWN[2],2)
    r.ball(0,72+b,11,14,BIRCH)
    # Knot eyes are narrow asymmetric holes, mouth a deep bark split.
    for ex,sz in [(-4,2),(5,3)]:
        r.poly([(ex-2,76+b),(ex+3,74+b),(ex+2,70+b),(ex-3,71+b)],OUTLINE)
        if d<.55:r.line([(ex-1,73+b),(ex+1,72+b)],GOLD[3],1)
    r.line([(-2,69+b),(1,65+b),(-1,61+b),(3,60+b)],OUTLINE,2)
    for side in (-1,1):
        r.limb([(side*6,80+b),(side*14,91+b),(side*18,101+b)],BIRCH,2)
        r.line([(side*12,89+b),(side*23,93+b)],BIRCH[2],2)
        for j in range(3):leaf(r,side*(13+j*4),89+b+j*3,side*.5,size=5)
    r.ball(0,88+b,6,6,GOLD);r.ellipse(0,88+b,3,3,AMBER[2])
    if d>.3:
        # A visible fracture in the thick trunk, separate leafy crown chips.
        r.line([(-9,45+b),(-2,49+b),(2,44+b),(9,48+b)],OUTLINE,2)
        ground=Rig(a,0,0,0)
        for j in range(4):leaf(ground,-18+j*18,3+(1-d)*(25+j*4),j*.8,size=5)
    return a


def briarheart(setup,clip,n):
    a,r,w,s,d,ph,b=setup('briarheart',clip,n,(0,13),-1.26)
    feet(r,d,ph,clip=='walk',BROWN,3,26)
    r.ball(0,38+b,11,21,BROWN)
    for side in (-1,1):
        for j in range(3):leaf(r,side*(8+j*3),47-j*4+b,side*.7,LEAF,7)
        hand=(side*18-11*w+27*s,29+22*w+2*s+b)
        r.limb([(side*9,52+b),(side*19-9*w+12*s,43+17*w+b),hand],BROWN,3)
        r.ball(*hand,4,5,LEAF)
        for j in range(3):
            r.poly([(hand[0]+j*3-4,hand[1]-2),(hand[0]+j*3+3+8*s,hand[1]-9-5*s),(hand[0]+j*3-2,hand[1]-5)],GOLD[2],OUTLINE)
        for j in range(3):r.poly([(side*(10+j*2),53-j*3+b),(side*(20+j*2),58-j*2+b),(side*(12+j*2),49-j*3+b)],GOLD[2],OUTLINE)
    # Asymmetric spiral rose made of separate shaded petals, thorn slit face.
    for j in range(8):
        an=j*math.tau/8
        x,y=math.cos(an)*(11+2*(j%2)),72+b+math.sin(an)*13
        if d>.2:
            x+=(j-3)*d*3;y-=d*(8+j*2)
        r.ball(x,y,7,10,PINK,an+.3)
    r.ball(0,72+b,7,9,CRIMSON)
    r.poly([(-6,76+b),(-1,73+b),(-5,69+b)],OUTLINE)
    r.poly([(2,73+b),(7,78+b),(6,69+b)],OUTLINE)
    if d<.55:
        r.line([(-5,73+b),(-3,72+b)],GOLD[4],1);r.line([(4,74+b),(5,72+b)],GOLD[4],1)
    r.line([(-3,67+b),(0,65+b),(4,68+b)],OUTLINE,1)
    # A heart-shaped seed with an actual notch, dark after death.
    heart=BROWN if d>.5 else CRIMSON
    r.ball(-3,39+b,4,4,heart);r.ball(3,39+b,4,4,heart)
    r.poly([(-7,39+b),(0,29+b),(7,39+b)],heart[2],heart[0])
    for side in (-1,1):r.poly([(side*8,82+b),(side*18,99+b),(side*12,79+b)],GOLD[2],OUTLINE)
    return a


def starrocketeer(setup,clip,n):
    a,r,w,s,d,ph,b=setup('starrocketeer',clip,n,(0,13),-1.37)
    # Rigid red rocket pack follows the falling torso; the fuses die out.
    for side in (-1,1):
        x=side*13
        r.ball(x,48+b,5,18,CRIMSON)
        plate(r,[(x-5,65+b),(x,76+b),(x+5,65+b)],GOLD)
        r.line([(x-4,39+b),(x+4,39+b)],GOLD[2],2)
        flame(r,x,72+b,6+5*s,ph+side,d)
    feet(r,d,ph,clip=='walk',SLATE,3,23)
    r.ball(0,36+b,12,22,SLATE);r.ball(0,52+b,11,5,CRIMSON)
    r.line([(-11,23+b),(11,23+b)],GOLD[2],2)
    for j in range(3):r.ball(2,32+j*6+b,1.4,1.4,GOLD)
    hand=(16-19*w+24*s,39+20*w-4*s+b)
    r.limb([(9,52+b),(18-11*w+10*s,49+13*w+b),hand],SLATE,4)
    r.ball(*hand,4,4,BONE)
    r.limb([(-9,52+b),(-17,40+b),(-15,34+b)],SLATE,3);r.ball(-15,34+b,3,4,BONE)
    tool=Socket(a,*r.t(*hand),r.phi+.1+1.5*w-1.45*s)
    tool.line([(0,-5),(0,25)],GOLD[2],2)
    pts=[]
    for j in range(10):
        an=math.pi/2+j*math.pi/5;rad=9 if j%2==0 else 4
        pts.append((math.cos(an)*rad,25+math.sin(an)*rad))
    tool.poly(pts,GOLD[3],OUTLINE)
    if s>.08:flame(tool,0,26,12*s,ph,d)
    r.ball(0,68+b,11,12,BONE)
    for side in (-1,1):
        ex=side*5
        r.ball(ex,71+b,5,5,GOLD);r.ellipse(ex,71+b,3,3,OUTLINE)
        if d<.55:r.line([(ex-1,72+b),(ex+1,73+b)],PEARL[4],1)
    r.line([(-10,76+b),(10,76+b)],SLATE[0],2)
    for side in (-1,1):
        r.limb([(side,64+b),(side*6,62+b),(side*10,66+b)],PEARL,2)
    r.ball(0,80+b,13,4,SLATE)
    plate(r,[(-11,81+b),(-3,107+b),(10,83+b)],SLATE)
    r.ball(-3,107+b,3,3,GOLD)
    return a
