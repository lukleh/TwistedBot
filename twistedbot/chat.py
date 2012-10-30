
import re


import goals
import logbot

log = logbot.getlogger("BOT_ENTITY")


class Chat(object):
    def __init__(self, bot):
        self.bot = bot
        self.clean_colors_re = re.compile(ur'\u00A7.', re.UNICODE)
        self.commander_re = re.compile(
            ur'<%s> .*' % self.bot.commander.name.lower(), re.UNICODE)
        self.wspace_re = re.compile(ur"\s+")

    def clean(self, orig_msg):
        msg = self.clean_colors_re.sub('', orig_msg)
        log.msg("Chat: %s" % msg)
        msg = msg.strip().lower()
        return msg

    def from_commander(self, msg):
        return self.commander_re.match(msg)

    def get_command(self, msg):
        name_end = msg.find(">")
        if name_end > 0:
            msg = msg[name_end + 2:]
        msg = self.wspace_re.sub(" ", msg)
        log.msg("Possible command >%s<" % msg)
        return msg

    def get_verb(self, msg):
        return msg.partition(" ")[0]

    def get_subject(self, msg):
        return msg.partition(" ")[2]

    def process(self, msg):
        msg = self.clean(msg)
        if self.from_commander(msg):
            self.process_command(msg)

    def process_command(self, msg):
        command = self.get_command(msg)
        verb = self.get_verb(command)
        subject = self.get_subject(command)
        self.parse_command(verb, subject, msg)

    def parse_command(self, verb, subject, original):
        if verb == "rotate" or verb == "circulate":
            if subject:
                self.bot.goal_manager.command_goal(
                    goals.WalkSignsGoal, group=subject, type=verb)
            else:
                self.bot.chat_message("which sign group to %s?" % verb)
        elif verb == "go":
            if subject:
                self.bot.goal_manager.command_goal(
                    goals.GoToSignGoal, sign_name=subject)
            else:
                self.bot.chat_message("go where?")
        elif verb == "look":
            if subject == "at me":
                self.bot.goal_manager.command_goal(goals.LookAtPlayerGoal)
            else:
                self.bot.chat_message("look at what?")
        elif verb == "cancel":
            self.bot.goal_manager.cancel_goal()
        elif verb == "show":
            if subject:
                sign = self.bot.world.navgrid.sign_waypoints.get_namepoint(subject)
                if sign is not None:
                    self.bot.chat_message(str(sign))
                    return
                sign = self.bot.world.navgrid.sign_waypoints.get_name_from_group(subject)
                if sign is not None:
                    self.bot.chat_message(str(sign))
                    return
                if not self.bot.world.navgrid.sign_waypoints.has_group(subject):
                    self.bot.chat_message("no group named %s" % subject)
                    return
                for sign in self.bot.world.navgrid.sign_waypoints.ordered_sign_groups[subject].iter():
                    self.bot.chat_message(str(sign))
            else:
                self.bot.chat_message("show what?")
        else:
            log.msg("Unknown command: %s" % original)
