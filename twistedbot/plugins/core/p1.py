

from twistedbot.plugins.base import PluginChatBase


class A(PluginChatBase):
	def do(self):
		print "do it"


plugin = A
