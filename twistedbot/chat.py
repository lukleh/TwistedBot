
import re
from collections import deque

import behaviours
import logbot

log = logbot.getlogger("CHAT")


class Chat(object):
    def __init__(self, world):
        self.world = world
        self.clean_colors_re = re.compile(ur'\u00A7.', re.UNICODE)
        self.commander_re = re.compile(
            ur'<%s> .*' % self.world.commander.name.lower(), re.UNICODE)
        self.wspace_re = re.compile(ur"\s+")
        self.chat_spam_treshold_count = 0
        self.chat_spam_treshold_buffer = deque()

    def tick(self):
        if self.chat_spam_treshold_count > 0:
            self.chat_spam_treshold_count -= 1
        if self.chat_spam_treshold_count <= 160 and self.chat_spam_treshold_buffer:
            self.send_chat_message(self.chat_spam_treshold_buffer.popleft())

    def send_chat_message(self, msg):
        self.chat_spam_treshold_count += 20
        if self.chat_spam_treshold_count > 180:
            self.chat_spam_treshold_buffer.append(msg)
            return
        log.msg(msg)
        self.world.send_packet("chat message", {"message": msg})

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

    def on_chat_message(self, msg):
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
                self.world.bot.behaviour_manager.command(
                    behaviours.WalkSignsBehaviour, group=subject, type=verb)
            else:
                self.send_chat_message("which sign group to %s?" % verb)
        elif verb == "go":
            if subject:
                self.world.bot.behaviour_manager.command(behaviours.GoToSignBehaviour, sign_name=subject)
            else:
                self.send_chat_message("go where?")
        elif verb == "look":
            if subject == "at me":
                self.world.bot.behaviour_manager.command(behaviours.LookAtPlayerBehaviour)
            else:
                self.send_chat_message("look at what?")
        elif verb == "follow":
            self.world.bot.behaviour_manager.command(behaviours.FollowPlayerBehaviour)
        elif verb == "cancel":
            self.world.bot.behaviour_manager.cancel_running()
        elif verb == "show":
            if subject:
                sign = self.world.sign_waypoints.get_namepoint(subject)
                if sign is not None:
                    self.send_chat_message(str(sign))
                    return
                sign = self.world.sign_waypoints.get_name_from_group(subject)
                if sign is not None:
                    self.send_chat_message(str(sign))
                    return
                if not self.world.sign_waypoints.has_group(subject):
                    self.send_chat_message("no group named %s" % subject)
                    return
                for sign in self.world.sign_waypoints.ordered_sign_groups[subject].iter():
                    self.send_chat_message(str(sign))
            else:
                self.send_chat_message("show what?")
        else:
            log.msg("Unknown command: %s" % original)
