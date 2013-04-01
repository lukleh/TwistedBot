

from twistedbot.plugins.base import PluginEventHandlerBase


class GeneralEvents(PluginEventHandlerBase):

    def on_death(self):
        log.msg("I am dead")
        self.world.bot.i_am_dead = True
        utils.do_later(2.0, self.do_respawn)


plugin = GeneralEvents