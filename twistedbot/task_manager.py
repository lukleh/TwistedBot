

import tasks


class TaskManager(object):
	def __init__(self, bot):
		self.bot = bot
		self.taskq = [tasks.LookAtPlayerTask(self, self.bot)]
		
	@property
	def current_task(self):
		return self.taskq[-1]

	def run_current_task(self):
		toptask = self.current_task
		toptask.perform()
		if toptask.finished:
			self.taskq.pop()
		
	def add_task(self, task):
		self.taskq.append(task(self, self.bot))
