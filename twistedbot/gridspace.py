
import time

import logbot
import blocks
import config
import fops
from axisbox import AABB
from tools import NodeState


log = logbot.getlogger("GRIDSPACE")

state_catch = {'fast': 0, 'slow': 0}

def compute_state(grid, x, y, z):       
    block_0 = grid.get_block(x, y, z)
    if block_0.number == blocks.Cactus.number:
        state_catch['fast'] += 1
        return NodeState.NO
    if isinstance(block_0, blocks.BlockLava):
        state_catch['fast'] += 1
        return NodeState.NO
    block_1 = grid.get_block(x, y + 1, z)
    if isinstance(block_1, blocks.BlockCube):
        return NodeState.NO
    if block_0.is_free and block_1.is_free:
        state_catch['fast'] += 1
        return NodeState.FREE
    if isinstance(block_0, blocks.BlockCube):
        if block_1.is_free:
            block_2 = grid.get_block(x, y + 2, z)
            if block_2.is_free:
                state_catch['fast'] += 1
                return NodeState.YES
            elif isinstance(block_2, blocks.BlockCube):
                state_catch['fast'] += 1
                return NodeState.NO
        elif isinstance(block_1, blocks.BlockCube):
            state_catch['fast'] += 1
            return NodeState.NO
    elif not block_0.is_collidable:
        if block_0.is_water or block_0.is_ladder_or_vine or block_0.is_free:
            if grid.get_block(x, y - 1, z).is_fence:
                if block_1.is_free and block_2.is_free:
                    state_catch['fast'] += 1
                    return NodeState.YES
            elif block_1.is_free:
                state_catch['fast'] += 1
                return NodeState.YES
    gs = GridState(grid, block=block_0)
    t_start = time.time()
    state = gs.get_state()
    state_catch['slow'] += 1
    return state


class GridBase(object):
    def __init__(self, grid, coords=None, block=None, bb=None):
        self.grid = grid
        if block is not None:
            self.block = block
            self.coords = self.block.coords
        elif coords is not None:
            self.coords = coords
            self.block = self.grid.get_block(self.coords.x, self.coords.y, self.coords.z)
        else:
            raise Exception("Empty grid object")

    def __unicode__(self):
        return unicode(self.block)

    def __str__(self):
        return unicode(self)

    def in_interval(self, a, i1, i2):
        return fops.lt(i1, a) and fops.lt(a, i2)

    def is_big_enough_bb(self, bb):
        return fops.gte(bb.width, config.PLAYER_BODY_DIAMETER) and fops.gte(bb.height, config.PLAYER_HEIGHT)


class Space(object):
    def __init__(self, orig_aabb, stand=True):
        self.orig = orig_aabb
        self.space = None
        self.block = None



