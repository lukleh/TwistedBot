
from collections import defaultdict, OrderedDict

from twisted.internet import reactor
from twisted.internet.task import cooperate

import config
import tools
import logbot
import blocks
from signwaypoints import SignWayPoints
from pathfinding import AStar
from gridspace import GridSpace



log = logbot.getlogger("NAVMESH")


class ChunkBorders(object):
	def __init__(self):
		self.borders = defaultdict(lambda: defaultdict(set))

	def chunk_diff(self, c1, c2):
		return (c1[0] - c2[0], c1[1] - c2[1]) 

	def add(self, from_crd, to_crd):
		chunk_from = from_crd[0] >> 4, from_crd[2] >> 4
		chunk_to   = to_crd[0] >> 4, to_crd[2] >> 4
		ch_diff = self.chunk_diff(chunk_from, chunk_to)
		self.borders[chunk_from][ch_diff].add(to_crd)

	def remove(self, crd):
		chunk_from = crd[0] >> 4, crd[2] >> 4
		for i in [-1, 1]:
			for j in [-1, 1]:
				try:
					self.borders[chunk_from][(i,j)].remove(crd)
				except KeyError:
					pass

	def between(self, chunk_from, chunk_to):
		ch_diff = self.chunk_diff(chunk_from, chunk_to)
		for crd in self.borders[chunk_from][ch_diff]:
			yield crd


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
	def node_count(self):
		return len(self.nodes)

	@property
	def edge_count(self):
		return len(self.pred) + len(self.succ)
		
	def has_node(self, crd):
		return crd in self.nodes
		
	def get_node(self, crd):
		return self.nodes[crd]
		
	def add_node(self, crd, miny=None):
		if crd not in self.nodes:
			self.nodes[crd] = miny
			self.pred[crd] = {}
			self.succ[crd] = {}
		
	def remove_node(self, crd):
		affected = set()
		del self.nodes[crd]
		for n in self.succ[crd].keys():
			del self.pred[n][crd]
			affected.add(n)
		del self.succ[crd]
		for n in self.pred[crd].keys():
			del self.succ[n][crd]
			affected.add(n)
		del self.pred[crd]
		return affected
				
	def has_edge(self, crd1, crd2):
		return crd2 in self.succ.get(crd1, {})
		
	def get_edge(self, crd1, crd2):
		try:
			return self.succ[crd1][crd2]
		except KeyError:
			return None

	def add_edge(self, crd1, crd2, cost):
		self.succ[crd1][crd2] = cost
		self.pred[crd2][crd1] = cost
		
	def remove_edge(self, crd1, crd2):
		if self.has_edge(crd1, crd2):
			del self.succ[crd1][crd2]
			del self.pred[crd2][crd1]

	def get_succ(self, crd):
		return self.succ[crd].items()

		
