
import heapq

import config
import logbot


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
    def __init__(self, goal=None):
        self.goal = goal
        self.nodes = []
        self.reconstruct_path(self.goal)
        self.step_index = len(self.nodes)

    def __str__(self):
        return "Path nodes %s" % [str(n) for n in self.nodes]

    def reconstruct_path(self, current):
        self.nodes.append(current)
        while current.parent is not None:
            self.nodes.append(current.parent)
            current = current.parent

    def __iter__(self):
        self.iter_index = len(self.nodes)
        return self

    def next(self):
        self.iter_index -= 1
        if self.iter_index < 0:
            raise StopIteration()
        return self.nodes[self.iter_index]

    def has_next(self):
        return self.step_index > 0

    def next_step(self):
        self.step_index -= 1
        if self.step_index < 0:
            raise Exception("Path consumed")
        return self.nodes[self.step_index]


class AStar(object):
    def __init__(self, navgrid, start, goal, max_cost=config.PATHFIND_LIMIT):
        self.navgrid = navgrid
        self.succesors = self.navgrid.graph.get_succ
        self.get_node = self.navgrid.graph.get_node
        self.start_node = PathNode(start)
        self.goal_node = PathNode(goal)
        self.max_cost = max_cost
        self.path = None
        self.closed_set = set()
        self.open_heap = [self.start_node]
        self.open_set = set([self.start_node])
        self.start_node.set_score(
            0, self.heuristic_cost_estimate(self.start_node, self.goal_node))

    def reconstruct_path(self, current):
        nodes = []
        nodes.append(current)
        while current.parent is not None:
            nodes.append(current.parent)
            current = current.parent
        nodes.reverse()
        return nodes

    def get_edge_cost(self, node_from, node_to):
        return self.navgrid.graph.get_edge(node_from.coords, node_to.coords)

    def neighbours(self, start):
        for node, cost in self.succesors(start.coords):
            if node not in self.closed_set:
                yield PathNode(node, cost=cost)

    def heuristic_cost_estimate(self, start, goal):
        h_diagonal = min(abs(start[0] - goal[0]), abs(start[2] - goal[2]))
        h_straight = (abs(start[0] - goal[0]) + abs(start[2] - goal[2]))
        h = config.COST_DIAGONAL * h_diagonal + \
            config.COST_DIRECT * (h_straight - 2 * h_diagonal)
        return h

    def next(self):
        if not self.open_set:
            log.err("pathfinding no path")
            raise StopIteration()
        x = heapq.heappop(self.open_heap)
        if x == self.goal_node:
            self.path = Path(goal=x)
            raise StopIteration()
        self.open_set.remove(x)
        self.closed_set.add(x)
        for y in self.neighbours(x):
            if y in self.closed_set:
                continue
            tentative_g_core = x.g + self.get_edge_cost(x, y)
            if y not in self.open_set or tentative_g_core < y.g:
                y.set_score(tentative_g_core,
                            self.heuristic_cost_estimate(y, self.goal_node))
                y.parent = x
                if y not in self.open_set:
                    heapq.heappush(self.open_heap, y)
                    self.open_set.add(y)
                if y.step > self.max_cost:
                    log.err("pathfinding too wide")
                    raise StopIteration()
