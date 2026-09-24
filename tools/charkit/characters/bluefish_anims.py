"""Animations for 蓝色大肥鱼. Rotations are about armature axes: X = her left, Y = back, Z = up."""
import math


from .. import core as C

TAU = 2 * math.pi


def s(ph, k=1.0, off=0.0):
    return math.sin(TAU * (ph * k + off))


def add(arm):
    def idle(f, ph):
        b = s(ph)
        return {
            'spine': {'rot': (1.5 * b, 0, 0)},
            'chest': {'rot': (1.0 * s(ph, 1, 0.1), 0, 1.5 * s(ph, 1, 0.3))},
            'head': {'rot': (0, 2.5 * s(ph, 1, 0.2), 2 * s(ph, 1, 0.45))},
            'upperarm.L': {'rot': (0, 2 * s(ph, 1, 0.1), 3 + 2 * b)},
            'upperarm.R': {'rot': (0, -2 * s(ph, 1, 0.1), -3 - 2 * b)},
            'ahoge': {'rot': (6 * s(ph, 2, 0.1), 0, 4 * s(ph, 1, 0.3))},
            'fin.L': {'rot': (0, 4 * s(ph, 2), -3 * s(ph, 2, 0.2))},
            'fin.R': {'rot': (0, -4 * s(ph, 2), 3 * s(ph, 2, 0.2))},
            'hair.B.1': {'rot': (2 * s(ph, 1, 0.3), 0, 0)},
            'hair.L.1': {'rot': (0, 0, 1.5 * s(ph, 1, 0.35))},
            'hair.R.1': {'rot': (0, 0, -1.5 * s(ph, 1, 0.35))},
            **{f'tail.{i}': {'rot': (0, 3 * s(ph, 1, -0.12 * i), 7 * s(ph, 1, -0.12 * i))} for i in range(1, 6)},
        }
    C.action(arm, 'idle', 90, idle)

    def blink(f, ph):
        k = 1 - math.sin(math.pi * ph) ** 0.6 * 0.92
        return {'eye.L': {'scale': (1, 1, k)}, 'eye.R': {'scale': (1, 1, k)}}
    C.action(arm, 'blink', 8, blink, loop=False)
    C.finish_actions(arm, 'idle')