class GridState(GridBase):
    def __init__(self, grid, coords=None, block=None, bb=None):
        super(GridSpace, self).__init__(grid, coords, block, bb)
        self._state = None

    def get_state(self):
        if self._state is None:
            self._state = self.compute_state()
            assert self._state is not None, '_state is None'
        return self._state

    def aabb_on_and_expand(self, bb):
        return AABB(bb.min_x - config.PLAYER_BODY_STAND_REACH,
                    bb.max_y,
                    bb.min_z - config.PLAYER_BODY_STAND_REACH,
                    bb.max_x + config.PLAYER_BODY_STAND_REACH,
                    bb.max_y + config.PLAYER_HEIGHT,
                    bb.max_z + config.PLAYER_BODY_STAND_REACH)

    def space_expand(self, h_expand=0):
        return AABB(self.coords.x - h_expand,
                    self.coords.y,
                    self.coords.z - h_expand,
                    self.coords.x + 1 + h_expand,
                    self.coords.y + 1 + config.PLAYER_HEIGHT,
                    self.coords.z + 1 + h_expand)

    def compute_state(self):
        boxes = []
        possibly_free = False
        under = self.grid.get_block(self.coords.x, self.coords.y - 1, self.coords.z)
        if isinstance(self.block, blocks.BlockCube):
            boxes = [self.aabb_on_and_expand(AABB.from_block_cube(self.coords.x, self.coords.y, self.coords.z))]
        else:
            if self.block.is_collidable or under.is_fence:
                if under.is_fence:
                    boxes.extend(map(self.aabb_on_and_expand, under.grid_bounding_boxes))
                if self.block.is_collidable:
                    boxes.extend(map(self.aabb_on_and_expand, block.grid_bounding_boxes))
                if self.block.is_ladder and not under.is_fence:
                    boxes.append(self.space_expand(h_expand=config.PLAYER_BODY_EXTEND))
            else:
                possibly_free = True
                boxes.append(self.space_expand())
        if boxes:
            if len(boxes) == 1:
                bb = boxes[0].copy()
            else:
                bb = reduce(AABB.union, boxes)
            collisions = self.grid.collision_aabbs_in(bb)
            for col_bb in collisions:
                boxes = self.break_boxes(boxes, col_bb)
                if not boxes:
                    break
            if boxes:
                for col_bb in self.grid.avoid_aabbs_in(bb):  # lava, fire, web
                    boxes = self.break_boxes(boxes, col_bb, frame_box)
                boxes = [box for box in boxes if not self.aabb_eyelevel_inside_water(box)]
        if boxes:
            if possibly_free:
                return NodeState.FREE
            else:
                return NodeState.YES
        else:
            return NodeState.NO

    def aabb_eyelevel_inside_water(self, bb):
        self.grid.aabb_eyelevel_inside_water(bb, eye_height=bb.height - (config.PLAYER_HEIGHT - config.PLAYER_EYELEVEL))

    def sits_on_any(self, bb, collisions):
        for col in collisions:
            if not fops.eq(bb.min_y, col.max_y):
                continue
            if fops.lt(bb.max_x, col.min_x) or fops.gt(bb.min_x, col.max_x):
                continue
            if fops.lt(bb.max_z, col.min_z) or fops.gt(bb.min_z, col.max_z):
                continue
            return True
        return False

    def break_boxes(self, boxes, col):
        out = []
        for box in boxes:
            if not col.collides(box):
                out.append(box)
                continue
            if self.is_big_enough(col.min_x, box.min_x, config.PLAYER_BODY_DIAMETER) and self.in_interval(col.min_x, box.min_x, box.max_x):
                out.append(AABB(box.min_x, box.min_y, box.min_z, col.min_x, box.max_y, box.max_z))
            if self.is_big_enough(box.max_x, col.max_x, config.PLAYER_BODY_DIAMETER) and self.in_interval(col.max_x, box.min_x, box.max_x):
                out.append(AABB(col.max_x, box.min_y, box.min_z, box.max_x, box.max_y, box.max_z))
            if self.is_big_enough(col.min_y, box.min_y, config.PLAYER_HEIGHT) and self.in_interval(col.min_y, box.min_y, box.max_y):
                out.append(AABB(box.min_x, box.min_y, box.min_z, box.max_x, col.min_y, box.max_z))
            if self.is_big_enough(box.max_y, col.max_y, config.PLAYER_HEIGHT) and self.in_interval(col.max_y, box.min_y, box.max_y):
                out.append(AABB(box.min_x, col.max_y, box.min_z, box.max_x, box.max_y, box.max_z))
            if self.is_big_enough(col.min_z, box.min_z, config.PLAYER_BODY_DIAMETER) and self.in_interval(col.min_z, box.min_z, box.min_z):
                out.append(AABB(box.min_x, box.min_y, box.min_z, box.max_x, box.max_y, col.min_z))
            if self.is_big_enough(box.max_z, col.max_z, config.PLAYER_BODY_DIAMETER) and self.in_interval(col.max_z, box.min_z, box.min_z):
                out.append(AABB(box.min_x, box.min_y, col.max_z, box.max_x, box.max_y, box.max_z))
        return out


