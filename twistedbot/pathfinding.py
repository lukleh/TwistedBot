
import heapq
import time

import config
import logbot
from gridspace import GridSpace
from axisbox import AABB


log = logbot.getlogger("ASTAR")


class BaseEx(Exception):
    def __init__(self, value=None):
        self.value = value

    def __repr__(self):
        if self.value is None:
            return self.__class__.__name__
        else:
            return "%s %s" % (self.__class__.__name__, self.value)

    @property
    def message(self):
        return str(self)


class PathNotFound(BaseEx):
    pass


class PathFound(BaseEx):
    pass


class PathOverLimit(BaseEx):
    pass


class PathNode(object):
    def __init__(self, coords=None, cost=1):
        self.coords = coords
        self.cost = cost
        self.g = 0
        self.h = 0
        self.f = 0
        self.step = 0
        self._parent = None
        self.hash = hash(self.coords)

    def __repr__(self):
        #return "%s:st%s:cost:%s:g%s:h%s:f%s" % (str(self.coords), self.step, self.cost, self.g, self.h, self.f)
        return str(self.coords)

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


class AStarCoords(object):
    def __init__(self, dimension, start_coords, goal_coords):
        self.goal_coords = goal_coords
        self.goal_node = PathNode(goal_coords)
        self.start_node = PathNode(start_coords)
        self.astar = AStarAlgo(graph=GridSpace(dimension.grid), start_node=self.start_node, goal_node=self.goal_node, is_goal=self.is_goal, heuristics=self.heuristics)
        self.t_start = time.time()
        self.path = None

    def heuristics(self, start, goal):
        adx = abs(start.coords.x - goal.coords.x)
        adz = abs(start.coords.z - goal.coords.z)
        h_diagonal = min(adx, adz)
        h_straight = adx + adz
        h = config.COST_DIAGONAL * h_diagonal + config.COST_DIRECT * (h_straight - 2 * h_diagonal)
        return h

    def is_goal(self, current):
        return current == self.goal_node

    def time_sice_start(self):
        return time.time() - self.t_start

    def next(self):
        count = 0
        try:
            while count < 1000:
                self.astar.next()
        except PathNotFound:
            log.err("did not find path between %s and %s" % (self.start_node.coords, self.goal_node.coords))
            log.msg('time consumed %s sec, made %d iterations' % (self.time_sice_start(), self.astar.iter_count))
            raise StopIteration()
        except PathFound:
            log.msg('found path %d steps long' % len(self.astar.path))
            log.msg('time consumed %s sec, made %d iterations' % (self.time_sice_start(), self.astar.iter_count))
            self.path = self.astar.path
            raise StopIteration()
        except PathOverLimit:
            log.err("finding path over limit between %s and %s" % (self.start_node.coords, self.goal_node.coords))
            log.msg('time consumed %s sec, made %d iterations' % (self.time_sice_start(), self.astar.iter_count))
            raise StopIteration()
        except:
            raise


class AStarMultiCoords(AStarCoords):
    def __init__(self, multiple_goals=None, **kwargs):
        self.multiple_goals = [PathNode(g) for g in multiple_goals]
        super(AStarMultiCoords, self).__init__(**kwargs)

    def is_goal(self, current):
        for g in self.multiple_goals:
            if current == g:
                return True
        else:
            return False


class AStarBBCol(AStarCoords):
    def __init__(self, bb=None, **kwargs):
        self.bb = bb
        super(AStarBBCol, self).__init__(goal_coords=bb.bottom_center, **kwargs)

    def is_goal(self, current):
        x = current.coords.x
        y = current.coords.y
        z = current.coords.z
        return self.bb.collides(AABB(x, y, z, x + 1, y + config.PLAYER_HEIGHT, z + 1))


class AStarAlgo(object):

    def __init__(self, graph=None, start_node=None, goal_node=None, heuristics=None, is_goal=None, max_cost=None):
        self.graph = graph
        self.start_node = start_node
        self.goal_node = goal_node
        self.heuristics = heuristics
        self.is_goal = is_goal
        if max_cost is None:
            vdist = start_node.coords - goal_node.coords
            self.max_cost = int(max(32, min(vdist.manhatan_size * 2, config.PATHFIND_LIMIT)))
        else:
            self.max_cost = int(max_cost)
        log.msg("limit for astar is %s" % self.max_cost)
        self.path = None
        self.closed_set = set()
        self.open_heap = [self.start_node]
        self.open_set = set([self.start_node])
        self.start_node.set_score(0, self.heuristics(self.start_node, self.goal_node))
        self.iter_count = 0

    def reconstruct_path(self, current):
        nodes = []
        nodes.append(current)
        while current.parent is not None:
            nodes.append(current.parent)
            current = current.parent
        return nodes

    def get_edge_cost(self, node_from, node_to):
        return config.COST_DIRECT

    def neighbours(self, node):
        for state in self.graph.neighbours_of(node.coords):
            if state.coords not in self.closed_set:
                yield PathNode(state.coords)

    def next(self):
        self.iter_count += 1
        if not self.open_set:
            raise PathNotFound()
        x = heapq.heappop(self.open_heap)
        if self.is_goal(x):
            self.path = self.reconstruct_path(x)
            self.graph = None
            raise PathFound()
        self.open_set.remove(x)
        self.closed_set.add(x.coords)
        for y in self.neighbours(x):
            tentative_g_core = x.g + self.get_edge_cost(x, y)
            if y not in self.open_set:
                y.set_score(tentative_g_core, self.heuristics(y, self.goal_node))
                y.parent = x
                heapq.heappush(self.open_heap, y)
                self.open_set.add(y)
                if y.step > self.max_cost:
                    raise PathOverLimit()
            elif tentative_g_core < y.g:
                y.set_score(tentative_g_core, self.heuristics(y, self.goal_node))
                y.parent = x
                if y.step > self.max_cost:
                    raise PathOverLimit()
