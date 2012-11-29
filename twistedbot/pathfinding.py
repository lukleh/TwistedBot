
import heapq

import config
import logbot
from gridspace import compute_state


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
        return "%s:%s:g%s:h%s:f%s" % \
            (str(self.coords), self.cost, self.g, self.h, self.f)

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.f < other.f

    def __eq__(self, other):
        return self.hash == other.__hash__()

    def __hash__(self):
        return self.hash

    def __getitem__(self, i):
        return self.coords[i]

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
    def __init__(self, dimension=None, nodes=None):
        self.dimension = dimension
        self.goal = goal
        self.nodes = nodes
        self.space_graph = SpaceGraph()

    def __str__(self):
        return "Path nodes %s" % [str(n) for n in self.nodes]

    def __iter__(self):
        return self.space_graph

    def check_path(self, current_aabb):
        previous = GridSpace(self.dimension.grid, coords=self.nodes[0].coords)
        previous.compute_spaces()
        if not self.space_graph.check_start(previous, current_aabb):
            return False
        for ni in xrange(1, len(self.nodes)):
            node = self.nodes[ni]
            current = GridSpace(self.dimension.grid, coords=node.coords)
            current.compute_spaces()
            if self.space_graph.can_go_to(current):
                previous = current
            else:
                return False
        return True


class AStar(object):
    def __init__(self, dimension=None, start_coords=None, end_coords=None, current_aabb=None, max_cost=config.PATHFIND_LIMIT):
        self.dimension = dimension
        self.navgrid = dimension.navgrid
        self.get_node = self.navgrid.get_node
        self.start_node = PathNode(start_coords)
        self.goal_node = PathNode(end_coords)
        self.current_aabb = current_aabb
        self.max_cost = max_cost
        self.path = None
        self.closed_set = set()
        self.open_heap = [self.start_node]
        self.open_set = set([self.start_node])
        self.start_node.set_score(0, self.heuristic_cost_estimate(self.start_node, self.goal_node))

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
        for node in self.navgrid.neighbours_of(node.coords):
            if node not in self.closed_set:
                yield PathNode(node)

    def heuristic_cost_estimate(self, start, goal):
        h_diagonal = min(abs(start[0] - goal[0]), abs(start[2] - goal[2]))
        h_straight = (abs(start[0] - goal[0]) + abs(start[2] - goal[2]))
        h = config.COST_DIAGONAL * h_diagonal + \
            config.COST_DIRECT * (h_straight - 2 * h_diagonal)
        return h

    def next(self):
        if not self.open_set:
            log.err("Did not find path between %s and %s" % (self.start_node.coords, self.goal_node.coords))
            raise StopIteration()
        x = heapq.heappop(self.open_heap)
        if x == self.goal_node:
            self.path = Path(dimension=self.dimension, nodes=reconstruct_path(x), current_aabb=self.current_aabb)
            raise StopIteration()
        self.open_set.remove(x)
        self.closed_set.add(x)
        for y in self.neighbours(x):
            if y in self.closed_set:
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
