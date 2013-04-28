
from twistedbot.plugins.base import PluginChatBase
from twistedbot.behavior_tree import FollowPlayer


class Follow(PluginChatBase):
    @property
    def command_verb(self):
        return "follow"

    @property
    def help(self):
        return "bot starts following you"

    def command(self, sender, command, args):
        self.world.bot.behavior_tree.new_command(FollowPlayer)


plugin = Follow
