

import logbot
import tasks


log = logbot.getlogger("TASK MANAGER")


class TaskManager(object):
	def __init__(self, bot):
		self.bot = bot
		self.grid = self.bot.world.grid
		self.taskq = []
		self.add_task(tasks.NullTask)
		self.add_task(tasks.LookAtPlayerTask)
		self.add_task(tasks.InitTask)
		
	@property
	def current_task(self):
		return self.taskq[-1]

	def run_current_task(self):
		toptask = self.current_task
		toptask.perform()
		if toptask.status != tasks.Status.not_finished:
			if toptask.callback_finished is not None:
				toptask.callback_finished(toptask)
			self.taskq.pop()
			self.current_task.child_status = toptask.status
		
	def add_task(self, task, *args, **kwargs):
		self.taskq.append(task(self, self.bot, *args, **kwargs))

	def add_command(self, task, *args, **kwargs):
		self.cancel_task()
		self.taskq.append(task(self, self.bot, *args, is_command=True, **kwargs))
		log.msg("Added command task %s" % self.current_task)

	def remove_top_task(self):
		if len(self.taskq) == 2:
			return
		t = self.taskq.pop()
		log.msg("Removed task %s, %d left" % (t, len(self.taskq)))

	def cancel_task(self):
		self.remove_top_task()
		while True:
			if self.taskq[-1].is_command:
				log.msg("Task %s is user command, not removing" % self.taskq[-1])
				break
			elif len(self.taskq) == 2:
				log.msg("Only basic task '%s' left in the queue, not removing" % self.taskq[-1])
				break
			else:
				self.remove_top_task()
				


