
from collections import defaultdict, OrderedDict

from twisted.internet.task import cooperate

import tools
import logbot
from signwaypoints import SignWayPoints
from gridspace import GridSpace


log = logbot.getlogger("navgrid")


class ChunkBorders(object):
    def __init__(self):
        self.borders = defaultdict(lambda: defaultdict(set))

    def chunk_diff(self, c1, c2):
        return (c1[0] - c2[0], c1[1] - c2[1])

    def add(self, from_crd, to_crd):
        chunk_from = from_crd[0] >> 4, from_crd[2] >> 4
        chunk_to = to_crd[0] >> 4, to_crd[2] >> 4
        ch_diff = self.chunk_diff(chunk_from, chunk_to)
        self.borders[chunk_from][ch_diff].add(to_crd)

    def remove(self, crd):
        chunk_from = crd[0] >> 4, crd[2] >> 4
        for i in [-1, 1]:
            for j in [-1, 1]:
                try:
                    self.borders[chunk_from][(i, j)].remove(crd)
                except KeyError:
                    pass

    def between(self, chunk_from, chunk_to):
        ch_diff = self.chunk_diff(chunk_from, chunk_to)
        for crd in self.borders[chunk_from][ch_diff]:
            yield crd


class GridEdge(object):
    __slots__ = ('cost')

    def __init__(self, cost):
        self.cost = cost


class GridNode(object):
    __slots__ = ('area_id')

    def __init__(self):
        self.area_id = None


class NavigationGrid(object):
    def __init__(self, world):
        self.world = world
        self.incomplete_nodes = OrderedDict()
        self.graph = tools.DirectedGraph()
        self.chunk_borders = ChunkBorders()
        self.sign_waypoints = SignWayPoints(self)

    def check_node_resources(self, crd):
        pass

    def compute(self, node, recheck=False):
        if self.incomplete_nodes:
            self.incomplete_nodes[node] = recheck
        else:
            self.incomplete_nodes[node] = recheck
            cootask = cooperate(self.do_incomplete_nodes())
            d = cootask.whenDone()
            d.addErrback(logbot.exit_on_error)

    def do_incomplete_nodes(self):
        while self.incomplete_nodes:
            crd, recheck = self.incomplete_nodes.popitem(last=False)
            self.do_incomplete_node(crd, recheck)
            self.check_node_resources(crd)
            yield None

    def do_incomplete_node(self, crd, recheck):
        center_space = GridSpace(self.world.grid, coords=crd)
        if not center_space.can_stand_on:
            self.delete_node(crd)
            return
        elif not self.graph.has_node(crd):
            self.graph.add_node(crd, miny=center_space.bb_stand.min_y)
        for i, j in tools.adjacency:
            tocrd = (crd[0] + i, crd[1], crd[2] + j)
            if not self.world.grid.chunk_complete_at((tocrd[0] >> 4, tocrd[2] >> 4)):
                self.chunk_borders.add(center_space.coords, tocrd)
                continue
            if i != 0 and j != 0:
                if not self.world.grid.chunk_complete_at((crd[0] >> 4, (crd[2] + j) >> 4)) or \
                        not self.world.grid.chunk_complete_at(((crd[0] + i) >> 4, crd[2] >> 4)):
                    continue
            if recheck or not self.graph.has_edge(center_space.coords, tocrd):
                gs = GridSpace(self.world.grid, coords=tocrd)
                if gs.can_stand_on:
                    self.make_node(center_space, gs)
                    continue
            tocrd = (crd[0] + i, crd[1] + 1, crd[2] + j)
            if recheck or not self.graph.has_edge(center_space.coords, tocrd):
                gs = GridSpace(
                    self.world.grid, coords=tocrd)
                if gs.can_stand_on:
                    self.make_node(center_space, gs)
                    continue
            tocrd = (crd[0] + i, crd[1] + 2, crd[2] + j)
            if recheck or not self.graph.has_edge(center_space.coords, tocrd):
                gs = GridSpace(
                    self.world.grid, coords=tocrd)
                if gs.can_stand_on:
                    self.make_node(center_space, gs)
                    continue
            for k in [-1, -2, -3]:
                tocrd = (crd[0] + i, crd[1] + k, crd[2] + j)
                if recheck or not self.graph.has_edge(center_space.coords, tocrd):
                    gs = GridSpace(
                        self.world.grid, coords=tocrd)
                    if gs.can_stand_on:
                        self.make_node(center_space, gs)
                        break
        for k in [-1, 1, 2]:  # climb, descend
            tocrd = (crd[0], crd[1] + k, crd[2])
            if recheck or not self.graph.has_edge(center_space.coords, tocrd):
                gs = GridSpace(self.world.grid, coords=tocrd)
                if gs.can_stand_on:
                    self.make_node(center_space, gs)

    def make_node(self, center_space, possible_space):
        if not self.graph.has_node(possible_space.coords):
            self.compute(possible_space.coords)
            self.graph.add_node(
                possible_space.coords, miny=possible_space.bb_stand.min_y)
        if center_space.can_go(possible_space):
            self.graph.add_edge(center_space.coords, possible_space.coords,
                                center_space.edge_cost)
        else:
            self.graph.remove_edge(center_space.coords, possible_space.coords)

    def check_path(self, path):
        if path is None:
            return None
        last_one = None
        ok = True
        for p in path:
            gs = GridSpace(self.world.grid, coords=p)
            if not gs.can_stand_on:
                self.delete_node(p)
                last_one = None
                ok = False
                continue
            if last_one is not None:
                if not last_one.can_go(gs):
                    self.graph.remove_edge(last_one.coords, gs.coords)
                    ok = False
            last_one = gs
        return ok

    def delete_node(self, crd):
        if self.graph.has_node(crd):
            affected = self.graph.remove_node(crd)
            for aff in affected:
                self.compute(aff)
            self.chunk_borders.remove(crd)
        try:
            del self.incomplete_nodes[crd]
        except KeyError:
            pass

    def insert_node(self, coords, gspace):
        if self.graph.has_node(coords):
            self.compute(coords, recheck=True)
        else:
            self.compute(coords)
            self.graph.add_node(coords, miny=gspace.bb_stand.min_y)

    def incomplete_on_chunk_border(self, chunk_from, chunk_to):
        for crd in self.chunk_borders.between(chunk_from, chunk_to):
            self.compute(crd)
            self.chunk_borders.remove(crd)

    def block_change(self, old_block, new_block):
        coords = new_block.coords
        gs = GridSpace(self.world.grid, coords=coords)
        if gs.can_stand_on:
            self.insert_node(gs.coords, gspace=gs)
        else:
            self.delete_node(gs.coords)
        for i in [-2, -1, 1, 2]:
            crd = (coords[0], coords[1] - i, coords[2])
            gs = GridSpace(self.world.grid, crd)
            if gs.can_stand_on:
                self.insert_node(gs.coords, gspace=gs)
            else:
                self.delete_node(gs.coords)
