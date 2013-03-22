
from twistedbot.plugins.base import PluginChatBase


class B(PluginChatBase):
	def do(self):
		print "do it"


plugin = B
