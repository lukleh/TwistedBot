
import re


import goals
import logbot

log = logbot.getlogger("BOT_ENTITY")


class Chat(object):
    def __init__(self, bot):
        self.bot = bot
        self.clean_colors_re = re.compile(ur'\u00A7.', re.UNICODE)
        self.commander_re = re.compile(ur'<%s> .*' % self.bot.commander.name.lower(), re.UNICODE)
        self.wspace_re = re.compile(ur"\s+")

    def clean(self, orig_msg):
        msg = self.clean_colors_re.sub('', orig_msg)
        log.msg("Chat: %s" % msg)
        msg = msg.strip().lower()
        return msg
        
    def from_commander(self, msg):
        return self.commander_re.match(msg)
        
    def get_command(self, msg):
        msg = msg[msg.find(">")+2:]
        msg = self.wspace_re.sub(" ", msg)
        log.msg("Possible command >%s<" % msg)
        return msg

    def get_verb(self, msg):
        return msg.partition(" ")[0]

    def get_subject(self, msg):
        return msg.partition(" ")[2]

    def process(self, msg):
        self.clean_msg = self.clean(msg)
        if self.from_commander(self.clean_msg):
            command = self.get_command(self.clean_msg)
            verb = self.get_verb(command)
            subject = self.get_subject(command)
            self.parse_command(verb, subject)

    def parse_command(self, verb, subject):
        if verb == "rotate" or verb == "circulate":
            if subject:
                self.bot.goal_manager.command_goal(goals.WalkSignsGoal, group=subject, type=verb)
            else:
                self.bot.chat_message("which sign group to %s?" % verb)
        elif verb == "go":
            if subject:
                self.bot.goal_manager.command_goal(goals.GoToSignGoal, sign_name=subject)
            else:
                self.bot.chat_message("go where?")
        elif verb == "look":
            if subject == "at me":
                self.bot.goal_manager.command_goal(goals.LookAtPlayerGoal)
            else:
                self.bot.chat_message("look at what?")
        elif verb == "cancel":
            self.bot.goal_manager.cancel_goal()
        else:
            log.msg("Unknown command: %s" % self.clean_msg)
