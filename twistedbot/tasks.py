
import math
from collections import deque


import config
import tools
import pathfinding
import logbot
import fops
from aabb import AABB
from gridspace import GridSpace


log = logbot.getlogger("TASKS")


class Status(object):
	not_finished = 10
	finished = 20
	broken = 30
	impossible = 40


class TaskBase(object):
	def __init__(self, manager, bot, callback_finished=None, **kwargs):
		self.manager = manager
		self.bot = bot
		self.callback_finished = callback_finished
		self.is_command = kwargs.get("is_command", False)
		self.world = bot.world
		self.grid = self.world.grid
		self.status = Status.not_finished
		self.child_status = None

	def __str__(self):
		return self.__class__.__name__

	def __unicode__(self):
		return self.__str__()

	def perform(self):
		self.check_situation()
		if self == self.manager.current_task:
			self.do()
		else:
			self.manager.run_current_task()

	def check_situation(self):
		if False: # TODO bot axis in water blocks
			self.manager.add_task(SwimToAirTask)


class NullTask(TaskBase):
	def __init__(self, *args, **kwargs):
		super(NullTask, self).__init__(*args, **kwargs)

	def do(self):
		self.bot.move()


class SwimToAirTask(TaskBase):
	#TODO
	def __init__(self, *args, **kwargs):
		super(SwimToAirTask, self).__init__(*args, **kwargs)


class LookAtPlayerTask(TaskBase):
	def __init__(self, *args, **kwargs):
		super(LookAtPlayerTask, self).__init__(*args)

	def do(self):
		self.bot.move()
		self._do()
		
	def _do(self):
		eid = self.bot.commander.eid
		if eid is None: return
		player = self.world.entities.get_entity(eid)
		if player is None: return
		p = player.position
		self.bot.turn_to((p[0], p[1] + config.PLAYER_EYELEVEL, p[2]), elevation=True)


class CirculateSignsTask(TaskBase):
	def __init__(self, *args, **kwargs):
		super(CirculateSignsTask, self).__init__(*args)
		self.next_waypoint = None
		self.group = kwargs.get("group", None)
		self.bot.world.navmesh.sign_waypoints.reset_group(self.group)

	def do(self):
		self.bot.move()
		self.handle_child_status()

	def handle_child_status(self):
		if self.child_status is None or self.child_status == Status.finished or self.child_status == Status.impossible:
			self._do()
		elif self.child_status == Status.broken:
			if self.next_waypoint is not None:
				self.manager.add_task(TravelToTask, coords=self.next_waypoint, check_sign=True)
		self.child_status = None

	def _do(self):
		if not self.bot.world.navmesh.sign_waypoints.has_name_group(self.group):
			self.bot.chat_message("no group named %s" % self.group)
			self.status = Status.finished
			return
		self.next_waypoint = self.bot.world.navmesh.sign_waypoints.get_groupnext_circulate(self.group)
		if self.next_waypoint is not None:
			self.manager.add_task(TravelToTask, coords=self.next_waypoint, check_sign=True)
		
					
class RotateSignsTask(TaskBase):
	def __init__(self, *args, **kwargs):
		super(RotateSignsTask, self).__init__(*args)
		self.next_waypoint = None
		self.group = kwargs.get("group", None)
		self.bot.world.navmesh.sign_waypoints.reset_group(self.group)

	def do(self):
		self.bot.move()
		self.handle_child_status()

	def handle_child_status(self):
		if self.child_status is None or self.child_status == Status.finished or self.child_status == Status.impossible:
			self._do()
		elif self.child_status == Status.broken:
			if self.next_waypoint is not None:
				self.manager.add_task(TravelToTask, coords=self.next_waypoint, check_sign=True)
		self.child_status = None

	def _do(self):
		if not self.bot.world.navmesh.sign_waypoints.has_name_group(self.group):
			self.bot.chat_message("no group named %s" % self.group)
			self.status = Status.finished
			return
		self.next_waypoint = self.bot.world.navmesh.sign_waypoints.get_groupnext(self.group)
		if self.next_waypoint is not None:
			self.manager.add_task(TravelToTask, coords=self.next_waypoint, check_sign=True)
		#else:
		#	self.status = Status.impossible


class GoToSignTask(TaskBase):
	def __init__(self, *args, **kwargs):
		super(GoToSignTask, self).__init__(*args)
		self.next_waypoint = None
		self.name = kwargs.get("name", "")

	def do(self):
		self.bot.move()
		self.handle_child_status()

	def handle_child_status(self):
		if self.child_status is None or self.child_status == Status.broken:
			self._do()
		else:
			self.status = self.child_status
		self.child_status = None

	def _do(self):
		self.next_waypoint = self.bot.world.navmesh.sign_waypoints.get_namepoint(self.name)
		if self.next_waypoint is not None:
			self.manager.add_task(TravelToTask, coords=self.next_waypoint, check_sign=True)
		#else:
		#	self.status = Status.impossible


