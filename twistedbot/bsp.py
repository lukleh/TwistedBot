

import math

import fops
from axisbox import AABB
from vector import Vector


class BSPNode(object):
    def __init__(self, in_front=None, in_back=None, splitter=None, leaf=None, node_id=None, depth=None):
        self.in_front = in_front
        self.in_back = in_back
        self.splitter = splitter
        self.leaf = leaf
        self.node_id = node_id
        self.depth = depth
        self.is_leaf = leaf is not None
        self.is_empty = self.is_leaf and len(self.leaf) == 0

    def check_hull(self):
        pass

    def make_face_pairs(self):
        #fs = sorted(self.leaf, key=lamba f: (abs(f.mormal.a), abs(f.mormal.b), abs(f.mormal.c)))
        #return [(fs[i], fs[i + 1]) for i in xrange(len(fs) - 1)]
        pass

    def create_aabb(self):
        for face_pair in self.make_face_pairs():
            AABB.from_two_points(face_pair.point[0], face_pair.point[1])


    def format_leaf_faces(self):
        return '\n\tfaces:%d\n\t' % len(self.leaf) + '\n\t'.join([str(l) for l in self.leaf])

    def __str__(self):
        base = "Node %d depth:%d " % (self.node_id, self.depth)
        if not self.is_leaf:
            return base + "is splitter: %s front:%s back:%s" % (self.splitter, 'None' if self.in_front is None else self.in_front.node_id,
                                                                'None' if self.in_back is None else self.in_back.node_id)
        else:
            if len(self.leaf) == 1:
                return base + "single plane %s" % self.leaf[0]
            #else:
            #    is_hull, is_solid = self.check_hull()
            #    return base + "is_hull %s is_solid %s %s" % (is_hull, is_solid, self.format_leaf_faces())
            else:
                return base + self.format_leaf_faces()

    def __repr__(self):
        return str(self)


class Face(object):
    def __init__(self, point_min, point_max, orient_outside, face_id, bb_id=None):
        a = orient_outside if (point_min.x - point_max.x) == 0 else 0
        b = orient_outside if (point_min.y - point_max.y) == 0 else 0
        c = orient_outside if (point_min.z - point_max.z) == 0 else 0
        self.d = -(point_min.x * a + point_min.y * b + point_min.z * c)
        self.normal = Vector(a, b, c)
        self.points = [point_min, point_max]
        self.orient_outside = orient_outside
        self.face_id = face_id
        self.bb_id=bb_id
        self.is_splitter = False
        self.a = a
        self.b = b
        self.c = c

    def __str__(self):
        return "Face id:%d,\tbbid:%d,\t%d %d %d %f/%s" % (self.face_id, self.bb_id, self.a, self.b, self.c, self.d, self.points)

    def __repr__(self):
        return str(self)


