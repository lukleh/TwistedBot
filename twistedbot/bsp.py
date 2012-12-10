

import math

import fops
from axisbox import AABB
from vector import Vector


class BSPNode(object):
    def __init__(self, in_front=None, in_back=None, splitter=None, leaf=None, node_id=None):
        self.in_front = in_front
        self.in_back = in_back
        self.splitter = splitter
        self.leaf = leaf
        self.node_id = node_id
        self.is_solid = splitter is None
        print self

    def __str__(self):
        return "Node %d is_solid:%s front:%s back:%s split:%s %s" % (self.node_id, "True " if self.is_solid else "False",
                                                                            'None' if self.in_front is None else 'Tree',
                                                                            'None' if self.in_back is None else 'Tree',
                                                                            self.splitter, 'non-convex' if not self.leaf else '\n\tconvex:%d\n\t' % len(self.leaf) + '\n\t'.join([str(l) for l in self.leaf]))

    def __repr__(self):
        return str(self)


class Face(object):
    def __init__(self, point_min, point_max, orient_outside, face_id):
        a = orient_outside if (point_min.x - point_max.x) == 0 else 0
        b = orient_outside if (point_min.y - point_max.y) == 0 else 0
        c = orient_outside if (point_min.z - point_max.z) == 0 else 0
        self.d = -(point_min.x * a + point_min.y * b + point_min.z * c)
        self.normal = Vector(a, b, c)
        self.points = [point_min, point_max]
        self.orient_outside = orient_outside
        self.face_id = face_id
        self.is_splitter = False
        self.a = a
        self.b = b
        self.c = c

    def __str__(self):
        return "Face id:%d, %d %d %d %d/%s" % (self.face_id, self.a, self.b, self.c, self.d, self.points)

    def __repr__(self):
        return str(self)


class BSPTree(object):
    def __init__(self, bbs=[]):
        self.root_node = None
        self.face_count = 0
        self.node_count = 0
        if bbs:
            self.insert_aabbs(bbs)
            print "node count", self.node_count
            print "face count", self.face_count

    def make_faces(self, bbs):
        for bb in bbs:
            for face in self.decompose_to_faces(bb, 1):
                yield face

    def insert_aabbs(self, bbs):
        self.root_node = self.build_bsp([face for face in self.make_faces(bbs)])

    def face_id(self):
        self.face_count += 1
        return self.face_count

    def node_id(self):
        self.node_count += 1
        return self.node_count

    def decompose_to_faces(self, bb, orient_outside):
        yield Face(Vector(bb.min_x, bb.min_y, bb.min_z), Vector(bb.min_x, bb.max_y, bb.max_z),  1, self.face_id())
        yield Face(Vector(bb.max_x, bb.min_y, bb.min_z), Vector(bb.max_x, bb.max_y, bb.max_z), -1, self.face_id())
        yield Face(Vector(bb.min_x, bb.min_y, bb.min_z), Vector(bb.max_x, bb.min_y, bb.max_z),  1, self.face_id())
        yield Face(Vector(bb.min_x, bb.max_y, bb.min_z), Vector(bb.max_x, bb.max_y, bb.max_z), -1, self.face_id())
        yield Face(Vector(bb.min_x, bb.min_y, bb.min_z), Vector(bb.max_x, bb.max_y, bb.min_z),  1, self.face_id())
        yield Face(Vector(bb.min_x, bb.min_y, bb.max_z), Vector(bb.max_x, bb.max_y, bb.max_z), -1, self.face_id())

    def build_bsp(self, faces):
        if faces:
            splitter = None
            for face in faces:
                if not face.is_splitter:
                    splitter = face
                    splitter.is_splitter = True
                    break
            if splitter is None:
                BSPNode(leaf=faces, node_id=self.node_id())
            else:
                in_front = []
                in_back = []
                for face in faces:
                    side = self.facing(splitter, face)
                    if side == 1:
                        in_front.append(face)
                    elif side == -1:
                        in_back.append(face)
                    elif side == 0:
                        if self.same_direction(splitter, face):
                            in_front.append(face)
                        else:
                            in_back.append(face)
                    elif side == 2:
                        self.split_face_to(splitter, face, in_front, in_back)
                return BSPNode(in_front=self.build_bsp(in_front), in_back=self.build_bsp(in_back), splitter=splitter, node_id=self.node_id())
        else:
            return None
        
    def same_direction(self, splitter, face):
        return splitter.a == face.a and splitter.b == face.b and splitter.c == face.c

    def split_face_to(self, splitter, face, in_front, in_back):
        on_plane1 = face.points[0] - splitter.normal * self.point_distance(splitter, face.points[0])
        on_plane2 = face.points[1] - splitter.normal * self.point_distance(splitter, face.points[1])
        face1 = Face(face.points[0], on_plane2, face.orient_outside, self.face_id())
        face2 = Face(on_plane1, face.points[1], face.orient_outside, self.face_id())
        print 'SPLITTING %s into %s and %s' % (face, face1, face2)
        side = self.facing(splitter, face1)
        if side == 1:
            in_front.append(face1)
        elif side == -1:
            in_back.append(face1)
        else:
            raise Exception('uh oh...')
        side = self.facing(splitter, face2)
        if side == 1:
            in_front.append(face2)
        elif side == -1:
            in_back.append(face2)
        else:
            raise Exception('uh oh...')

    def point_distance(self, splitter, point):
        return splitter.a * point.x + splitter.b * point.y + splitter.c * point.z + splitter.d

    def facing(self, splitter, face):
        n_positive = 0
        n_negative = 0
        for point in face.points:
            side = self.point_distance(splitter, point)
            if fops.gt(side, 0):
                n_positive += 1
            elif fops.lt(side, 0):
                n_negative += 1
        if n_positive > 0 and n_negative == 0:
            return 1
        elif n_positive == 0 and n_negative > 0:
            return -1
        elif  n_positive == 0 and n_negative == 0:
            return 0
        else:
            return 2


if __name__ == '__main__':
    bbs = []
    bbs.append(AABB.from_block_cube(0, 0, 0))
    bbs.append(AABB.from_block_cube(0, 2, 0))
    bbs.append(AABB.from_block_cube(0, 1, 0))
    bbs.append(AABB.from_block_cube(0, 1.5, 0))
    bsp = BSPTree(bbs)
    #print bb1, [o for o in BSPTree().make_faces([bb1])]
    #print bb2, [o for o in BSPTree().make_faces([bb2])]