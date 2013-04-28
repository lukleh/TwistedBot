
from twistedbot.plugins.base import PluginChatBase
from twistedbot.behavior_tree import GoToSign


class Go(PluginChatBase):
    @property
    def command_verb(self):
        return "go"

    @property
    def help(self):
        return "go to specific sign, can be group name and order separated with space"

    def command(self, sender, command, args):
        if subject:
            self.world.bot.behavior_tree.new_command(GoToSign, sign_name=" ".join(subject))
        else:
            self.world.chat.send_chat_message("go where?")


plugin = Go
