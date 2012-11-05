
import math

from twisted.internet.task import cooperate
from twisted.internet.defer import inlineCallbacks, returnValue

import config
import tools

import logbot
import fops
from gridspace import GridSpace
from pathfinding import AStar

log = logbot.getlogger("BEHAVIOURS")


class Status(object):
    success = 20
    failure = 30
    running = 40
    suspended = 50


class BehaviourManager(object):
    def __init__(self, bot):
        self.bot = bot
        self.grid = self.bot.world.grid
        self.bqueue = []
        self.default_behaviour = LookAtPlayerBehaviour(self, self.bot)
        self.running = False
        self.new_command = None

    @property
    def current_behaviour(self):
        if self.bqueue:
            return self.bqueue[-1]
        else:
            return self.default_behaviour

    def run(self):
        if self.running:
            return
        self.tick()

    @inlineCallbacks
    def tick(self):
        self.running = True
        try:
            while 1:
                self.check_new_command()
                g = self.current_behaviour
                ignore = yield g.tick()
                self.bot.floating_flag = g.floating_flag
                if g.status == Status.running:
                    break
                elif g.status == Status.suspended:
                    ignore = yield tools.reactor_break()
                    continue
                else:
                    ignore = yield tools.reactor_break()
                    g.return_to_parent()
        except:
            logbot.exit_on_error()
        self.running = False

    def cancel_running(self):
        if self.bqueue:
            log.msg('Cancelling %s' % self.bqueue[0])
        for b in self.bqueue:
            b.cancel()
        self.bqueue = []

    def check_new_command(self):
        if self.new_command is not None:
            self.cancel_running()
            behaviour, args, kwargs = self.new_command
            self.bqueue.append(behaviour(manager=self, parent=None, *args, **kwargs))
            self.new_command = None

    def command(self, behaviour, *args, **kwargs):
        self.new_command = (behaviour, args, kwargs)
        log.msg("Added command %s" % self.current_behaviour.name)


class BehaviourBase(object):
    def __init__(self, manager=None, parent=None, **kwargs):
        self.manager = manager
        self.bot = manager.bot
        self.parent = parent
        self.world = self.bot.world
        self.grid = self.world.grid
        self.cancelled = False
        self.status = Status.running
        self.floating_flag = True

    @inlineCallbacks
    def tick(self):
        if self.cancelled:
            returnValue(None)
        ignore = yield self._tick()

    def cancel(self):
        self.cancelled = True

    def _tick(self):
        pass

    def from_child(self):
        pass

    def add_subbehaviour(self, behaviour, *args, **kwargs):
        g = behaviour(manager=self.manager, parent=self, **kwargs)
        self.manager.bqueue.append(g)
        self.status = Status.suspended

    def return_to_parent(self):
        self.manager.bqueue.pop()
        if self.parent is not None:
            self.parent.from_child(self)


class LookAtPlayerBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(LookAtPlayerBehaviour, self).__init__(*args, **kwargs)
        self.name = 'Look at player %s' % config.COMMANDER
        log.msg(self.name)

    def _tick(self):
        eid = self.bot.commander.eid
        if eid is None:
            return
        player = self.world.entities.get_entity(eid)
        if player is None:
            return
        p = player.position
        self.bot.set_turn_to((p[0], p[1] + config.PLAYER_EYELEVEL, p[2]), elevation=True)


class WalkSignsBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(WalkSignsBehaviour, self).__init__(*args, **kwargs)
        self.signpoint = None
        self.group = kwargs.get("group")
        self.walk_type = kwargs.get("type")
        self.name = '%s signs in group "%s"' % (self.walk_type.capitalize(), self.group)
        self.activate()
        log.msg(self.name)

    def activate(self):
        if self.walk_type == "circulate":
            self.next_sign = \
                self.bot.world.navgrid.sign_waypoints.get_groupnext_circulate
        elif self.walk_type == "rotate":
            self.next_sign = \
                self.bot.world.navgrid.sign_waypoints.get_groupnext_rotate
        else:
            raise Exception("unknown walk type")
        self.bot.world.navgrid.sign_waypoints.reset_group(self.group)

    def from_child(self, g):
        self.status = Status.running

    def _tick(self):
        if not self.bot.world.navgrid.sign_waypoints.has_group(self.group):
            self.bot.chat_message("cannnot %s group named %s" % (self.walk_type, self.group))
            self.status = Status.failure
            return
        self.signpoint = self.next_sign(self.group)
        if self.signpoint is not None:
            if not self.grid.check_sign(self.signpoint):
                return
            self.add_subbehaviour(TravelToBehaviour, coords=self.signpoint.nav_coords)
        else:
            self.status = Status.failure


class GoToSignBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(GoToSignBehaviour, self).__init__(*args, **kwargs)
        self.sign_name = kwargs.get("sign_name", "")
        self.name = 'Go to %s' % self.sign_name
        log.msg(self.name)

    def from_child(self, g):
        self.status = g.status

    def _tick(self):
        self.signpoint = self.bot.world.navgrid.sign_waypoints.get_namepoint(self.sign_name)
        if self.signpoint is None:
            self.signpoint = self.bot.world.navgrid.sign_waypoints.get_name_from_group(self.sign_name)
        if self.signpoint is None:
            self.bot.chat_message("cannot idetify sign with name %s" % self.sign_name)
            self.status = Status.failure
            return
        if not self.grid.check_sign(self.signpoint):
            self.status = Status.failure
            return
        self.add_subbehaviour(TravelToBehaviour, coords=self.signpoint.nav_coords)


class TravelToBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(TravelToBehaviour, self).__init__(*args, **kwargs)
        self.travel_coords = kwargs["coords"]
        self.ready = False
        log.msg(self.name)

    @property
    def name(self):
        return 'Travel to %s from %s' % (str(self.travel_coords), self.bot.standing_on_block)

    @inlineCallbacks
    def activate(self):
        sb = self.bot.standing_on_block
        if sb is None:
            self.ready = False
        else:
            astar = yield cooperate(AStar(self.bot.world.navgrid,
                                          sb.coords,
                                          self.travel_coords)).whenDone()
            if astar.path is None:
                self.status = Status.failure
            else:
                if self.bot.world.navgrid.check_path(astar.path):
                    self.path = astar.path
                    self.ready = True

    def from_child(self, g):
        self.status = Status.running
        if g.status != Status.success:
            self.ready = False

    def _tick(self):
        if not self.ready:
            self.activate()
            if self.status == Status.failure:
                return
            if not self.ready:
                return
        if self.path.has_next():
            gs = GridSpace(self.grid, coords=self.path.next_step().coords)
            if gs.can_stand_on:
                self.add_subbehaviour(MoveToBehaviour, target_space=gs)
            else:
                self.ready = False
        else:
            self.status = Status.success


class MoveToBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(MoveToBehaviour, self).__init__(*args, **kwargs)
        self.target_space = kwargs["target_space"]
        self.was_at_target = False
        self.floating_flag = False
        self.name = 'Move to %s' % str(self.target_space.block)
        #log.msg(self.name + ' from %s' % self.bot.aabb)

    def check_status(self):
        bb_stand = self.target_space.bb_stand
        elev = bb_stand.min_y - self.bot.aabb.min_y
        gs = GridSpace(self.grid, bb=self.bot.aabb)
        if not self.target_space._can_stand_on():
            self.grid.navgrid.delete_node(self.target_space.coords)
            log.msg('CANNOT STAND ON %s' % self.target_space)
            return Status.failure
        if not gs.can_go_between(self.target_space, debug=True):
            log.msg('CANNOT GO BETWEEN %s AND %s' % (self.bot.aabb, self.target_space))
            return Status.failure
        if self.bot.is_on_ladder or self.grid.aabb_in_water(self.bot.aabb):
            if self.bot.position_grid == self.target_space.coords:
                return Status.success
        if self.bot.aabb.horizontal_distance(bb_stand) < self.bot.current_motion:
            self.was_at_target = True
            if fops.eq(elev, 0):
                return Status.success
        if self.bot.horizontally_blocked and self.bot.on_ground:
            if not gs.can_go(self.target_space):
                log.msg("I am stuck, let's try again? vels %s" %
                        str(self.bot.velocities))
                return Status.failure
        return Status.running

    def _tick(self):
        self.status = self.check_status()
        if self.status != Status.running:
            return
        col_distance, col_bb = self.grid.min_collision_between(self.bot.aabb,
                                                               self.target_space.bb_stand,
                                                               horizontal=True,
                                                               max_height=True)
        if self.bot.is_on_ladder or self.grid.aabb_in_water(self.bot.aabb):
            elev = self.target_space.bb_stand.min_y - self.bot.aabb.min_y
            if fops.gt(elev, 0):
                self.jump()
                self.move()
            elif fops.lt(elev, 0):
                if col_distance is None:
                    self.move()
            else:
                self.move()
        elif self.bot.is_standing:
            if col_distance is None:
                self.move()
            else:
                elev = self.target_space.bb_stand.min_y - self.bot.aabb.min_y
                if fops.lte(elev, 0):
                    self.move()
                elif fops.gt(elev, 0) and fops.lte(elev, config.MAX_STEP_HEIGHT):
                    if fops.lte(col_distance, self.bot.current_motion):
                        self.jumpstep()
                        self.move()
                    else:
                        self.move()
                elif fops.gt(elev, config.MAX_STEP_HEIGHT) and fops.lt(elev, config.MAX_JUMP_HEIGHT):
                    first_elev = col_bb.max_y - self.bot.aabb.min_y
                    if fops.lt(first_elev, elev):
                        if fops.lte(col_distance, self.bot.current_motion):
                            self.jumpstep()
                        self.move()
                    else:
                        ticks_to_col = col_distance / self.bot.current_motion
                        ticks_to_jump = math.sqrt(2 * elev / config.G) * 20
                        if ticks_to_col < ticks_to_jump:
                            self.jump()
                        self.move()
                else:
                    raise Exception("move elevation error %s with collision %s" % (elev, col_distance))
        else:
            self.move()

    def move(self, towards=None):
        if towards is None:
            towards = self.target_space.bb_stand
        direction = self.bot.aabb.horizontal_direction_to(towards)
        if not self.was_at_target:
            self.bot.set_turn_to(self.target_space.bb_stand.bottom_center)
        self.bot.set_direction(direction)

    def jump(self, height=0):
        self.bot.is_jumping = True

    def jumpstep(self, h=config.MAX_STEP_HEIGHT):
        self.bot.set_jumpstep(h)
