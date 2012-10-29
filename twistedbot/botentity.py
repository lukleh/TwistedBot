

import math
from datetime import datetime

import config
import tools
import packets
import logbot
import fops
import blocks
import goals
from statistics import Statistics
from axisbox import AABB
from chat import Chat
from entity import EntityBot

log = logbot.getlogger("BOT_ENTITY")


class StatusDiff(object):
    def __init__(self, bot, world):
        self.bot = bot
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


class Bot(object):
    def __init__(self, world, name, commander_name):
        self.world = world
        self.name = name
        self.commander = Commander(commander_name)
        self.eid = None
        self.world.bot = self
        self.grid = self.world.grid
        self.velocities = [0.0, 0.0, 0.0]
        self.direction = [0, 0]
        self.x = 0
        self.y = 0
        self.z = 0
        self.ticks = 0
        self.chunks_ready = False
        self.goal_manager = goals.Manager(self)
        self.stance_diff = config.PLAYER_EYELEVEL
        self.pitch = None
        self.yaw = None
        self.on_ground = False
        self.ready = False
        self.location_received = False
        self.check_location_received = False
        self.spawn_point_received = False
        self.chat = Chat(self)
        self.stats = Statistics()
        self.startup()
        tools.do_later(config.TIME_STEP, self.iterate)
        self.last_time = datetime.now()
        self.period_time_estimation = 1 / 20.0
        self.status_diff = StatusDiff(self, self.world)
        self.is_collided_horizontally = False
        self.horizontally_blocked = False
        self.is_in_water = False
        self.is_in_lava = False
        self.action = 2  # normal
        self.is_jumping = False
        self.floating_flag = True
        self.turn_to_setup = None

    def connection_lost(self):
        self.protocol = None
        if self.location_received:
            self.location_received = False
            self.chunks_ready = False
            #TODO remove current chunks
            # erase all data that came from server

    def shutdown(self):
        """ save anything that needs to be saved and shutdown"""
        log.msg("Gracefully shutting down.......")

    def startup(self):
        """ load anything that needs to be loaded """
        log.msg("Gracefully starting up.......")

    def set_location(self, kw):
        self.x = kw["x"]
        self.y = kw["y"]
        self.z = kw["z"]
        self.stance_diff = kw["stance"] - kw["y"]
        self.on_ground = kw["grounded"]
        self.yaw = kw["yaw"]
        self.pitch = kw["pitch"]
        self.velocities = [0.0, 0.0, 0.0]
        self.check_location_received = True
        if self.location_received is False:
            self.location_received = True
        if not self.in_complete_chunks:
            log.msg("Server send location into incomplete chunks")
            self.ready = False

    @property
    def position(self):
        return (self.x, self.y, self.z)

    @property
    def position_grid(self):
        return (self.grid_x, self.grid_y, self.grid_z)

    @property
    def position_eyelevel(self):
        return (self.x, self.y_eyelevel, self.z)

    @property
    def y_eyelevel(self):
        return self.y + config.PLAYER_EYELEVEL

    @property
    def stance(self):
        return self.y + self.stance_diff

    @property
    def grid_x(self):
        return tools.grid_shift(self.x)

    @property
    def grid_y(self):
        return int(self.y)

    @property
    def grid_z(self):
        return tools.grid_shift(self.z)

    @property
    def aabb(self):
        return AABB.from_player_coords(self.position)

    @aabb.setter
    def aabb(self, v):
        raise Exception('setting bot aabb')

    @property
    def in_complete_chunks(self):
        return self.world.grid.aabb_in_complete_chunks(self.aabb)

    def every_n_ticks(self, n=100):
        if self.ticks % n == 0:
            self.status_diff.log()

    def iterate(self):
        iter_start = datetime.now()
        self.ticks += 1
        if self.location_received is False:
            self.last_iterate_time = iter_start
            tools.do_later(config.TIME_STEP, self.iterate)
            return
        if not self.ready:
            self.ready = self.in_complete_chunks and self.spawn_point_received
            if not self.ready:
                self.last_iterate_time = iter_start
                tools.do_later(config.TIME_STEP, self.iterate)
                return
        self.move(direction=self.direction)
        self.direction = [0, 0]
        self.send_location()
        tools.do_later(0, self.on_standing_ready)
        tools.do_later(0, self.every_n_ticks)
        tools.do_later(0, self.goal_manager.run_goal)
        iter_end = datetime.now()
        d_run = (iter_end - iter_start).total_seconds()  # time this step took
        t = config.TIME_STEP - d_run  # decreased by computation in iterate
        d_iter = (iter_start - self.last_iterate_time).total_seconds()  # real iterate period
        r_over = d_iter - self.period_time_estimation  # diff from scheduled by
        t -= r_over
        t = max(0, t)  # cannot delay into past
        self.period_time_estimation = t + d_run
        self.last_iterate_time = iter_start
        tools.do_later(t, self.iterate)

    def send_packet(self, name, payload):
        if self.protocol is not None:
            self.protocol.send_packet(name, payload)

    def send_location(self):
        self.send_packet("player position&look", {
            "position": packets.Container(x=self.x, y=self.y, z=self.z,
                                          stance=self.stance),
            "orientation": packets.Container(yaw=self.yaw, pitch=self.pitch),
            "grounded": packets.Container(grounded=self.on_ground)})

    def set_action(self, action_id):
        """
        sneaking, not sneaking, leave bed, start sprinting, stop sprinting
        """
        if self.action != action_id:
            self.action = action_id
        self.send_packet(
            "entity action", {"eid": self.eid, "action": self.action})

    def chat_message(self, msg):
        log.msg(msg)
        self.send_packet("chat message", {"message": msg})

    def turn_to(self, point, elevation=False):
        if point[0] == self.x and point[2] == self.z:
            return
        yaw, pitch = tools.yaw_pitch_between(point, self.position_eyelevel)
        if yaw is None or pitch is None:
            return
        self.yaw = yaw
        if elevation:
            self.pitch = pitch
        else:
            self.pitch = 0

    def update_position(self, x, y, z, onground):
        self.x = x
        self.y = y
        self.z = z
        self.on_ground = onground

    def set_turn_to(self, point, elevation=False):
        self.turn_to_setup = (point, elevation)

    def set_jumpstep(self, v=config.MAX_STEP_HEIGHT):
        self.velocities[1] = 0
        aabbs = self.grid.aabbs_in(self.aabb.extend_to(0, v, 0))
        for bb in aabbs:
            v = self.aabb.calculate_axis_offset(bb, v, 1)
        ab = self.aabb.offset(dy=v)
        self.y = ab.posy

    def do_move(self):
        zero_vels = False
        if self.is_in_web:
            self.velocities[0] *= 0.25
            self.velocities[1] *= 0.05000000074505806
            self.velocities[2] *= 0.25
            zero_vels = True
        aabbs = self.grid.aabbs_in(self.aabb.extend_to(
            self.velocities[0], self.velocities[1], self.velocities[2]))
        b_bb = self.aabb
        dy = self.velocities[1]
        for bb in aabbs:
            dy = b_bb.calculate_axis_offset(bb, dy, 1)
        b_bb = b_bb.offset(dy=dy)
        dx = self.velocities[0]
        for bb in aabbs:
            dx = b_bb.calculate_axis_offset(bb, dx, 0)
        b_bb = b_bb.offset(dx=dx)
        dz = self.velocities[2]
        for bb in aabbs:
            dz = b_bb.calculate_axis_offset(bb, dz, 2)
        b_bb = b_bb.offset(dz=dz)
        onground = self.velocities[1] != dy and self.velocities[1] < 0
        self.is_collided_horizontally = dx != self.velocities[
            0] or dz != self.velocities[2]
        self.horizontally_blocked = dx != self.velocities[0] and dz != self.velocities[2]
        if self.velocities[0] != dx:
            self.velocities[0] = 0
        if self.velocities[1] != dy:
            self.velocities[1] = 0
        if self.velocities[2] != dz:
            self.velocities[2] = 0
        self.update_position(b_bb.posx, b_bb.min_y, b_bb.posz, onground)
        if zero_vels:
            self.velocities = [0, 0, 0]
        self.do_block_collision()

    def clip_abs_velocities(self):
        out = list(self.velocities)
        for i in xrange(3):
            if abs(self.velocities[i]) < 0.005:  # minecraft value
                out[i] = 0
        return out

    def clip_ladder_velocities(self):
        out = list(self.velocities)
        if self.is_on_ladder:
            for i in xrange(3):
                if i == 1:
                    if self.velocities[i] < -0.15:
                        out[i] = -0.15
                elif abs(self.velocities[i]) > 0.15:
                    out[i] = math.copysign(0.15, self.velocities[i])
        if self.is_sneaking and self.velocities[1] < 0:
            out[1] = 0
        return out

    def handle_water_movement(self, aabb=None):
        if aabb is None:
            aabb = self.aabb
        is_in_water = False
        water_current = (0, 0, 0)
        bb = aabb.expand(-0.001, -0.4010000059604645, -0.001)
        top_y = tools.grid_shift(bb.max_y) + 1
        for blk in self.grid.blocks_in_aabb(bb):
            if isinstance(blk, blocks.BlockWater):
                wy = blk.y + 1 - blk.height_percent
                if top_y >= wy:
                    is_in_water = True
                    water_current = blk.add_velocity_to(water_current)
        if tools.vector_size(water_current) > 0:
            water_current = tools.normalize(water_current)
            wconst = 0.014
            water_current = (water_current[0] * wconst, water_current[
                             1] * wconst, water_current[2] * wconst)
        return is_in_water, water_current

    def handle_lava_movement(self):
        for blk in self.grid.blocks_in_aabb(
                self.aabb.expand(-0.10000000149011612,
                                 -0.4000000059604645,
                                 -0.10000000149011612)):
            if isinstance(blk, blocks.BlockLava):
                return True
        return False

    def move(self, direction=(0, 0)):
        self.velocities = self.clip_abs_velocities()
        self.is_in_water, water_current = self.handle_water_movement()
        self.is_in_lava = self.handle_lava_movement()
        if self.is_jumping:
            if self.is_in_water or self.is_in_lava:
                self.velocities[1] += config.SPEED_LIQUID_JUMP
            elif self.on_ground:
                self.velocities[1] = config.SPEED_JUMP
            elif self.is_on_ladder:
                self.velocities[1] = config.SPEED_CLIMB
            self.is_jumping = False
        if self.is_in_water:
            if self.floating_flag:
                if self.head_inside_water:
                    self.velocities[1] += config.SPEED_LIQUID_JUMP
                else:
                    x, y, z = self.aabb.grid_bottom_center
                    b_up = self.grid.get_block(x, y + 1, z)
                    b_down = self.grid.get_block(x, y - 1, z)
                    b_cent = self.grid.get_block(x, y, z)
                    no_up = not b_up.is_water and b_down.collidable and fops.eq(b_down.max_y, y)
                    if not no_up and b_cent.is_water and fops.gt(b_cent.y + 0.5, self.aabb.min_y):
                        self.velocities[1] += config.SPEED_LIQUID_JUMP
            print 'WATER CURRENT', water_current
            self.velocities = [self.velocities[0] + water_current[0],
                               self.velocities[1] + water_current[1],
                               self.velocities[2] + water_current[2]]
            orig_y = self.y
            self.update_directional_speed(
                direction, 0.02, balance=True)
            self.do_move()
            self.velocities[0] *= 0.800000011920929
            self.velocities[1] *= 0.800000011920929
            self.velocities[2] *= 0.800000011920929
            self.velocities[1] -= 0.02
            if self.is_collided_horizontally and \
                    self.is_offset_in_liquid(self.velocities[0],
                                             self.velocities[1] + 0.6 -
                                             self.y + orig_y,
                                             self.velocities[2]):
                self.velocities[1] = 0.30000001192092896
        elif self.is_in_lava:
            orig_y = self.y
            self.update_directional_speed(direction, 0.02)
            self.do_move()
            self.velocities[0] *= 0.5
            self.velocities[1] *= 0.5
            self.velocities[2] *= 0.5
            self.velocities[1] -= 0.02
            if self.is_collided_horizontally and \
                    self.is_offset_in_liquid(self.velocities[0],
                                             self.velocities[1] + 0.6 -
                                             self.y + orig_y,
                                             self.velocities[2]):
                self.velocities[1] = 0.30000001192092896
        else:
            slowdown = self.current_slowdown
            self.update_directional_speed(direction, self.current_speed_factor)
            self.velocities = self.clip_ladder_velocities()
            self.do_move()
            if self.is_collided_horizontally and self.is_on_ladder:
                self.velocities[1] = 0.2
            self.velocities[1] -= config.BLOCK_FALL
            self.velocities[1] *= config.DRAG
            self.velocities[0] *= slowdown
            self.velocities[2] *= slowdown

    def directional_speed(self, direction, speedf):
        x, z = direction
        dx = x * speedf
        dz = z * speedf
        return (dx, dz)

    def turn_direction(self, x, z):
        if x == 0 and z == 0:
            return
        yaw, _ = tools.yaw_pitch_to_vector(x, 0, z)
        self.yaw = yaw

    def update_directional_speed(self, direction, speedf, balance=False):
        direction = self.directional_speed(direction, speedf)
        if self.turn_to_setup is not None:
            self.turn_to(*self.turn_to_setup)
            self.turn_to_setup = None
        if balance and tools.vector_size(direction) > 0:
            perpedicular_dir = (- direction[1], direction[0])
            dot = (self.velocities[0] * perpedicular_dir[0] + self.velocities[2] * perpedicular_dir[1]) / \
                (perpedicular_dir[0] * perpedicular_dir[0] + perpedicular_dir[1] * perpedicular_dir[1])
            if dot < 0:
                dot *= -1
                perpedicular_dir = (direction[1], - direction[0])
            direction = (direction[0] - perpedicular_dir[0] * dot, direction[1] - perpedicular_dir[1] * dot)
            self.turn_direction(*direction)
        self.velocities[0] += direction[0]
        self.velocities[2] += direction[1]

    def set_direction(self, direction):
        self.direction = direction

    @property
    def current_slowdown(self):
        slowdown = 0.91
        if self.on_ground:
            slowdown = 0.546
            block = self.grid.get_block(
                self.grid_x, self.grid_y - 1, self.grid_z)
            if block is not None:
                slowdown = block.slipperiness * 0.91
        return slowdown

    @property
    def current_speed_factor(self):
        if self.on_ground:
            slowdown = self.current_slowdown
            modf = 0.16277136 / (slowdown * slowdown * slowdown)
            factor = config.SPEED_ON_GROUND * modf
        else:
            factor = config.SPEED_IN_AIR
        return factor * 0.98

    @property
    def current_motion(self):
        #TODO
        # check if in water or lava -> factor = 0.2
        # else check ladder and clip if necessary
        velocities = self.clip_abs_velocities()
        vx = velocities[0]
        vz = velocities[2]
        return math.hypot(vx, vz) + self.current_speed_factor

    @property
    def is_on_ladder(self):
        return self.grid.aabb_on_ladder(self.aabb)

    @property
    def is_in_web(self):
        bb = self.aabb.expand(dx=-0.001, dy=-0.001, dz=-0.001)
        for blk in self.grid.blocks_in_aabb(bb):
            if isinstance(blk, blocks.Cobweb):
                return True
        return False

    @property
    def head_inside_water(self):
        return self.grid.aabb_eyelevel_inside_water(self.aabb)

    def do_block_collision(self):
        bb = self.aabb.expand(-0.001, -0.001, -0.001)
        for blk in self.grid.blocks_in_aabb(bb):
            blk.on_entity_collided(self)

    @property
    def is_sneaking(self):
        return self.action == 1

    def start_sneaking(self):
        self.set_action(1)

    def stop_sneaking(self):
        self.set_action(2)

    def is_offset_in_liquid(self, dx, dy, dz):
        bb = self.aabb.offset(dx, dy, dz)
        if self.grid.aabb_collides(bb):
            return False
        else:
            return not self.grid.is_any_liquid(bb)

    def do_respawn(self):
        self.send_packet("client statuses", {"status": 1})

    def health_update(self, health, food, food_saturation):
        log.msg("current health %s food %s saturation %s" % (
            health, food, food_saturation))
        if health <= 0:
            self.on_death()

    def login_data(self, eid, level_type, mode,
                   dimension, difficulty, players):
        self.eid = eid
        self.world.entities.entities[eid] = EntityBot(eid=eid, x=0, y=0, z=0)

    def respawn_data(self, dimension, difficulty,
                     mode, world_height, level_type):
        # TODO
        # ignore the details now
        # should clear the world(chunks, entities, etc.)
        # signs can stay self.grid.navgrid.reset_signs()
        pass

    def on_death(self):
        self.location_received = False
        self.spawn_point_received = False
        tools.do_later(1.0, self.do_respawn)
        #TODO self.world_erase()

    @property
    def standing_on_block(self):
        return self.grid.standing_on_block(self.aabb)

    @property
    def is_standing(self):
        col_d, _ = self.grid.min_collision_between(
            self.aabb, self.aabb - (0, 1, 0))
        if col_d is None:
            stand = False
        else:
            stand = fops.eq(col_d, 0)
        return stand

    def on_standing_ready(self):
        if self.check_location_received:
            block = self.standing_on_block
            if block is None:
                return
            log.msg("Standing on block %s" % block)
            if not self.world.navgrid.graph.has_node(block.coords):
                self.world.navgrid.block_change(None, block)
            self.check_location_received = False
