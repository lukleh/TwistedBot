
import re
from collections import deque

from pyparsing import ParseException, Word, OneOrMore, alphanums

import config
import behavior_tree as bt
import logbot


log = logbot.getlogger("CHAT")


class Chat(object):
    clean_colors_re = re.compile(ur'\u00A7.', re.UNICODE)
    commander_name = Word(alphanums + '_').setResultsName("commander")
    commander_head_chat = "<" + commander_name + ">"
    commander_head_whisper = commander_name + OneOrMore(Word(alphanums)) + ":"
    command_part = OneOrMore(Word(alphanums)).setResultsName("command")
    commander_message = (commander_head_chat | commander_head_whisper) + command_part

    def __init__(self, world):
        self.world = world
        self.chat_spam_treshold_count = 0
        self.chat_spam_treshold_buffer = deque()

    def tick(self):
        if self.chat_spam_treshold_count > 0:
            self.chat_spam_treshold_count -= 1
        if self.chat_spam_treshold_count <= 160 and self.chat_spam_treshold_buffer:
            log.msg("consume chat buffer size %d" % len(self.chat_spam_treshold_buffer))
            self.send_chat_message(self.chat_spam_treshold_buffer.popleft())

    def send_chat_message(self, msg):
        if isinstance(msg, list):
            for line in msg:
                self.send_chat_message(line)
            return
        log.msg("out| %s" % msg)
        if self.world.commander.in_game:
            if self.chat_spam_treshold_count > 160:
                self.chat_spam_treshold_buffer.append(msg)
                p_msg = "spam protection, buffer %d long" % len(self.chat_spam_treshold_buffer)
                log.msg(p_msg)
                if len(self.chat_spam_treshold_buffer) < 2:
                    self.chat_spam_treshold_count += 20
                    self.world.send_packet("chat message", {"message": "spam protection, posponing chat"})
                return
            if config.WHISPER:
                msg = "/tell %s %s" % (self.world.commander.name, msg)
            #TODO split msg in a better way
            if len(msg) > 100:
                self.chat_spam_treshold_buffer.appendleft(msg[:100])
                self.chat_spam_treshold_buffer.appendleft(msg[100:])
                log.msg("message too long, splitting")
                return
            self.chat_spam_treshold_count += 20
            self.world.send_packet("chat message", {"message": msg})
        elif self.chat_spam_treshold_buffer:
            self.chat_spam_treshold_buffer = deque()

    def clean(self, orig_msg):
        msg = self.clean_colors_re.sub('', orig_msg)
        msg = msg.lower()
        return msg

    def parse_message(self, msg):
        try:
            p = self.commander_message.parseString(msg)
        except ParseException:
            return None, None
        else:
            return p.commander, p.command

    def parse_command(self, msg):
        try:
            p = self.command_part.parseString(msg)
        except ParseException:
            return None
        else:
            return p.command

    def process_command_line(self, msg):
        command = self.parse_command(msg)
        if not command:
            log.msg("your message does not appear to be a command")
            return
        self.process_command("operator", command)

    def process_command(self, sender, command):
        cmd_msg = " ".join(command)
        log.msg("possible command >%s<" % cmd_msg)
        verb = command[0]
        subject = command[1:]
        self.dispatch_command(sender, verb, subject, cmd_msg)

    @property
    def verbs(self):
        return self.world.eventregister.chat_commands

    def dispatch_command(self, sender, verb, subject, cmd_msg):
        if verb in self.verbs:
            try:
                self.verbs[verb].command(sender, verb, subject)
            except Exception as e:
                log.err(e, "error for command %s" % verb)
                self.send_chat_message("code error in this command")
        else:
            self.send_chat_message("Unknown command: %s" % cmd_msg)
