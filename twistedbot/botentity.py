

import math
from datetime import datetime

import config
import tools
import packets
import logbot
import fops
import blocks
from axisbox import AABB


log = logbot.getlogger("BOT_ENTITY")


class Bot(object):
    def __init__(self, world, name):
        self.world = world
        self.name = name
        self.eid = None
        self.velocities = [0.0, 0.0, 0.0]
        self.direction = [0, 0]
        self.x = 0
        self.y = 0
        self.z = 0
        self.chunks_ready = False
        self.stance_diff = config.PLAYER_EYELEVEL
        self.pitch = None
        self.yaw = None
        self.on_ground = False
        self.ready = False
        self.location_received = False
        self.check_location_received = False
        self.spawn_point_received = False
        self.last_time = datetime.now()
        self.period_time_estimation = 1 / 20.0
        self.is_collided_horizontally = False
        self.horizontally_blocked = False
        self.is_in_water = False
        self.is_in_lava = False
        self.action = 2  # normal
        self.is_jumping = False
        self.floating_flag = True
        self.turn_to_setup = None

    def connection_lost(self):
        if self.location_received:
            self.location_received = False
            self.chunks_ready = False

    def shutdown(self):
        """ save anything that needs to be saved and shutdown"""
        log.msg("Gracefully shutting down.......")

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
        return (self.world.grid_x, self.world.grid_y, self.world.grid_z)

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

    def tick(self):
        tick_start = datetime.now()
        if self.location_received is False:
            self.last_tick_time = tick_start
            return config.TIME_STEP
        if not self.ready:
            self.ready = self.in_complete_chunks and self.spawn_point_received
            if not self.ready:
                self.last_tick_time = tick_start
                return config.TIME_STEP
        self.move(direction=self.direction)
        self.direction = [0, 0]
        self.send_location()
        tools.do_later(0, self.on_standing_ready)
        tools.do_later(0, self.world.behaviour_manager.run)
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

    def send_location(self):
        self.world.send_packet("player position&look", {
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
        aabbs = self.world.grid.aabbs_in(self.aabb.extend_to(0, v, 0))
        for bb in aabbs:
            v = self.aabb.calculate_axis_offset(bb, v, 1)
        ab = self.aabb.offset(dy=v)
        self.y = ab.posy

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
        top_y = tools.grid_shift(bb.max_y + 1)
        for blk in self.world.grid.blocks_in_aabb(bb):
            if isinstance(blk, blocks.BlockWater):
                if top_y >= (blk.y + 1 - blk.height_percent):
                    is_in_water = True
                    water_current = blk.add_velocity_to(water_current)
        if tools.vector_size(water_current) > 0:
            water_current = tools.normalize(water_current)
            wconst = 0.014
            water_current = (water_current[0] * wconst, water_current[
                             1] * wconst, water_current[2] * wconst)
        return is_in_water, water_current

    def handle_lava_movement(self, aabb=None):
        if aabb is None:
            aabb = self.aabb
        for blk in self.world.grid.blocks_in_aabb(
                aabb.expand(-0.10000000149011612,
                            -0.4000000059604645,
                            -0.10000000149011612)):
            if isinstance(blk, blocks.BlockLava):
                return True
        return False

    def move_collisions(self):
        zero_vels = False
        if self.is_in_web:
            self.velocities[0] *= 0.25
            self.velocities[1] *= 0.05000000074505806
            self.velocities[2] *= 0.25
            zero_vels = True
        aabbs = self.world.grid.aabbs_in(self.aabb.extend_to(
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
                    b_up = self.world.grid.get_block(x, y + 1, z)
                    b_down = self.world.grid.get_block(x, y - 1, z)
                    b_cent = self.world.grid.get_block(x, y, z)
                    no_up = not b_up.is_water and b_down.collidable and fops.eq(b_down.max_y, y)
                    if (not no_up and b_cent.is_water and fops.gt(b_cent.y + 0.5, self.aabb.min_y)) or isinstance(b_up, blocks.StillWater):
                        self.velocities[1] += config.SPEED_LIQUID_JUMP
            self.velocities = [self.velocities[0] + water_current[0],
                               self.velocities[1] + water_current[1],
                               self.velocities[2] + water_current[2]]
            orig_y = self.y
            self.update_directional_speed(
                direction, 0.02, balance=True)
            self.move_collisions()
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
            self.move_collisions()
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
            self.move_collisions()
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
            block = self.world.grid.get_block(
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
        return self.world.grid.aabb_on_ladder(self.aabb)

    @property
    def is_in_web(self):
        bb = self.aabb.expand(dx=-0.001, dy=-0.001, dz=-0.001)
        for blk in self.world.grid.blocks_in_aabb(bb):
            if isinstance(blk, blocks.Cobweb):
                return True
        return False

    @property
    def head_inside_water(self):
        return self.world.grid.aabb_eyelevel_inside_water(self.aabb)

    def do_block_collision(self):
        bb = self.aabb.expand(-0.001, -0.001, -0.001)
        for blk in self.world.grid.blocks_in_aabb(bb):
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
        if self.world.grid.aabb_collides(bb):
            return False
        else:
            return not self.world.grid.is_any_liquid(bb)

    def do_respawn(self):
        self.send_packet("client statuses", {"status": 1})

    def health_update(self, health, food, food_saturation):
        log.msg("current health %s food %s saturation %s" % (
            health, food, food_saturation))
        if health <= 0:
            self.on_death()

    def on_death(self):
        self.location_received = False
        self.spawn_point_received = False
        tools.do_later(1.0, self.do_respawn)

    @property
    def standing_on_block(self):
        return self.world.grid.standing_on_block(self.aabb)

    @property
    def is_standing(self):
        col_d, _ = self.world.grid.min_collision_between(
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

    def update_experience(self, experience_bar=None, level=None, total_experience=None):
        pass
