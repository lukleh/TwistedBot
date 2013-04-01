
from twistedbot.plugins.base import PluginChatBase


class Help(PluginChatBase):
    @property
    def command_verb(self):
        return "help"

    @property
    def help(self):
        return "without argument shows aviable commands or help for specfic command"

    def command(self, sender, command, args):
        if not args:
            msg = ["%s [COMMAND]" % self.command_verb]
            msg.append(" ".join(self.world.eventregister.chat_commands.keys()))
            self.send_chat_message(msg)
        else:
            cmd = args[0]
            if cmd in self.world.eventregister.chat_commands:
                self.send_chat_message(self.world.eventregister.chat_commands[cmd].help)
            else:
                self.send_chat_message("unknown comamnd %s" % cmd)


plugin = Help
