
from twistedbot.plugins.base import PluginChatBase


class Stop(PluginChatBase):
    @property
    def command_verb(self):
        return "stop"

    @property
    def help(self):
        return "cancel current activity"

    def command(self, sender, command, args):
        self.world.bot.behavior_tree.cancel_running()


plugin = Stop
