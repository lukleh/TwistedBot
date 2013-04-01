
from twistedbot.plugins.base import PluginChatBase
from twistedbot.behavior_tree import LookAtPlayer


class Look(PluginChatBase):
    @property
    def command_verb(self):
        return "look"

    @property
    def help(self):
        return "'look at me' bot keep looking at you"

    def command(self, sender, command, args):
        if args == ["at", "me"]:
            self.world.bot.behavior_tree.new_command(LookAtPlayer)
        else:
            self.world.chat.send_chat_message("look at what?")


plugin = Look