class TravelToTask(TaskBase):
	def __init__(self, *args, **kwargs):
		super(TravelToTask, self).__init__(*args)
		self.coords = kwargs["coords"]
		self.check_sign = kwargs.get("check_sign", False)
		self.astar = pathfinding.AStar(self.bot.world.navmesh)
		self.calculate_path()
		self.current_step = None
		self.last_step = None

	def calculate_path(self):
		if self.bot.standing_on_block is not None:
			self.path = self.astar.find_path(self.bot.standing_on_block.coords, self.coords)
			self.path_ok = self.bot.world.navmesh.check_path(self.path)
		else:
			self.path_ok = False
		print 'path', self.path

	def do(self):
		self.bot.move()
		if self.bot.standing_on_block is None:
			return
		if self.path_ok == False:
			self.calculate_path()
			return
		elif self.path_ok is None:
			self.status = Status.impossible
			return
		self.handle_child_status()

	def handle_child_status(self):
		if self.child_status is None or self.child_status == Status.finished:
			self._do()
		elif self.child_status == Status.broken:
			self.calculate_path()
		self.child_status = None

	def _do(self):
		if self.current_step is not None:
			self.last_step = self.current_step
			if self.check_sign:
				self.manager.grid.check_sign((self.current_step[0], self.current_step[1] - 1, self.current_step[2]))
		if self.path.has_next():
			self.current_step = self.path.next_step().coords
			gs = GridSpace(self.manager.grid, coords=self.current_step)
			if not gs.can_stand_on:
				self.status = Status.broken
				return
			if self.last_step is not None:
				last_gs = GridSpace(self.manager.grid, coords=self.last_step)
				if not last_gs.can_go(gs):
					self.status = Status.broken
					return
			self.manager.add_task(MoveToTask, target_space=gs)
		else:
			self.status = Status.finished
			return


class MoveToTask(TaskBase):
	def __init__(self, *args, **kwargs):
		super(MoveToTask, self).__init__(*args)
		self.target_space = kwargs["target_space"]
		self.direction = (0,0)
		self.started = False
		self.was_at_target = False
		print 'at', self.bot.aabb
		print 'moveto', self.target_space.bb_stand

	def do(self):
		if self.status != Status.not_finished:
			raise Exception("this task is done")
		elif not self.target_space._can_stand_on():
			self.bot.move()
			self.status = Status.broken
		elif not self.started and self.bot.standing_on_block is None:
			self.bot.move()
		else:
			if not self.started:
				self.started = True
				gs = GridSpace(self.grid, block=self.bot.standing_on_block)
				if not gs.can_go(self.target_space, update_to_bb_stand=True):
					self.status = Status.broken
					self.bot.move()
					return
				print 'started to', self.target_space.bb_stand
			self.check_state()
			if self.status != Status.not_finished:
				return
			self._do()
			self.check_state(after_move=False)
			
	def check_state(self, after_move=True):
		if self.bot.aabb.horizontal_distance_to(self.target_space.bb_stand) > 2: #too far from the next step, better try again
			self.status = Status.broken
			if after_move: self.bot.move()
			return
		if self.bot.aabb.horizontal_distance_to(self.target_space.bb_stand) < self.bot.current_motion:
			self.was_at_target = True
			if self.bot.is_on_ladder:
				d = self.bot.aabb.min_y - self.target_space.bb_stand.min_y
				if fops.gte(d, 0) and fops.lt(d, 0.2):
					print 'finished vines'
					print self.bot.aabb
					self.status = Status.finished
					return
			elif self.bot.is_standing:
				print 'finished standing'
				print self.bot.aabb
				self.status = Status.finished
				if after_move: self.bot.move()
				return
		if self.started and fops.eq(self.bot.velocities[0], 0) and fops.eq(self.bot.velocities[2], 0):
			if self.bot.on_ground:
				gs = GridSpace(self.grid, bb=self.bot.aabb)
				if not gs.can_go(self.target_space):
					log.msg("I am stuck, let's try again? vels %s" % str(self.bot.velocities))
					self.status = Status.broken
					if after_move: self.bot.move()
					return

	def _do(self):
		if self.bot.is_on_ladder:
			elev = self.target_space.bb_stand.min_y - self.bot.aabb.min_y
			if fops.gt(elev, 0):
				self.jump()
			self.move()
		elif self.bot.is_standing:
			col_distance, col_bb = self.grid.min_collision_between(self.bot.aabb, self.target_space.bb_stand, horizontal=True, max_height=True)
			if col_distance is None:
				self.move()
			else:
				elev = self.target_space.bb_stand.min_y - self.bot.aabb.min_y
				if fops.lte(elev, 0):
					self.move()
				elif fops.gt(elev, 0) and fops.lte(elev, config.MAX_STEP_HEIGHT):
					if fops.lte(col_distance, self.bot.current_motion):
						self.jumpstep(config.MAX_STEP_HEIGHT)
						self.move()
					else:
						self.move()
				elif fops.gt(elev, config.MAX_STEP_HEIGHT) and fops.lt(elev, config.MAX_JUMP_HEIGHT):
					first_elev = col_bb.max_y - self.bot.aabb.min_y
					if fops.lt(first_elev, elev):
						if fops.lte(col_distance, self.bot.current_motion):
							self.jumpstep(config.MAX_STEP_HEIGHT)
						self.move()
					else:
						elev += 0.01
						ticks_to_col = col_distance / self.bot.current_motion
						ticks_to_jump = math.sqrt(2 * elev / config.G) * 20
						if ticks_to_col < ticks_to_jump:
							self.jump(elev)
						self.move()
				elif fops.gt(elev, config.MAX_JUMP_HEIGHT):
					self.status = Status.broken
					self.bot.move()
					return
				else:
					raise Exception("move elevation error %s with collision %s" % (elev, col_distance))
		else:
			self.move()

	def move(self, towards=None):
		if towards is None:
			towards = self.target_space.bb_stand
		direction = self.bot.aabb.horizontal_direction_to(towards)
		if not self.was_at_target:
			self.bot.turn_to(self.target_space.bb_stand.bottom_center)
		self.bot.move(direction=direction)

	def jump(self, height=0):
		#TODO calculate jump speed
		log.msg("JUMP")
		self.bot.set_jump()

	def jumpstep(self, h):
		log.msg("JUMPSTEP")
		self.bot.set_jumpstep(h)
