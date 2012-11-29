

from collections import defaultdict

import logbot
import tools
import config
import gridspace
from entities import Entities
from grid import Grid
from navigationgrid import NavigationGrid, NavigationCubes
from statistics import Statistics
from chat import Chat
from botentity import BotEntity
from tools import NodeState


log = logbot.getlogger("WORLD")


class Dimension(object):

    def __init__(self, world):
        self.world = world
        self.entities = Entities(self.world)
        self.grid = Grid(self.world)
        self.navgrid = NavigationGrid(self.world)
        self.nav_cubes = NavigationCubes(self.world)


class World(object):
    def __init__(self, host=None, port=None, commander_name=None, bot_name=None):
        self.server_host = host
        self.server_port = port
        self.commander = Commander(commander_name)
        self.status_diff = StatusDiff(self)
        self.bot = BotEntity(self, bot_name)
        self.chat = Chat(self)
        self.stats = Statistics()
        self.game_state = GameState()
        self.game_ticks = 0
        self.connected = False
        self.logged_in = False
        self.protocol = None
        self.entities = None
        self.grid = None
        self.navgrid = None
        self.nav_cubes = None
        self.dimension = None
        self.dimensions = [Dimension(self), Dimension(self), Dimension(self)]
        self.spawn_position = None
        self.players = defaultdict(int)
        tools.do_later(config.TIME_STEP, self.tick)

    def tick(self):
        t = config.TIME_STEP
        if self.logged_in:
            t = self.bot.tick()
            self.chat.tick()
            self.every_n_ticks()
        tools.do_later(t, self.tick)

    def every_n_ticks(self, n=100):
        self.game_ticks += 1
        if self.game_ticks % n == 0:
            self.status_diff.log()

    def on_connection_lost(self):
        self.connected = False
        self.logged_in = False
        self.protocol = None
        self.bot.on_connection_lost()

    def connection_made(self):
        self.connected = True

    def on_shutdown(self):
        pass

    def send_packet(self, name, payload):
        if self.protocol is not None:
            self.protocol.send_packet(name, payload)
        else:
            log.msg("Trying to send %s while disconnected" % name)

    def dimension_change(self, dimension):
        dim = dimension + 1  # to index from 0
        d = self.dimensions[dim]
        self.dimension = d
        self.entities, self.grid, self.navgrid, self.nav_cubes = d.entities, d.grid, d.navgrid, d.nav_cubes
        if not self.entities.has_entity(self.bot.eid):
            self.entities.new_bot(self.bot.eid)

    def on_login(self, bot_eid=None, game_mode=None, dimension=None, difficulty=None):
        self.bot.eid = bot_eid
        self.logged_in = True
        self.dimension_change(dimension)
        self.game_state.update_settings(game_mode=game_mode, dimension=dimension, difficulty=difficulty)

    def on_spawn_position(self, x, y, z):
        self.spawn_position = (x, y, z)
        self.bot.spawn_point_received = True

    def on_respawn(self, game_mode=None, dimension=None, difficulty=None):
        self.dimension_change(dimension)
        self.game_state.update_settings(game_mode=game_mode, dimension=dimension, difficulty=difficulty)


class GameState(object):
    def __init__(self):
        self.game_mode = None
        self.dimension = None
        self.difficulty = None
        self.daytime = None
        self.timestamp = None

    def update_settings(self, game_mode=None, dimension=None, difficulty=None):
        self.game_mode = game_mode
        self.difficulty = difficulty
        self.dimension = dimension

    def on_time_update(self, timestamp=None, daytime=None):
        self.timestamp = timestamp
        self.daytime = daytime


class StatusDiff(object):
    def __init__(self, world):
        self.world = world
        self.packets_in = 0
        self.n_checks = {NodeState.UNKNOWN: 0,
                         NodeState.NO: 0,
                         NodeState.YES: 0,
                         NodeState.FREE: 0}
        self.state_catch_count = 0
        self.logger = logbot.getlogger("BOT_ENTITY_STATUS")

    def log(self):
        if self.state_catch_count != sum(gridspace.state_catch.values()):
            self.logger.msg(gridspace.state_catch)
            self.state_catch_count = sum(gridspace.state_catch.values())
        #self.logger.msg("received %d packets" % self.packets_in)
        #self.logger.msg(self.bot.stats)


class Commander(object):
    def __init__(self, name):
        self.name = name
        self.eid = None
        self.last_possition = None
        self.last_block = None
