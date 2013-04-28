
from twistedbot.plugins.base import PluginChatBase
from twistedbot.behavior_tree import ShowPlayerCursor


class Show(PluginChatBase):
    @property
    def command_verb(self):
        return "show"

    @property
    def help(self):
        return ["show [sign, inventory, cursor]",
                "sign - show waypoint, group or waypoints in group",
                "inventory - prints bot inventory",
                "cursor - prints block you are pointing at with your cursor"]

    def command(self, sender, command, args):
        if args:
            what = args[0]
            if what == "sign":
                sign_name = " ".join(args[1:])
                if not sign_name:
                    self.send_chat_message("show which sign?")
                    return
                sign = self.world.sign_waypoints.get_namepoint(sign_name)
                if sign is not None:
                    self.send_chat_message(str(sign))
                    return
                sign = self.world.sign_waypoints.get_name_from_group(sign_name)
                if sign is not None:
                    self.send_chat_message(str(sign))
                    return
                if not self.world.sign_waypoints.has_group(sign_name):
                    self.send_chat_message("no group named %s" % sign_name)
                    return
                for sign in self.world.sign_waypoints.ordered_sign_groups[sign_name].iter():
                    self.send_chat_message(str(sign))
            elif what == "inventory":
                content = [i for i in self.world.inventories.player_inventory.slot_items()]
                if content:
                    for slot_id, item in content:
                        self.send_chat_message("slot %d %s" % (slot_id, item))
                else:
                    self.send_chat_message("inventory is empty")
            elif what == "cursor":
                self.world.bot.behavior_tree.new_command(ShowPlayerCursor)
            else:
                self.send_chat_message("I can show sign, inventory and cursor")
        else:
            self.send_chat_message("show what?")


plugin = Show
