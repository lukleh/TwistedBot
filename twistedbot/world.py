

from collections import defaultdict

import logbot
import utils
import config
from entities import Entities
from grid import Grid
from statistics import Statistics
from chat import Chat
from botentity import BotEntity
from signwaypoints import SignWayPoints


log = logbot.getlogger("WORLD")


class Dimension(object):

    def __init__(self, world):
        self.world = world
        self.entities = Entities(self)
        self.grid = Grid(self)
        self.sign_waypoints = SignWayPoints(self)


class World(object):
    def __init__(self, host=None, port=None, commander_name=None, bot_name=None):
        self.server_host = host
        self.server_port = port
        self.commander = Commander(commander_name)
        self.bot = BotEntity(self, bot_name)
        self.chat = Chat(self)
        self.stats = Statistics()
        self.game_ticks = 0
        self.connected = False
        self.logged_in = False
        self.protocol = None
        self.entities = None
        self.grid = None
        self.sign_waypoints = None
        self.dimension = None
        self.dimensions = [Dimension(self), Dimension(self), Dimension(self)]
        self.spawn_position = None
        self.game_mode = None
        self.difficulty = None
        self.players = defaultdict(int)
        utils.do_later(config.TIME_STEP, self.tick)

    def tick(self):
        t = config.TIME_STEP
        if self.logged_in:
            t = self.bot.tick()
            self.chat.tick()
            self.every_n_ticks()
        utils.do_later(t, self.tick)

    def every_n_ticks(self, n=100):
        self.game_ticks += 1

    def on_connection_lost(self):
        self.connected = False
        self.logged_in = False
        self.protocol = None
        self.bot.on_connection_lost()

    def connection_made(self):
        self.connected = True

    def on_shutdown(self):
        log.msg("Reactor shutdown")
        self.protocol.factory.log_connection_lost = False

    def send_packet(self, name, payload):
        if self.protocol is not None:
            self.protocol.send_packet(name, payload)
        else:
            log.msg("Trying to send %s while disconnected" % name)

    def dimension_change(self, dimension):
        dim = dimension + 1  # to index from 0
        d = self.dimensions[dim]
        self.dimension = d
        self.entities, self.grid, self.sign_waypoints = d.entities, d.grid, d.sign_waypoints
        if not self.entities.has_entity(self.bot.eid):
            self.entities.new_bot(self.bot.eid)

    def on_login(self, bot_eid=None, game_mode=None, dimension=None, difficulty=None):
        self.bot.eid = bot_eid
        self.logged_in = True
        self.dimension_change(dimension)
        self.game_mode = game_mode
        self.difficulty = difficulty

    def on_spawn_position(self, x, y, z):
        self.spawn_position = (x, y, z)
        self.bot.spawn_point_received = True

    def on_respawn(self, game_mode=None, dimension=None, difficulty=None):
        self.dimension_change(dimension)
        self.game_mode = game_mode
        self.difficulty = difficulty
        self.bot.location_received = False
        self.bot.spawn_point_received = False
        self.bot.i_am_dead = False

    def on_time_update(self, timestamp=None, daytime=None):
        self.timestamp = timestamp
        self.daytime = daytime


class Commander(object):
    def __init__(self, name):
        self.name = name
        self.eid = None
        self.last_possition = None
        self.last_block = None
