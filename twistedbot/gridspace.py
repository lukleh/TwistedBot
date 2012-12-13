

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
    WATER = 4


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
                if NodeState.FREE == compute_state(grid, x, y + 1, z):
                    yield x + i, y + 1, z + j
        elif state == NodeState.FREE:
            state = compute_state(grid, x + i, y - 1, z + j)
            if state == NodeState.YES:
                yield x + i, y - 1, z + j
        else:
            pass


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
    return NodeState.NO


def can_go(grid, from_coords, to_coords):
    return True


def can_stand(grid, x, y, z):
    return compute_state(grid, x, y, z) == NodeState.YES


class GridBase(object):

    def __unicode__(self):
        return unicode(self.block)

    def __str__(self):
        return unicode(self)

    def in_interval(self, a, i1, i2):
        return fops.lt(i1, a) and fops.lt(a, i2)

    def is_big_enough(self, upper, lower, limit):
        return fops.gte(upper - lower, limit)

    def maxy_in_block(self, bb):
        return fops.lt(bb.max_y, self.block.coords.y + 1) and fops.gte(bb.max_y, self.block.coords.y)

    def aabb_eyelevel_inside_water(self, bb):
        self.grid.aabb_eyelevel_inside_water(bb, eye_height=bb.height - (config.PLAYER_HEIGHT - config.PLAYER_EYELEVEL))

    def space_expand(self, coords):
        return AABB(coords.x,
                    coords.y,
                    coords.z,
                    coords.x + 1,
                    coords.y + 1 + config.PLAYER_HEIGHT,
                    coords.z + 1)

    def space_liquid_expand(self, coords):
        return AABB(coords.x - config.PLAYER_WIDTH,
                    coords.y - (config.PLAYER_HEIGHT - 0.4),
                    coords.z - config.PLAYER_WIDTH,
                    coords.x + 1 + config.PLAYER_WIDTH,
                    coords.y + 0.6 + config.PLAYER_HEIGHT,
                    coords.z + 1 + config.PLAYER_WIDTH)

    def space_laddervine_expand(self, coords):
        return AABB(coords.x - config.PLAYER_BODY_RADIUS,
                    coords.y,
                    coords.z - config.PLAYER_BODY_RADIUS,
                    coords.x + 1 + config.PLAYER_BODY_RADIUS,
                    coords.y + 1 + config.PLAYER_HEIGHT,
                    coords.z + 1 + config.PLAYER_BODY_RADIUS)


class GridState(GridBase):

    def __init__(self, grid, block_0=None, block_1=None, block_2=None):
        self.under = block_0
        self.block = block_1
        self.over = block_2
        self.state = self.compute_state()

    def compute_state(self):
        boxes = []
        if self.block.is_collidable:
            boxes.extend(map(self.aabb_on_and_expand, filter(self.maxy_in_block, self.block.grid_bounding_boxes)))
        elif self.block.is_ladder_or_vine:
            boxes.append(self.space_laddervine_expand(self.coords))
        elif self.block.is_water:
            boxes.append(self.space_liquid_expand(self.coords))
        if self.under.is_collidable:
            boxes.extend(map(self.aabb_on_and_expand, filter(self.maxy_in_block, self.under.grid_bounding_boxes)))
        boxes = self.break_space(boxes)
        if boxes:
            return NodeState.YES
        else:
            boxes = self.break_space([self.space_expand(self.coords)])
            if boxes:
                return NodeState.FREE
            else:
                return NodeState.NO

    def aabb_on_and_expand(self, bb):
        return AABB(bb.min_x - config.PLAYER_WIDTH - 0.001,
                    bb.max_y,
                    bb.min_z - config.PLAYER_WIDTH - 0.001,
                    bb.max_x + config.PLAYER_WIDTH - 0.001,
                    bb.max_y + config.PLAYER_HEIGHT,
                    bb.max_z + config.PLAYER_WIDTH - 0.001)

    def break_space(self, boxes):
        if not boxes:
            return []
        bb = self.union_bb(boxes)
        for col_bb in self.grid.collision_aabbs_in(bb):
            boxes = self.break_boxes(boxes, col_bb)
            if not boxes:
                break
        else:
            for col_bb in self.grid.avoid_aabbs_in(bb):  # lava, fire, web
                boxes = self.break_boxes(boxes, col_bb)
            #boxes = [box for box in boxes if not self.aabb_eyelevel_inside_water(box)]
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
        if self.is_big_enough(col.min_x, box.min_x, config.PLAYER_WIDTH) and self.in_interval(col.min_x, box.min_x, box.max_x):
            out.append(AABB(box.min_x, box.min_y, box.min_z, col.min_x, box.max_y, box.max_z))
        if self.is_big_enough(box.max_x, col.max_x, config.PLAYER_WIDTH) and self.in_interval(col.max_x, box.min_x, box.max_x):
            out.append(AABB(col.max_x, box.min_y, box.min_z, box.max_x, box.max_y, box.max_z))
        if self.is_big_enough(col.min_y, box.min_y, config.PLAYER_HEIGHT) and self.in_interval(col.min_y, box.min_y, box.max_y):
            out.append(AABB(box.min_x, box.min_y, box.min_z, box.max_x, col.min_y, box.max_z))
        if self.is_big_enough(box.max_y, col.max_y, config.PLAYER_HEIGHT) and self.in_interval(col.max_y, box.min_y, box.max_y):
            out.append(AABB(box.min_x, col.max_y, box.min_z, box.max_x, box.max_y, box.max_z))
        if self.is_big_enough(col.min_z, box.min_z, config.PLAYER_WIDTH) and self.in_interval(col.min_z, box.min_z, box.min_z):
            out.append(AABB(box.min_x, box.min_y, box.min_z, box.max_x, box.max_y, col.min_z))
        if self.is_big_enough(box.max_z, col.max_z, config.PLAYER_WIDTH) and self.in_interval(col.max_z, box.min_z, box.min_z):
            out.append(AABB(box.min_x, box.min_y, col.max_z, box.max_x, box.max_y, box.max_z))
        return out
