

import math

import config
import utils
import packets
import logbot
import fops
import blocks
import behavior_tree as bt
from axisbox import AABB


log = logbot.getlogger("BOT_ENTITY")


class BotObject(object):
    def __init__(self):
        self.velocities = utils.Vector(0.0, 0.0, 0.0)
        self.direction = utils.Vector2D(0, 0)
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
        self._action = self.action
        self.is_jumping = False
        self.hold_position_flag = True

    def set_xyz(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z
        self._aabb = AABB.from_player_coords(self.position)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def z(self):
        return self._z

    @property
    def position(self):
        return utils.Vector(self.x, self.y, self.z)

    @property
    def position_grid(self):
        return utils.Vector(self.grid_x, self.grid_y, self.grid_z)

    @property
    def position_eyelevel(self):
        return utils.Vector(self.x, self.y_eyelevel, self.z)

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
        self.behavior_tree = bt.BehaviorTree(self.world, self)

    def on_connection_lost(self):
        if self.location_received:
            self.location_received = False
            self.chunks_ready = False

    def new_location(self, x, y, z, stance, grounded, yaw, pitch):
        self.bot_object.set_xyz(x, y, z)
        self.bot_object.stance_diff = stance - y
        self.bot_object.on_ground = grounded
        self.bot_object.yaw = yaw
        self.bot_object.pitch = pitch
        self.bot_object.velocities = utils.Vector(0.0, 0.0, 0.0)
        self.check_location_received = True
        if self.location_received is False:
            self.location_received = True
        if not self.in_complete_chunks(self.bot_object):
            log.msg("Server sent me into incomplete chunks, will wait until they load up.")
            self.ready = False

    def in_complete_chunks(self, b_obj):
        return self.world.grid.aabb_in_complete_chunks(b_obj.aabb)

    def tick(self):
        if self.location_received is False:
            return
        if not self.ready:
            self.ready = self.in_complete_chunks(self.bot_object) and self.spawn_point_received
            if not self.ready:
                return
        self.move(self.bot_object)
        self.bot_object.direction = utils.Vector2D(0, 0)
        self.send_location(self.bot_object)
        self.send_action(self.bot_object)
        self.stop_sneaking(self.bot_object)
        if not self.i_am_dead:
            utils.do_now(self.behavior_tree.tick)

    def send_location(self, b_obj):
        self.world.send_packet("player position&look", {
            "position": packets.Container(x=b_obj.x, y=b_obj.y, z=b_obj.z,
                                          stance=b_obj.stance),
            "orientation": packets.Container(yaw=b_obj.yaw, pitch=b_obj.pitch),
            "grounded": packets.Container(grounded=b_obj.on_ground)})

    def send_action(self, b_obj):
        """
        sneaking, not sneaking, leave bed, start sprinting, stop sprinting
        """
        if b_obj.action != b_obj._action:
            b_obj.action = b_obj._action
            self.send_packet("entity action", {"eid": self.eid, "action": b_obj._action})

    def turn_to_point(self, b_obj, point):
        if point.x == b_obj.x and point.z == b_obj.z:
            return
        yaw, pitch = utils.yaw_pitch_between(point, b_obj.position_eyelevel)
        if yaw is None or pitch is None:
            return
        b_obj.yaw = yaw
        b_obj.pitch = pitch

    def turn_to_direction(self, b_obj, x, y, z):
        if x == 0 and z == 0:
            return
        yaw, pitch = utils.vector_to_yaw_pitch(x, y, z)
        b_obj.yaw = yaw
        b_obj.pitch = pitch

    def turn_to_vector(self, b_obj, vect):
        if vect.x == 0 and vect.z == 0:
            return
        yaw, pitch = utils.vector_to_yaw_pitch(vect.x, vect.y, vect.z)
        b_obj.yaw = yaw
        b_obj.pitch = pitch

    def clip_abs_velocities(self, b_obj):
        if abs(b_obj.velocities.x) < 0.005:  # minecraft value
            b_obj.velocities.x = 0
        if abs(b_obj.velocities.y) < 0.005:  # minecraft value
            b_obj.velocities.y = 0
        if abs(b_obj.velocities.z) < 0.005:  # minecraft value
            b_obj.velocities.z = 0

    def clip_ladder_velocities(self, b_obj):
        if self.is_on_ladder(b_obj):
            if b_obj.velocities.y < -0.15:
                b_obj.velocities.y = -0.15
            if abs(b_obj.velocities.x) > 0.15:
                b_obj.velocities.x = math.copysign(0.15, b_obj.velocities.x)
            if abs(b_obj.velocities.z) > 0.15:
                b_obj.velocities.z = math.copysign(0.15, b_obj.velocities.z)
        if self.is_sneaking(b_obj) and b_obj.velocities.y < 0:
            b_obj.velocities.y = 0

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
            b_obj.velocities.x = 0
            b_obj.velocities.y = 0
            b_obj.velocities.z = 0
        aabbs = self.world.grid.collision_aabbs_in(b_obj.aabb.extend_to(vx, vy, vz))
        b_bb = b_obj.aabb
        dy = vy
        if not fops.eq(vy, 0):
            for bb in aabbs:
                dy = b_bb.calculate_axis_offset(bb, dy, 1)
            b_bb = b_bb.offset(dy=dy)
        dx = vx
        if not fops.eq(vx, 0):
            for bb in aabbs:
                dx = b_bb.calculate_axis_offset(bb, dx, 0)
            b_bb = b_bb.offset(dx=dx)
        dz = vz
        if not fops.eq(vz, 0):
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
            b_obj.velocities.x = 0
        if not fops.eq(vy, dy):
            b_obj.velocities.y = 0
        if not fops.eq(vz, dz):
            b_obj.velocities.z = 0
        b_obj.set_xyz(b_bb.posx, b_bb.min_y, b_bb.posz)
        self.do_block_collision(b_obj)

    def move(self, b_obj):
        self.clip_abs_velocities(b_obj)
        is_in_water = self.handle_water_movement(b_obj)
        is_in_lava = self.handle_lava_movement(b_obj)
        if b_obj.is_jumping:
            if is_in_water or is_in_lava:
                b_obj.velocities.y += config.SPEED_LIQUID_JUMP
            elif b_obj.on_ground:
                b_obj.velocities.y = config.SPEED_JUMP
            elif self.is_on_ladder(b_obj):
                b_obj.velocities.y = config.SPEED_CLIMB
            b_obj.is_jumping = False
        if is_in_water:
            if b_obj.hold_position_flag:
                b_obj.velocities.y = 0
            orig_y = b_obj.y
            self.update_directional_speed(b_obj, 0.02, balance=True)
            self.move_collisions(b_obj, b_obj.velocities.x, b_obj.velocities.y, b_obj.velocities.z)
            b_obj.velocities.x *= 0.8
            b_obj.velocities.y *= 0.8
            b_obj.velocities.z *= 0.8
            b_obj.velocities.y -= 0.02
            if b_obj.is_collided_horizontally and \
                    self.is_offset_in_liquid(b_obj, b_obj.velocities.x,
                                             b_obj.velocities.y + 0.6 -
                                             b_obj.y + orig_y,
                                             b_obj.velocities.z):
                b_obj.velocities.y = 0.3
        elif is_in_lava:
            if b_obj.hold_position_flag:
                b_obj.velocities.y = 0
            orig_y = b_obj.y
            self.update_directional_speed(b_obj, 0.02)
            self.move_collisions(b_obj, b_obj.velocities.x, b_obj.velocities.y, b_obj.velocities.z)
            b_obj.velocities.x *= 0.5
            b_obj.velocities.y *= 0.5
            b_obj.velocities.z *= 0.5
            b_obj.velocities.y -= 0.02
            if b_obj.is_collided_horizontally and \
                    self.is_offset_in_liquid(b_obj, self.velocities.x,
                                             self.velocities.y + 0.6 -
                                             self.y + orig_y,
                                             self.velocities.z):
                self.velocities.y = 0.3
        else:
            if self.is_on_ladder(b_obj) and b_obj.hold_position_flag:
                self.start_sneaking(b_obj)
            slowdown = self.current_slowdown(b_obj)
            self.update_directional_speed(b_obj, self.current_speed_factor(b_obj))
            self.clip_ladder_velocities(b_obj)
            self.move_collisions(b_obj, b_obj.velocities.x, b_obj.velocities.y, b_obj.velocities.z)
            if b_obj.is_collided_horizontally and self.is_on_ladder(b_obj):
                b_obj.velocities.y = 0.2
            b_obj.velocities.y -= config.BLOCK_FALL
            b_obj.velocities.y *= config.DRAG
            b_obj.velocities.x *= slowdown
            b_obj.velocities.z *= slowdown

    def directional_speed(self, direction, speedf):
        dx = direction.x * speedf
        dz = direction.z * speedf
        return utils.Vector2D(dx, dz)

    def update_directional_speed(self, b_obj, speedf, balance=False):
        direction = self.directional_speed(b_obj.direction, speedf)
        if balance and direction.size > 0:
            perpedicular_dir = utils.Vector2D(- direction.z, direction.x)
            dot = (b_obj.velocities.x * perpedicular_dir.x + b_obj.velocities.z * perpedicular_dir.z) / \
                (perpedicular_dir.x * perpedicular_dir.x + perpedicular_dir.z * perpedicular_dir.z)
            if dot < 0:
                dot *= -1
                perpedicular_dir = utils.Vector2D(direction.z, - direction.x)
            direction = utils.Vector2D(direction.x - perpedicular_dir.x * dot, direction.z - perpedicular_dir.z * dot)
            self.turn_to_direction(b_obj, direction.x, 0, direction.z)
        if balance and b_obj.hold_position_flag:
            self.turn_to_direction(b_obj, -b_obj.velocities.x, 0, -b_obj.velocities.z)
            b_obj.velocities.x = 0
            b_obj.velocities.z = 0
        b_obj.velocities.x += direction.x
        b_obj.velocities.z += direction.z

    def current_slowdown(self, b_obj):
        slowdown = 0.91
        if b_obj.on_ground:
            slowdown = 0.546
            block = self.world.grid.get_block(b_obj.grid_x, b_obj.grid_y - 1, b_obj.grid_z)
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
        self.clip_abs_velocities(b_obj)
        vx = b_obj.velocities.x
        vz = b_obj.velocities.z
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

    def standing_on_block(self, b_obj):
        return self.world.grid.standing_on_block(b_obj.aabb)

    def is_standing(self, b_obj):
        return self.standing_on_block(b_obj) is not None

