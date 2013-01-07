

import logbot
import utils
import blocks


log = logbot.getlogger("GRIDSPACE")


class NodeState(object):
    def __init__(self, grid, x=None, y=None, z=None, vector=None):
        self.grid = grid
        if vector is not None:
            self.x = vector.x
            self.y = vector.y
            self.z = vector.z
        else:
            self.x = x
            self.y = y
            self.z = z
        self.coords = utils.Vector(x, y, z)
        self.block_0 = grid.get_block(x, y - 1, z)
        self.block_1 = grid.get_block(x, y, z)
        self.block_2 = grid.get_block(x, y + 1, z)
        self.can_be = self.block_1.can_fall_through and self.block_2.can_fall_through
        self.can_stand = self.block_0.can_stand_on and self.can_be
        self.can_jump = self.can_stand and self.block_1.is_free and self.block_2.is_free
        self.can_fall = self.can_be and self.block_0.can_fall_through
        self.can_climb = self.can_be and self.block_1.is_climbable
        self.in_fire = self.block_1.is_burning or self.block_2.is_burning
        self.in_water = self.block_1.is_water or self.block_2.is_water
        self.can_hold = self.in_water or self.block_1.is_ladder or (self.block_1.is_vine and self.block_1.is_climbable)


def neighbours_of(grid, base_state, go_fire=False):
    x = base_state.x
    y = base_state.y
    z = base_state.z
    if base_state.in_water:
        for k in [0, 1, -1]:
            for i, j in utils.adjacency:
                to_state = NodeState(grid, x + i, y + k, z + j)
                if to_state.in_water:
                    go = can_swim(grid, base_state, to_state)
                    if go:
                        yield to_state
                elif to_state.can_stand:
                    if i != 0 and j != 0:
                        continue
                    if k == 0:
                        yield to_state
                    else:
                        go = can_go(grid, base_state, to_state)
                        if go:
                            yield to_state
                elif to_state.can_hold:
                    if (i != 0 and j != 0) or k != 0:
                        continue
                    yield to_state
        to_state = NodeState(grid, x, y + 1, z)
        if to_state.in_water:
            yield to_state
        to_state = NodeState(grid, x, y - 1, z)
        if to_state.can_stand or to_state.in_water:
            yield to_state
    elif base_state.can_hold:
        for k in [0, 1, -1]:
            for i, j in utils.cross:
                to_state = NodeState(grid, x + i, y + k, z + j)
                if to_state.can_stand:
                    go = can_go(grid, base_state, to_state)
                    if go:
                        yield to_state
                elif to_state.can_hold:
                    if k == 0:
                        yield to_state
        to_state = NodeState(grid, x, y + 1, z)
        if to_state.can_hold:
            yield to_state
        to_state = NodeState(grid, x, y - 1, z)
        if to_state.can_stand or to_state.can_hold:
            yield to_state
    else:
        for i, j in utils.adjacency:
            to_state = NodeState(grid, x + i, y, z + j)
            if to_state.can_stand or to_state.can_hold:
                go = can_go(grid, base_state, to_state)
                if go:
                    yield to_state
            elif to_state.can_fall:
                for k in [-1, -2, -3]:
                    to_state = NodeState(grid, x + i, y + k, z + j)
                    if to_state.can_stand or to_state.can_hold:
                        go = can_go(grid, base_state, to_state)
                        if go:
                            yield to_state
                        break
                    elif to_state.can_fall:
                        continue
                    else:
                        break
            else:
                to_state = NodeState(grid, x + i, y + 1, z + j)
                if to_state.can_stand or to_state.can_hold:
                    go = can_go(grid, base_state, to_state)
                    if go:
                        yield to_state


def can_swim(from_state, to_state):
    grid = from_state.grid
    for x in xrange(from_state.x, to_state.x + 1):
        for y in xrange(from_state.y, to_state.y + 1):
            for z in xrange(from_state.z, to_state.z + 1):
                if from_state.x == x and from_state.y == y and from_state.z == z:
                    continue
                if to_state.x == x and to_state.y == y and to_state.z == z:
                    continue
                to_state = NodeState(grid, x, y, z)
                if not to_state.can_be:
                    return False
    return True


def can_go(from_state, to_state):
    grid = from_state.grid
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
            return diagonal_free(grid, from_state, to_state, from_state.y)
        elif from_state.y < to_state.y:
            down = NodeState(grid, to_state.x, from_state.y, to_state.z)
            if not down.can_be:
                return False
            return diagonal_free(grid, from_state, to_state, to_state.y)
        else:
            go = diagonal_free(grid, from_state, to_state, from_state.y)
            if not go:
                return False
            for i in xrange(from_state.y - to_state.y):
                down = NodeState(grid, to_state.x, from_state.y - i, to_state.z)
                if not down.can_be:
                    return False
            return True
    else:
        if from_state.y == to_state.y:
            return True
        elif from_state.y < to_state.y:
            up = NodeState(grid, from_state.x, from_state.y + 1, from_state.z)
            if not up.can_be:
                return False
            return True
        else:
            for i in xrange(from_state.y - to_state.y):
                down = NodeState(grid, to_state.x, from_state.y - i, to_state.z)
                if not down.can_be:
                    return False
            return True


def diagonal_free(from_state, to_state, y_level):
    grid = from_state.grid
    left = NodeState(grid, to_state.x, y_level, from_state.z)
    if not left.can_be:
        return False
    right = NodeState(grid, from_state.x, y_level, to_state.z)
    if not right.can_be:
        return False
    return True


def can_stand(grid, x, y, z):
    return NodeState(grid, x, y, z).can_stand
