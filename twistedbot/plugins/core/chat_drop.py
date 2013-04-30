
from twistedbot.plugins.base import PluginChatBase
from twistedbot.behavior_tree import DropInventory


class Drop(PluginChatBase):
    @property
    def command_verb(self):
        return "drop"

    @property
    def help(self):
        return "'drop inventory' drops all items from inventory"

    def command(self, sender, command, args):
        if args:
            what = args[0]
            if what == "inventory":
                self.world.bot.behavior_tree.new_command(DropInventory)
            else:
                self.send_chat_message("unknown subject")
        else:
            self.send_chat_message("drop what?")


plugin = Drop
