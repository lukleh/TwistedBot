


from twisted.internet import reactor

import config
import tools
from signwaypoints import SignWayPoints
from pathfinding import AStar
from gridspace import GridSpace

class MeshEdge(object):
	__slots__ = ('cost')
	def __init__(self, cost):
		self.cost = cost

		
class MeshNode(object):
	__slots__ = ('area_id')
	def __init__(self):
		self.area_id = None

		
class MeshGraph(object):
	def __init__(self):
		self.nodes = {}
		self.pred = {}
		self.succ = {}

	@property
	def count(self):
		return len(self.nodes)
		
	def has_node(self, crd):
		return crd in self.nodes
		
	def get_node(self, crd):
		return self.nodes[crd]
		
	def add_node(self, crd, node):
		if crd not in self.nodes:
			self.nodes[crd] = node
			self.pred[crd] = {}
			self.succ[crd] = {}
		else:
			raise Exception("node %s already present" % crd)
		
	def remove_node(self, crd):
		del self.node[crd]
		for n in self.succ[crd].keys():
			del self.pred[n][crd]
		del self.succ[crd]
		for n in self.pred[crd].keys():
			del self.succ[n][crd]
		del self.pred[crd]
				
	def has_edge(self, crd1, crd2):
		return crd2 in self.succ.get(crd1, {})
		
	def get_edge(self, crd1, crd2):
		return self.succ[crd1][crd2]

	def add_edge(self, crd1, crd2, edge):
		self.succ[crd1][crd2] = edge
		self.pred[crd2][crd1] = edge
		
	def remove_edge(self, crd1, crd2):
		del self.succ[crd1][crd2]
		del self.pred[crd2][crd1]


class ChunkBorders(object):
	def __init__(self):
		self.borders = {}

	def chunk_diff(self, c1, c2):
		return (c1[0] - c2[0], c1[1] - c2[1]) 

	def add(self, from_crd, to_crd):
		chunk_from = from_crd[0] >> 4, from_crd[2] >> 4
		chunk_to   = to_crd[0] >> 4, to_crd[2] >> 4
		ch_diff = self.chunk_diff(chunk_from, chunk_to)
		self.borders.setdefault(chunk_from, {}).setdefault(ch_diff, set()).add(to_crd)

	def remove(self, meta):
		chunk_from, chunk_to, crd  = meta
		ch_diff = self.chunk_diff(chunk_from, chunk_to)
		self.borders[chunk_from][ch_diff].remove(crd)

	def between(self, chunk_from, chunk_to):
		ch_diff = self.chunk_diff(chunk_from, chunk_to)
		for crd in self.borders.setdefault(chunk_from, {}).setdefault(ch_diff, set()):
			yield crd
		
		
class NavigationMesh(object):
	def __init__(self, world):
		self.world = world
		self.incomplete_nodes = {}
		self.graph = MeshGraph()
		self.chunk_borders = ChunkBorders()
		self.sign_waypoints = SignWayPoints(self)
		self.astar = AStar(self)

	#TODO proxy some graph methods, that would hide 'self.graph' from the rest of the code
		
	def check_node_resources(self, crd):
		pass

	def make_walk_steps(self):
		if not self.incomplete_nodes:
			return
		while self.incomplete_nodes:
			crd, meta = self.incomplete_nodes.popitem()
			self.make_walk_step(crd, meta)
			self.check_node_resources(crd)
		
	def make_walk_step(self, crd, meta):
		center_space = GridSpace(self.grid, crd)
		if "check" in meta:
			self.make_step(crd, center_space, meta["check"])
		else:
			for i, j in supplemental.adjacency:
				self.make_step(crd, center_space, (crd[0] + i, crd[1], crd[2] + j))

	def make_step(self, crd, center_space, tocrd):
		if not self.grid.get_chunk((crd[0] >> 4, crd[2] >> 4)).complete:
			self.chunk_borders.add(crd, tocrd)
			return
		possible_space = GridSpace(self.grid, tocrd).standing_at_space()
		if possible_space is None: 
			return
		side_crd = possible_space.as_crd
		if center_space.can_go(possible_space): 
			self.nodes.add_edge(crd, side_crd, MeshEdge(center_space.cost))
		if possible_space.can_go(center_space): 
			self.nodes.add_edge(side_crd, crd, MeshEdge(possible_space.cost))
		self.incomplete_nodes[side_crd] = {}

	def remove_node(self, crd):
		if self.has_node(crd):
			self.nodes.remove_node(crd)
			self.sign_waypoints.remove((crd[0], crd[1]+1, crd[2]))
			self.chunk_borders.remove(crd)
		
	def insert_node(self, n):
		if self.has_node(n):
			n.check_edges()
			return
		self.incomplete_nodes.add(n)
		self.nodes[n] = n
		x, y, z = n.coords
		for i in [-3, -2, -1]:
			coord = (x, y+i, z)
			if self.has_node(coord):
				gs = GridSpace(self.grid, coord)
				if gs.can_stand():
					gs.as_meshnode().check_edges()
				else:
					self.remove_node(coord)
		self.compute_do()
		
	def incomplete_on_chunk_border(self, chunk_from, chunk_to):
		for crd in self.chunk_borders.between(chunk_from, chunk_to):
			self.incomplete_nodes[crd] = {"border": (chunk_from, chunk_to, crd)}
		self.make_walk_steps()
			
	def block_change(self, old_block, new_block):
		return
		# TODO
		#stand_at = GridSpace(self.grid, new_block.coords).standing_at
		#if stand_at is not None:
		#	self.insert_node(MeshNode(stand_at))
			

