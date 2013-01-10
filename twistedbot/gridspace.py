

import logbot
import utils
import fops


log = logbot.getlogger("GRIDSPACE")


class NodeState(object):
    def __init__(self, grid, x=None, y=None, z=None, vector=None):
        self.grid = grid
        self.x = x
        self.y = y
        self.z = z
        self.coords = utils.Vector(self.x, self.y, self.z)
        self.block_0 = grid.get_block(self.x, self.y - 1, self.z)
        self.block_1 = grid.get_block(self.x, self.y, self.z)
        self.block_2 = grid.get_block(self.x, self.y + 1, self.z)
        self.can_be = self.block_1.can_fall_through and self.block_2.can_fall_through
        self.can_stand = self.block_0.can_stand_on and self.can_be
        self.can_jump = self.can_stand and self.block_1.is_free and self.block_2.is_free
        self.can_fall = self.can_be and self.block_0.can_fall_through
        self.can_climb = self.can_be and self.block_1.is_climbable
        self.in_fire = self.block_1.is_burning or self.block_2.is_burning
        self.in_water = self.block_1.is_water or self.block_2.is_water
        self.can_hold = self.in_water or self.block_1.is_ladder or (self.block_1.is_vine and self.block_1.is_climbable)
        self.platform_y = self.y
        self.center_x = self.x + 0.5
        self.center_z = self.z + 0.5

    def __str__(self):
        if self.can_stand:
            return "ON %s" % self.block_0
        else:
            return "IN %s" % self.block_1

    def vertical_center_in(self, center):
        return self.x < center.x and center.x < (self.x + 1) and self.z < center.z and center.z < (self.z + 1)

    def base_in(self, bb):
        return self.vertical_center_in(utils.Vector2D(bb.min_x, bb.min_z)) and self.vertical_center_in(utils.Vector2D(bb.max_x, bb.max_z))

    def touch_platform(self, center):
        if self.can_stand:
            return fops.eq(center.y, self.y)
        elif self.can_hold:
            return self.y < center.y and center.y < (self.y + 1)


class GridSpace(object):

    def __init__(self, grid):
        self.grid = grid
        self.cache = {}

    def get_state_coords(self, coords):
        return self._get_state(coords.tuple)

    def get_state(self, x, y, z):
        return self._get_state((x, y, z))

    def _get_state(self, t_coords):
        try:
            return self.cache[t_coords]
        except KeyError:
            state = NodeState(self.grid, t_coords[0], t_coords[1], t_coords[2])
            self.cache[t_coords] = state
            return state

    def neighbours_of(self, coords, go_fire=False):
        x = coords.x
        y = coords.y
        z = coords.z
        base_state = self.get_state_coords(coords)
        if base_state.in_water:
            for k in [0, 1, -1]:
                for i, j in utils.adjacency:
                    to_state = self.get_state(x + i, y + k, z + j)
                    if to_state.in_water:
                        go = self.can_swim(base_state, to_state)
                        if go:
                            yield to_state
                    elif to_state.can_stand:
                        if i != 0 and j != 0:
                            continue
                        if k == 0:
                            yield to_state
                        else:
                            go = self.can_go(base_state, to_state)
                            if go:
                                yield to_state
                    elif to_state.can_hold:
                        if (i != 0 and j != 0) or k != 0:
                            continue
                        yield to_state
            to_state = self.get_state(x, y + 1, z)
            if to_state.in_water:
                yield to_state
            to_state = self.get_state(x, y - 1, z)
            if to_state.can_stand or to_state.in_water:
                yield to_state
        elif base_state.can_hold:
            for k in [0, 1, -1]:
                for i, j in utils.cross:
                    to_state = self.get_state(x + i, y + k, z + j)
                    if to_state.can_stand:
                        go = self.can_go(base_state, to_state)
                        if go:
                            yield to_state
                    elif to_state.can_hold:
                        if k == 0:
                            yield to_state
            to_state = self.get_state(x, y + 1, z)
            if to_state.can_hold:
                yield to_state
            to_state = self.get_state(x, y - 1, z)
            if to_state.can_stand or to_state.can_hold:
                yield to_state
        else:
            for i, j in utils.adjacency:
                to_state = self.get_state(x + i, y, z + j)
                if to_state.can_stand or to_state.can_hold:
                    go = self.can_go(base_state, to_state)
                    if go:
                        yield to_state
                elif to_state.can_fall:
                    for k in [-1, -2, -3]:
                        to_state = self.get_state(x + i, y + k, z + j)
                        if to_state.can_stand or to_state.can_hold:
                            go = self.can_go(base_state, to_state)
                            if go:
                                yield to_state
                            break
                        elif to_state.can_fall:
                            continue
                        else:
                            break
                else:
                    to_state = self.get_state(x + i, y + 1, z + j)
                    if to_state.can_stand or to_state.can_hold:
                        go = self.can_go(base_state, to_state)
                        if go:
                            yield to_state

    def can_swim(self, from_state, to_state):
        grid = from_state.grid
        for x in xrange(from_state.x, to_state.x + 1):
            for y in xrange(from_state.y, to_state.y + 1):
                for z in xrange(from_state.z, to_state.z + 1):
                    if from_state.x == x and from_state.y == y and from_state.z == z:
                        continue
                    if to_state.x == x and to_state.y == y and to_state.z == z:
                        continue
                    to_state = self.get_state(x, y, z)
                    if not to_state.can_be:
                        return False
        return True

    def can_go(self, from_state, to_state):
        vertical = from_state.y != to_state.y and from_state.x == to_state.x and from_state.z == to_state.z
        cross = from_state.x == to_state.x or from_state.z == to_state.z
        if vertical:
            if from_state.y > to_state.y:
                if from_state.can_climb:
                    return True
                else:
                    return False
            else:
                return True
        elif not cross:
            if from_state.y == to_state.y:
                return self.diagonal_free(from_state, to_state, from_state.y)
            elif from_state.y < to_state.y:
                down = self.get_state(to_state.x, from_state.y, to_state.z)
                if not down.can_be:
                    return False
                return self.diagonal_free(from_state, to_state, to_state.y)
            else:
                go = self.diagonal_free(from_state, to_state, from_state.y)
                if not go:
                    return False
                for i in xrange(from_state.y - to_state.y):
                    down = self.get_state(to_state.x, from_state.y - i, to_state.z)
                    if not down.can_be:
                        return False
                return True
        else:
            if from_state.y == to_state.y:
                return True
            elif from_state.y < to_state.y:
                up = self.get_state(from_state.x, from_state.y + 1, from_state.z)
                if not up.can_be:
                    return False
                return True
            else:
                for i in xrange(from_state.y - to_state.y):
                    down = self.get_state(to_state.x, from_state.y - i, to_state.z)
                    if not down.can_be:
                        return False
                return True


    def diagonal_free(self, from_state, to_state, y_level):
        grid = from_state.grid
        left = self.get_state(to_state.x, y_level, from_state.z)
        if not left.can_be:
            return False
        right = self.get_state(from_state.x, y_level, to_state.z)
        if not right.can_be:
            return False
        return True


    def can_stand(self, x, y, z):
        return self.get_state(x, y, z).can_stand


def can_stand_coords(grid, coords):
    gs = GridSpace(grid)
    return gs.can_stand(coords.x, coords.y, coords.z)
