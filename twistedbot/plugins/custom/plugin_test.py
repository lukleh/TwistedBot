
from twistedbot.plugins.base import PluginEventHandlerBase


class PTest(PluginEventHandlerBase):
    def on_dummy(self):
        print "do it"


plugin = PTest
