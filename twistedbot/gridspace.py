

import logbot
import utils
import blocks


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


def compute_state(grid, x, y, z, debug=False):
    block_1 = grid.get_block(x, y, z)
    if block_1.is_cube:
        return NodeState.NO
    block_2 = grid.get_block(x, y + 1, z)
    if not block_2.is_fall_through:
        return NodeState.NO
    block_0 = grid.get_block(x, y - 1, z)
    if block_0.is_cube:
        if block_1.is_fall_through:
            return NodeState.YES
    if block_1.can_stand_in:
        if block_1.is_stairs:
            for bb in block_1.check_aabbs():
                if grid.aabb_collides(bb):
                    continue
                else:
                    return NodeState.YES
            return NodeState.NO
        elif block_0.is_fence or block_1.stand_in_over2:
            block_3 = grid.get_block(x, y + 2, z)
            if block_3.is_fall_through:
                return NodeState.YES
            else:
                return NodeState.NO
        else:
            return NodeState.YES
    elif not block_1.is_fall_through:
        return NodeState.NO
    elif block_0.can_stand_on:
        if block_0.is_fall_through and (not block_1.is_free or not block_2.is_free):
            return NodeState.FREE
        else:
            return NodeState.YES
    else:
        return NodeState.FREE


def can_go(grid, from_coords, to_coords):
    #TODO turn this dummy function into something usefull
    return True


def can_stand(grid, x, y, z):
    return compute_state(grid, x, y, z) == NodeState.YES
