

import logbot
import blocks
import config
import fops
from axisbox import AABB
from tools import NodeState


log = logbot.getlogger("GRIDSPACE")

state_catch = {'fast': 0, 'slow': 0}

def compute_state(grid, x, y, z):       
    block_1 = grid.get_block(x, y, z)
    if isinstance(block_1, blocks.BlockCube):
        state_catch['fast'] += 1
        return NodeState.NO
    block_2 = grid.get_block(x, y + 1, z)
    if isinstance(block_2, blocks.BlockCube):
        state_catch['fast'] += 1
        return NodeState.NO
    block_0 = grid.get_block(x, y - 1, z)
    if isinstance(block_0, blocks.BlockCube):
        if block_1.is_free and block_2.is_free:
            state_catch['fast'] += 1
            return NodeState.YES
    if block_0.is_free and block_1.is_free and block_2.is_free:
        state_catch['fast'] += 1
        return NodeState.FREE
    if block_1.is_avoid or block_2.is_avoid:
        state_catch['fast'] += 1
        return NodeState.NO
    gs = GridState(grid, block_0=block_0, block_1=block_1, block_2=block_2)
    state = gs.get_state()
    state_catch['slow'] += 1
    return state


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
        self._state = None

    def get_state(self):
        if self._state is None:
            self._state = self.compute_state()
            assert self._state is not None, '_state is None'
        return self._state

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
        return AABB(bb.min_x - config.PLAYER_WIDTH,
                    bb.max_y,
                    bb.min_z - config.PLAYER_WIDTH,
                    bb.max_x + config.PLAYER_WIDTH,
                    bb.max_y + config.PLAYER_HEIGHT,
                    bb.max_z + config.PLAYER_WIDTH)

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
            bb = reduce(AABB.union, boxes)
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


class GridSpace(GridBase):

    def __init__(self, grid, coords=None):
        self.coords = coords
        self.spaces = None

    def compute_spaces(self):
        self.spaces = []
        if self.block.is_collidable:
            broken = self.break_spaces(map(self.space_on_and_expand, filter(self.maxy_in_block, self.block.grid_bounding_boxes)))
            self.spaces.extend(map(self.water_filter, broken))
        elif self.block.is_ladder_or_vine:
            self.spaces.append(self.space_laddervine_expand(self.coords))
        elif self.block.is_water:
            self.spaces.append(self.break_spaces(self.space_liquid_expand(self.coords)))
        if self.under.is_collidable:
            broken = self.break_spaces(map(self.space_on_and_expand, filter(self.maxy_in_block, self.under.grid_bounding_boxes)))
            self.spaces.extend(map(self.water_filter, broken))

    def break_spaces(self, spaces):
        if not boxes:
            return []
        bb = self.union_bb(spaces)
        for col_bb in self.grid.collision_aabbs_in(bb):
            spaces = self.break_spaces_with(spaces, col_bb)
            if not spaces:
                break
        else:
            for col_bb in self.grid.avoid_aabbs_in(bb):  # lava, fire, web
                spaces = self.break_spaces_with(spaces, col_bb)
        return spaces

    def union_bb(self, spaces):
        if len(spaces) == 1:
            bb = spaces[0].operational.copy()
        else:
            bb = reduce(AABB.union, [space.operational for space in spaces])
        return bb

    def break_spaces_with(self, spaces, col):
        out = []
        for space in spaces:
            out.extend([broken_space for broken_space in self.break_space_with(space, col) if broken_space.is_valid_space])
        return out

    def water_filter(self, spaces):
        return True

    def space_on_and_expand(self, bb):
        aabb = AABB(bb.min_x - config.PLAYER_WIDTH,
                    bb.max_y,
                    bb.min_z - config.PLAYER_WIDTH,
                    bb.max_x + config.PLAYER_WIDTH,
                    bb.max_y + config.PLAYER_HEIGHT + config.MAX_JUMP_HEIGHT,
                    bb.max_z + config.PLAYER_WIDTH)
        return Space(bb, aabb, on_solid=True)

    def space_laddervine_expand(self, coords):
        cube = AABB.from_block_cube(coords.x, coords.y, coords.z)
        if self.block.is_vine:
            space = Space(cube, super(GridSpace, self).space_laddervine_expand(coords), in_laddervine=True)
            base_box = super(GridSpace, self).space_laddervine_expand(coords)
            for col_bb in self.grid.collision_aabbs_in(base_box):
                if base_box.collides(col_bb):
                    broken = self.break_space_with(base_box, col_bb)
                    broken = map(self.climb_space, broken)
                boxes = self.break_boxes(boxes, col_bb)

            for col_bb in self.grid.avoid_aabbs_in(bb):  # lava, fire, web
                boxes = self.break_boxes(boxes, col_bb)
            #boxes = [box for box in boxes if not self.aabb_eyelevel_inside_water(box)]
        return boxes
            return Space(cube, )
        elif self.block.is_ladder:
            return Space(self.block.grid_bounding_box.cube_completent, super(GridSpace, self).space_laddervine_expand(coords))
        else:
            raise Exception('is not ladder or vine')

    def space_liquid_expand(self, coords):
        return Space(blocks.BlockFluid.fluid_aabb(coords.x, coords.y, coords.z), super(GridSpace, self).space_liquid_expand(coords), in_liquid=True)

    def break_space_with(self, space, col):
        if not col.collides(space.operational):
            return [space]
        out = []
        box = space.operational
        if self.is_big_enough(col.min_y, box.min_y, config.PLAYER_HEIGHT) and self.in_interval(col.min_y, box.min_y, box.max_y):
            out.append(AABB(box.min_x, box.min_y, box.min_z, box.max_x, col.min_y, box.max_z))
        if self.is_big_enough(box.max_y, col.max_y, config.PLAYER_HEIGHT) and self.in_interval(col.max_y, box.min_y, box.max_y):
            out.append(AABB(box.min_x, col.max_y, box.min_z, box.max_x, box.max_y, box.max_z))
        if self.is_big_enough(col.min_x, box.min_x, config.PLAYER_WIDTH) and self.in_interval(col.min_x, box.min_x, box.max_x):
            out.append(AABB(box.min_x, box.min_y, box.min_z, col.min_x, box.max_y, box.max_z))
        if self.is_big_enough(box.max_x, col.max_x, config.PLAYER_WIDTH) and self.in_interval(col.max_x, box.min_x, box.max_x):
            out.append(AABB(col.max_x, box.min_y, box.min_z, box.max_x, box.max_y, box.max_z))
        if self.is_big_enough(col.min_z, box.min_z, config.PLAYER_WIDTH) and self.in_interval(col.min_z, box.min_z, box.min_z):
            out.append(AABB(box.min_x, box.min_y, box.min_z, box.max_x, box.max_y, col.min_z))
        if self.is_big_enough(box.max_z, col.max_z, config.PLAYER_WIDTH) and self.in_interval(col.max_z, box.min_z, box.min_z):
            out.append(AABB(box.min_x, box.min_y, col.max_z, box.max_x, box.max_y, box.max_z))
        space_out = []
        for o in out:
            space_new = space.copy()
            space_new.operational = o
            space_out.append(space_new)
            if space.in_laddervine:
                space_lv = space.copy()
                space_lv.operational = o
                space_lv.crop_to_lean_on(col)
                if space_lv.is_big_enough:
                    space_out.append(space_lv)
        return space_out


  
