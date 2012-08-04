
import re


import tasks
import logbot
from task_manager import TaskManager

log = logbot.getlogger("BOT_ENTITY")


class Chat(object):
	def __init__(self, bot):
		self.bot = bot
		self.clean_colors_re = re.compile(ur'\u00A7.', re.UNICODE)
		self.commander_re = re.compile(ur'<%s> .*' % self.bot.commander.name.lower(), re.UNICODE)
		self.wspace = re.compile(ur"\s+")

	def clean(self, orig_msg):
		msg = self.clean_colors_re.sub('', orig_msg)
		log.msg("Chat: %s" % msg)
		msg = msg.strip().lower()
		return msg
		
	def from_commander(self, msg):
		return self.commander_re.match(msg)
		
	def get_command(self, msg):
		msg = msg[msg.find(">")+2:]
		msg = self.chat_wspace.sub(" ", msg)
		log.msg("Possible command >%s<" % msg)
		return msg

	def process(self, msg):
		clean_msg = self.clean(msg)
		if self.from_commander(clean_msg):
			command = self.get_command(clean_msg)
			if command == "rotate":
				self.bot.taskmgr.add_task(tasks.RotateWaypoints)
			elif command == "look at me":
				self.bot.taskmgr.add_task(tasks.LookAtPlayer)
			elif command == "cancel":
				self.bot.taskmgr.add_task(tasks.NullTask)
			else:
				log.msg("Unknown command: %s" % clean_msg)
