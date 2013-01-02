

import math
from datetime import datetime

import config
import utils
import packets
import logbot
import fops
import blocks
import behaviours
from axisbox import AABB


log = logbot.getlogger("BOT_ENTITY")


class BotObject(object):
    def __init__(self):
        self.velocities = utils.Vector(0.0, 0.0, 0.0)
        self.direction = [0, 0]
        self._x = 0
        self._y = 0
        self._z = 0
        self.stance_diff = config.PLAYER_EYELEVEL
        self.pitch = None
        self.yaw = None
        self.on_ground = False
        self.is_collided_horizontally = False
        self.horizontally_blocked = False
        self.action = 2  # normal
        self.is_jumping = False
        self.floating_flag = True

    def set_xyz(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z
        self._aabb = AABB.from_player_coords(self.x, self.y, self.z)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, v):
        self._y = v
        self._aabb = AABB.from_player_coords(self.position)

    @property
    def z(self):
        return self._z

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
        return utils.grid_shift(self.x)

    @property
    def grid_y(self):
        return utils.grid_shift(self.y)

    @property
    def grid_z(self):
        return utils.grid_shift(self.z)

    @property
    def aabb(self):
        return self._aabb

    @aabb.setter
    def aabb(self, v):
        raise Exception('setting bot aabb')


