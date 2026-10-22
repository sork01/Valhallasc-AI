"""Original Bloodfang-inspired Chainforged Assassin panels, fitted to both rigs."""
from cel_common import V,unit

def draw(ink,kind,p,Q,xf,j):
    u,a=Q@V(0,0,1),Q@V(1,0,0)
    def plate(points,mat='forge',tone=2):ink.plate([xf(q) for q in points],mat,tone)
    if kind=='armor':
        import cel_common as cc
        cc.torso(ink,xf,'forge',8.9,5.9,37,70)
        # Red chevrons outline a fitted black breast and layered abdominal plates.
        for side in (-1,1):
            plate([(side*1,8.3,68),(side*8,6.8,72),(side*10,6.8,62),
                   (side*4,9,55),(0,9.1,59)],'brass',2)
            plate([(side*2,8.8,65),(side*7,7.8,68),(side*8,7.8,62),
                   (side*4,9.4,58),(side*1,9.5,60)],'forge',1)
            plate([(0,9,55),(side*6,8.8,59),(side*10,7,52),(side*6,9,47),(0,10,50)],'brass',1)
            plate([(side*1,10.3,53),(side*6,9.8,56),(side*8,8.5,52),
                   (side*5,10,50),(side*1,10.4,51)],'forge',2)
            for n in range(2):
                z=46-n*5
                plate([(side*.8,9,z+3),(side*7,7,z+4),(side*8,7,z),
                       (side*.8,9,z-1)],'forge',2-n)
            plate([(side*2,7,39),(side*9,5,42),(side*13,4,29),
                   (side*7,8,25),(side*4,8,32)],'brass',1)
            plate([(side*4,8.5,37),(side*8,6.5,39),(side*10,5.5,30),
                   (side*7,9,28)],'forge',1)
            plate([(side*1,-7,68),(side*8,-6,71),(side*9,-6,41),
                   (side*2,-7,38)],'forge',1)
            plate([(side*2,-7.4,66),(side*4,-7.4,66),(side*5,-7.4,44),
                   (side*3,-7.4,43)],'brass',1)
            ink.bone(j['L' if side<0 else 'R']['shoulder'],j['L' if side<0 else 'R']['elbow'],3.8,3,'clothforge',-1)
        plate([(-9,7.7,40),(9,7.7,40),(9,7.7,37),(-9,7.7,37)],'brass',1)
        plate([(-3,9,41),(3,9,41),(3,9,36),(-3,9,36)],'brass',2)
    elif kind=='shoulders':
        front=Q@V(0,1,0)
        for side,key in ((-1,'L'),(1,'R')):
            c=j[key]['shoulder'];out=a*side
            ink.plate([c-out*3+u*5,c+out*6+u*11,c+out*15+u*3,
                       c+out*17-u*7,c+out*4-u*8], 'forge',1)
            # Three swept crimson blades and a dark recessed shoulder shell.
            for n in range(2):
                base=c+out*(4+n*7)+u*5
                tip=c+out*(8+n*9)+u*(37-n*9)
                ink.plate([base-out*3-front*2,tip,base+out*6+u*6],'brass',2)
                ink.plate([base+out*2-front*3,tip,base+out*6+u*6],'brass',0)
            for n in range(3):
                base=c+out*(1+n*4)-front*(n-1)*3
                ink.plate([base-out*3-u*2,base+out*(2+n)+u*(23-n*5),
                           base+out*(9+n*3)+u*(17-n*6),base+out*(17+n*2)-u*(6+n*2),
                           base+out*6-u*5],'brass',2)
                ink.plate([base+out*2+u*(17-n*5),base+out*(8+n*3)+u*(14-n*6),
                           base+out*(16+n*2)-u*(6+n*2),base+out*5-u*2],'brass',0)
    elif kind=='gloves':
        for key in ('L','R'):
            c=j[key]['hand'];v=unit(j[key]['elbow']-c)
            ink.bone(c,c+v*15,4,5.2,'forge',-1.4)
            for t in (2,13):
                d=c+v*t
                ink.bone(c+v*(t-1.5),c+v*(t+1.5),5.7,5.9,'brass',-2.2,2)
            d=c+v*8+Q@V(0,4,0)
            ink.plate([d-a*4,d-a*4+v*3,d+v*5,d+a*4+v*3,d+a*4,d-v*2],'brass',1)
            ink.plate([c-a*4,c-a*3-v*6,c+a*3-v*6,c+a*4+v*2],'forge',1)
    elif kind=='pants':
        # This shared item's Assassin fitting uses the original common palette:
        # nearly-black iron/leather and the darkest crimson ember tones.
        front=Q@V(0,5,0)
        for key in ('L','R'):
            hip,knee,ankle=j[key]['hip'],j[key]['knee'],j[key]['ankle'];v=unit(ankle-knee)
            ink.bone(hip,knee,5.4,4.9,'leather',-1.2)
            ink.bone(knee,ankle,4.8,3.4,'forge',-1.3)
            for n in range(3):
                c=hip*(1-(n+1)/4)+knee*((n+1)/4)+front
                ink.plate([c-a*4,c+v*4,c+a*4,c+v*7,c-a*3+v*3],'forge',1)
            d=knee+front+v*2
            ink.plate([d-a*6-v*4,d-v*7,d+a*6-v*4,d+a*6+v*5,d+v*8,d-a*6+v*5],'hot',0)
            ink.plate([d-a*4-v*3,d-v*5,d+a*4-v*3,d+a*4+v*3,d+v*5,d-a*4+v*3],'forge',0)
            ink.bone(ankle+Q@V(0,-2,-1),ankle+Q@V(0,7,-2),4.8,3.8,'forge',-1.5)
            ink.bone(ankle+Q@V(0,4,1)-a*3,ankle+Q@V(0,4,1)+a*3,1.6,1.6,'hot',-2,0)
    else:raise ValueError(kind)
