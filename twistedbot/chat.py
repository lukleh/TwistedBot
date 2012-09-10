
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
		self.wspace_re = re.compile(ur"\s+")

	def clean(self, orig_msg):
		msg = self.clean_colors_re.sub('', orig_msg)
		log.msg("Chat: %s" % msg)
		msg = msg.strip().lower()
		return msg
		
	def from_commander(self, msg):
		return self.commander_re.match(msg)
		
	def get_command(self, msg):
		msg = msg[msg.find(">")+2:]
		msg = self.wspace_re.sub(" ", msg)
		log.msg("Possible command >%s<" % msg)
		return msg

	def get_verb(self, msg):
		return msg.partition(" ")[0]

	def get_subject(self, msg):
		return msg.partition(" ")[2]

	def process(self, msg):
		self.clean_msg = self.clean(msg)
		if self.from_commander(self.clean_msg):
			command = self.get_command(self.clean_msg)
			verb = self.get_verb(command)
			subject = self.get_subject(command)
			self.parse_command(verb, subject)

	def parse_command(self, verb, subject):
		if verb == "rotate":
			if subject:
				if self.bot.world.navmesh.sign_waypoints.has_name_group(subject):
					self.bot.taskmgr.add_command(tasks.RotateSignsTask, group=subject)
				else:
					self.bot.chat_message("don't have group %s" % subject)
			else:
				self.bot.chat_message("which sign group to rotate?")
		elif verb == "circulate":
			if subject:
				if self.bot.world.navmesh.sign_waypoints.has_name_group(subject):
					self.bot.taskmgr.add_command(tasks.CirculateSignsTask, group=subject)
				else:
					self.bot.chat_message("don't have group %s" % subject)
			else:
				self.bot.chat_message("which sign group to circulate?")
		elif verb == "go":
			if subject:
				if self.bot.world.navmesh.sign_waypoints.has_name_point(subject):
					self.bot.taskmgr.add_command(tasks.GoToSignTask, name=subject)
				else:
					self.bot.chat_message("don't have sign with name %s" % subject)
			else:
				self.bot.chat_message("go where?")
		elif verb == "look":
			if subject == "at me":
				self.bot.taskmgr.add_command(tasks.LookAtPlayerTask)
			else:
				self.bot.chat_message("look at what?")
		elif verb == "cancel":
			self.bot.taskmgr.cancel_task()
		else:
			log.msg("Unknown command: %s" % self.clean_msg)
