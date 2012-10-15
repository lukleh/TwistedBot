
import math


class Vector(object):
    def __init__(self, x, y, z):
        self.xyz = (x, y, z)

    def __hash__(self):
        return hash(self.xyz)

    def __eq__(self, o):
        return self.__hash__() == o.__hash__()

    def __add__(self, v):
        return Vector(self.x + v[0] , self.y + v[1], self.z + v[2])

    def __sub__(self, v):
        return Vector(self.x - v[0] , self.y - v[1], self.z - v[2])

    def __getitem__(self, k):
        return self.xyz[k]

    def __str__(self):
        return "<%s %s %s>" % (self.x, self.y, self.z)

    def __repr__(self):
        return self.__str__()
        
        
    @property
    def x(self):
        return self.xyz[0]
        
    @property
    def y(self):
        return self.xyz[1]
        
    @property
    def z(self):
        return self.xyz[2]
        
    @property
    def size(self):
        math.sqrt(pow(self.x, 2) + pow(self.y, 2) + pow(self.z, 2))
        
        
    @property
    def size_pow(self):
        return pow(self.x, 2) + pow(self.y, 2) + pow(self.z, 2)


    def norm_xz_direction(self, vect):
        x = vect.x - self.x
        z = vect.z - self.z
        size = math.hypot(x, z)
        if size == 0:
            return (0.0, 0.0) 
        return (x/size, z/size)
        

    def distance_xz_from(self, v):
        return math.hypot(self.x - v.x, self.z - v.z)


    def copy(self):
        return Vector(self.x, self.y, self.z)

