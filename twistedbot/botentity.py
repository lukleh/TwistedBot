

import math
from datetime import datetime


from twisted.internet import reactor, defer


import config
import tools
import packets
import logbot
import fops
import blocks
from statistics import Statistics
from aabb import AABB
from chat import Chat
from task_manager import TaskManager
from entity import EntityBot

log = logbot.getlogger("BOT_ENTITY")


class StatusDiff(object):
	def __init__(self, bot, world):
		self.bot = bot
		self.world = world
		self.packets_in = 0
		self.node_count = 0
		self.edge_count = 0
		self.logger = logbot.getlogger("BOT_ENTITY_STATUS")

	def log(self):
		if self.node_count != self.world.navmesh.graph.node_count:
			self.logger.msg("navmesh having %d nodes" % self.world.navmesh.graph.node_count)
			self.node_count = self.world.navmesh.graph.node_count
		if self.edge_count != self.world.navmesh.graph.edge_count:
			self.logger.msg("navmesh having %d edges" % self.world.navmesh.graph.edge_count)
			self.edge_count = self.world.navmesh.graph.edge_count
		#self.logger.msg("received %d packets" % self.packets_in)
		#self.logger.msg(self.bot.stats)


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
		self.world.bot = self
		self.grid = self.world.grid
		self.velocities = [0.0, 0.0, 0.0]
		self._x = 0
		self._y = 0
		self.ticks = 0
		self.chunks_ready = False
		self.taskmgr = TaskManager(self)
		self.stance = None
		self.pitch = None
		self.yaw = None
		self.on_ground = False
		self.ready = False
		self.location_received = False
		self.new_location_received = False
		self.spawn_point_received = False
		self.chat = Chat(self)
		self.stats = Statistics()
		self.startup()
		self.do_later(self.iterate, config.TIME_STEP)
		self.last_time = datetime.now()
		self.status_diff = StatusDiff(self, self.world)
		self.is_collided_horizontally = False
		self.is_in_water = False
		self.is_in_lava = False
	
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
		self.on_ground = kw["grounded"]
		self.yaw = kw["yaw"]
		self.pitch = kw["pitch"]
		self.velocities = [0.0, 0.0, 0.0]
		self.new_location_received = True
		if self.location_received == False:
			self.location_received = True
		if not self.in_complete_chunks:
			log.msg("Server send location into incomplete chunks")
			self.ready = False
		
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

	@property
	def z(self):
		return self._z
		
	@z.setter
	def z(self, v):
		self._z = v

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
		return AABB.from_player_coords(self.position)

	@aabb.setter
	def aabb(self, v):
		raise Exception('setting bot aabb')

	@property
	def in_complete_chunks(self):
		return self.world.grid.aabb_in_complete_chunks(self.aabb)

	def do_later(self, fn, delay=0):
		d = defer.Deferred()
		d.addCallback(fn)
		d.addErrback(logbot.exit_on_error)
		reactor.callLater(delay, d.callback, None)

	def every_n_ticks(self, n=100):
		return
		if self.ticks % n == 0:
			self.status_diff.log()

	def iterate(self, ignore):
		self.ticks += 1
		if self.location_received == False:
			self.do_later(self.iterate, config.TIME_STEP)
			return
		if not self.ready:
			self.ready = self.in_complete_chunks and self.spawn_point_received
		if self.ready:
			self.taskmgr.run_current_task()
		self.send_location()
		self.do_later(self.iterate, config.TIME_STEP)
		self.every_n_ticks()
		self.on_standing_ready()

	def send_packet(self, name, payload):
		if self.protocol is not None:
			self.protocol.send_packet(name, payload)

	def send_location(self):
		self.send_packet("player position&look", {
							"position": packets.Container(x=self.x, y=self.y, z=self.z, stance=self.stance),
							"orientation": packets.Container(yaw=self.yaw, pitch=self.pitch),
							"grounded": packets.Container(grounded=self.on_ground)})
			
	def chat_message(self, msg):
		self.send_packet("chat message", {"message": msg})

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

	def update_position(self, x, y, z, onground):
		self.x = x
		self.y = y
		self.z = z
		self.on_ground = onground

	def set_jump(self, custom_speed=config.SPEED_JUMP):
		self.velocities[1] = custom_speed

	def set_jumpstep(self, v):
		self.velocities[1] = 0
		aabbs = self.grid.aabbs_in(self.aabb.extend_to(0, v, 0))
		for bb in aabbs:
			v = self.aabb.calculate_axis_offset(bb, v, 1)
		ab = self.aabb.offset(dy=v)
		self.y = ab.posy

	def do_move(self):
		aabbs = self.grid.aabbs_in(self.aabb.extend_to(self.velocities[0], self.velocities[1], self.velocities[2]))
		b_bb = self.aabb
		dy = self.velocities[1]
		for bb in aabbs:
			dy = b_bb.calculate_axis_offset(bb, dy, 1)
		b_bb = b_bb.offset(dy=dy)
		dx = self.velocities[0]
		for bb in aabbs:
			dx = b_bb.calculate_axis_offset(bb, dx, 0)
		b_bb = b_bb.offset(dx=dx)
		dz = self.velocities[2]
		for bb in aabbs:
			dz = b_bb.calculate_axis_offset(bb, dz, 2)
		b_bb = b_bb.offset(dz=dz)
		onground = self.velocities[1] != dy and self.velocities[1] < 0
		self.is_collided_horizontally = dx != self.velocities[0] or dz != self.velocities[2]
		if self.velocities[0] != dx:
			self.velocities[0] = 0
		if self.velocities[1] != dy:
			self.velocities[1] = 0
		if self.velocities[2] != dz:
			self.velocities[2] = 0
		self.update_position(b_bb.posx, b_bb.min_y, b_bb.posz, onground)

	def clip_abs_velocities(self):
		out = list(self.velocities)
		for i in xrange(3):
			if abs(self.velocities[i]) < 0.005: # minecraft value 
				out[i] = 0
		return out

	def clip_ladder_velocities(self):
		out = list(self.velocities)
		if self.is_on_ladder:
			for i in xrange(3):
				if i == 1:
					if self.velocities[i] < -0.15:
						self.out[i] = -0.15
				elif abs(self.velocities[i]) > 0.15:
					self.out[i] = math.copysign(0.15, self.velocities[i])
		return out

	def handle_water_movement(self):
		is_in_water = False
		water_current = (0,0,0)
		bb = self.aabb.expand(-0.001, -0.4010000059604645, -0.001)
		max_y = bb.snap_to_grid.max_y + 1
		for blk in self.grid.blocks_in_aabb(bb):
			if isinstance(blk, blocks.BlockWater):
				wy = blk.y + 1 - blk.height_percent
				if max_y >= wy:
					is_in_water = True
					water_current = blk.velocity_to_add_to(water_current)
		if max(water_current) > 0:
			water_current = tools.normalize(water_current)
			wconst = 0.014
			water_current = (water_current[0] * wconst, water_current[1] * wconst, water_current[2] * wconst)	
		return is_in_water, water_current

	def handle_lava_movement(self):
		for blk in self.grid.blocks_in_aabb(self.aabb.expand(-0.10000000149011612, -0.4000000059604645, -0.10000000149011612)):
			if isinstance(blk, blocks.BlockLava):
				return True
		return False

	def move(self, direction=(0, 0)):
		self.velocities = self.clip_abs_velocities()
		self.is_in_water, water_current = self.handle_water_movement()
		self.is_in_lava = self.handle_lava_movement()
		if self.is_in_water:
			self.velocities = [self.velocities[0] + water_current [0], self.velocities[1] + water_current [1], self.velocities[2] + water_current [2]]
			orig_y = self.y
			self.update_directional_speed(direction, 0.02)
			self.do_move()
			self.velocities[0] *= 0.800000011920929
			self.velocities[1] *= 0.800000011920929
			self.velocities[2] *= 0.800000011920929
			self.velocities[1] -= 0.02
			if self.is_collided_horizontally and self.is_offset_in_liquid(self.velocities[0], self.velocities[1] + 0.6000000238418579 - self.y + orig_y, self.velocities[2]):
				self.velocities[1] = 0.30000001192092896
		elif self.is_in_lava:
			orig_y = self.y
			self.update_directional_speed(direction, 0.02)
			self.do_move()
			self.velocities[0] *= 0.5
			self.velocities[1] *= 0.5
			self.velocities[2] *= 0.5
			self.velocities[1] -= 0.02
			if self.is_collided_horizontally and self.is_offset_in_liquid(self.velocities[0], self.velocities[1] + 0.6000000238418579 - self.y + orig_y, self.velocities[2]):
				self.velocities[1] = 0.30000001192092896
		else:
			slowdown = self.current_slowdown
			self.update_directional_speed(direction, self.current_speed_factor)
			self.velocities = self.clip_ladder_velocities()
			self.do_move()
			if self.is_collided_horizontally and self.is_on_ladder:
				self.velocities[1] = 0.2
			self.velocities[1] -= config.BLOCK_FALL
			self.velocities[1] *= config.DRAG
			self.velocities[0] *= slowdown
			self.velocities[2] *= slowdown

	def directional_speed(self, direction, speedf):
		x, z = direction
		dx = x * speedf
		dz = z * speedf
		return dx, dz

	def update_directional_speed(self, direction, speedf):
		x, z = self.directional_speed(direction, speedf)
		self.velocities[0] += x
		self.velocities[2] += z

	@property
	def current_slowdown(self):
		slowdown = 0.91
		if self.on_ground:
			slowdown = 0.546
			block = self.grid.get_block(self.grid_x, self.grid_y - 1, self.grid_z)
			if block is not None:
				slowdown = block.slipperiness * 0.91
		return slowdown		

	@property
	def current_speed_factor(self):
		if self.on_ground:
			slowdown = self.current_slowdown
			modf = 0.16277136 / (slowdown * slowdown * slowdown)
			factor = config.SPEED_FACTOR * modf
		else:
			factor = config.JUMP_FACTOR
		return factor * 0.98

	@property
	def current_motion(self):
		#TODO
		# check if in water or lava -> factor = 0.2
		# else check ladder and clip if necessary
		velocities = self.clip_velocities()
		vx = velocities[0]
		vz = velocities[2]
		return math.hypot(vx, vz) + self.current_speed_factor
		
	@property	
	def is_on_ladder(self):
		x = tools.grid_shift(self.x)
		y = tools.grid_shift(self.y)
		z = tools.grid_shift(self.z)
		blk = self.grid.get_block(x, y, z)
		return blk.number == blocks.Ladders.number or blk.number == blocks.Vines.number

	def is_offset_in_liquid(self, dx, dy, dz):
		bb = self.aabb.offset(dx, dy, dz)
		if self.grid.aabb_collides(bb):
			return False
		else:
			return not self.grid.is_any_liquid(bb)

	def do_respawn(self, ignore):
		self.send_packet("client statuses", {"status": 1})
			
	def health_update(self, health, food, food_saturation):
		log.msg("current health %s food %s saturation %s" % (health, food, food_saturation))
		if health <= 0:
			self.on_death()
			
	def login_data(self, eid, level_type, mode, dimension, difficulty ,players):
		self.eid = eid
		self.world.entities.entities[eid] = EntityBot(eid=eid, x=0, y=0, z=0)
		
	def respawn_data(self, dimension, difficulty, mode, world_height, level_type):
		# TODO
		# ignore the details now
		# should clear the world(chunks, entities, etc.)
		# signs can stay self.grid.navmesh.reset_signs()
		pass
		
	def on_death(self):
		self.location_received = False
		self.spawn_point_received = False
		self.do_later(self.do_respawn, 1.0)
		#TODO self.world_erase()

	@property
	def standing_on_block(self):
		return self.grid.standing_on_solidblock(self.aabb)

	@property
	def is_standing(self):
		col_d, _ = self.grid.min_collision_between(self.aabb, self.aabb - (0, 1, 0))
		if col_d is None:
			stand = False
		else:
			stand = fops.eq(col_d, 0)
		return stand

	def on_standing_ready(self, ignore=None):
		if self.new_location_received:
			block = self.standing_on_block
			if block is None:
				return
			log.msg("Standing on block %s" % block)
			if not self.world.navmesh.graph.has_node(block.coords):
				self.world.navmesh.block_change(None, block)
			self.new_location_received = False
