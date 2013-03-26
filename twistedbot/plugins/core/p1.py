

from twistedbot.plugins.base import PluginChatBase


class A(PluginChatBase):
    @register
    def on_do(self):
        print "do it"


plugin = A
