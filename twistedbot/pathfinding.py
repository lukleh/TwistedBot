
import heapq

import config
import logbot
import gridspace
from utils import Vector


log = logbot.getlogger("ASTAR")


class PathNode(object):
    def __init__(self, coords, cost=1):
        self.coords = coords
        self.cost = cost
        self.g = 0
        self.h = 0
        self.f = 0
        self.step = 0
        self._parent = None
        self.hash = hash(self.coords)

    def __str__(self):
        #return "%s:st%s:cost:%s:g%s:h%s:f%s" % (str(self.coords), self.step, self.cost, self.g, self.h, self.f)
        return str(self.coords)

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.f < other.f

    def __eq__(self, other):
        return self.coords == other.coords

    def __hash__(self):
        return self.hash

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, p):
        self._parent = p
        self.step = p.step + 1

    def set_score(self, g, h):
        self.g = g
        self.h = h
        self.f = g + h


class Path(object):
    def __init__(self, dimension=None, nodes=None, start_aabb=None):
        self.dimension = dimension
        self.nodes = nodes
        self.start_aabb = start_aabb
        self.is_valid = True

    def __str__(self):
        return "Path nodes %d\n\t%s" % (len(self.nodes), '\n\t'.join([str(n) for n in self.nodes]))

    def take_step(self):
        pass

    def start_from(self, bb):
        self.start_aabb = bb


class AStar(object):

    def __init__(self, dimension=None, start_coords=None, end_coords=None, start_aabb=None, max_cost=config.PATHFIND_LIMIT):
        self.dimension = dimension
        self.grid = dimension.grid
        self.start_node = PathNode(start_coords)
        self.goal_node = PathNode(end_coords)
        self.start_aabb = start_aabb
        self.max_cost = max_cost
        self.path = None
        self.closed_set = set()
        self.open_heap = [self.start_node]
        self.open_set = set([self.start_node])
        self.start_node.set_score(0, self.heuristic_cost_estimate(self.start_node, self.goal_node))
        self.iter_count = 0

    def reconstruct_path(self, current):
        nodes = []
        nodes.append(current)
        while current.parent is not None:
            nodes.append(current.parent)
            current = current.parent
        nodes.reverse()
        return nodes

    def get_edge_cost(self, node_from, node_to):
        return config.COST_DIRECT

    def neighbours(self, node):
        for t_coords in gridspace.neighbours_of(self.grid, node.coords):
            if t_coords not in self.closed_set:
                if gridspace.can_go(self.grid, node.coords.tuple, t_coords):
                    yield PathNode(Vector.from_tuple(t_coords))

    def heuristic_cost_estimate(self, start, goal):
        adx = abs(start.coords.x - goal.coords.x)
        adz = abs(start.coords.z - goal.coords.z)
        h_diagonal = min(adx, adz)
        h_straight = adx + adz
        h = config.COST_DIAGONAL * h_diagonal + config.COST_DIRECT * (h_straight - 2 * h_diagonal)
        return h

    def next(self):
        self.iter_count += 1
        if not self.open_set:
            log.err("Did not find path between %s and %s" % (self.start_node.coords, self.goal_node.coords))
            raise StopIteration()
        x = heapq.heappop(self.open_heap)
        if x == self.goal_node:
            self.path = Path(dimension=self.dimension, nodes=self.reconstruct_path(x), start_aabb=self.start_aabb)
            raise StopIteration()
        self.open_set.remove(x)
        self.closed_set.add(x.coords.tuple)
        for y in self.neighbours(x):
            if y.coords.tuple in self.closed_set:
                continue
            tentative_g_core = x.g + self.get_edge_cost(x, y)
            if y not in self.open_set or tentative_g_core < y.g:
                y.set_score(tentative_g_core, self.heuristic_cost_estimate(y, self.goal_node))
                y.parent = x
                if y not in self.open_set:
                    heapq.heappush(self.open_heap, y)
                    self.open_set.add(y)
                if y.step > self.max_cost:
                    log.err("Finding path over limit between %s and %s" % (self.start_node.coords, self.goal_node.coords))
                    raise StopIteration()
