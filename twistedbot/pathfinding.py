
import heapq
	

class PathNode(object):
	def __init__(self, point, cost=1):
		self.coords = point
		self.cost = cost
		self.g = 0
		self.h = 0
		self.f = 0
		self.parent = None
		self.hash = hash(self.coords)

	def __str__(self):
		return str(self.coords)

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
		
	def load_block(self, block):
		#TODO have to take center of the top face, not center of square (0.5, 0.5)
		x = block.coords[0] + 0.5
		y = block.grid_height
		z = block.coords[2] + 0.5
		self.path_point = (x, y, z)
		self.block = block
		
	
class Path(object):
	def __init__(self, goal=None, broken=False):
		self.broken = broken
		self.goal = goal
		self.nodes = []
		if not broken:
			self.reconstruct_path(self.goal)
			self.atstep = len(self.nodes)
		self.done = False
		#log.msg("Path broken %s nodes %s" % (self.broken, [str(p) for p in self.nodes]))

	def __str__(self):
		return "Path nodes %s" % [str(n) for n in self.nodes]

	def reconstruct_path(self, current):
		self.nodes.append(current)
		while current.parent is not None:
			self.nodes.append(current.parent)
			current = current.parent
		
	def next_step(self):
		self.atstep -= 1
		if self.atstep < 0:
			self.atstep = 0
			self.done = True
		self.next_node = self.nodes[self.atstep]
		return self.next_node
	

class AStar(object):
	def __init__(self, navmesh):
		self.navmesh = navmesh
		
	def neighbours(self, start, closed_set):
		for node, cost in self.navmesh.successors(start.coords):
			if node not in closed_set:
				yield PathNode(node, cost=cost)
	
	def heuristic_cost_estimate(self, x, y):
		#D axis cost
		#D2 diagonal cost
		#h_diagonal(n) = min(abs(n.x-goal.x), abs(n.y-goal.y))
		#h_straight(n) = (abs(n.x-goal.x) + abs(n.y-goal.y))
		#h(n) = D2 * h_diagonal(n) + D * (h_straight(n) - 2*h_diagonal(n)))
		#return h(n)
		return 0
	
	def find_path(self, start, goal, max_cost=50):
		#log.msg("Find path between %s and %s" % (start, goal))
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
				tentative_g_core = x.g + self.navmesh.get_edge(x.coords, y.coords).cost
				if y not in open_set or tentative_g_core < y.g:
					y.set_score(tentative_g_core, self.heuristic_cost_estimate(y, goal_node))
					y.parent = x
					if y not in open_set:
						heapq.heappush(open_heap, y)
						open_set.add(y)
					if y.g > max_cost:
						return Path(broken=True)
		return Path(broken=True)	  
