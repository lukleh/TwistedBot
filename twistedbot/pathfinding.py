
import heapq
	
import config
import fops
import logbot
import tools


log = logbot.getlogger("ASTAR")


class PathNode(object):
	def __init__(self, coords, cost=1):
		self.coords = coords
		self.cost = cost
		self.g = 0
		self.h = 0
		self.f = 0
		self.parent = None
		self.hash = hash(self.coords)

	def __str__(self):
		return "%s:%s:g%s:h%s:f%s" % (str(self.coords), self.cost, self.g, self.h, self.f)

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
		#log.msg("Path broken %s nodes %s" % (self.broken, [str(p) for p in self.nodes]))

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
	def __init__(self, navmesh):
		self.navmesh = navmesh
		self.succesors = self.navmesh.graph.get_succ
		self.get_node = self.navmesh.graph.get_node

	def reconstruct_path(self, current):
		nodes = []
		nodes.append(current)
		while current.parent is not None:
			nodes.append(current.parent)
			current = current.parent
		nodes.reverse()
		return nodes

	def get_edge_cost(self, node_from, node_to):
		return self.navmesh.graph.get_edge(node_from.coords, node_to.coords)
		
	def neighbours(self, start, closed_set):
		for node, cost in self.succesors(start.coords):
			if node not in closed_set:
				yield PathNode(node, cost=cost)
	
	def heuristic_cost_estimate(self, start, goal):
		h_diagonal = min(abs(start[0]-goal[0]), abs(start[2]-goal[2]))
		h_straight = (abs(start[0]-goal[0]) + abs(start[2]-goal[2]))
		h = config.COST_DIAGONAL*h_diagonal + config.COST_DIRECT*(h_straight - 2*h_diagonal)
		return h
	
	def find_path(self, start, goal, max_cost=config.ASTAR_LIMIT):
		start_node = PathNode(start)
		goal_node  = PathNode(goal)
		closed_set = set() 
		open_heap = [start_node]
		open_set = set([start_node])
		start_node.set_score(0, self.heuristic_cost_estimate(start_node, goal_node))
		while open_set:
			x = heapq.heappop(open_heap)
			if x == goal_node:
				return Path(goal=x)
			open_set.remove(x)
			closed_set.add(x)
			for y in self.neighbours(x, closed_set):
				tentative_g_core = x.g + self.get_edge_cost(x, y)
				if y not in open_set or tentative_g_core < y.g:
					y.set_score(tentative_g_core, self.heuristic_cost_estimate(y, goal_node))
					y.parent = x
					if y not in open_set:
						heapq.heappush(open_heap, y)
						open_set.add(y)
					if y.g > max_cost:
						log.err("pathfinding too wide")
						return None
		log.err("pathfinding no path")
		return None
