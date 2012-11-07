
import re


import behaviours
import logbot

log = logbot.getlogger("BOT_ENTITY")


class Chat(object):
    def __init__(self, world):
        self.world = world
        self.clean_colors_re = re.compile(ur'\u00A7.', re.UNICODE)
        self.commander_re = re.compile(
            ur'<%s> .*' % self.world.commander.name.lower(), re.UNICODE)
        self.wspace_re = re.compile(ur"\s+")

    def clean(self, orig_msg):
        msg = self.clean_colors_re.sub('', orig_msg)
        log.msg("Chat: %s" % msg)
        msg = msg.strip().lower()
        return msg

    def from_commander(self, msg):
        return self.commander_re.match(msg)

    def get_command(self, msg):
        msg = msg[msg.find(">") + 2:]
        msg = self.wspace_re.sub(" ", msg)
        return msg

    def get_verb(self, msg):
        return msg.partition(" ")[0]

    def get_subject(self, msg):
        return msg.partition(" ")[2]

    def process(self, msg):
        msg = self.clean(msg)
        if self.from_commander(msg):
            command = self.get_command(msg)
            self.process_command(command, msg)

    def process_command(self, command, msg=None):
        if msg is None:
            msg = command
        log.msg("Possible command >%s<" % command)
        verb = self.get_verb(command)
        subject = self.get_subject(command)
        self.parse_command(verb, subject, msg)

    def parse_command(self, verb, subject, original):
        if verb == "rotate" or verb == "circulate":
            if subject:
                self.world.behaviour_manager.command(
                    behaviours.WalkSignsBehaviour, group=subject, type=verb)
            else:
                self.world.chat_message("which sign group to %s?" % verb)
        elif verb == "go":
            if subject:
                self.world.behaviour_manager.command(
                    behaviours.GoToSignBehaviour, sign_name=subject)
            else:
                self.world.chat_message("go where?")
        elif verb == "look":
            if subject == "at me":
                self.world.behaviour_manager.command(behaviours.LookAtPlayerBehaviour)
            else:
                self.world.chat_message("look at what?")
        elif verb == "cancel":
            self.world.behaviour_manager.cancel_running()
        elif verb == "show":
            if subject:
                sign = self.world.navgrid.sign_waypoints.get_namepoint(subject)
                if sign is not None:
                    self.world.chat_message(str(sign))
                    return
                sign = self.world.navgrid.sign_waypoints.get_name_from_group(subject)
                if sign is not None:
                    self.world.chat_message(str(sign))
                    return
                if not self.world.navgrid.sign_waypoints.has_group(subject):
                    self.world.chat_message("no group named %s" % subject)
                    return
                for sign in self.world.navgrid.sign_waypoints.ordered_sign_groups[subject].iter():
                    self.world.chat_message(str(sign))
            else:
                self.world.chat_message("show what?")
        else:
            log.msg("Unknown command: %s" % original)
