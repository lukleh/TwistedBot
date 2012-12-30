

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
    if block_1.is_cube:
        return NodeState.NO
    block_2 = grid.get_block(x, y + 1, z)
    if block_2.is_cube:
        return NodeState.NO
    block_0 = grid.get_block(x, y - 1, z)
    if block_0.is_cube:
        if block_1.is_free and block_2.is_free:
            return NodeState.YES
    if block_0.is_free and block_1.is_free and block_2.is_free:
        return NodeState.FREE
    if not block_2.is_fall_through:
        return NO
    if block_1.can_stand_in:
        if block_1.is_stairs:
            raise NotImplemented('stairs state')
        elif block_0.is_fence and block_1.fence_overlap:
            if block_3.is_fall_through or block_3.is_slab:
                return YES
            else:
                return NO
        elif block_1.stand_in_over2:
            if block_3.is_fall_through or block_3.min_y > block_1.max_y + PLAYER_HEIGHT:
                return YES
            else:
                return NO
        else:
            return YES
    elif block_0.can_stand_on:
        if block_0.is_fall_through and block_1.is_fall_through:
            return FREE
        else:
            return YES
    elif block_1.is_fall_through:
        return FREE
    else:
        return NO


def can_go(grid, from_coords, to_coords):
    #TODO turn this dummy function into something usefull
    return True


def can_stand(grid, x, y, z):
    return compute_state(grid, x, y, z) == NodeState.YES
