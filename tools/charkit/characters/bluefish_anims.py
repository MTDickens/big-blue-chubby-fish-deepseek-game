"""Animations for 蓝色大肥鱼.

Rotations are about the armature's axes: X = her left, Y = back, Z = up (see core.action).
+X rotation swings a leg/arm backwards and bends the spine forward; +Z turns toward her left.
"""
import math

from .. import core as C

TAU = 2 * math.pi


def s(ph, k=1.0, off=0.0):
    return math.sin(TAU * (ph * k + off))


def tail_wave(ph, amp_z=8.0, amp_x=3.0, speed=1.0, lag=0.12):
    return {f'tail.{i}': {'rot': (amp_x * s(ph, speed, -lag * i), 0, amp_z * s(ph, speed, -lag * i))} for i in range(1, 6)}


def arm_pose(dirs, side, elbow, hand, chest_q=None):
    """Aim upper/lower arm of `side` ('L'/'R') so the elbow and hand reach the given points."""
    from mathutils import Vector
    sh = {'L': Vector((0.066, 0, 0.482)), 'R': Vector((-0.066, 0, 0.482))}[side]
    e, h = Vector(elbow), Vector(hand)
    q1 = C.aim(dirs[f'upperarm.{side}'], e - sh, chest_q)
    q2 = C.aim(dirs[f'lowerarm.{side}'], h - e, (chest_q @ q1) if chest_q else q1)
    return {f'upperarm.{side}': {'q': q1}, f'lowerarm.{side}': {'q': q2}}


