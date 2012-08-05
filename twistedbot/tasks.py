from collections import deque


import config
import tools
from aabb import AABB


class TaskBase(object):
	def __init__(self, manager, bot, callback_finished=None):
		self.manager = manager
		self.bot = bot
		self.callback_finished = callback_finished
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
	def __init__(self, *args, **kwargs):
		super(SwimToAirTask, self).__init__(*args, **kwargs)



class FallTask(TaskBase):
	def __init__(self, *args, **kwargs):
		super(FallTask, self).__init__(*args, **kwargs)
		self.callback_finished = self.bot.on_standing_ready

	def do(self):
		self._do()	

	def _do(self):
		if not self.bot.is_standing:
			gd, vel = tools.gravity_displ(self.bot.velocities[1])
			d = tools.directional_collision_distance(self.grid, self.bot.aabb, dy=gd)
			if d is None or d > abs(gd):
				self.bot.velocities[1] = vel
				self.bot.update_position(dy = gd, grounded=False)
			else:
				if gd < 0:
					self.bot.velocities[1] = 0
					self.bot.update_position(dy = -d, grounded=True)
					self.finished = True
				else:
					self.bot.update_position(dy = d, grounded=False)
					self.bot.velocities[1] = 0
		else:
			self.bot.velocities[1] = 0
			self.bot.update_position(grounded=True)
			self.finished = True

class LookAtPlayerTask(TaskBase):
	def __init__(self, *args, **kwargs):
		super(LookAtPlayerTask, self).__init__(*args)

	def do(self):
		if not self.bot.is_standing:
			self.manager.add_task(FallTask)
		else:
			self._do()
		
	def _do(self):
		eid = self.bot.commander.eid
		if eid is None: return
		player = self.world.entities.get_entity(eid)
		if player is None: return
		p = player.position
		self.bot.turn_to((p[0], p[1] + config.PLAYER_EYELEVEL, p[2]), elevation=True)
		
					

		

		
