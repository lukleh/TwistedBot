
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

    def parse_full(self, msg):
        try:
            p = self.commander_message.parseString(msg)
        except ParseException:
            return None, None
        else:
            return p.commander, p.command

    def parse_partial(self, msg):
        try:
            p = self.command_part.parseString(msg)
        except ParseException:
            return None
        else:
            return p.command

    def on_chat_message(self, msg):
        msg = self.clean(msg)
        commander, command = self.parse_full(msg)
        if commander == config.COMMANDER:
            log.msg("in # %s" % msg)
            self.process_command(command)

    def process_command_line(self, msg):
        command = self.parse_partial(msg)
        self.process_command(command)

    def process_command(self, command):
        if not command:
            self.send_chat_message("your message does not appear to be a command")
            return
        cmd_msg = " ".join(command)
        log.msg("possible command >%s<" % cmd_msg)
        verb = command[0]
        subject = command[1:] if len(command) > 1 else []
        self.parse_command(verb, subject, cmd_msg)

    def parse_command(self, verb, subject, cmd_msg):
        if verb == "rotate" or verb == "circulate":
            if subject:
                self.world.bot.behavior_tree.new_command(bt.WalkSigns, group=" ".join(subject), walk_type=verb)
            else:
                self.send_chat_message("which sign group to %s?" % verb)
        elif verb == "go":
            if subject:
                self.world.bot.behavior_tree.new_command(bt.GoToSign, sign_name=" ".join(subject))
            else:
                self.send_chat_message("go where?")
        elif verb == "look":
            if subject == ["at", "me"]:
                self.world.bot.behavior_tree.new_command(bt.LookAtPlayer)
            else:
                self.send_chat_message("look at what?")
        elif verb == "collect":
            if subject:
                itemstack, count = bt.CollectResources.parse_parameters(subject)
                if itemstack is None:
                    self.send_chat_message("collect what item?")
                    return
                if count is None:
                    self.send_chat_message("what amount of %s to collect?" % itemstack.name)
                    return
                if count < 1:
                    self.send_chat_message("amount has to be bigger that zero" % itemstack.name)
                    return
                itemstack.count = count
                self.world.bot.behavior_tree.new_command(bt.CollectResources, itemstack=itemstack)
            else:
                self.send_chat_message("collect what?")
        elif verb == "follow":
            self.world.bot.behavior_tree.new_command(bt.FollowPlayer)
        elif verb == "stop":
            self.world.bot.behavior_tree.cancel_running()
        elif verb == "show":
            if subject:
                what = subject[0]
                if what == "sign":
                    sign_name = " ".join(subject[1:])
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
                    for slot_id, item in self.world.inventories.player_inventory.slot_items():
                        self.send_chat_message("slot %d %s" % (slot_id, item))
                elif what == "cursor":
                    self.world.bot.behavior_tree.new_command(bt.ShowPlayerCursor)
                else:
                    self.send_chat_message("I can show only signs now")
            else:
                self.send_chat_message("show what?")
        elif verb == "debug":
            if subject:
                what = subject[0]
                if what == "inventoryselect":
                    item_name = " ".join(subject[1:])
                    if not item_name:
                        self.send_chat_message("specify item")
                        return
                    itemstack = bt.InventorySelect.parse_parameters(item_name)
                    if itemstack is not None:
                        self.world.bot.behavior_tree.new_command(bt.InventorySelect, itemstack=itemstack)
                    else:
                        self.send_chat_message("unknown item %s" % item_name)
                else:
                    self.send_chat_message("I can show only signs now")
            else:
                self.send_chat_message("debug what?")
        else:
            self.send_chat_message("Unknown command: %s" % cmd_msg)
