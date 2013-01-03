

import logbot
import utils
import blocks


log = logbot.getlogger("GRIDSPACE")


class NodeState(object):
    NO = 1
    FREE = 2
    YES = 3

    def __init__(self, can_stand=False, can_jump=False, move_horizontal=False, move_down=False, move_up=False):
        self.can_be = can_stand or move_down


def neighbours_of(grid, coords):
    x = coords.x
    y = coords.y
    z = coords.z
    for i, j in utils.adjacency:
        state = compute_state(grid, x + i, y, z + j)
        if state == NodeState.YES:
            yield Vector(x + i, y, z + j)
        elif state == NodeState.NO:
            state = compute_state(grid, x + i, y + 1, z + j)
            if state == NodeState.YES:
                yield Vector(x + i, y + 1, z + j)
        elif state == NodeState.FREE:
            for k in [-1, -2, -3]:
                state = compute_state(grid, x + i, y + k, z + j)
                if state == NodeState.YES:
                    yield Vector(x + i, y + k, z + j)
                    break
                elif state == NodeState.NO:
                    break
    state = compute_state(grid, x, y + 1, z)
    if state == NodeState.YES:
        yield Vector(x, y + 1, z)
    state = compute_state(grid, x, y - 1, z)
    if state == NodeState.YES:
        yield Vector(x, y - 1, z)


def compute_state(grid, x, y, z):
    block_0 = grid.get_block(x, y - 1, z)
    block_1 = grid.get_block(x, y, z)
    block_2 = grid.get_block(x, y + 1, z)
    block_3 = grid.get_block(x, y + 2, z)
    if not block_2.is_fall_through:
        return NodeState()
    elif block_1.can_stand_in or block_0.is_fence:
        if block_1.is_stairs:
            for bb in block_1.check_aabbs():
                if grid.aabb_collides(bb):
                    continue
                else:
                    return NodeState.YES
            return NodeState()
        elif block_0.is_fence or block_1.stand_in_over2:
            if block_3.is_fall_through:
                return NodeState(can_stand=True)
            else:
                return NodeState()
        else:
            return NodeState.YES
    elif not block_1.is_fall_through:
        return NodeState()
    elif block_0.can_stand_on:
        return NodeState(can_stand=True)
    else:
        return NodeState.FREE


def can_go(grid, from_coords, to_coords):
    from_block = grid.get_block_coords(from_coords)
    to_block = grid.get_block_coords(to_coords)
    cross = from_coords.x == to_coords.x or from_coords.z == to_coords.z
    vertical = from_coords.y != to_coords.y
    if vertical:
        if from_block.is_stairs:
            pass
        elif from_block.is_climbable:
            pass
    elif cross:
        pass
    else: # diagonal
        pass
    """
    if in cross
    if in diagonal
    platform 2 platform
    if p1_level == p2_level:
    if p1_level > p2_level:
    if p1_level < p2_level:
    """
    return True


def can_stand(grid, x, y, z):
    return compute_state(grid, x, y, z) == NodeState.YES
