"""Staff construction for later Mage tiers with room for the attack rig."""
import gear_shapes as base
from cel_common import V, unit


def render_mage_head(theme, gender, clip, facing, k):
    _, ink, _, _, _, _, head = base.pose('mage', gender, clip, facing, k)
    # The tall crown touches the top edge in the south-facing death pose.
    short_head = {**head, 'H': lambda x, y: head['H'](x, y * .85)}
    base.headgear(ink, 'mage', base.DESIGNS[theme], short_head)
    return ink.resolve(clip in ('hurt', 'die') and k == 0)


def render_mage_staff(theme, gender, clip, facing, k):
    _, ink, p, R, _, joints, _ = base.pose('mage', gender, clip, facing, k)
    ix = base.DESIGNS[theme]['index']
    hand = joints['L']['hand']
    u, across = R @ unit(V(*p['staff'])), R @ V(1, 0, 0)
    if p['dropped']:
        hand, u = V(-21, 8, 3), unit(V(.4, 1, 0))
        across = unit(V(u[1], -u[0], 0))
    end = hand + u * 27
    ink.bone(hand - u * 24, end, 1.6, 1.3, 'leather', -.2)
    ink.bone(hand + u * 5, hand + u * 7, 2.5, 2.5, 'trim', -.6)
    size = 6.5 + ix * .35
    base.jewel(ink, end, across, u, size)
    for sx in (-1, 1):
        ink.plate([end - u * size, end + across * sx * (size + 3),
                   end + u * (size + 2), end + across * sx * 3], 'metal', 2)
    ink.plate([end + u * 4, end + across * 6, end - u * 2, end - across * 6],
              'gem' if ix % 2 else 'trim', 2, True)
    return ink.resolve(clip in ('hurt', 'die') and k == 0)
