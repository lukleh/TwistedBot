
import array
from collections import defaultdict, OrderedDict

from twisted.internet.task import cooperate

import tools
import logbot
from signwaypoints import SignWayPoints
from gridspace import compute_state
from tools import NodeState


log = logbot.getlogger("navgrid")


class ChunkBorders(object):
    def __init__(self):
        self.borders = defaultdict(set)
        self.rev_borders = defaultdict(set)

    def add(self, from_crd, to_crd):
        crd = from_crd.x >> 4, from_crd.z >> 4, to_crd.x >> 4, to_crd.z >> 4
        self.borders[crd].add(from_crd)
        self.rev_borders[from_crd].add(crd)

    def remove(self, crd):
        for cc in self.rev_borders.get(crd, []):
            self.borders[cc].remove(crd)
            if not self.borders[cc]:
                del self.borders[cc]
        try:
            del self.rev_borders[crd]
        except KeyError:
            pass

    def between(self, chunk_from, chunk_to):
        crd = chunk_from[0], chunk_from[1], chunk_to[0], chunk_to[1]
        for coords in self.borders[crd]:
            yield coords


class NavigationCubes(object):

    def __init__(self, world):
        self.world = world
        self.cubes = {}
        self.ZEROS = [0 for _ in xrange(256 * 256)]

    def new_cube(self, crd):
        self.cubes[crd] = array.array('B', self.ZEROS)

    def array_pos(self, x, y, z):
        return y * 256 + z * 16 + x

    def mark(self, coords, state):
        crd = coords.x >> 4, coords.z >> 4
        self.cubes[crd][self.array_pos(coords.x, coords.y, coords.z)] = state

    def state_at(self, coords):
        crd = coords.x >> 4, coords.z >> 4
        return self.cubes[crd][self.array_pos(coords.x, coords.y, coords.z)]


class NavigationGrid(object):
    def __init__(self, world):
        self.world = world
        self.incomplete_nodes = OrderedDict()
        self.chunk_borders = ChunkBorders()
        self.sign_waypoints = SignWayPoints(self)

    def neighbours_of(self, coords):
        for i, j in tools.adjacency:
            for k in [0, 1, 2, -1, -2, -3]:
                to_crd = (coords[0] + i, coords[1] + k, coords[2] + j)
                try:
                    st = self.world.nav_cubes.state_at(coords)
                    if st == NodeState.YES:
                        yield to_crd
                except IndexError:
                    pass

    def compute(self, coords, recheck=False):
        if self.incomplete_nodes:
            if recheck or coords not in self.incomplete_nodes:
                self.incomplete_nodes[coords] = recheck
        else:
            self.incomplete_nodes[coords] = recheck
            cootask = cooperate(self.do_incomplete_nodes())
            d = cootask.whenDone()
            d.addErrback(logbot.exit_on_error)

    def do_incomplete_nodes(self):
        while self.incomplete_nodes:
            coords, recheck = self.incomplete_nodes.popitem(last=False)
            self.do_incomplete_node(coords, recheck)
            yield None

    def do_incomplete_node(self, crd, recheck):
        if recheck or not self.node_is_marked(crd):
            state = compute_state(self.world.grid, crd.x, crd.y, crd.z)
            if self.world.nav_cubes.state_at(crd) != state:
                self.mark_node(crd, state)
        for i, j in tools.plane:
            to_crd = crd.offset(dx=i, dz=j)
            if not self.world.grid.chunk_complete_at(to_crd.x, to_crd.z):
                self.chunk_borders.add(crd, to_crd)
                continue
            for k in [0, 1, 2, -1, -2, -3]:
                to_crd = crd.offset(dx=i, dy=k, dz=j)
                if recheck or not self.node_is_marked(to_crd):
                    n_state = compute_state(self.world.grid, to_crd.x, to_crd.y, to_crd.z)
                    self.mark_node(to_crd, n_state)

    def mark_node(self, coords, state):
        if state == NodeState.YES:
            self.compute(coords)
        self.world.nav_cubes.mark(coords, state)

    def node_is_marked(self, coords):
        return self.world.nav_cubes.state_at(coords) != NodeState.UNKNOWN

    def node_is_solid(self, coords):
        return self.world.nav_cubes.state_at(coords) == NodeState.YES

    def delete_node(self, coords):
        if self.node_is_marked(coords):
            self.mark_node(coords, NodeState.NO)
            self.chunk_borders.remove(coords)
        try:
            del self.incomplete_nodes[coords]
        except KeyError:
            pass

    def check_node(self, coords):
        if self.node_is_marked(coords):
            self.compute(coords, recheck=True)
        else:
            self.compute(coords)

    def incomplete_on_chunk_border(self, chunk_from, chunk_to):
        for crd in self.chunk_borders.between(chunk_from, chunk_to):
            self.compute(crd)
            self.chunk_borders.remove(crd)

    def block_change(self, old_block, new_block):
        print 'block_change', old_block, new_block
        if new_block is None:
            return
        coords = new_block.coords
        self.check_node(coords)
        for i in [-2, -1, 1, 2]:
            self.check_node(coords.offset(dy=i))
