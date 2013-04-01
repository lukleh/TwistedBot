

from collections import defaultdict
from datetime import datetime

import logbot
import utils
import config
import inventory
from entities import Entities
from grid import Grid
from statistics import Statistics
from chat import Chat
from botentity import BotEntity
from signwaypoints import SignWayPoints
from eventregister import EventRegister


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
        self.config = config
        self.eventregister = EventRegister(self)
        self.eventregister.setup()
        self.commander = Commander(commander_name)
        self.chat = Chat(self)
        self.stats = Statistics()
        self.bot = BotEntity(self, bot_name)
        self.game_ticks = 0
        self.connected = False
        self.logged_in = False
        self.protocol = None
        self.factory = None
        self.entities = None
        self.inventories = inventory.InvetoryContainer(self)
        self.grid = None
        self.sign_waypoints = None
        self.dimension = None
        self.dimensions = [Dimension(self), Dimension(self), Dimension(self)]
        self.spawn_position = None
        self.game_mode = None
        self.difficulty = None
        self.players = defaultdict(int)
        self.last_tick_time = datetime.now()
        self.period_time_estimation = config.TIME_STEP
        utils.do_later(config.TIME_STEP, self.tick)

    def predict_next_ticktime(self, tick_start):
        tick_end = datetime.now()
        d_run = (tick_end - tick_start).total_seconds()  # time this step took
        t = config.TIME_STEP - d_run  # decreased by computation in tick
        d_iter = (tick_start - self.last_tick_time).total_seconds()  # real tick period
        r_over = d_iter - self.period_time_estimation  # diff from scheduled by
        t -= r_over
        t = max(0, t)  # cannot delay into past
        self.period_time_estimation = t + d_run
        self.last_tick_time = tick_start
        return t

    def tick(self):
        tick_start = datetime.now()
        if self.logged_in:
            self.bot.tick()
            self.chat.tick()
            self.every_n_ticks()
        utils.do_later(self.predict_next_ticktime(tick_start), self.tick)

    def every_n_ticks(self, n=100):
        self.game_ticks += 1

    def on_shutdown(self):
        log.msg("Shutdown")
        self.factory.log_connection_lost = False

    def send_packet(self, name, payload):
        if self.protocol is not None:
            self.protocol.send_packet(name, payload)
        else:
            log.err("Trying to send %s while disconnected" % name)

    def dimension_change(self, dimension):
        dim = dimension + 1  # to index from 0
        d = self.dimensions[dim]
        self.dimension = d
        self.entities, self.grid, self.sign_waypoints = d.entities, d.grid, d.sign_waypoints
        if not self.entities.has_entity_eid(self.bot.eid):
            self.entities.new_bot(self.bot.eid)
        log.msg("NEW DIMENSION %d" % dim)

    @property
    def server_lag(self):
        return self.players[config.USERNAME]


class Commander(object):
    def __init__(self, name):
        self.name = name
        self.eid = None
        self.last_possition = None
        self.last_block = None

    @property
    def in_game(self):
        return self.eid is not None