class NavigationMesh(object):
	def __init__(self, world):
		self.world = world
		self.incomplete_nodes = OrderedDict()
		self.graph = MeshGraph()
		self.chunk_borders = ChunkBorders()
		self.astar = AStar(self)
		self.reset_signs()

	def reset_signs(self):
		self.sign_waypoints = SignWayPoints(self)

	def check_node_resources(self, crd):
		pass

	def compute(self, node):
		if self.incomplete_nodes:
			self.incomplete_nodes[node] = node
		else:
			self.incomplete_nodes[node] = node
			cootask = cooperate(self.do_incomplete_nodes())
			d = cootask.whenDone()
			d.addErrback(logbot.exit_on_error)
			#log.msg("New compute cooperate")

	def do_incomplete_nodes(self):
		while self.incomplete_nodes:
			crd = self.incomplete_nodes.popitem(last=False)[1]
			self.do_incomplete_node(crd)
			self.check_node_resources(crd)
			yield None
		
	def do_incomplete_node(self, crd):
		center_space = GridSpace(self.grid, coords=crd)
		if not center_space.can_stand_on:
			self.delete_node(crd)
			return
		elif not self.graph.has_node(crd):
			self.graph.add_node(crd, miny=center_space.bb_stand.min_y)
		for i, j in tools.adjacency:
			tocrd = (crd[0] + i, crd[1], crd[2] + j)
			if not self.grid.chunk_complete_at((tocrd[0] >> 4, tocrd[2] >> 4)):
				self.chunk_borders.add(center_space.coords, tocrd)
				continue
			if i != 0 and j != 0:
				if not self.grid.chunk_complete_at((crd[0] >> 4, (crd[2] + j) >> 4)) or not self.grid.chunk_complete_at(((crd[0] + i) >> 4, crd[2] >> 4)):
					continue
			gs = GridSpace(self.grid, coords=tocrd)
			if gs.can_stand_on:
				self.make_node(center_space, gs)
				continue
			gs = GridSpace(self.grid, coords=(crd[0] + i, crd[1] + 1, crd[2] + j))
			if gs.can_stand_on:
				self.make_node(center_space, gs)
				continue
			gs = GridSpace(self.grid, coords=(crd[0] + i, crd[1] + 2, crd[2] + j))
			if gs.can_stand_on:
				self.make_node(center_space, gs)
				continue
			for k in [-1, -2, -3]:
				gs = GridSpace(self.grid, coords=(crd[0] + i, crd[1] + k, crd[2] + j))
				if gs.can_stand_on:
					self.make_node(center_space, gs)
					break
		for k in [-1, 1, 2]: # climb, descend
			gs = GridSpace(self.grid, coords=(crd[0], crd[1] + k, crd[2]))
			if gs.can_stand_on:
				self.make_node(center_space, gs)

	def make_node(self, center_space, possible_space):
		is_new = False
		if not self.graph.has_node(possible_space.coords):
			self.compute(possible_space.coords)
			is_new = True
		self.graph.add_node(possible_space.coords, miny=possible_space.bb_stand.min_y)
		if center_space.can_go(possible_space):
			self.graph.add_edge(center_space.coords, possible_space.coords, center_space.edge_cost)
		else:
			self.graph.remove_edge(center_space.coords, possible_space.coords)
		if not is_new:
			if possible_space.can_go(center_space):
				self.graph.add_edge(possible_space.coords, center_space.coords, possible_space.edge_cost)
			else:
				self.graph.remove_edge(possible_space.coords, center_space.coords)

	def check_path(self, path):
		if path is None:
			return None
		last_one = None
		ok = True
		for p in path:
			gs = GridSpace(self.grid, coords=p)
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

	def check_edges_of(self, nodes):
		spaces = []
		for n in nodes:
			gs = GridSpace(self.grid, coords=n)
			if not gs.can_stand_on:
				self.delete_node(n)
			else:
				spaces.append(gs)
		for s1 in spaces:
			for s2 in spaces:
				if s1 == s2:
					continue
				if self.graph.has_edge(s1.coords, s2.coords):
					if not s1.can_go(s2):
						self.graph.remove_edge(s1.coords, s2.coords)

	def delete_node(self, crd):
		if self.graph.has_node(crd):
			affected = self.graph.remove_node(crd)
			for aff in affected:
				self.compute(aff)
			self.check_edges_of(affected)
			self.chunk_borders.remove(crd)
		try:
			del self.incomplete_nodes[crd]
		except KeyError:
			pass
		
	def insert_node(self, coords, gspace=None):
		self.compute(coords)
		self.graph.add_node(coords, miny=gspace.bb_stand.min_y)
		
		
	def incomplete_on_chunk_border(self, chunk_from, chunk_to):
		for crd in self.chunk_borders.between(chunk_from, chunk_to):
			self.compute(crd)
			
	def block_change(self, old_block, new_block):
		# log.msg("block change %s %s %s => %s %s" % \
		# 	(new_block.coords, old_block.name if old_block is not None else "none", tools.meta2str(old_block.meta) if old_block is not None else "none", \
		# 		new_block.name, tools.meta2str(new_block.meta)))
		coords = new_block.coords
		gs = GridSpace(self.grid, coords=coords)
		if gs.can_stand_on:
			self.insert_node(gs.coords, gspace=gs)
		else:
			self.delete_node(gs.coords)
		for i in [-2, -1, 1, 2]:
			crd = (coords[0], coords[1] - i, coords[2])
			gs = GridSpace(self.grid, crd)
			if gs.can_stand_on:
				self.insert_node(gs.coords, gspace=gs)
			else:
				self.delete_node(gs.coords)

