
import os
import pkgutil
import abc

from functools import wraps


class PluginBase(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, world):
        self.world = world
        self.world.eventregister.register_plugin(self)
        
    @classmethod
    def register(cls, fn):
        if not getattr(cls, "handlers", False):
            cls.handlers = []
        cls.handlers.append(fn.__name__)
        @wraps
        def f(self):
            return fn(self, **kwargs)
        return f


class PluginChatBase(PluginBase):
    @abc.abstractproperty
    def command_verb(self):
        pass

    @abc.abstractmethod
    def on_command(self, sender, command, args):
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
                log.msg("module %s missing plugin attribute" % module.__name__)
                continue
            if issubclass(module.plugin, PluginChatBase):
                log.msg("loaded %s chat plugin" % module.plugin.__name__)
                plugs.append(module.plugin)
            elif issubclass(module.plugin, PluginProtocolBase):
                log.msg("loaded %s protocol plugin" % module.plugin.__name__)
                plugs.append(module.plugin)
            elif issubclass(module.plugin, PluginPlannerBase):
                log.msg("loaded %s planner plugin" % module.plugin.__name__)
                plugs.append(module.plugin)
            else:
                log.msg("file %s is not plugin" % module.__file__)
        except Exception as e:
            log.err(_stuff=e, _why="could not load plugin %s.py" % os.path.join(path[0], name))
    return plugs
