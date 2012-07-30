from collections import deque


import config
import tools
from aabb import AABB


class TaskBase(object):
	def __init__(self, manager, bot):
		self.manager = manager
		self.bot = bot
		self.world = bot.world
		self.grid = self.world.grid
		self.finished = False

	def perform(self):
		self.check_situation()
		if self == self.manager.current_task:
			self.do()
		else:
			self.manager.run_current_task()

	def check_situation(self):
		if False: # TODO bot axis in water blocks
			self.manager.add_task(SwimToAirTask)


class SwimToAirTask(TaskBase):
	#TODO
	def __init__(self, *args):
		super(SwimToAirTask, self).__init__(*args)



class FallTask(TaskBase):
	def __init__(self, *args):
		super(FallTask, self).__init__(*args)

	def do(self):
		self._do()	

	def _do(self):
		if not self.bot.is_standing:
			d, vel = tools.gravity_displ(self.bot.velocities[1])
			dcd, _ = tools.directional_collision_distance(self.grid, self.bot.aabb, dy=d)
			if dcd is None or dcd > d:
				self.velocities[1] = vel
				self.update_position(dy = d, grounded=False)
			else:
				self.update_position(dy = dcd, grounded=True)
				self.velocities[1] = 0
		else:
			self.velocities[1] = 0
			self.update_position(grounded=True)
			self.finished = True


class LookAtPlayerTask(TaskBase):
	def __init__(self, *args):
		super(LookAtPlayerTask, self).__init__(*args)

	def do(self):
		if not self.bot.is_standing:
			self.manager.add_task(FallTask)
		else:
			self._do()
		
	def _do(self):
		eid = self.bot.commander_eid
		if eid is None: return
		player = self.world.entities.get_entity(eid)
		if player is None: return
		p = player.position
		self.bot.turn_to((p[0], p[1] + config.PLAYER_EYELEVEL, p[2]), elevation=True)
		
					
class RotateWaypointsTask(TaskBase):
	def __init__(self, *args):
		super(RotateWaypointsTask, self).__init__(*args)
		self.next_waypoint = None
		self.walker = None
		log.msg("Rotating task")
		
	def do(self):
		if self.walker is None:
			self.next_point()
		else:
			if self.walker.broken:
				self.next_point(try_again=True)
			elif self.walker.done:
				self.next_point()
		if self.walker is not None:
			self.walker.walk()

	def next_point(self, try_again=False):
		if not self.bot.is_standing:
			self.bot.fall()
			return
		valid_again = try_again and self.bot.grid.navmesh.has_node(self.next_waypoint)
		if not (valid_again):
			self.next_waypoint = self.bot.grid.navmesh.sign_waypoints.get_next_waypoint()
			#TODO try to get waypoint that is on mesh, if cannot (or found the same), skip 
			if self.next_waypoint is not None:
				#log.msg("Next waypoint: new %s " % str(self.next_waypoint))
				pass
		if self.next_waypoint is not None:
			if self.bot.standing_on_block(after_fall=True).coords == self.next_waypoint:
				self.walker = None
				return
			self.walker = Walker(self.bot, self.bot.standing_on_block(after_fall=True).coords, self.next_waypoint)
			if valid_again:
				#log.msg("Next waypoint: last %s " % str(self.next_waypoint))
				pass
		else:
			self.walker = None

		
class Walker(object):
	def __init__(self, bot, start, goal):
		self.bot = bot
		self.start = start
		self.goal = goal
		self.path = self.bot.grid.navmesh.astar.find_path(start, goal)
		self.plan = None
		self.broken = self.path.broken
		self.done = False
		#log.msg("Walker init, path broken %s" % self.path.broken)
		
	def walk(self):
		if self.broken or self.done:
			return
		if self.plan is None:
			self.plan = Plan(self.path, self.bot)
		self.move()
		
	def move(self):
		if self.plan.broken or self.plan.done:
			return
		step = self.plan.next_step()
		if self.plan.done:
			self.done = self.plan.done
			return
		if self.plan.broken:
			self.broken = self.plan.broken
			return
		if step["grounded"]:
			if not self.bot.standing_at(step["xyz"]):
				log.msg("not standing at %s" % str(step["xyz"]))
				self.broken = True
				return
		else:
			bb = AABB.from_player_coords(step["xyz"])
			col, col_bb, col_block = self.bot.grid.collision_with(bb)
			if col:
				log.msg("Collision on path between", bb, col_bb, col_block)
				self.broken = True
				return
		self.bot.update_position(xyz=step["xyz"], grounded=step["grounded"])
		
		
