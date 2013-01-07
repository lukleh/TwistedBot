
import heapq

import config
import logbot
import gridspace
from utils import Vector


log = logbot.getlogger("ASTAR")


class PathNode(object):
    def __init__(self, coords=None, state=None, cost=1):
        if coords:
            self.coords = coords
        else:
            self.coords = state.coords
        self.state = state
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
        self.node_step = 0
        self.is_finished = False

    def __str__(self):
        return "Path nodes %d\n\t%s" % (len(self.nodes), '\n\t'.join([str(n) for n in self.nodes]))

    def take_step(self):
        try:
            step = self.nodes[self.node_step]
            self.node_step += 1
            if self.node_step == len(self.nodes):
                self.is_finished = True
            return step
        except IndexError:
            return None



class AStar(object):

    def __init__(self, dimension=None, start_coords=None, end_coords=None, start_aabb=None, max_cost=config.PATHFIND_LIMIT):
        self.dimension = dimension
        self.grid = dimension.grid
        start_state = gridspace.NodeState(self.grid, start_coords.x, start_coords.y, start_coords.z)
        goal_state = gridspace.NodeState(self.grid, end_coords.x, end_coords.y, end_coords.z)
        self.start_node = PathNode(state=start_state)
        self.goal_node = PathNode(state=goal_state)
        self.start_aabb = start_aabb
        self.max_cost = max_cost
        self.path = None
        self.closed_set = set()
        if goal_state.can_stand or goal_state.can_hold:
            self.open_heap = [self.start_node]
            self.open_set = set([self.start_node])
        else:
            self.open_heap = []
            self.open_set = set([])
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
        for state in gridspace.neighbours_of(self.grid, node.state):
            if state.coords not in self.closed_set:
                yield PathNode(state=state)

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
        self.closed_set.add(x.coords)
        for y in self.neighbours(x):
            if y.coords in self.closed_set:
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
