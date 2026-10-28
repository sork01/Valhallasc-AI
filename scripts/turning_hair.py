"""Directional scalp geometry shared by the five class sprite makers.

Faces remain anime billboards. Hair is a rounded surface in head-local space:
its part, fringe and tufts rotate with yaw rather than following the camera.
Only scalp polygons are replaced; long hair, beards and equipment stay separate.
"""
import math

import numpy as np
from scipy import ndimage as ndi


class Scalp:
    def __init__(self, ink, head, style, female=False):
        self.ink, self.head, self.style, self.female = ink, head, style, female
        self.poly = ink.poly
        self.colours = set(ink.color['hair'])
        self.origin = head['H'](0, 0)
        self.right = head['H'](1, 0) - self.origin
        self.up = head['H'](0, 1) - self.origin
        ink.poly = self.filter

    def filter(self, points, colour, *args, **kwargs):
        if colour in self.colours:
            local = np.asarray(points) - self.origin
            x, y = local @ self.right, local @ self.up
            if y.max() >= 8 and y.min() > -18 and y.max() < 29 and np.abs(x).max() < 18:
                return
        return self.poly(points, colour, *args, **kwargs)

    def project(self, point):
        x, y, z = point
        front, side = self.head['front'], self.head['side']
        horizontal, near = front * x + side * y, -side * x + front * y
        xy = self.head['H'](horizontal, z - near * .32)
        # Match existing headgear's depth contract: a worn hat stays over hair.
        depth = self.head['hd'] - 3.7 - near * .22 - z * .025
        return xy, depth

    def face(self, points, tone, bias=0., outline=False):
        projected = [self.project(q) for q in points]
        xy = np.array([q[0] for q in projected])
        depths = np.array([q[1] for q in projected])
        plane = np.linalg.lstsq(np.c_[np.ones(len(xy)), xy], depths, rcond=None)[0]
        slope = plane[1:]; length = np.linalg.norm(slope)
        if length < 1e-6:
            self.poly(xy, self.ink.color['hair'][tone], depths.mean() - bias, outline)
            return
        axis = slope / length; along = xy @ axis; centre = xy.mean(0)
        a = centre + axis * (along.min() - centre @ axis)
        b = centre + axis * (along.max() - centre @ axis)
        self.poly(xy, self.ink.color['hair'][tone], -bias, outline,
                  gradient=(a, b, plane[0] + a @ slope, plane[0] + b @ slope))

    def finish(self):
        self.ink.poly = self.poly
        # Render the scalp separately so its outline follows the actual curved
        # silhouette, including gaps between tufts, rather than a convex hull.
        body_index, body_depth = self.ink.index, self.ink.z
        self.ink.index = np.zeros_like(body_index)
        self.ink.z = np.full_like(body_depth, np.inf)
        spiky = self.style == 'assassin' or (self.style == 'warrior' and not self.female)
        height = {'warrior': 18.5 if self.female else 19.5, 'assassin': 16,
                  'mage': 17.5, 'hunter': 17, 'priest': 15.5}[self.style]
        part = 0. if self.style == 'priest' else -.4
        offset = 0. if self.style == 'priest' else -1.8
        count = 16

        def vertex(ring, col):
            theta = col / count * math.tau
            front = math.cos(theta)
            fringe = max(0., front) * (1.8 + 1.4 * math.sin(theta * (5 if spiky else 3) + .7))
            edge = -1 + 9 * front - fringe
            t, radius = [(0, 10.7), (.48, 11.2), (.83, 7.6), (1., 4.4)][ring]
            z = edge * (1 - t) + (height - .7 * t) * t
            if spiky and ring == 2:
                z += max(0., math.sin(theta * 5 + .5)) * 4
            return np.array([radius * math.sin(theta) + offset * t,
                             radius * math.cos(theta) * .82 - t * .8, z])

        for ring in range(3):
            for col in range(count):
                theta = (col + .5) / count * math.tau
                # Lighting stays in world space; the narrow part and strand bands
                # belong to the head, so they visibly travel around the crown.
                light = math.sin(theta) * self.head['front'] + math.cos(theta) * self.head['side']
                tone = 2 if light < .25 else 1
                if ring > 0 and abs(math.atan2(math.sin(theta - part), math.cos(theta - part))) < .35:
                    tone = 3
                self.face([vertex(ring, col), vertex(ring, col + 1),
                           vertex(ring + 1, col + 1), vertex(ring + 1, col)], tone)
        peak = np.array([offset, -.8, height + (1.4 if spiky else -.8)])
        for col in range(count):
            self.face([vertex(3, col), vertex(3, col + 1), peak], 2 if col < count // 2 else 1)
        # Fine head-local strands and an off-centre part make the turning
        # readable even where the rounded silhouette is almost symmetric.
        for angle, tone, width in [(part, 1, .06), (part - .75, 3, .09),
                                   (part + .75, 2, .07), (part + 2.3, 3, .07), (part + 3.5, 2, .08)]:
            a, b = (angle - width) / math.tau * count, (angle + width) / math.tau * count
            for ring in (1, 2):
                self.face([vertex(ring, a), vertex(ring, b), vertex(ring + 1, b), vertex(ring + 1, a)], tone, .08)
        if spiky:
            for x, y, height_add in [(-5, 1, 3.5), (1.5, 2.5, 4.5), (5, -2, 2.5)]:
                tip = np.array([x - 1, y - 1.5, height + height_add])
                base = [np.array([x - 2, y - 2, height - 3]), np.array([x + 2, y - 2, height - 3]),
                        np.array([x + 1, y + 2, height - 3])]
                for i in range(3):
                    self.face([base[i], base[(i + 1) % 3], tip], 2 if i == 0 else 1)
        mask = self.ink.index > 0
        nearest = ndi.distance_transform_edt(~mask, return_distances=False, return_indices=True)
        outline = ndi.binary_dilation(mask) & ~mask
        self.ink.index[outline] = 1
        self.ink.z[outline] = self.ink.z[tuple(nearest[:, outline])]
        take = (self.ink.index > 0) & (self.ink.z <= body_depth + .001)
        body_index[take], body_depth[take] = self.ink.index[take], self.ink.z[take]
        self.ink.index, self.ink.z = body_index, body_depth


def replace(ink, head, style, female=False):
    return Scalp(ink, head, style, female)
