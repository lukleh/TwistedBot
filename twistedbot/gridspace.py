

import fops
import logbot
import blocks
import config
from axisbox import AABB


log = logbot.getlogger("GRIDSPACE")


class GridSpace(object):

    def __init__(self, grid, coords=None, block=None, bb=None):
        self.grid = grid
        self.bb_stand = None
        if block is not None:
            self.block = block
            self.coords = self.block.coords
        elif coords is not None:
            self.coords = coords
            self.block = self.grid.get_block(coords[0], coords[1], coords[2])
        elif bb is not None:
            self.bb_stand = bb
            self.block = self.grid.standing_on_block(bb)
            if self.block is None:
                self.block = self.grid.get_block(*bb.grid_bottom_center)
            self.coords = self.block.coords
        else:
            raise Exception("Empty gridspace object")
        self.blocks3 = (self.block,
                        self.grid.get_block(self.coords[0], self.coords[
                                            1] + 1, self.coords[2]),
                        self.grid.get_block(self.coords[0], self.coords[1] + 2, self.coords[2]))
        self._can_stand_on_value = None
        self.stand_block = None
        self.platform = None
        self.intersection = None

    def __unicode__(self):
        return unicode(self.block)

    def __str__(self):
        return unicode(self)

    def __eq__(self, other):
        return self.coords == other.coords

    @property
    def b3(self):
        return "%s %s" % (self.block.coords, ", ".join([b.name for b in self.blocks3]))

    def blocks_to_avoid(self, blks):
        for b in blks:
            if isinstance(b, blocks.Cobweb) or isinstance(b, blocks.Fire) or isinstance(b, blocks.BlockLava):
                return True
        else:
            return False

    @property
    def can_stand_on(self):
        if self._can_stand_on_value is None:
            self._can_stand_on_value = self.compute()
        return self._can_stand_on_value

    def compute(self):
        can = self._can_stand_on()
        self.grid.can_stand_memory[[b.identifier for b in self.blocks3]] = can
        return can

    def can_be_in(self, bb):
        if self.grid.aabb_collides(bb):
            return False
        if self.blocks_to_avoid(self.grid.blocks_in_aabb(bb)):
            return False
        if self.grid.aabb_eyelevel_inside_water(bb):
            return False
        return True

    def _can_stand_on(self):
        """
        can stand on top of the center of the block
        """
        if isinstance(self.block, blocks.Cactus):
            return False
        under = self.grid.get_block(
            self.coords[0], self.coords[1] - 1, self.coords[2])
        if not self.block.collidable and not under.is_fence and not self.block.is_water and not self.block.is_ladder_vine:
            return False
        if self.block.is_ladder_vine or self.block.is_water:
            bb = AABB.from_block_coords(self.block.coords)
            if under.is_fence:
                self.bb_stand = bb.shift(min_y=under.max_y)
            else:
                if not under.collidable or (under.collidable and fops.lt(under.max_y, bb.min_y)):
                    bb1 = bb.offset(dy=0.5)
                    if self.can_be_in(bb1):
                        bb = bb1
                self.bb_stand = bb
            self.stand_block = self.block
            self.platform = self.bb_stand.set_to(max_y=self.bb_stand.min_y)
        else:
            if under.is_fence:
                fence_top = under.maxedge_platform(y=1)
                if self.block.collidable:
                    self.platform = self.block.maxedge_platform(y=1)
                    self.stand_block = self.block
                    if fence_top.min_y > self.platform.min_y:
                        self.platform = fence_top
                        self.stand_block = under
                else:
                    self.platform = fence_top
                    self.stand_block = under
            else:
                self.platform = self.block.maxedge_platform(y=1)
                self.stand_block = self.block
            bb = AABB.from_block_coords(self.block.coords)
            self.bb_stand = bb.offset(dy=self.platform.min_y - bb.min_y)
            if not self.bb_stand.collides_on_axes(self.platform, x=True, z=True):
                return False
        return self.can_be_in(self.bb_stand)

    def can_go(self, gs, update_to_bb_stand=False):
        self.can_stand_on
        if not self.can_stand_between(gs):
            return False
        if not self.can_go_between(gs, update_to_bb_stand=update_to_bb_stand):
            return False
        return True

    def can_stand_between(self, gs, debug=False):
        if self.block.is_ladder_vine or gs.block.is_ladder_vine:
            return True
        if self.block.is_water or gs.block.is_water:
            return True
        if fops.gt(abs(self.platform.min_y - gs.platform.min_y), config.MAX_STEP_HEIGHT):
            return True
        stand_platform = self.platform.expand(config.PLAYER_BODY_DIAMETER - 0.09, 0, config.PLAYER_BODY_DIAMETER - 0.09)
        self.intersection = gs.stand_block.intersection_on_axes(
            stand_platform, x=True, z=True, debug=debug)
        if self.intersection is None:
            return False
        if self.stand_block.x != gs.stand_block.x and self.stand_block.z != gs.stand_block.z:
            if fops.lt(gs.platform.get_side('min', x=True, z=True), 0.5):
                return False
            else:
                return True
        else:
            return True

    def can_go_between(self, gs, update_to_bb_stand=False, debug=False):
        edge_cost = 0
        bb_stand = self.bb_stand
        other_bb_stand = gs.bb_stand
        if bb_stand.horizontal_distance(other_bb_stand) > 2:
            # too far from the next step
            return False
        if fops.gt(bb_stand.min_y, other_bb_stand.min_y):
            elev = bb_stand.min_y - other_bb_stand.min_y
            elev_bb = other_bb_stand.extend_to(dy=elev)
            bb_from = bb_stand
            bb_to = other_bb_stand.offset(dy=elev)
        elif fops.lt(bb_stand.min_y, other_bb_stand.min_y):
            if fops.lte(bb_stand.grid_y + 2, other_bb_stand.min_y):
                if debug:
                    print 'over 2 high difference',
                return False
            elev = other_bb_stand.min_y - bb_stand.min_y
            in_water = self.grid.aabb_in_water(bb_stand)
            if in_water and \
                    other_bb_stand.grid_y > bb_stand.grid_y and \
                    fops.gt(other_bb_stand.min_y, other_bb_stand.grid_y) and \
                    not self.grid.aabb_in_water(bb_stand.shift(min_y=other_bb_stand.min_y)) and \
                    fops.gte(other_bb_stand.min_y - (bb_stand.grid_y + 1), config.MAX_WATER_JUMP_HEIGHT - 0.15):
                if debug:
                    print 'water cannot go',
                return False
            if self.grid.aabb_on_ladder(bb_stand) and \
                    other_bb_stand.grid_y > bb_stand.grid_y and \
                    fops.gt(other_bb_stand.min_y, other_bb_stand.grid_y) and \
                    not self.grid.aabb_on_ladder(bb_stand.shift(min_y=other_bb_stand.min_y)) and \
                    fops.gte(other_bb_stand.min_y - (bb_stand.grid_y + 1), config.MAX_VINE_JUMP_HEIGHT - 0.2):
                return False
            if fops.gt(elev, config.MAX_JUMP_HEIGHT) and not in_water:
                return False
            if fops.lte(elev, config.MAX_STEP_HEIGHT):
                elev = config.MAX_STEP_HEIGHT
                aabbs = self.grid.aabbs_in(bb_stand.extend_to(0, elev, 0))
                for bb in aabbs:
                    elev = bb_stand.calculate_axis_offset(bb, elev, 1)
                if fops.lt(bb_stand.min_y + elev, other_bb_stand.min_y):
                    return False
            elev_bb = bb_stand.extend_to(dy=elev)
            bb_from = bb_stand.offset(dy=elev)
            bb_to = other_bb_stand
        else:
            elev = 0
            elev_bb = None
            bb_from = bb_stand
            bb_to = other_bb_stand
        if elev_bb is not None:
            if self.grid.aabb_collides(elev_bb):
                return False
            if self.blocks_to_avoid(self.grid.blocks_in_aabb(elev_bb)):
                return False
        if self.grid.collision_between(bb_from, bb_to, debug=debug):
            return False
        if self.blocks_to_avoid(self.grid.passing_blocks_between(bb_from, bb_to)):
            return False
        if fops.lte(elev, config.MAX_STEP_HEIGHT) and fops.gte(elev, -config.MAX_STEP_HEIGHT):
            edge_cost += config.COST_DIRECT * \
                bb_from.horizontal_distance(bb_to)
        else:
            edge_cost += config.COST_FALL * \
                bb_from.horizontal_distance(bb_to)
            vd = bb_from.horizontal_distance(bb_to)
            if vd < 0:
                edge_cost += config.COST_FALL * vd
            else:
                edge_cost += config.COST_CLIMB * vd
        self.edge_cost = edge_cost
        if update_to_bb_stand:
            gs.bb_stand = other_bb_stand
        return True
