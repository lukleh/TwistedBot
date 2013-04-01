
from twistedbot.plugins.base import PluginChatBase
from twistedbot.behavior_tree import CollectResources


class Collect(PluginChatBase):
    @property
    def command_verb(self):
        return "collect"

    @property
    def help(self):
        return "collect amount of item "

    def command(self, sender, command, args):
        if subject:
            itemstack, count = CollectResources.parse_parameters(subject)
            if itemstack is None:
                self.send_chat_message("collect what item?")
                return
            if count is None:
                self.send_chat_message("what amount of %s to collect?" % itemstack.name)
                return
            if count < 1:
                self.send_chat_message("amount has to be bigger that zero" % itemstack.name)
                return
            self.world.bot.behavior_tree.new_command(CollectResources, itemstack=itemstack)
        else:
            self.send_chat_message("collect what?")

#plugin = Collect