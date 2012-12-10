

import math

import config
import fops
import tools
from vector import Vector


class AABB(object):
    """ Axis aligned bounding box """
    def __init__(self, min_x, min_y, min_z, max_x, max_y, max_z):
        self.min_x = min_x
        self.min_y = min_y
        self.min_z = min_z
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z
        self.mins = [min_x, min_y, min_z]
        self.maxs = [max_x, max_y, max_z]

    def __add__(self, o):
        return self.offset(o[0], o[1], o[2])

    def __sub__(self, o):
        return self.offset(-o[0], -o[1], -o[2])

    def __str__(self):
        return "AABB [%s, %s, %s : %s, %s, %s]" % \
            (self.min_x, self.min_y, self.min_z,
             self.max_x, self.max_y, self.max_z)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, o):
        return self.min_x == o.min_x and \
            self.min_y == o.min_y and \
            self.min_z == o.min_z and \
            self.max_x == o.max_x and \
            self.max_y == o.max_y and \
            self.max_z == o.max_z

    def copy(self):
        return AABB(self.min_x,
                    self.min_y,
                    self.min_z,
                    self.max_x,
                    self.max_y,
                    self.max_z)

    @property
    def width(self):
        return self.max_x - self.min_x

    @property
    def height(self):
        return self.max_y - self.min_y

    @property
    def posx(self):
        return (self.min_x + self.max_x) / 2.0

    @property
    def posy(self):
        return self.min_y

    @property
    def posz(self):
        return (self.min_z + self.max_z) / 2.0

    @property
    def grid_x(self):
        return tools.grid_shift(self.posx)

    @property
    def grid_y(self):
        return tools.grid_shift(self.posy)

    @property
    def grid_z(self):
        return tools.grid_shift(self.posz)

    @classmethod
    def from_player_coords(cls, x, y, z):
        return cls(
            x - config.PLAYER_BODY_RADIUS,
            y,
            z - config.PLAYER_BODY_RADIUS,
            x + config.PLAYER_BODY_RADIUS,
            y + config.PLAYER_HEIGHT,
            z + config.PLAYER_BODY_RADIUS)

    @classmethod
    def from_block_coords(cls, x, y, z):
        return cls.from_player_coords(x + 0.5, y, z + 0.5)

    @classmethod
    def from_block_cube(cls, x, y, z):
        return cls(x, y, z, x + 1, y + 1, z + 1)

    @property
    def bottom_center(self):
        return (self.posx, self.posy, self.posz)

    @property
    def grid_bottom_center(self):
        return (self.grid_x, self.grid_y, self.grid_z)

    def collides(self, bb):
        for i in xrange(3):
            if fops.lte(self.maxs[i], bb.mins[i]) or \
                    fops.gte(self.mins[i], bb.maxs[i]):
                return False
        return True

    def collision_distance(self, collidee, axis=None, direction=None):
        for i in xrange(3):
            if i == axis:
                continue
            if fops.lte(self.maxs[i], collidee.mins[i]) or \
                    fops.gte(self.mins[i], collidee.maxs[i]):
                return None
        p = None
        if direction < 0:
            if fops.eq(self.mins[axis], collidee.maxs[axis]):
                p = 0
            elif fops.gt(self.mins[axis], collidee.maxs[axis]):
                p = self.mins[axis] - collidee.maxs[axis]
        else:
            if fops.eq(collidee.mins[axis], self.maxs[axis]):
                p = 0
            elif fops.gt(collidee.mins[axis], self.maxs[axis]):
                p = collidee.mins[axis] - self.maxs[axis]
        return p

    def offset(self, dx=0, dy=0, dz=0):
        return AABB(self.min_x + dx,
                    self.min_y + dy,
                    self.min_z + dz,
                    self.max_x + dx,
                    self.max_y + dy,
                    self.max_z + dz)

    def shift(self, min_x=None, min_y=None, min_z=None):
        return AABB(min_x if min_x is not None else self.min_x,
                    min_y if min_y is not None else self.min_y,
                    min_z if min_z is not None else self.min_z,
                    self.max_x - self.min_x + min_x if min_x is not None else self.max_x,
                    self.max_y - self.min_y + min_y if min_y is not None else self.max_y,
                    self.max_z - self.min_z + min_z if min_z is not None else self.max_z)

    def extend_to(self, dx=0, dy=0, dz=0):
        return AABB(self.min_x if dx == 0 or dx > 0 else self.min_x + dx,
                    self.min_y if dy == 0 or dy > 0 else self.min_y + dy,
                    self.min_z if dz == 0 or dz > 0 else self.min_z + dz,
                    self.max_x if dx == 0 or dx < 0 else self.max_x + dx,
                    self.max_y if dy == 0 or dy < 0 else self.max_y + dy,
                    self.max_z if dz == 0 or dz < 0 else self.max_z + dz)

    def expand(self, dx=0, dy=0, dz=0):
        return AABB(self.min_x - dx,
                    self.min_y - dy,
                    self.min_z - dz,
                    self.max_x + dx,
                    self.max_y + dy,
                    self.max_z + dz)

    def union(self, bb):
        return AABB(self.min_x if self.min_x < bb.min_x else bb.min_x,
                    self.min_y if self.min_y < bb.min_y else bb.min_y,
                    self.min_z if self.min_z < bb.min_z else bb.min_z,
                    self.max_x if self.max_x > bb.max_x else bb.max_x,
                    self.max_y if self.max_y > bb.max_y else bb.max_y,
                    self.max_z if self.max_z > bb.max_z else bb.max_z)

    def intersection(self, bb):
        return AABB(self.min_x if self.min_x > bb.min_x else bb.min_x,
                    self.min_y if self.min_y > bb.min_y else bb.min_y,
                    self.min_z if self.min_z > bb.min_z else bb.min_z,
                    self.max_x if self.max_x < bb.max_x else bb.max_x,
                    self.max_y if self.max_y < bb.max_y else bb.max_y,
                    self.max_z if self.max_z < bb.max_z else bb.max_z)

    @property
    def cube_completent(self):
        return AABB(self.grid_x if self.min_x > self.grid_x else self.max_x,
                    self.grid_y if self.min_y > self.grid_y else self.max_y,
                    self.grid_z if self.min_z > self.grid_z else self.max_z,
                    self.min_x if self.min_x > self.grid_x else self.grid_x + 1,
                    self.min_y if self.min_y > self.grid_y else self.grid_y + 1,
                    self.min_z if self.min_z > self.grid_z else self.grid_z + 1)

    @property
    def grid_box(self):
        return [int(math.floor(self.min_x)),
                int(math.floor(self.min_y)),
                int(math.floor(self.min_z)),
                int(math.floor(self.max_x)),
                int(math.floor(self.max_y)),
                int(math.floor(self.max_z))]

    @property
    def grid_area(self):
        gbb = self.grid_box
        for x in xrange(gbb[0], gbb[3] + 1):
            for y in xrange(gbb[1], gbb[4] + 1):
                for z in xrange(gbb[2], gbb[5] + 1):
                    yield x, y, z

    def vector_to(self, bb):
        return Vector(bb.posx - self.posx, bb.posy - self.posy, bb.posz - self.posz)

    def horizontal_direction_to(self, bb):
        v = self.vector_to(bb)
        size = v.horizontal_size
        if fops.eq(size, 0):
            return (0, 0)
        return (v.x / size, v.z / size)

    def sweep_collision(self, collidee, v, debug=False):
        """
        self moving by v, collidee stationery
        based on http://bit.ly/3grWzs
        """
        u_0 = [2, 2, 2]
        u_1 = [1, 1, 1]
        dists = [None, None, None]
        for i in xrange(3):
            if fops.lte(self.maxs[i], collidee.mins[i]) and fops.gt(v[i], 0):
                d = collidee.mins[i] - self.maxs[i]
                dists[i] = d
                u_0[i] = d / v[i]
            elif fops.lte(collidee.maxs[i], self.mins[i]) and fops.lt(v[i], 0):
                d = collidee.maxs[i] - self.mins[i]
                dists[i] = d
                u_0[i] = d / v[i]
            elif not(fops.lte(self.maxs[i], collidee.mins[i]) or
                     fops.gte(self.mins[i], collidee.maxs[i])):
                u_0[i] = 0
            if fops.gte(collidee.maxs[i], self.mins[i]) and fops.gt(v[i], 0):
                d = collidee.maxs[i] - self.mins[i]
                u_1[i] = d / v[i]
            elif fops.gte(self.maxs[i], collidee.mins[i]) and fops.lt(v[i], 0):
                d = collidee.mins[i] - self.maxs[i]
                u_1[i] = d / v[i]
        u0 = max(u_0)
        if u0 == 2 or fops.gte(u0, 1.0):
            col = False
        else:
            col = fops.lte(u0, min(u_1))
        return col, u0

    def calculate_axis_offset(self, collidee, d, axis):
        for i in xrange(3):
            if i == axis:
                continue
            if fops.lte(self.maxs[i], collidee.mins[i]) or \
                    fops.gte(self.mins[i], collidee.maxs[i]):
                return d
        if d < 0 and fops.lte(collidee.maxs[axis], self.mins[axis]):
            dout = collidee.maxs[axis] - self.mins[axis]
            if fops.gt(dout, d):
                d = dout
        elif d > 0 and fops.gte(collidee.mins[axis], self.maxs[axis]):
            dout = collidee.mins[axis] - self.maxs[axis]
            if fops.lt(dout, d):
                d = dout
        return d