class Plan(object):
	def __init__(self, path, bot):
		self.path = path
		self.bot = bot
		self.steps = deque()
		self.broken = False
		self.done = False
		
	def next_step(self):
		if self.steps:
			step = self.steps.pop(0)
			return step
		else:
			self.make_plan()
			if self.steps:
				return self.next_step()
			else:
				self.broken = True
		
	def distance_between(self, pbb):
		if abs(self.nx) > abs(self.nz):
			axis = 0
		else:
			axis = 2
		ds = None
		for bb in self.bend.grid_bounding_boxes:
			d = pbb.distance_from(bb, on_axis=axis)
			if ds is None or d < ds:
				ds = d
		return ds
		
	def make_plan(self):
		self.next_node = self.path.next_step()
		if self.path.done:
			self.done = True
			return
		block = self.bot.grid.get_block_coords(self.next_node.coords)
		if not self.bot.grid.can_stand_on(block):
			self.broken = True
			return
		self.next_node.load_block(block)	
		self.bot.turn_to(self.next_node.path_point)
		self.start = self.bot.position
		self.end = self.next_node.path_point
		
		dist = self.bot.position.distance_xz_from(self.end)
		if dist <= config.DISTANCE_STEP:
			self.steps = [{"xyz": self.end, "grounded": True}]
			return
		self.maneuver(dist)
			
	def maneuver(self, dist):
		bstart = self.bot.standing_on_block()
		self.bend = self.bot.grid.get_block_coords(self.next_node.coords)
		elev = self.bend.grid_height - bstart.grid_height
		if abs(elev) < config.FOAT_EPSILON:
			elev = 0
		self.nx, self.nz = self.bot.position.norm_xz_direction(self.next_node.path_point)
		self.y = self.bot.y
		self.speed_y = 0
		if elev == 0:
			nsteps = int(dist / config.DISTANCE_STEP)
			self.horizontal(self.start, nsteps)
		elif elev > 0:
			self.jump_on(elev)
		else:
			self.fall_to(abs(elev))
		self.steps.append({"xyz": self.end, "grounded": True})
			
	def horizontal(self, start, nsteps):
		dx = self.nx * config.SPEED_WALK * config.TIME_STEP
		dz = self.nz * config.SPEED_WALK * config.TIME_STEP
		x = start[0]
		z = start[2]
		for s in xrange(1, int(nsteps)):
			self.steps.append({"xyz": (x + s*dx, self.y, z + s*dz), "grounded": True})
		
	def jump_on(self, elev):
		#phase 1 - jump
		d = self.distance_between(self.bot.aabb)
		d -= 0.01
		tjt = tools.time_jump_to(elev)
		if d < 0:
			speed_xz = 0
		else:
			speed_xz = d / tjt
		nsteps = tjt / config.TIME_STEP
		nsteps = int(nsteps) + 2
		self.speed_y = config.SPEED_JUMP
		self.make_jump(nsteps, speed_xz, self.start)
		#phase 2 - landing
		last = self.steps[-1]["xyz"]
		d = self.next_node.path_point.distance_xz_from(last)
		tjo = tools.time_jump_onto(elev)
		if (tjo - tjt) > (d / config.SPEED_WALK):
			t = tjo - tjt
			speed_xz = d / t
		else:
			t = d / config.SPEED_WALK
			speed_xz = config.SPEED_WALK
		nsteps = t / config.TIME_STEP
		nsteps = int(nsteps) + 1
		self.make_fall(nsteps, speed_xz, self.bend.grid_height, last)
		
	def fall_to(self, decl):
		#phase 1 - go to the edge
		d = self.distance_between(self.bot.aabb)
		d += 0.6
		t = d / config.SPEED_WALK
		nsteps = t / config.TIME_STEP
		nsteps = int(nsteps) + 2
		self.horizontal(self.start, nsteps)
		self.steps[-1]["grounded"] = False
		#phase 2 - fall
		last = self.steps[-1]["xyz"]
		d = last.distance_xz_from(self.next_node.path_point)
		t = tools.time_fall_to(decl)
		speed_xz = d / t
		nsteps = t / config.TIME_STEP
		nsteps = int(nsteps) + 1
		self.speed_y = 0
		self.make_fall(nsteps, speed_xz, self.bend.grid_height, last)
		
	def make_jump(self, nsteps, speed_xz, last):
		dx = self.nx * speed_xz * config.TIME_STEP
		dz = self.nz * speed_xz * config.TIME_STEP
		for s in xrange(1, nsteps):
			self.y += config.TIME_STEP * self.speed_y
			self.speed_y += config.G * config.TIME_STEP
			self.y += 0.5 * config.G * pow(config.TIME_STEP, 2)
			self.steps.append({"xyz": (last[0] + s*dx, self.y, last[2] + s*dz), "grounded": False})
			
	def make_fall(self, nsteps, speed_xz, heigh, last):
		dx = self.nx * speed_xz * config.TIME_STEP
		dz = self.nz * speed_xz * config.TIME_STEP
		gr = False
		for s in xrange(1, nsteps):
			if not gr:
				self.y += config.TIME_STEP * self.speed_y
				self.speed_y += config.G * config.TIME_STEP
				self.y += 0.5 * config.G * pow(config.TIME_STEP, 2)
			if self.y > heigh:
				gr = False
			else:
				gr = True
				#gy = self.bend.grid_height + config.MIN_DISTANCE
			self.steps.append({"xyz": (last[0] + s*dx, self.y, last[2] + s*dz), "grounded": gr})
			
	
		
		

		

		
