
import re


import tasks

class Chat(object):
	def __init__(self, bot):
		self.bot = bot
		self.clean_colors_re = re.compile(ur'\u00A7.', re.UNICODE)
		self.commander_re = re.compile(ur'<%s> .*' % self.bot.commander.name, re.UNICODE)
		self.wspace = re.compile(ur"\s+")

	def clean(self, orig_msg):
		msg = self.chat_clean_colors_re.sub('', orig_msg)
		log.msg("Chat: %s" % msg)
		msg = msg.strip().lower()
		if not self.commander_re.match(msg): return False, orig_msg 
		msg = msg[msg.find(">")+2:]
		msg = self.chat_wspace.sub(" ", msg)
		log.msg("Possible command >%s<" % msg)
		return True, msg

	def process(self, msg):
		proc, msg = self.clean(msg)
		if proc: 
			out = None
			if msg == "rotate":
				self.bot.new_task(tasks.RotateWaypoints)
			elif msg == "look at me":
				self.bot.new_task(tasks.LookAtPlayer)
			elif msg == "cancel":
				self.bot.new_task(tasks.NullTask)
			if out is not None:
				self.bot.send_packet("chat", {"message": str(out)})
