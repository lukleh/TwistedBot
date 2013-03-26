
import plugins.core
import plugins.custom


class EventHook(object):

    def __init__(self):
        self.handlers = []

    def fire(self, *args, **kwargs):
        for handler in self.handlers:
            utils.do_now(handler, *args, **kwargs)

    def subscribe(self, f):
        self.handlers.append(f)

    def unsubscribe(self, f):
        self.handlers.remove(f)


class EventRegister(object):
    event_names = ["on_chat"]
    def __init__(self, world):
        self.world = world
        self.setup()

    def setup(self):
        for name in event_names:
            setattr(self, name, EventHook())
        for plugin in plugins.core.plugs:
            self.register_plugin(plugin)
        for plugin in plugins.custom.plugs:
            self.register_plugin(plugin)

    def register_plugin(self, plugin):
        for name in getattr(plugin, "handlers", []):
            event = getattr(self, name, False)
            if not event:
                print "no event %s handled by %s" % (name, plugin)
                continue
            event += getattr(plugin, name)



