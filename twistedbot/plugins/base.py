
import os
import pkgutil
import abc

from functools import wraps


class PluginMeta(abc.ABCMeta): 
    def __new__(meta, name, bases, dct):
        cls = super(PluginMeta, meta).__new__(meta, name, bases, dct)
        cls.handlers = []
        for name, obj in cls.__dict__.iteritems():
            if hasattr(obj, "__call__") and  name.startswith("on_"):
                cls.handlers.append(name)
        return cls


class PluginBase(object):
    __metaclass__ = PluginMeta

    def __init__(self, world):
        self.world = world


class PluginChatBase(PluginBase):

    def send_chat_message(self, msg):
        self.world.chat.send_chat_message(msg)

    @abc.abstractproperty
    def command_verb(self):
        pass

    @property
    def aliases(self):
        return []

    @abc.abstractproperty
    def help(self):
        pass

    @abc.abstractmethod
    def command(self, sender, command, args):
        pass


class PluginEventHandlerBase(PluginBase):
    pass


class PluginPlannerBase(object):
    pass


def load(log, call_file, group):
    plugs = []
    path = [os.path.dirname(os.path.realpath(call_file))]
    for loader, name, _ in list(pkgutil.iter_modules(path=path)):
        try:
            mpath = ".".join([__package__, group, name])
            module = loader.find_module(mpath).load_module(mpath)
            if not getattr(module, "plugin", False):
                log.msg("module %s does not include plugin" % module.__name__)
                continue
            plugin_class = module.plugin
            plugin_path = "%s.%s" % (module.__name__, plugin_class.__name__)
            if issubclass(plugin_class, PluginChatBase):
                log.msg("loaded chat plugin %s" % plugin_path)
                plugs.append(plugin_class)
            elif issubclass(plugin_class, PluginEventHandlerBase):
                log.msg("loaded event plugin %s" % plugin_path)
                plugs.append(plugin_class)
            elif issubclass(plugin_class, PluginPlannerBase):
                log.msg("loaded planner plugin %s" % plugin_path)
                plugs.append(plugin_class)
            else:
                log.msg("class %s is not plugin" % plugin_path)
        except Exception as e:
            log.err(_stuff=e, _why="could not load plugin %s.py" % os.path.join(path[0], name))
    return plugs
