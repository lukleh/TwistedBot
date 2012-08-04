

from entities import Entities
from grid import Grid
from navigationmesh import NavigationMesh


class World(object):

	def __init__(self, host, port):
		self.server_host = host
		self.server_port = port
		self.bot = None
		self.entities = Entities(self)
		self.s_time = None
		self.players = {}
		self.grid = Grid(self)
		self.navmesh = NavigationMesh(self)
		self.grid.navmesh = self.navmesh
		self.navmesh.grid = self.grid

	def shutdown(self):
		""" actions to perform before shutdown """
		pass
