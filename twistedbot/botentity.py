


from twisted.internet import reactor, defer


import config
import tools
import packets
import logbot
from statistics import Statistics
from aabb import AABB
from chat import Chat
from task_manager import TaskManager
from entity import EntityBot

log = logbot.getlogger("BOT_ENTITY")

class Commander(object):
	def __init__(self, name):
		self.name = name
		self.eid = None
		self.last_possition = None


class Bot(object):
	def __init__(self, world, name, commander_name):
		self.world = world
		self.name = name
		self.commander = Commander(commander_name)
		self.eid = None
		world.bot = self
		self.grid = self.world.grid
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
		self.do_later(self.iterate, config.TIME_STEP)
	
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
		d = tools.directional_collision_distance(self.grid, self.aabb, dy=-1)
		if d is None or d > 0:
			return False
		else:
			return True

	def do_later(self, fn, delay):
		d = defer.Deferred()
		d.addCallback(fn)
		d.addErrback(logbot.exit_on_error)
		reactor.callLater(delay, d.callback, None)

	def iterate(self, ignore):
		if self.location_received == False:
			self.do_later(self.iterate, config.TIME_STEP)
			return
		if not self.ready:
			if not self.chunks_ready:
				self.chunks_ready = tools.chunks_complete(tools.aabb_in_chunks(self.world.grid, self.aabb))
			self.ready = self.chunks_ready and self.spawn_point_received
		if self.ready:
			self.taskmgr.run_current_task()
		self.send_location()
		self.do_later(self.iterate, config.TIME_STEP)

	def send_packet(self, name, payload):
		if self.protocol is not None:
			self.protocol.send_packet(name, payload)

	def send_location(self):
		#log.msg("position %s" % str(self.position))
		self.send_packet("player position&look", {
							"position": packets.Container(x=self.x, y=self.y, z=self.z, stance=self.stance),
							"orientation": packets.Container(yaw=self.yaw, pitch=self.pitch),
							"grounded": packets.Container(grounded=self.grounded)})
			

	def turn_to(self, point, elevation=False):
		if point[0] == self.x and point[2] == self.z:
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
		elif dy is not None:
			self.y += dy
		if deltas or grounded or xyz or dy:
			log.msg("Updating position x %s y %s z %s stance %s grounded %s" % (self.x, self.y, self.z, self.stance, self.grounded))
			pass
			
	def do_respawn(self, ignore):
		self.send_packet("client statuses", {"status": 1})
			
	def health_update(self, health, food, food_saturation):
		if health <= 0:
			self.on_death()
			
	def login_data(self, eid, level_type, mode, dimension, difficulty ,players):
		self.eid = eid
		self.world.entities.entities[eid] = EntityBot(eid=eid, x=0, y=0, z=0)
		
	def on_death(self):
		self.location_received = False
		self.spawn_point_received = False
		self.do_later(self.do_respawn, 1.0)
		#self.world_erase()

	def on_standing_ready(self, from_task):
		block = tools.standing_on_solidblock(self.grid, self.aabb, self.position_grid)
		log.msg("Standing on block %s" % block)
		self.world.navmesh.block_change(block, None)