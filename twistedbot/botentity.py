


from twisted.internet import reactor, defer


import config
import tools
import packets
import logbot
from statistics import Statistics
from aabb import AABB
from chat import Chat
from task_manager import TaskManager

log = logbot.getlogger("BOT_ENTITY")

class Commander(object):
	def __init__(self, name):
		self.name = name
		self.eid = None
		self.last_possition = None


class Bot(object):
	def __init__(self, name, commander_name):
		self.name = name
		self.commander = Commander(commander_name)
		self.world = None
		self.grid = None
		self.velocities = [0.0, 0.0, 0.0]
		self.chunks_ready = False
		self.taskmgr = TaskManager(self)
		self.stance = None
		self.pitch = None
		self.yaw = None
		self.grounded = None
		self.ready = False
		self.location_received = False
		self.spawn_point_received = False
		self.chat = Chat(self)
		self.stats = Statistics()
		self.startup()
		self.iterate_later()
	
	def connection_lost(self):
		self.protocol = None
		if self.location_received:
			self.location_received = False
			self.chunks_ready = False
			#TODO remove current chunks
			# erase all data that came from server

	def shutdown(self):
		""" save anything that needs to be saved and shutdown"""
		log.msg("Gracefully shutting down.......")
		if self.location_received:
			self.timer.stop()

	def startup(self):
		""" load anything that needs to be loaded """
		log.msg("Gracefully starting up.......")

	def set_location(self, kw):
		self.x = kw["x"]
		self.y = kw["y"]
		self.z = kw["z"]
		self.stance = kw["stance"]
		self.grounded = kw["grounded"]
		self.yaw = kw["yaw"]
		self.pitch = kw["pitch"]
		self.velocities = [0.0, 0.0, 0.0]
		if self.location_received == False:
			self.location_received = True
		
	@property
	def position(self):
		return (self.x, self.y, self.z)
		
	@property
	def position_grid(self):
		return (self.grid_x, self.grid_y, self.grid_z)

	@property
	def position_eyelevel(self):
		return (self.x, self.y_eyelevel, self.z)
		
	@property
	def x(self):
		return self._x
	
	@x.setter
	def x(self, v):
		self._x = v
		self._aabb = None
		
	@property
	def y(self):
		return self._y
		
	@property
	def y_eyelevel(self):
		return self.y + config.PLAYER_EYELEVEL
		
	@y.setter
	def y(self, v):
		self._y = v
		self.stance = v + config.PLAYER_EYELEVEL
		self._aabb = None

	@property
	def z(self):
		return self._z
		
	@z.setter
	def z(self, v):
		self._z = v
		self._aabb = None

	@property
	def grid_x(self):
		return tools.grid_shift(self.x)

	@property
	def grid_y(self):
		return int(self.y)

	@property
	def grid_z(self):
		return tools.grid_shift(self.z)

	@property
	def aabb(self):
		if self._aabb is None:
			self._aabb = AABB.from_player_coords(self.position)
		return self._aabb
				
	@property
	def is_standing(self):
		""" TODO test if it is possible to stand at the current position """
		if tools.standing_on_solidblock(self.grid, self.aabb, self.position_grid):
			return True
		else:
			return False

	def iterate_later(self):
		d = defer.Deferred()
		d.addCallback(self.iterate)
		d.addErrback(logbot.exit_on_error)
		reactor.callLater(config.TIME_STEP, d.callback, None)

	def iterate(self, last_time):
		if self.location_received == False:
			self.iterate_later()
			return
		if not self.ready:
			if not self.chunks_ready:
				self.chunks_ready = tools.chunks_complete(tools.aabb_in_chunks(self.world.grid, self.aabb))
			self.ready = self.chunks_ready and self.spawn_point_received
		if self.ready:
			self.taskmgr.run_current_task()
		self.send_location()
		self.iterate_later()

	def send_packet(self, name, payload):
		if self.protocol is not None:
			self.protocol.send_packet(name, payload)

	def send_location(self):
		self.send_packet("player position&look", {
							"position": packets.Container(x=self.x, y=self.y, z=self.z, stance=self.stance),
							"orientation": packets.Container(yaw=self.yaw, pitch=self.pitch),
							"grounded": packets.Container(grounded=self.grounded)})
			

	def turn_to(self, point, elevation=False):
		if point[0] == self.position.x and point[2] == self.position.z:
			return
		yaw, pitch = tools.yaw_pitch_between(point, self.position_eyelevel)
		if yaw is None or pitch is None:
			return
		self.yaw = yaw
		if elevation:
			self.pitch = pitch
		else:
			self.pitch = 0
	
	def update_position(self, dy=None, deltas=None, xyz=None, grounded=None):
		if grounded is not None:
			if self.grounded != grounded:
				self.grounded = grounded
			else:
				grounded = None
		if deltas is not None:
			self.x += deltas.x
			self.y += deltas.y
			self.z += deltas.z
		elif xyz is not None:
			self.x = xyz.x
			self.y = xyz.y
			self.z = xyz.z
		if deltas or grounded or xyz:
			log.msg("Updating position x %s y %s z %s stance %s grounded %s" % (self.x, self.y, self.z, self.stance, self.grounded))
			pass

