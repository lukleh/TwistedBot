

import logbot
import blocks
import config
import fops
import utils
from axisbox import AABB


log = logbot.getlogger("GRIDSPACE")


class NodeState(object):
    NO = 1
    FREE = 2
    YES = 3


def neighbours_of(grid, coords):
    x = coords.x
    y = coords.y
    z = coords.z
    for i, j in utils.adjacency:
        state = compute_state(grid, x + i, y, z + j)
        if state == NodeState.YES:
            yield x + i, y, z + j
        elif state == NodeState.NO:
            state = compute_state(grid, x + i, y + 1, z + j)
            if state == NodeState.YES:
                yield x + i, y + 1, z + j
        elif state == NodeState.FREE:
            for k in [-1, -2, -3]:
                state = compute_state(grid, x + i, y + k, z + j)
                if state == NodeState.YES:
                    yield x + i, y + k, z + j
                    break
                elif state == NodeState.NO:
                    break
    state = compute_state(grid, x, y + 1, z)
    if state == NodeState.YES:
        yield x, y + 1, z
    state = compute_state(grid, x, y - 1, z)
    if state == NodeState.YES:
        yield x, y - 1, z


def compute_state(grid, x, y, z):
    block_1 = grid.get_block(x, y, z)
    if isinstance(block_1, blocks.BlockCube):
        return NodeState.NO
    block_2 = grid.get_block(x, y + 1, z)
    if isinstance(block_2, blocks.BlockCube):
        return NodeState.NO
    block_0 = grid.get_block(x, y - 1, z)
    if isinstance(block_0, blocks.BlockCube):
        if block_1.is_free and block_2.is_free:
            return NodeState.YES
    if block_0.is_free and block_1.is_free and block_2.is_free:
        return NodeState.FREE
    return GridState(grid, block_0, block_1, block_2).state


def can_go(grid, from_coords, to_coords):
    #spaces = [s for s in spaces_in(grid, from_coords, to_coords)]
    
    return True


def can_stand(grid, x, y, z):
    return compute_state(grid, x, y, z) == NodeState.YES


class GridSpace(object):
    def __init__(self, block):
        self.block = block
        self.is_start = False


class GridState(object):

    def __init__(self, grid, block_0, block_1, block_2):
        self.grid = grid
        self.under = block_0
        self.block = block_1
        self.over = block_2
        self.state = self.compute_state()

    def __unicode__(self):
        return unicode(self.block)

    def __str__(self):
        return str(self)

    def __repr__(self):
        return str(self)

    def in_interval(self, a, i1, i2):
        return fops.lt(i1, a) and fops.lt(a, i2)

    def is_big_enough(self, upper, lower, limit):
        return fops.gte(upper - lower, limit)

    def maxy_in_block(self, bb):
        return fops.gte(bb.max_y, self.block.coords.y) and fops.lt(bb.max_y, self.over.coords.y)

    def aabb_eyelevel_inside_water(self, bb):
        self.grid.aabb_eyelevel_inside_water(bb, eye_height=bb.height - (config.PLAYER_HEIGHT - config.PLAYER_EYELEVEL))

    def space_expand(self, coords):
        return AABB(coords.x,
                    coords.y,
                    coords.z,
                    coords.x + 1,
                    coords.y + config.PLAYER_HEIGHT,
                    coords.z + 1)

    def compute_state(self):
        boxes = []
        if self.under.is_collidable:
            boxes.extend(map(self.aabb_on_and_expand, filter(self.maxy_in_block, self.under.grid_bounding_boxes)))
        if self.block.is_collidable:
            boxes.extend(map(self.aabb_on_and_expand, filter(self.maxy_in_block, self.block.grid_bounding_boxes)))
        if boxes:
            boxes = self.break_space(boxes)
        if boxes:
            return NodeState.YES
        else: 
            if self.break_space([self.space_expand(self.block.coords)]):
                return NodeState.FREE
            else:
                return NodeState.NO

    def aabb_on_and_expand(self, bb):
        return AABB(bb.min_x - config.PLAYER_DIAMETER,
                    bb.max_y,
                    bb.min_z - config.PLAYER_DIAMETER,
                    bb.max_x + config.PLAYER_DIAMETER,
                    bb.max_y + config.PLAYER_HEIGHT,
                    bb.max_z + config.PLAYER_DIAMETER)

    def break_space(self, boxes):
        if not boxes:
            return boxes
        u_bb = self.union_bb(boxes)
        for col_bb in self.grid.collision_aabbs_in(u_bb):
            boxes = self.break_boxes(boxes, col_bb)
            if not boxes:
                return boxes
        for col_bb in self.grid.avoid_aabbs_in(u_bb):  # lava, fire, web
            boxes = self.break_boxes(boxes, col_bb)
            if not boxes:
                return boxes
        return boxes

    def union_bb(self, boxes):
        if len(boxes) == 1:
            bb = boxes[0].copy()
        else:
            bb = reduce(lambda x, y: x.union(y), boxes)
        return bb

    def break_boxes(self, boxes, col):
        out = []
        for box in boxes:
            out.extend(self.break_box_with(box, col))
        return out

    def break_box_with(self, box, col):
        if not col.collides(box):
            return [box]
        out = []
        if self.in_interval(col.min_x, box.min_x, box.max_x):
            out.append(AABB(box.min_x, box.min_y, box.min_z, col.min_x, box.max_y, box.max_z))
        if self.in_interval(col.max_x, box.min_x, box.max_x):
            out.append(AABB(col.max_x, box.min_y, box.min_z, box.max_x, box.max_y, box.max_z))
        #if self.in_interval(col.min_y, box.min_y, box.max_y):
        #    out.append(AABB(box.min_x, box.min_y, box.min_z, box.max_x, col.min_y, box.max_z))
        #if self.in_interval(col.max_y, box.min_y, box.max_y):
        #    out.append(AABB(box.min_x, col.max_y, box.min_z, box.max_x, box.max_y, box.max_z))
        if self.in_interval(col.min_z, box.min_z, box.min_z):
            out.append(AABB(box.min_x, box.min_y, box.min_z, box.max_x, box.max_y, col.min_z))
        if self.in_interval(col.max_z, box.min_z, box.min_z):
            out.append(AABB(box.min_x, box.min_y, col.max_z, box.max_x, box.max_y, box.max_z))
        return out