class BotEntity(object):
    def __init__(self, world, name):
        self.world = world
        self.name = name
        self.bot_object = BotObject()
        self.eid = None
        self.chunks_ready = False
        self.ready = False
        self.i_am_dead = False
        self.location_received = False
        self.check_location_received = False
        self.spawn_point_received = False
        self.last_tick_time = datetime.now()
        self.period_time_estimation = 1 / 20.0
        self.behaviour_manager = behaviours.BehaviourManager(self.world, self)

    def on_connection_lost(self):
        if self.location_received:
            self.location_received = False
            self.chunks_ready = False

    def on_new_location(self, kw):
        self.bot_object.set_xyz(kw["x"], kw["y"], kw["z"])
        self.bot_object.stance_diff = kw["stance"] - kw["y"]
        self.bot_object.on_ground = kw["grounded"]
        self.bot_object.yaw = kw["yaw"]
        self.bot_object.pitch = kw["pitch"]
        self.bot_object.velocities = [0.0, 0.0, 0.0]
        self.check_location_received = True
        if self.location_received is False:
            self.location_received = True
        if not self.in_complete_chunks(self.bot_object):
            log.msg("Server send location into incomplete chunks")
            self.ready = False

    def in_complete_chunks(self, b_obj):
        return self.world.grid.aabb_in_complete_chunks(b_obj.aabb)

    def tick(self):
        tick_start = datetime.now()
        if self.location_received is False:
            self.last_tick_time = tick_start
            return config.TIME_STEP
        if not self.ready:
            self.ready = self.in_complete_chunks(self.bot_object) and self.spawn_point_received
            if not self.ready:
                self.last_tick_time = tick_start
                return config.TIME_STEP
        self.move(self.bot_object)
        self.bot_object.direction = [0, 0]
        self.send_location(self.bot_object)
        if not self.i_am_dead:
            #print self.behaviour_manager.bqueue, self.behaviour_manager.default_behaviour
            utils.do_later(0, self.behaviour_manager.run)
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

    def send_location(self, b_obj):
        self.world.send_packet("player position&look", {
            "position": packets.Container(x=b_obj.x, y=b_obj.y, z=b_obj.z,
                                          stance=b_obj.stance),
            "orientation": packets.Container(yaw=b_obj.yaw, pitch=b_obj.pitch),
            "grounded": packets.Container(grounded=b_obj.on_ground)})

    def set_action(self, action_id):
        """
        sneaking, not sneaking, leave bed, start sprinting, stop sprinting
        """
        if self.action != action_id:
            self.action = action_id
        self.send_packet(
            "entity action", {"eid": self.eid, "action": self.action})

    def turn_to_point(self, b_obj, point):
        if point[0] == b_obj.x and point[2] == b_obj.z:
            return
        yaw, pitch = utils.yaw_pitch_between(point, b_obj.position_eyelevel)
        if yaw is None or pitch is None:
            return
        b_obj.yaw = yaw
        b_obj.pitch = pitch

    def turn_to_direction(self, b_obj, x, z):
        if x == 0 and z == 0:
            return
        yaw, _ = utils.yaw_pitch_to_vector(x, 0, z)
        b_obj.yaw = yaw
        b_obj.pitch = 0

    def clip_abs_velocities(self, b_obj):
        for i in xrange(3):
            if abs(b_obj.velocities[i]) < 0.005:  # minecraft value
                b_obj.velocities[i] = 0

    def clip_ladder_velocities(self, b_obj):
        if self.is_on_ladder(b_obj):
            for i in xrange(3):
                if i == 1:
                    if b_obj.velocities[i] < -0.15:
                        b_obj.velocities[i] = -0.15
                elif abs(b_obj.velocities[i]) > 0.15:
                    b_obj.velocities[i] = math.copysign(0.15, b_obj.velocities[i])
        if self.is_sneaking(b_obj) and b_obj.velocities[1] < 0:
            b_obj[1] = 0

    def handle_water_movement(self, b_obj):
        is_in_water = False
        water_current = utils.Vector(0, 0, 0)
        bb = b_obj.aabb.expand(-0.001, -0.401, -0.001)
        top_y = utils.grid_shift(bb.max_y + 1)
        for blk in self.world.grid.blocks_in_aabb(bb):
            if isinstance(blk, blocks.BlockWater):
                if top_y >= (blk.y + 1 - blk.height_percent):
                    is_in_water = True
                    water_current = blk.add_velocity_to(water_current)
        if water_current.size > 0:
            water_current.normalize()
            wconst = 0.014
            water_current = water_current * wconst
            b_obj.velocities = b_obj.velocities + water_current
        return is_in_water

    def handle_lava_movement(self, b_obj):
        for blk in self.world.grid.blocks_in_aabb(
                b_obj.aabb.expand(-0.1,
                                  -0.4,
                                  -0.1)):
            if isinstance(blk, blocks.BlockLava):
                return True
        return False

    def move_collisions(self, b_obj, vx, vy, vz):
        if self.is_in_web(b_obj):
            vx *= 0.25
            vy *= 0.05000000074505806
            vz *= 0.25
            b_obj.velocities[0] = 0
            b_obj.velocities[1] = 0
            b_obj.velocities[2] = 0
        aabbs = self.world.grid.collision_aabbs_in(b_obj.aabb.extend_to(vx, vy, vz))
        b_bb = b_obj.aabb
        dy = vy
        for bb in aabbs:
            dy = b_bb.calculate_axis_offset(bb, dy, 1)
        b_bb = b_bb.offset(dy=dy)
        dx = vx
        for bb in aabbs:
            dx = b_bb.calculate_axis_offset(bb, dx, 0)
        b_bb = b_bb.offset(dx=dx)
        dz = vz
        for bb in aabbs:
            dz = b_bb.calculate_axis_offset(bb, dz, 2)
        b_bb = b_bb.offset(dz=dz)
        if vy != dy and vy < 0 and (dx != vx or dz != vz):
            st = config.MAX_STEP_HEIGHT
            aabbs = self.world.grid.collision_aabbs_in(b_obj.aabb.extend_to(vx, st, vz))
            b_bbs = b_obj.aabb
            dys = st
            for bb in aabbs:
                dys = b_bbs.calculate_axis_offset(bb, dys, 1)
            b_bbs = b_bbs.offset(dy=dys)
            dxs = vx
            for bb in aabbs:
                dxs = b_bbs.calculate_axis_offset(bb, dxs, 0)
            b_bbs = b_bbs.offset(dx=dxs)
            dzs = vz
            for bb in aabbs:
                dzs = b_bbs.calculate_axis_offset(bb, dzs, 2)
            b_bbs = b_bbs.offset(dz=dzs)
            if fops.gt(dxs * dxs + dzs * dzs, dx * dx + dz * dz):
                dx = dxs
                dy = dys
                dz = dzs
                b_bb = b_bbs
        b_obj.on_ground = vy != dy and vy < 0
        b_obj.is_collided_horizontally = dx != vx or dz != vz
        b_obj.horizontally_blocked = not fops.eq(dx, vx) and not fops.eq(dz, vz)
        if not fops.eq(vx, dx):
            b_obj.velocities[0] = 0
        if not fops.eq(vy, dy):
            b_obj.velocities[1] = 0
        if not fops.eq(vz, dz):
            b_obj.velocities[2] = 0
        b_obj.set_xyz(b_bb.posx, b_bb.min_y, b_bb.posz)
        self.do_block_collision(b_obj)

    def move(self, b_obj):
        self.clip_abs_velocities(b_obj)
        is_in_water = self.handle_water_movement(b_obj)
        is_in_lava = self.handle_lava_movement(b_obj)
        if b_obj.is_jumping:
            if is_in_water or is_in_lava:
                b_obj.velocities[1] += config.SPEED_LIQUID_JUMP
            elif b_obj.on_ground:
                b_obj.velocities[1] = config.SPEED_JUMP
            elif self.is_on_ladder(b_obj):
                b_obj.velocities[1] = config.SPEED_CLIMB
            b_obj.is_jumping = False
        if is_in_water:
            if b_obj.floating_flag:
                if self.head_inside_water(b_obj):
                    b_obj.velocities[1] += config.SPEED_LIQUID_JUMP
                else:
                    x, y, z = b_obj.aabb.grid_bottom_center
                    b_up = self.world.grid.get_block(x, y + 1, z)
                    b_down = self.world.grid.get_block(x, y - 1, z)
                    b_cent = self.world.grid.get_block(x, y, z)
                    no_up = not b_up.is_water and b_down.collidable and fops.eq(b_down.max_y, y)
                    if (not no_up and b_cent.is_water and fops.gt(b_cent.y + 0.5, b_obj.aabb.min_y)) or isinstance(b_up, blocks.StillWater):
                        b_obj.velocities[1] += config.SPEED_LIQUID_JUMP
            orig_y = b_obj.y
            self.update_directional_speed(b_obj, 0.02, balance=True)
            self.move_collisions(b_obj, b_obj.velocities[0], b_obj.velocities[1], b_obj.velocities[2])
            b_obj.velocities[0] *= 0.8
            b_obj.velocities[1] *= 0.8
            b_obj.velocities[2] *= 0.8
            b_obj.velocities[1] -= 0.02
            if b_obj.is_collided_horizontally and \
                    self.is_offset_in_liquid(b_obj, b_obj.velocities[0],
                                             b_obj.velocities[1] + 0.6 -
                                             b_obj.y + orig_y,
                                             b_obj.velocities[2]):
                b_obj.velocities[1] = 0.3
        elif is_in_lava:
            orig_y = self.y
            self.update_directional_speed(b_obj, 0.02)
            self.move_collisions(b_obj, b_obj.velocities[0], b_obj.velocities[1], b_obj.velocities[2])
            b_obj.velocities[0] *= 0.5
            b_obj.velocities[1] *= 0.5
            b_obj.velocities[2] *= 0.5
            b_obj.velocities[1] -= 0.02
            if b_obj.is_collided_horizontally and \
                    self.is_offset_in_liquid(b_obj, self.velocities[0],
                                             self.velocities[1] + 0.6 -
                                             self.y + orig_y,
                                             self.velocities[2]):
                self.velocities[1] = 0.3
        else:
            slowdown = self.current_slowdown(b_obj)
            self.update_directional_speed(b_obj, self.current_speed_factor(b_obj))
            self.clip_ladder_velocities(b_obj)
            self.move_collisions(b_obj, b_obj.velocities[0], b_obj.velocities[1], b_obj.velocities[2])
            if b_obj.is_collided_horizontally and self.is_on_ladder(b_obj):
                b_obj.velocities[1] = 0.2
            b_obj.velocities[1] -= config.BLOCK_FALL
            b_obj.velocities[1] *= config.DRAG
            b_obj.velocities[0] *= slowdown
            b_obj.velocities[2] *= slowdown

    def directional_speed(self, direction, speedf):
        x, z = direction
        dx = x * speedf
        dz = z * speedf
        return (dx, dz)

    def update_directional_speed(self, b_obj, speedf, balance=False):
        direction = self.directional_speed(b_obj.direction, speedf)
        if balance and utils.vector_size(direction) > 0:
            perpedicular_dir = (- direction[1], direction[0])
            dot = (b_obj.velocities[0] * perpedicular_dir[0] + b_obj.velocities[2] * perpedicular_dir[1]) / \
                (perpedicular_dir[0] * perpedicular_dir[0] + perpedicular_dir[1] * perpedicular_dir[1])
            if dot < 0:
                dot *= -1
                perpedicular_dir = (direction[1], - direction[0])
            direction = (direction[0] - perpedicular_dir[0] * dot, direction[1] - perpedicular_dir[1] * dot)
            self.turn_to_direction(b_obj, direction[0], direction[1])
        b_obj.velocities[0] += direction[0]
        b_obj.velocities[2] += direction[1]

    def current_slowdown(self, b_obj):
        slowdown = 0.91
        if b_obj.on_ground:
            slowdown = 0.546
            block = self.world.grid.get_block(
                b_obj.grid_x, b_obj.grid_y - 1, b_obj.grid_z)
            if block is not None:
                slowdown = block.slipperiness * 0.91
        return slowdown

    def current_speed_factor(self, b_obj):
        if b_obj.on_ground:
            slowdown = self.current_slowdown(b_obj)
            modf = 0.16277136 / (slowdown * slowdown * slowdown)
            factor = config.SPEED_ON_GROUND * modf
        else:
            factor = config.SPEED_IN_AIR
        return factor * 0.98

    def current_motion(self, b_obj):
        #TODO
        # check if in water or lava -> factor = 0.2
        # else check ladder and clip if necessary
        self.clip_abs_velocities(b_obj)
        vx = b_obj.velocities[0]
        vz = b_obj.velocities[2]
        return math.hypot(vx, vz) + self.current_speed_factor(b_obj)

    def is_on_ladder(self, b_obj):
        return self.world.grid.aabb_on_ladder(b_obj.aabb)

    def is_in_water(self, b_obj):
        is_in_water = False
        bb = b_obj.aabb.expand(-0.001, -0.4010000059604645, -0.001)
        top_y = utils.grid_shift(bb.max_y + 1)
        for blk in self.world.grid.blocks_in_aabb(bb):
            if isinstance(blk, blocks.BlockWater):
                if top_y >= (blk.y + 1 - blk.height_percent):
                    is_in_water = True
        return is_in_water

    def is_in_web(self, b_obj):
        bb = b_obj.aabb.expand(dx=-0.001, dy=-0.001, dz=-0.001)
        for blk in self.world.grid.blocks_in_aabb(bb):
            if isinstance(blk, blocks.Cobweb):
                return True
        return False

    def head_inside_water(self, b_obj):
        return self.world.grid.aabb_eyelevel_inside_water(b_obj.aabb)

    def do_block_collision(self, b_obj):
        bb = b_obj.aabb.expand(-0.001, -0.001, -0.001)
        for blk in self.world.grid.blocks_in_aabb(bb):
            blk.on_entity_collided(b_obj)

    def is_sneaking(self, b_obj):
        return b_obj.action == 1

    def start_sneaking(self, b_obj):
        b_obj.action = 1

    def stop_sneaking(self, b_obj):
        b_obj.action = 2

    def is_offset_in_liquid(self, b_obj, dx, dy, dz):
        bb = b_obj.aabb.offset(dx, dy, dz)
        if self.world.grid.aabb_collides(bb):
            return False
        else:
            return not self.world.grid.is_any_liquid(bb)

    def do_respawn(self):
        self.world.send_packet("client statuses", {"status": 1})

    def on_health_update(self, health, food, food_saturation):
        log.msg("current health %s food %s saturation %s" % (health, food, food_saturation))
        if health <= 0:
            self.on_death()

    def on_death(self):
        log.msg("I am dead")
        self.i_am_dead = True
        utils.do_later(2.0, self.do_respawn)

    def standing_on_block(self, b_obj):
        return self.world.grid.standing_on_block(b_obj.aabb)

    def is_standing(self, b_obj):
        return self.standing_on_block(b_obj) is not None

    def on_update_experience(self, experience_bar=None, level=None, total_experience=None):
        pass