class Space(object):
    def __init__(self, base, operational, on_solid=False, in_liquid=False, in_laddervine=False):
        self.base = base
        self.operational = operational
        self.collision = None
        self.on_solid = on_solid
        self.in_liquid = in_liquid
        self.in_laddervine = in_laddervine
        if on_solid:
            self.movement = Movement.JUMP
        elif in_liquid:
            self.movement = Movement.UPDOWN
        elif in_laddervine:
            self.movement = Movement.DOWN

    def copy(self):
        return Space(self.base, self.operational, on_solid=self.on_solid, in_liquid=self.in_liquid, in_laddervine=self.in_laddervine)

    @property
    def is_valid_space(def):
        if self.on_solid:
            return fops.eq(self.base.max_y, self.operational.min_y)
        return True

    @property
    def is_big_enough(self):
        return fops.gte(self.operational.max_x - self.operational.min_x, config.PLAYER_WIDTH) and\
                fops.gte(self.operational.max_z - self.operational.min_z, config.PLAYER_WIDTH) and\
                fops.gte(self.operational.max_y - self.operational.min_y, config.PLAYER_HEIGHT)

    def crop_to_lean_on(self, collision):
        if fops.gte(self.operational.min_y, self.collision.max_y) or fops.lte(self.operational.max_y, self.collision.min_y):
            return
        full_lean = None
        if fops.eq(self.operational.min_x, self.collision.max_x):
            full_lean = AABB(self.operational.min_x,
                             self.collision.min_y - config.PLAYER_HEIGHT,
                             self.collision.min_z - config.PLAYER_WIDTH,
                             self.operational.min_x + config.PLAYER_WIDTH,
                             self.collision.max_y - config.PLAYER_HEIGHT,
                             self.collision.max_z + config.PLAYER_WIDTH)
        elif fops.eq(self.operational.max_x, self.collision.min_x):
            full_lean = AABB(self.operational.max_x - config.PLAYER_WIDTH,
                             self.collision.min_y - config.PLAYER_HEIGHT,
                             self.collision.min_z - config.PLAYER_WIDTH,
                             self.operational.max_x,
                             self.collision.max_y - config.PLAYER_HEIGHT,
                             self.collision.max_z + config.PLAYER_WIDTH)
        elif fops.eq(self.operational.min_z, self.collision.max_z):
            full_lean = AABB(self.collision.min_x - config.PLAYER_WIDTH,
                             self.collision.min_y - config.PLAYER_HEIGHT,
                             self.operational.min_z,
                             self.collision.max_x + config.PLAYER_WIDTH,
                             self.collision.max_y - config.PLAYER_HEIGHT,
                             self.operational.min_z + config.PLAYER_WIDTH)
        elif fops.eq(self.operational.max_z, self.collision.min_z):
            full_lean = AABB(self.collision.min_x - config.PLAYER_WIDTH,
                             self.collision.min_y - config.PLAYER_HEIGHT,
                             self.operational.max_z - config.PLAYER_WIDTH,
                             self.collision.max_x + config.PLAYER_WIDTH,
                             self.collision.max_y - config.PLAYER_HEIGHT,
                             self.operational.max_z)
        if full_lean is not None:
            self.operational = self.operational.intersection(full_lean)
            self.movement = Movement.UPDOWN
            

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
    