class BSPTree(object):
    def __init__(self, bbs=[]):
        self.root_node = None
        self.face_count = 0
        self.node_count = 0
        self.aabb_count = 0
        self.max_depth = 0
        if bbs:
            self.insert_aabbs(bbs)
            print "node count", self.node_count
            print "face count", self.face_count
            print "depth", self.max_depth

    def make_faces(self, bbs):
        for bb in bbs:
            for face in self.decompose_to_faces(bb, 1):
                yield face

    def cover_faces(self, bbs):
        union_bb = reduce(lambda x, y: x.union(y), bbs)
        return [f for f in self.decompose_to_faces(union_bb.expand(1, 1, 1), -1)]

    def insert_aabbs(self, bbs):
        faces = self.cover_faces(bbs)
        faces.extend([face for face in self.make_faces(bbs)])
        self.root_node = self.build_bsp(faces)

    def face_id(self):
        self.face_count += 1
        return self.face_count

    def node_id(self):
        self.node_count += 1
        return self.node_count

    def aabb_id(self):
        self.aabb_count += 1
        return self.aabb_count

    def decompose_to_faces(self, bb, orient_outside):
        bb_id = self.aabb_id()
        print 'AABB', bb_id, bb
        yield Face(Vector(bb.min_x, bb.min_y, bb.min_z), Vector(bb.min_x, bb.max_y, bb.max_z),  1 * orient_outside, self.face_id(), bb_id=bb_id)
        yield Face(Vector(bb.max_x, bb.min_y, bb.min_z), Vector(bb.max_x, bb.max_y, bb.max_z), -1 * orient_outside, self.face_id(), bb_id=bb_id)
        yield Face(Vector(bb.min_x, bb.min_y, bb.min_z), Vector(bb.max_x, bb.min_y, bb.max_z),  1 * orient_outside, self.face_id(), bb_id=bb_id)
        yield Face(Vector(bb.min_x, bb.max_y, bb.min_z), Vector(bb.max_x, bb.max_y, bb.max_z), -1 * orient_outside, self.face_id(), bb_id=bb_id)
        yield Face(Vector(bb.min_x, bb.min_y, bb.min_z), Vector(bb.max_x, bb.max_y, bb.min_z),  1 * orient_outside, self.face_id(), bb_id=bb_id)
        yield Face(Vector(bb.min_x, bb.min_y, bb.max_z), Vector(bb.max_x, bb.max_y, bb.max_z), -1 * orient_outside, self.face_id(), bb_id=bb_id)

    def build_bsp(self, faces, depth=0):
        if depth > self.max_depth:
            self.max_depth = depth
        if faces:
            splitter = None
            for face in faces:
                if not face.is_splitter:
                    splitter = face
                    splitter.is_splitter = True
                    break
            if splitter is None:
                return BSPNode(leaf=faces, node_id=self.node_id(), depth=depth+1)
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
                        face.is_splitter = True
                        if self.same_direction(splitter, face):
                            in_front.append(face)
                        else:
                            in_back.append(face)
                    elif side == 2:
                        self.split_face_to(splitter, face, in_front, in_back)
                nid = self.node_id()
                return BSPNode(in_front=self.build_bsp(in_front, depth=depth+1), in_back=self.build_bsp(in_back, depth=depth+1), splitter=splitter, node_id=nid, depth=depth)
        else:
            return BSPNode(leaf=[], node_id=self.node_id(), depth=depth+1)
        
    def same_direction(self, splitter, face):
        return splitter.a == face.a and splitter.b == face.b and splitter.c == face.c

    def split_face_to(self, splitter, face, in_front, in_back):
        on_plane1 = face.points[0] - splitter.normal * self.point_distance(splitter, face.points[0])
        on_plane2 = face.points[1] - splitter.normal * self.point_distance(splitter, face.points[1])
        face1 = Face(face.points[0], on_plane2, face.orient_outside, self.face_id(), bb_id=face.bb_id)
        face1.is_splitter = face.is_splitter
        face2 = Face(on_plane1, face.points[1], face.orient_outside, self.face_id(), bb_id=face.bb_id)
        face2.is_splitter = face.is_splitter
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

    def travense_tree(self, start_node=None):
        if start_node is None:
            start_node = self.root_node
        yield start_node
        if start_node.in_front is not None:
            for n in self.travense_tree(start_node.in_front):
                yield n
        if start_node.in_back is not None:
            for n in self.travense_tree(start_node.in_back):
                yield n

    def build_spaces(self):
        splitters = []
        split_dept = 0
        for node in self.travense_tree():
            if node.is_leaf:
                print split_dept
                #splitters.pop()
                if node.is_empty:
                    print 'empty', node.node_id
            else:
                split_dept = node.depth
                splitters.append(node.splitter)

    def pprint(self):
        for node in self.travense_tree():
            if node.is_leaf:
                print node


if __name__ == '__main__':
    bbs = []
    bbs.append(AABB.from_block_cube(0, 0, 0))
    #bs.append(AABB.from_block_cube(0, 2, 0))
    bbs.append(AABB.from_block_cube(0, 1, 0).expand(0.2, 0.2, 0.2))
    #bbs.append(AABB.from_block_cube(0.3, 1.4, 0))
    bsp = BSPTree(bbs)
    bsp.pprint()
    #bsp.build_spaces()