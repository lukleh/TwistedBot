
import math
from collections import namedtuple

from twisted.internet import defer, reactor

import logbot


cross = [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1) if ((i == 0) or (j == 0)) and (j != i)]
corners = [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1) if (i != 0) and (j != 0)]
adjacency = cross + corners
plane = [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1)]


def do_now(fn, *args, **kwargs):
    return do_later(0, fn, *args, **kwargs)


def do_later(delay, fn, *args, **kwargs):
    d = defer.Deferred()
    d.addCallback(lambda ignored: fn(*args, **kwargs))
    d.addErrback(logbot.exit_on_error)
    reactor.callLater(delay, d.callback, None)
    return d


def reactor_break():
    d = defer.Deferred()
    reactor.callLater(0, d.callback, None)
    return d


def meta2str(meta):
    bins = bin(meta)[2:]
    bins = "0" * (8 - len(bins)) + bins
    return bins


def grid_shift(v):
    return int(math.floor(v))


def yaw_pitch_between(p1, p2):
    p = p1 - p2
    return vector_to_yaw_pitch(p.x, p.y, p.z)


def vector_to_yaw_pitch(x, y, z):
    d = math.hypot(x, z)
    if d == 0:
        pitch = 0
    else:
        pitch = math.sin(y / d)
        pitch = math.degrees(pitch)
        if pitch < -90:
            pitch = -90
        elif pitch > 90:
            pitch = 90
    if z == 0.0:
        if x > 0:
            yaw = 270
        elif x < 0:
            yaw = 90
    else:
        yaw = math.atan2(-x, z)
        yaw = math.degrees(yaw)
        #yaw -= 90
        #if yaw < 0:
        #    yaw = 360 + yaw
    return yaw, -pitch


def yaw_pitch_to_vector(yaw, pitch):
    real_yaw = yaw * 2 * (math.pi / 256)
    real_pitch = pitch * 2 * (math.pi / 256)
    x = - math.cos(real_pitch) * math.sin(real_yaw)
    y = - math.sin(real_pitch)
    z = math.cos(real_pitch) * math.cos(real_yaw)
    return Vector(x, y, z)


def grid_sections_around(center, distance):
    min_x = center.x - distance
    max_x = center.x + distance + 1
    min_y = min(0, center.y - distance)
    max_y = min(16, center.y + distance) + 1
    min_z = center.z - distance
    max_z = center.z + distance + 1
    for x in xrange(min_x, max_x):
        for y in xrange(min_y, max_y):
            for z in xrange(min_z, max_z):
                yield Vector(x, y, z)


ListItem = namedtuple('ListItem', ["order", "obj"])


class OrderedLinkedList(object):
    def __init__(self, name=None):
        self.name = name
        self.olist = []

    def __len__(self):
        return len(self.olist)

    def __repr__(self):
        return "%s %s [%s]" % (self.name, len(self), ",".join([str((o.order, o.obj)) for o in self.olist]))

    def iter(self, forward_direction=True):
        if forward_direction:
            for i in self.olist:
                yield i.obj
        else:
            for i in reversed(self.olist):
                yield i.obj

    @property
    def is_empty(self):
        return len(self) == 0

    @property
    def first_sign(self):
        return self.olist[0].obj

    def get_by_order(self, o_val):
        for li in self.olist:
            if li.order == o_val:
                return li.obj
        return None

    def add(self, order, obj):
        new_item = ListItem(order, obj)
        if self.is_empty:
            self.olist.append(new_item)
            return
        for item in self.olist:
            if item.obj == obj:
                return
        for index, item in enumerate(self.olist):
            if item.order > order:
                self.olist.insert(index, new_item)
                break
        else:
            self.olist.append(new_item)

    def remove(self, obj):
        if self.is_empty:
            return
        if len(self) == 1:
            self.olist = []
            return
        for i, item in enumerate(self.olist):
            if item.obj == obj:
                self.olist.pop(i)
                break


class Vector(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    @classmethod
    def from_tuple(cls, tpl):
        return Vector(tpl[0], tpl[1], tpl[2])

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def __eq__(self, o):
        return self.x == o.x and self.y == o.y and self.z == o.z

    def __ne__(self, o):
        return not self.__eq__(o)

    def __add__(self, v):
        return Vector(self.x + v.x, self.y + v.y, self.z + v.z)

    def __sub__(self, v):
        return Vector(self.x - v.x, self.y - v.y, self.z - v.z)

    def __mul__(self, m):
        return Vector(self.x * m, self.y * m, self.z * m)

    def __div__(self, d):
        return Vector(self.x / d, self.y / d, self.z / d)

    def __repr__(self):
        return "<%s %s %s>" % (self.x, self.y, self.z)

    @property
    def tuple(self):
        return (self.x, self.y, self.z)

    @property
    def size(self):
        return math.sqrt(pow(self.x, 2) + pow(self.y, 2) + pow(self.z, 2))

    @property
    def manhatan_size(self):
        return abs(self.x) + abs(self.y) + abs(self.z)

    def normalize(self):
        d = self.size
        if d < 0.0001:
            self.x = 0
            self.y = 0
            self.z = 0
        else:
            self.x = self.x / d
            self.y = self.y / d
            self.z = self.z / d

    @property
    def size_pow(self):
        return pow(self.x, 2) + pow(self.y, 2) + pow(self.z, 2)

    @property
    def horizontal_size(self):
        return math.hypot(self.x, self.z)

    def offset(self, dx=0, dy=0, dz=0):
        return Vector(self.x + dx, self.y + dy, self.z + dz)

    def copy(self):
        return Vector(self.x, self.y, self.z)

    def turn_direction(self, turn):
        if turn:
            self.x *= -1
            self.y *= -1
            self.z *= -1
        return self

    def grid_shift(self):
        return Vector(grid_shift(self.x), grid_shift(self.y), grid_shift(self.z))

    def distance(self, v):
        return (self - v).size


class Vector2D(object):
    def __init__(self, x, z):
        self.x = x
        self.z = z

    def __repr__(self):
        return "<%s %s>" % (self.x, self.z)

    def __sub__(self, v):
        return Vector2D(self.x - v.x, self.z - v.z)

    @property
    def size(self):
        return math.hypot(self.x, self.z)

    def normalize(self):
        d = self.size
        if d < 0.0001:
            self.x = 0
            self.z = 0
        else:
            self.x = self.x / d
            self.z = self.z / d
