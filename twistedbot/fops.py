

"""
functions for numerical stability
details at
http://realtimecollisiondetection.net/blog/?p=89
"""

ABS_TOL = 0.000001
REL_TOL = 0.000001


def eq_abs(a, b):
    return abs(a - b) <= ABS_TOL * max(1.0, max(abs(a), abs(b)))


def eq(a, b):
    return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))


def lt(a, b):
    if eq(a, b):
        return False
    return a < b


def gt(a, b):
    if eq(a, b):
        return False
    return a > b


def gte(a, b):
    if eq(a, b):
        return True
    return a > b


def lte(a, b):
    if eq(a, b):
        return True
    return a < b


def eqzero(a):
    return eq(a, 0)
