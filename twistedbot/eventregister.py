
import plugins.core
import plugins.custom
import logbot
import utils

from plugins.base import PluginChatBase


log = logbot.getlogger("EVENTREGISTER")


class EventHook(object):

    def __init__(self):
        self.handlers = []

    def fire(self, *args, **kwargs):
        for handler in self.handlers:
            handler(*args, **kwargs)

    def subscribe(self, f):
        self.handlers.append(f)

    def unsubscribe(self, f):
        self.handlers.remove(f)

    @property
    def no_handlers(self):
        return len(self.handlers) == 0


class EventRegister(object):
    event_names = ["on_dummy",
                   "on_connection_lost",
                   "on_connection_made",
                   "on_login",
                   "on_ping",
                   "on_chat",
                   "on_time_update",
                   "on_spawn_position",
                   "on_health_update",
                   "on_respawn",
                   "on_location",
                   "on_held_item_change",
                   "on_spawn_player",
                   "on_collect",
                   "on_spawn_objectvehicle",
                   "on_spawn_mob",
                   "on_spawn_painting",
                   "on_spawn_experience_orb",
                   "on_entity_velocity",
                   "on_entity_destroy",
                   "on_entity_move",
                   "on_entity_look",
                   "on_entity_move_look",
                   "on_entity_teleport",
                   "on_entity_head_look",
                   "on_entity_status",
                   "on_entity_attach",
                   "on_entity_metadata",
                   "on_update_experience",
                   "on_load_chunk",
                   "on_multi_block_change",
                   "on_block_change",
                   "on_load_bulk_chunk",
                   "on_explosion",
                   "on_open_window",
                   "on_close_window",
                   "on_set_window_slot",
                   "on_set_inventory",
                   "on_confirm_transaction",
                   "on_update_sign",
                   "on_update_stats",
                   "on_player_list_item",
                   "on_encryption_key_response",
                   "on_encryption_key_request",
                   "on_server_kick",
                   "on_death"]
    def __init__(self, world):
        self.world = world
        self.chat_commands = {}

    def setup(self):
        for name in self.event_names:
            setattr(self, name, EventHook())
        for plugin_cls in plugins.core.plugs:
            self.register_plugin(plugin_cls)
        for plugin_cls in plugins.custom.plugs:
            self.register_plugin(plugin_cls)
        for name in self.event_names:
            eh = getattr(self, name)
            if eh.no_handlers:
                log.msg("no handlers for event %s" % name)

    def register_chat_plugin(self, plugin):
        self.register_chat_command(plugin.command_verb, plugin)
        for alias in plugin.aliases:
            self.register_chat_command(alias, plugin)

    def register_chat_command(self, command, plugin):
        if command not in self.chat_commands:
            self.chat_commands[command] = plugin
        else:
            log.msg("command verb %s already registered" % command)

    def register_plugin(self, plugin_cls):
        plugin = plugin_cls(self.world)
        if isinstance(plugin, PluginChatBase):
            self.register_chat_plugin(plugin)
        for name in getattr(plugin, "handlers", []):
            event = getattr(self, name, False)
            if not event:
                log.msg("no event %s handled by %s" % (name, plugin))
                continue
            event.subscribe(getattr(plugin, name))