def add(arm):
    dirs = C.bone_dirs(arm)

    def idle(f, ph):
        b = s(ph)
        return {
            'hips': {'loc': (0, 0, -0.002 * (1 - math.cos(TAU * ph)))},
            'spine': {'rot': (1.5 * b, 0, 0)},
            'chest': {'rot': (1.0 * s(ph, 1, 0.1), 0, 1.5 * s(ph, 1, 0.3))},
            'head': {'rot': (0, 3 * s(ph, 1, 0.2), 2.5 * s(ph, 1, 0.45))},
            'upperarm.L': {'rot': (0, 2 * s(ph, 1, 0.1), 2 + 2 * b)},
            'upperarm.R': {'rot': (0, -2 * s(ph, 1, 0.1), -2 - 2 * b)},
            'ahoge': {'rot': (6 * s(ph, 2, 0.1), 0, 5 * s(ph, 1, 0.3))},
            'fin.L': {'rot': (0, 5 * s(ph, 2), -3 * s(ph, 2, 0.2))},
            'fin.R': {'rot': (0, -5 * s(ph, 2), 3 * s(ph, 2, 0.2))},
            'hair.B.1': {'rot': (2 * s(ph, 1, 0.3), 0, 0)},
            'hair.L.1': {'rot': (0, -1.5 * s(ph, 1, 0.35), 0)},
            'hair.R.1': {'rot': (0, 1.5 * s(ph, 1, 0.35), 0)},
            **tail_wave(ph, 7, 3),
        }
    C.action(arm, 'idle', 90, idle)

    def walk(f, ph):
        a = s(ph)
        bob = 0.012 * (1 - math.cos(2 * TAU * ph)) / 2
        return {
            'root': {'loc': (0, 0, bob)},
            'hips': {'rot': (0, 3 * a, 6 * a)},
            'spine': {'rot': (4, 0, -4 * a)},
            'chest': {'rot': (0, -2 * a, -3 * a)},
            'head': {'rot': (-3, 0, 2 * a)},
            'upperleg.L': {'rot': (-24 * a, 0, 0)},
            'upperleg.R': {'rot': (24 * a, 0, 0)},
            'lowerleg.L': {'rot': (30 * max(0.0, s(ph, 1, 0.25)), 0, 0)},
            'lowerleg.R': {'rot': (30 * max(0.0, s(ph, 1, 0.75)), 0, 0)},
            'foot.L': {'rot': (-10 * s(ph, 1, 0.1), 0, 0)},
            'foot.R': {'rot': (10 * s(ph, 1, 0.1), 0, 0)},
            'upperarm.L': {'rot': (22 * a, 0, 6)},
            'upperarm.R': {'rot': (-22 * a, 0, -6)},
            'lowerarm.L': {'rot': (-12 - 8 * max(0.0, -a), 0, 0)},
            'lowerarm.R': {'rot': (-12 - 8 * max(0.0, a), 0, 0)},
            'ahoge': {'rot': (10 * s(ph, 2, -0.15), 0, 0)},
            'fin.L': {'rot': (0, 7 * s(ph, 2, -0.1), 0)},
            'fin.R': {'rot': (0, -7 * s(ph, 2, -0.1), 0)},
            'hair.B.1': {'rot': (4 * s(ph, 2, -0.2), 0, 0)},
            'hair.L.1': {'rot': (0, -3 * s(ph, 2, -0.2), 0)},
            'hair.R.1': {'rot': (0, 3 * s(ph, 2, -0.2), 0)},
            **tail_wave(ph, 12, 4, 1.0, 0.15),
        }
    C.action(arm, 'walk', 24, walk)

    def run(f, ph):
        a = s(ph)
        bob = 0.022 * abs(math.sin(TAU * ph))
        return {
            'root': {'loc': (0, 0, bob)},
            'hips': {'rot': (0, 4 * a, 8 * a)},
            'spine': {'rot': (12, 0, -6 * a)},
            'chest': {'rot': (4, 0, -4 * a)},
            'head': {'rot': (-10, 0, 3 * a)},
            'upperleg.L': {'rot': (-40 * a, 0, 0)},
            'upperleg.R': {'rot': (40 * a, 0, 0)},
            'lowerleg.L': {'rot': (55 * max(0.0, s(ph, 1, 0.2)), 0, 0)},
            'lowerleg.R': {'rot': (55 * max(0.0, s(ph, 1, 0.7)), 0, 0)},
            'upperarm.L': {'rot': (40 * a, 0, 14)},
            'upperarm.R': {'rot': (-40 * a, 0, -14)},
            'lowerarm.L': {'rot': (-45, 0, 0)},
            'lowerarm.R': {'rot': (-45, 0, 0)},
            'ahoge': {'rot': (18 + 10 * s(ph, 2), 0, 0)},
            'fin.L': {'rot': (0, 12 * s(ph, 2), 0)},
            'fin.R': {'rot': (0, -12 * s(ph, 2), 0)},
            'hair.B.1': {'rot': (14 + 5 * s(ph, 2), 0, 0)},
            'hair.B.2': {'rot': (8, 0, 0)},
            'hair.L.1': {'rot': (10, -4 * s(ph, 2), 0)},
            'hair.R.1': {'rot': (10, 4 * s(ph, 2), 0)},
            **tail_wave(ph, 16, 6, 1.0, 0.15),
        }
    C.action(arm, 'run', 16, run)

    from mathutils import Quaternion
    raise_pose = {}
    for side, sgn in (('L', 1), ('R', -1)):
        raise_pose.update(arm_pose(dirs, side, (sgn * 0.135, -0.07, 0.535), (sgn * 0.15, -0.085, 0.625)))

    def cheer(f, ph):
        # crouch, hop with both arms up, land
        hop = max(0.0, math.sin(math.pi * min(1.0, max(0.0, (ph - 0.15) / 0.5))))
        crouch = max(0.0, math.sin(math.pi * ph / 0.15)) if ph < 0.15 else (max(0.0, math.sin(math.pi * (ph - 0.65) / 0.25)) if 0.65 < ph < 0.9 else 0.0)
        up = 0.07 * hop - 0.015 * crouch
        arms = min(1.0, ph / 0.2) if ph < 0.85 else (1 - (ph - 0.85) / 0.15)
        arms = arms * arms * (3 - 2 * arms)
        return {
            'root': {'loc': (0, 0, up)},
            'spine': {'rot': (6 * crouch - 4 * hop, 0, 0)},
            'head': {'rot': (-8 * hop, 0, 6 * s(ph, 2))},
            'upperleg.L': {'rot': (-20 * crouch, 0, 0)},
            'upperleg.R': {'rot': (-20 * crouch, 0, 0)},
            'lowerleg.L': {'rot': (35 * crouch + 20 * hop, 0, 0)},
            'lowerleg.R': {'rot': (35 * crouch + 20 * hop, 0, 0)},
            **{b: {'q': Quaternion().slerp(v['q'], arms)} for b, v in raise_pose.items()},
            'ahoge': {'rot': (-20 * hop + 15 * crouch, 0, 0)},
            'fin.L': {'rot': (0, 18 * hop, 0)},
            'fin.R': {'rot': (0, -18 * hop, 0)},
            'hair.B.1': {'rot': (-6 * hop + 8 * crouch, 0, 0)},
            'hair.L.1': {'rot': (0, -8 * hop, 0)},
            'hair.R.1': {'rot': (0, 8 * hop, 0)},
            **tail_wave(ph, 20, 10, 2.0, 0.15),
        }
    C.action(arm, 'cheer', 36, cheer)

    def hold(elbow, hand, spine=(0, 0, 0)):
        pose = {}
        for side, sgn in (('L', 1), ('R', -1)):
            pose.update(arm_pose(dirs, side, (sgn * elbow[0], elbow[1], elbow[2]), (sgn * hand[0], hand[1], hand[2])))
        return pose

    sign_pose = hold((0.118, -0.075, 0.405), (0.104, -0.14, 0.378))

    def sign(f, ph):
        p = dict(sign_pose)
        p.update({
            'spine': {'rot': (-2, 0, 3 * s(ph))},
            'head': {'rot': (0, 6 * s(ph, 1, 0.2), 4 * s(ph))},
            'prop': {'loc': (0, -0.02, 0.0), 'rot': (0, 3 * s(ph), 0)},
            'ahoge': {'rot': (8 * s(ph, 2), 0, 0)},
            'fin.L': {'rot': (0, 6 * s(ph, 2), 0)},
            'fin.R': {'rot': (0, -6 * s(ph, 2), 0)},
            **tail_wave(ph, 10, 3),
        })
        return p
    C.action(arm, 'sign', 60, sign)

    carry_pose = hold((0.13, -0.055, 0.405), (0.092, -0.118, 0.372))

    def carry(f, ph):
        p = dict(carry_pose)
        p.update({
            'spine': {'rot': (-4, 0, 2 * s(ph))},
            'head': {'rot': (4, 0, 3 * s(ph, 1, 0.2))},
            'ahoge': {'rot': (6 * s(ph, 2), 0, 0)},
            **tail_wave(ph, 9, 3),
        })
        return p
    C.action(arm, 'carry', 60, carry)

    def swim(f, ph):
        a = s(ph)
        return {
            'root': {'loc': (0, 0.0, 0.34), 'rot': (80, 0, 0)},
            'head': {'rot': (-45, 0, 3 * a)},
            'neck': {'rot': (-15, 0, 0)},
            'upperleg.L': {'rot': (12 * a, 0, 0)},
            'upperleg.R': {'rot': (-12 * a, 0, 0)},
            'lowerleg.L': {'rot': (15 + 10 * a, 0, 0)},
            'lowerleg.R': {'rot': (15 - 10 * a, 0, 0)},
            'upperarm.L': {'rot': (-150 + 20 * a, -30, 0)},
            'upperarm.R': {'rot': (-150 - 20 * a, 30, 0)},
            'hair.B.1': {'rot': (40, 0, 0)},
            'hair.B.2': {'rot': (20, 0, 0)},
            'hair.L.1': {'rot': (35, 0, 0)},
            'hair.R.1': {'rot': (35, 0, 0)},
            'fin.L': {'rot': (0, 15 * s(ph, 2), 0)},
            'fin.R': {'rot': (0, -15 * s(ph, 2), 0)},
            **{f'tail.{i}': {'rot': (18 * s(ph, 1, -0.14 * i), 0, 4 * s(ph, 1, -0.14 * i))} for i in range(1, 6)},
        }
    C.action(arm, 'swim', 40, swim)

    def peek(f, ph):
        lean = 14 + 3 * s(ph)
        return {
            'hips': {'loc': (0, 0, -0.02)},
            'upperleg.L': {'rot': (-22, 0, 0)},
            'upperleg.R': {'rot': (-22, 0, 0)},
            'lowerleg.L': {'rot': (40, 0, 0)},
            'lowerleg.R': {'rot': (40, 0, 0)},
            'spine': {'rot': (8, lean, 0)},
            'head': {'rot': (0, lean * 0.6, -10 + 6 * s(ph, 0.5))},
            **arm_pose(dirs, 'R', (-0.1, -0.08, 0.44), (-0.06, -0.14, 0.5)),
            **arm_pose(dirs, 'L', (0.1, -0.08, 0.44), (0.06, -0.14, 0.5)),
            'ahoge': {'rot': (0, 0, 15 * s(ph, 1))},
            **tail_wave(ph, 14, 4, 0.5),
        }
    C.action(arm, 'peek', 60, peek)

    def blink(f, ph):
        k = 1 - math.sin(math.pi * ph) ** 0.6 * 0.92
        return {'eye.L': {'scale': (1, 1, k)}, 'eye.R': {'scale': (1, 1, k)}}
    C.action(arm, 'blink', 8, blink, loop=False)
    C.finish_actions(arm, 'idle')
