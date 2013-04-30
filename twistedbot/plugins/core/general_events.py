
import twistedbot.logbot

from twistedbot import utils
from twistedbot.plugins.base import PluginEventHandlerBase


log = twistedbot.logbot.getlogger("GENERAL EVENT")


class GeneralEvents(PluginEventHandlerBase):

    def on_death(self):
        log.msg("I am dead")
        self.world.bot.i_am_dead = True
        utils.do_later(2.0, self.world.bot.do_respawn)


plugin = GeneralEvents