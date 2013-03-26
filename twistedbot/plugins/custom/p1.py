
from twistedbot.plugins.base import PluginChatBase


class B(PluginChatBase):
    @register
    def do(self):
        print "do it"


plugin = B
