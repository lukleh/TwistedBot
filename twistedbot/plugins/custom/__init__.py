
import twistedbot.logbot as logbot
from twistedbot.plugins.base import load, PluginChatBase


name = __name__.split('.')[-1]
log = logbot.getlogger("%s PLUGINS" % name.upper())
plugs = load(log, __file__, name)