class GridSpace(GridBase):
    def __init__(self, grid, coords=None, block=None, bb=None):
        super(GridSpace, self).__init__(grid, coords, block, bb)
        self.spaces = None

    def space_expand(self, h_expand=config.PLAYER_BODY_EXTEND):
        return AABB(self.coords.x - h_expand,
                    self.coords.y,
                    self.coords.z - h_expand,
                    self.coords.x + 1 + h_expand,
                    self.coords.y + 1 + config.PLAYER_HEIGHT,
                    self.coords.z + 1 + h_expand)

    def aabb_on_and_expand(self, bb):
        return AABB(bb.min_x - config.PLAYER_BODY_STAND_REACH,
                    bb.max_y,
                    bb.min_z - config.PLAYER_BODY_STAND_REACH,
                    bb.max_x + config.PLAYER_BODY_STAND_REACH,
                    bb.max_y + config.JUMP_HEIGHT + config.PLAYER_HEIGHT,
                    bb.max_z + config.PLAYER_BODY_STAND_REACH)

    def compute_spaces(self):
        self.spaces = []
        if isinstance(self.block, blocks.BlockCube):
            self.spaces = [self.aabb_on_and_expand(AABB.from_block_cube(self.coords.x, self.coords.y, self.coords.z))]
        else:
            under = self.grid.get_block(self.coords.x, self.coords.y - 1, self.coords.z)
            if self.block.is_collidable or under.is_fence:
                if under.is_fence:
                    under.add_grid_bounding_boxes_to(self.spaces)
                self.block.add_grid_bounding_boxes_to(self.spaces)
                self.spaces = [self.aabb_on_and_expand(box) for box in self.spaces]
                if self.block.is_ladder:
                    self.spaces.append(self.space_expand())
            else:
                if self.block.is_water:
                    self.spaces.append(self.space_expand(h_expand=config.PLAYER_BODY_STAND_REACH))
                elif self.block.is_vine:
                    self.spaces.append(self.space_expand())
        if self.spaces:
            if len(self.spaces) == 1:
                bb = self.spaces[0].copy()
            else:
                bb = reduce(AABB.union, self.spaces)
            collisions = self.grid.collision_aabbs_in(bb)
            for col_bb in collisions:
                self.spaces = self.break_boxes(self.spaces, col_bb)
                if not self.spaces:
                    break
            else:
                for col_bb in self.grid.avoid_aabbs_in(bb):  # lava, fire, web
                    self.spaces = self.break_boxes(self.spaces, col_bb)

    def break_boxes(self, boxes, col):
        out = []
        for box in boxes:
            if not col.collides(box):
                out.append(box)
                continue
            if self.in_interval(col.min_x, box.min_x, box.max_x):
                bb = AABB(box.min_x, box.min_y, box.min_z, col.min_x, box.max_y, box.max_z)
                if self.is_big_enough_bb(bb):
                    out.append(bb)
            if self.in_interval(col.max_x, box.min_x, box.max_x):
                bb = AABB(col.max_x, box.min_y, box.min_z, box.max_x, box.max_y, box.max_z)
                if self.is_big_enough_bb(bb):
                    out.append(bb)
            if self.in_interval(col.min_y, box.min_y, box.max_y):
                bb = AABB(box.min_x, box.min_y, box.min_z, box.max_x, col.min_y, box.max_z)
                if self.is_big_enough_bb(bb):
                    out.append(bb)
            if self.in_interval(col.max_y, box.min_y, box.max_y):
                bb = AABB(box.min_x, col.max_y, box.min_z, box.max_x, box.max_y, box.max_z)
                if self.is_big_enough_bb(bb):
                    out.append(bb)
            if self.in_interval(col.min_z, box.min_z, box.min_z):
                bb = AABB(box.min_x, box.min_y, box.min_z, box.max_x, box.max_y, col.min_z)
                if self.is_big_enough_bb(bb):
                    out.append(bb)
            if self.in_interval(col.max_z, box.min_z, box.min_z):
                bb = AABB(box.min_x, box.min_y, col.max_z, box.max_x, box.max_y, box.max_z)
                if self.is_big_enough_bb(bb):
                    out.append(bb)
        return out
        
    
class SpaceGraph(object):
    def __init__(self):
        self.start_nodes = []
        self.snodes = []

    def add_space_node(self, space, start=False):
        n = SpaceNode(space)
        if start:
            self.start_nodes.append(n)
        for snode in self.snodes:
            if self.check_connection(snode, n):
                snode.add_connection(n)
                n.connected = True
        self.snodes.append(n)
        return n

    def check_connection(self, n_from, n_to):
        if n_from.aabb.collides(n_to.aabb):
            return True
        else:
            return False

    def check_start(self, gs, bb):
        check = False
        for space in gs.spaces:
            if space.collides(bb):
                self.add_space_node(space, start=True)
                check = True
            else:
                self.add_space_node(space)
        return check

    def can_go_to(self, gs):
        if not gs.spaces:
            return False
        can_go = False
        for space in gs.spaces:
            node = self.space_graph.add_space_node(space)
            if node.connected:
                can_go = True
        return can_go
    
