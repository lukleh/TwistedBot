
from twistedbot.plugins.base import PluginChatBase
from twistedbot.behavior_tree import InventorySelectActive


class Debug(PluginChatBase):
    @property
    def command_verb(self):
        return "debug"

    @property
    def help(self):
        return "help for debug"

    def command(self, sender, command, args):
        if subject:
            what = subject[0]
            if what == "inventoryselect":
                item_name = " ".join(subject[1:])
                if not item_name:
                    self.send_chat_message("specify item")
                    return
                itemstack = InventorySelectActive.parse_parameters(item_name)
                if itemstack is not None:
                    self.world.bot.behavior_tree.new_command(InventorySelectActive, itemstack=itemstack)
                else:
                    self.send_chat_message("unknown item %s" % item_name)
            else:
                self.send_chat_message("unknown subject")
        else:
            self.send_chat_message("debug what?")


plugin = Debug
