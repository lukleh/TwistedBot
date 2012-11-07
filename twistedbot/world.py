

from collections import defaultdict

import behaviours
import logbot
import tools
import config
from entities import Entities
from grid import Grid
from navigationgrid import NavigationGrid
from statistics import Statistics
from chat import Chat
from botentity import Bot


class World(object):

    def __init__(self, host=None, port=None, commander_name=None, bot_name=None):
        self.server_host = host
        self.server_port = port
        self.commander = Commander(commander_name)
        self.status_diff = StatusDiff(self)
        self.bot = Bot(self, bot_name)
        self.behaviour_manager = behaviours.BehaviourManager(self)
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
        self.spawn_position = None
        self.dim_entities = [None, None, None]
        self.dim_grid = [None, None, None]
        self.dim_navgrid = [None, None, None]
        self.players = defaultdict(int)
        tools.do_later(config.TIME_STEP, self.tick)

    def tick(self):
        t = config.TIME_STEP
        if self.logged_in:
            t = self.bot.tick()
            self.every_n_ticks()
        tools.do_later(t, self.tick)

    def every_n_ticks(self, n=100):
        self.game_ticks += 1
        if self.game_ticks % n == 0:
            self.status_diff.log()

    def connection_lost(self):
        self.connected = False
        self.logged_in = False
        self.protocol = None
        self.bot.connection_lost()

    def connection_made(self):
        self.connected = True

    def send_packet(self, name, payload):
        if self.protocol is not None:
            self.protocol.send_packet(name, payload)

    def dimension_change(self, dimension):
        dim = dimension + 1  # to index from 0
        if self.dim_entities[dim] is None:
            es = Entities(self)
            self.dim_entities[dim] = es
            self.entities = es
        if self.dim_grid[dim] is None:
            gd = Grid(self)
            self.dim_grid[dim] = gd
            self.grid = gd
        if self.dim_navgrid[dim] is None:
            ng = NavigationGrid(self)
            self.dim_navgrid[dim] = ng
            self.navgrid = ng
        if not self.entities.has_entity(self.bot.eid):
            self.entities.new_bot(self.bot.eid)

    def login_data(self, bot_eid=None, game_mode=None, dimension=None, difficulty=None):
        self.bot.eid = bot_eid
        self.logged_in = True
        self.dimension_change(dimension)
        self.game_state.update_settings(game_mode=game_mode, dimension=dimension, difficulty=difficulty)

    def respawn_data(self, **kwargs):
        self.login_data(**kwargs)

    def shutdown(self):
        """ actions to perform before shutdown """
        pass


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

    def update_time(self, timestamp=None, daytime=None):
        self.timestamp = timestamp
        self.daytime = daytime


class StatusDiff(object):
    def __init__(self, world):
        self.world = world
        self.packets_in = 0
        self.node_count = 0
        self.edge_count = 0
        self.logger = logbot.getlogger("BOT_ENTITY_STATUS")

    def log(self):
        return
        if self.node_count != self.world.navgrid.graph.node_count or \
                self.edge_count != self.world.navgrid.graph.edge_count:
            self.logger.msg("navgrid having %d nodes and %d edges" %
                            (self.world.navgrid.graph.node_count,
                             self.world.navgrid.graph.edge_count))
            self.node_count = self.world.navgrid.graph.node_count
            self.edge_count = self.world.navgrid.graph.edge_count
        #self.logger.msg("received %d packets" % self.packets_in)
        #self.logger.msg(self.bot.stats)


class Commander(object):
    def __init__(self, name):
        self.name = name
        self.eid = None
        self.last_possition = None
        self.last_block = None
