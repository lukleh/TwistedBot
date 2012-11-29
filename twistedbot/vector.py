
import math


class Vector(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def __eq__(self, o):
        return self.x == o.x and self.y == o.y and self.z == o.z

    def __add__(self, v):
        return Vector(self.x + v.x, self.y + v.y, self.z + v.z)

    def __sub__(self, v):
        return Vector(self.x - v.z, self.y - v.z, self.z - v.z)

    def __mul__(self, m):
        return Vector(self.x * m, self.y * m, self.z * m)

    def __str__(self):
        return "<%s %s %s>" % (self.x, self.y, self.z)

    def __repr__(self):
        return self.__str__()

    @property
    def size(self):
        return math.sqrt(pow(self.x, 2) + pow(self.y, 2) + pow(self.z, 2))

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
