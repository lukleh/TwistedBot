

import time

from twisted.internet.task import cooperate
from twisted.internet.defer import inlineCallbacks, returnValue

import config
import utils
import logbot
from pathfinding import AStar
from axisbox import AABB


log = logbot.getlogger("BEHAVIOURS")


class Status(object):
    success = 20
    failure = 30
    running = 40
    suspended = 50


class BehaviourManager(object):
    def __init__(self, world, bot):
        self.world = world
        self.bot = bot
        self.bqueue = []
        self.default_behaviour = FollowPlayerBehaviour(self)  # LookAtPlayerBehaviour(self)
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
                if g.cancelled:
                    break
                if g.status == Status.running:
                    yield g.tick()
                self.bot.bot_object.floating_flag = g.floating_flag
                if g.status == Status.running:
                    break
                elif g.status == Status.suspended:
                    yield utils.reactor_break()
                    continue
                else:
                    yield utils.reactor_break()
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
        self.world = manager.world
        self.bot = manager.bot
        self.parent = parent
        self.cancelled = False
        self.status = Status.running
        self.floating_flag = True

    @inlineCallbacks
    def tick(self):
        if self.cancelled:
            returnValue(None)
        yield self._tick()

    def cancel(self):
        self.cancelled = True

    def _tick(self):
        raise NotImplemented('_tick')

    def from_child(self, g):
        self.status = Status.running

    def add_subbehaviour(self, behaviour, *args, **kwargs):
        g = behaviour(manager=self.manager, parent=self, **kwargs)
        self.manager.bqueue.append(g)
        self.status = Status.suspended

    def return_to_parent(self):
        for i, b in enumerate(self.manager.bqueue):
            if b == self:
                self.manager.bqueue.pop(i)
        if self.parent is not None:
            self.parent.from_child(self)


class LookAtPlayerBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(LookAtPlayerBehaviour, self).__init__(*args, **kwargs)
        self.name = 'Look at player %s' % config.COMMANDER
        log.msg(self.name)

    def _tick(self):
        eid = self.world.commander.eid
        if eid is None:
            return
        player = self.world.entities.get_entity(eid)
        if player is None:
            return
        p = player.position
        self.bot.turn_to_point(self.bot.bot_object, (p[0], p[1] + config.PLAYER_EYELEVEL, p[2]))


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
                self.world.sign_waypoints.get_groupnext_circulate
        elif self.walk_type == "rotate":
            self.next_sign = \
                self.world.sign_waypoints.get_groupnext_rotate
        else:
            raise Exception("unknown walk type")
        self.world.sign_waypoints.reset_group(self.group)

    def _tick(self):
        if not self.world.sign_waypoints.has_group(self.group):
            self.world.chat.send_chat_message("cannnot %s group named %s" % (self.walk_type, self.group))
            self.status = Status.failure
            return
        self.signpoint = self.next_sign(self.group)
        if self.signpoint is not None:
            if not self.world.sign_waypoints.check_sign(self.signpoint):
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
        self.signpoint = self.world.sign_waypoints.get_namepoint(self.sign_name)
        if self.signpoint is None:
            self.signpoint = self.world.sign_waypoints.get_name_from_group(self.sign_name)
        if self.signpoint is None:
            self.world.chat.send_chat_message("cannot idetify sign with name %s" % self.sign_name)
            self.status = Status.failure
            return
        if not self.world.sign_waypoints.check_sign(self.signpoint):
            self.status = Status.failure
            return
        self.add_subbehaviour(TravelToBehaviour, coords=self.signpoint.nav_coords)


class FollowPlayerBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(FollowPlayerBehaviour, self).__init__(*args, **kwargs)
        self.last_block = None

    def _tick(self):
        entity = self.world.entities.get_entity(self.world.commander.eid)
        if entity is None:
            return
        block = self.world.grid.standing_on_block(AABB.from_player_coords(*entity.position))
        if block is None:
            return
        if self.last_block != block:
            self.last_block = block
            self.add_subbehaviour(TravelToBehaviour, coords=block.coords)


class TravelToBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(TravelToBehaviour, self).__init__(*args, **kwargs)
        self.travel_coords = kwargs["coords"]
        self.ready = False
        log.msg(self.name)

    @property
    def name(self):
        return 'Travel to %s from %s' % (self.world.grid.get_block_coords(self.travel_coords), self.bot.standing_on_block(self.bot.bot_object))

    @inlineCallbacks
    def activate(self):
        sb = self.bot.standing_on_block(self.bot.bot_object)
        if sb is None:
            self.ready = False
        else:
            t_start = time.time()
            d = cooperate(AStar(dimension=self.world.dimension,
                                start_coords=sb.coords,
                                end_coords=self.travel_coords,
                                start_aabb=self.bot.bot_object.aabb)).whenDone()
            d.addErrback(logbot.exit_on_error)
            astar = yield d
            if astar.path is None:
                log.msg('ASTAR time consumed %s sec, made %d iterations' % (time.time() - t_start, astar.iter_count))
                self.status = Status.failure
            else:
                log.msg('ASTAR finished in %s sec, length %d, made %d iterations' % (time.time() - t_start, len(astar.path.nodes), astar.iter_count))
                print astar.path.nodes
                current_start = self.bot.standing_on_block(self.bot.bot_object)
                if sb == current_start:
                    self.path = astar.path
                    self.current_bot_coords = current_start.coords
                    self.ready = True

    @inlineCallbacks
    def _tick(self):
        if not self.ready:
            yield self.activate()
            if self.status == Status.failure:
                return
            if not self.ready:
                return
        self.follow(self.path, self.bot.bot_object)

    def follow(self, path, b_obj):
        if path.is_finished:
            self.status = Status.success
            return
        step = path.take_step()
        if step is None:
            self.status = Status.failure
            return
        else:
            self.add_subbehaviour(MoveToBehaviour, start=self.current_bot_coords, target=step.coords)


class MoveToBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(MoveToBehaviour, self).__init__(*args, **kwargs)
        self.target_coords = kwargs["target"]
        self.start_coords = kwargs["start"]
        self.was_at_target = False
        self.floating_flag = False
        self.name = 'Move to %s' % str(self.target_coords)

    def check_status(self, b_obj):
        self.start_state = gridspace.NodeState(self.grid, vector=self.start_coords)
        self.target_state = gridspace.NodeState(self.grid, vector=self.target_coords)
        go = gridspace.can_go(self.start_state, self.target_state)
        if not go:
            log.msg('Cannot go between %s %s' % (self.start_state, self.target_state))
            return Status.failure
        if not self.was_at_target:
            self.was_at_target = self.target_state.center_in(b_obj.position)
        if self.target_state.base_in(b_obj.aabb) and self.target_state.touch_platform(b_obj.position):
            return Status.success
        return Status.running

    def _tick(self):
        b_obj = self.bot.bot_object
        self.status = self.check_status(b_obj)
        if self.status != Status.running:
            return
        if self.bot.is_on_ladder(b_obj) or self.bot.is_in_water(b_obj):
            elev = self.target_state.platform_y - b_obj.y
            if fops.gt(elev, 0):
                self.jump(b_obj)
                self.move(b_obj)
            elif fops.lt(elev, 0):
                self.move(b_obj)
            else:
                self.sneak(b_obj)
                self.move(b_obj)
        elif self.bot.is_standing(b_obj):
            elev = self.target_state.platform_y - b_obj.y
            if fops.lte(elev, 0):
                self.move(b_obj)
            elif fops.gt(elev, 0):
                if self.target_state.base_in(b_obj.aabb):
                    self.jump(b_obj)
                self.move(b_obj)
        else:
            self.move(b_obj)

    def move(self, b_obj):
        direction = Vector2D(b_obj.x - self.target_state.center_x, b_obj.z - self.target_state.center_z)
        direction.normalize()
        if not self.was_at_target:
            self.bot.turn_to_direction(b_obj, direction.x, direction.z)
        b_obj.direction = direction

    def jump(self, b_obj):
        b_obj.is_jumping = True