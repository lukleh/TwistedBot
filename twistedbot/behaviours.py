

from twisted.internet.task import cooperate
from twisted.internet.defer import inlineCallbacks, returnValue

import config
import utils
import logbot
import fops
from pathfinding import AStar
from axisbox import AABB
from gridspace import GridSpace


log = logbot.getlogger("BEHAVIOUR_TREE")


class Status(object):
    success = 20
    failure = 30
    running = 40
    suspended = 50


class Priorities(object):
    user_command = 10


class BehaviourTree(object):
    def __init__(self, world, bot):
        self.world = world
        self.bot = bot
        self.bqueue = []
        self.running = False
        self.user_command = None

    @property
    def current_behaviour(self):
        return self.bqueue[-1]

    @property
    def recheck_goal(self):
        return False

    def select_goal(self):
        """
        select survival goal if necessary, if same as current then pass
        right now only assign idle behaviour
        """
        bh = LookAtPlayerBehaviour(self)
        self.bqueue.append(bh)
        self.announce_behaviour(bh)

    def tick(self):
        if not self.bqueue or self.recheck_goal:
            self.select_goal()
        if self.running:
            return
        self.run()

    @inlineCallbacks
    def run(self):
        self.running = True
        try:
            while 1:
                yield utils.reactor_break()
                self.check_new_command()
                g = self.current_behaviour
                if g.status == Status.running:
                    yield g.tick()
                self.bot.bot_object.hold_position_flag = g.hold_position_flag
                if g.cancelled:
                    break
                elif g.status == Status.running:
                    break
                elif g.status == Status.suspended:
                    continue
                else:
                    self.leaf_to_parent()
        except:
            logbot.exit_on_error()
        self.running = False

    def leaf_to_parent(self):
        leaf = self.bqueue.pop()
        if self.bqueue:
            self.current_behaviour.from_child(leaf.status)
        else:
            self.select_goal()

    def cancel_running(self):
        log.msg('Cancelling %s' % self.bqueue[0])
        for b in self.bqueue:
            b.cancel()
        self.bqueue = []
        self.user_command = None

    def check_new_command(self):
        if self.user_command is not None and self.current_behaviour.priority <= Priorities.user_command:
            behaviour, args, kwargs = self.user_command
            self.cancel_running()
            bh = behaviour(manager=self, parent=None, *args, **kwargs)
            self.bqueue.append(bh)
            self.announce_behaviour(bh)

    def new_command(self, behaviour, *args, **kwargs):
        self.user_command = (behaviour, args, kwargs)
        log.msg("Added command %s" % self.current_behaviour.name)

    def announce_behaviour(self, bh):
        log.msg("Current top behaviour '%s'" % bh.name)
        self.world.chat.send_chat_message("New behaviour: %s" % bh.name)


class BehaviourBase(object):
    def __init__(self, manager=None, **kwargs):
        self.priority = Priorities.user_command
        self.manager = manager
        self.world = manager.world
        self.bot = manager.bot
        self.cancelled = False
        self.status = Status.running
        self.hold_position_flag = True

    @inlineCallbacks
    def tick(self):
        if self.cancelled:
            returnValue(None)
        yield self._tick()

    def cancel(self):
        self.cancelled = True

    def _tick(self):
        raise NotImplemented('_tick')

    def from_child(self, status):
        self.status = Status.running

    def add_subbehaviour(self, behaviour, *args, **kwargs):
        g = behaviour(manager=self.manager, parent=self, **kwargs)
        self.manager.bqueue.append(g)
        self.status = Status.suspended


class LookAtPlayerBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(LookAtPlayerBehaviour, self).__init__(*args, **kwargs)
        self.hold_position_flag = False
        self.name = 'Look at player %s' % config.COMMANDER

    def _tick(self):
        if not self.world.commander.in_game:
            return
        player = self.world.entities.get_entity(self.world.commander.eid)
        if player is None:
            return
        p = player.position
        self.bot.turn_to_point(self.bot.bot_object, (p.x, p.y + config.PLAYER_EYELEVEL, p.z))


class WalkSignsBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(WalkSignsBehaviour, self).__init__(*args, **kwargs)
        self.signpoint = None
        self.signpoint_forward_direction = True
        self.group = kwargs.get("group")
        self.walk_type = kwargs.get("type")
        self.name = '%s signs in group "%s"' % (self.walk_type.capitalize(), self.group)
        self._prepare()

    def _prepare(self):
        if self.walk_type == "circulate":
            self.next_sign = self.world.sign_waypoints.get_groupnext_circulate
        elif self.walk_type == "rotate":
            self.next_sign = self.world.sign_waypoints.get_groupnext_rotate
        else:
            raise Exception("unknown walk sign type")

    def _tick(self):
        if not self.world.sign_waypoints.has_group(self.group):
            self.world.chat.send_chat_message("No group named '%s'" % self.group)
            self.status = Status.failure
            return
        new_signpoint, self.signpoint_forward_direction = self.next_sign(self.group, self.signpoint, self.signpoint_forward_direction)
        if new_signpoint == self.signpoint:
            self.status = Status.success
            return
        else:
            self.signpoint = new_signpoint
        if self.signpoint is not None:
            if not self.world.sign_waypoints.check_sign(self.signpoint):
                return
            log.msg("Go to sign %s" % self.signpoint)
            self.add_subbehaviour(TravelToBehaviour, coords=self.signpoint.coords)
        else:
            self.status = Status.failure


class GoToSignBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(GoToSignBehaviour, self).__init__(*args, **kwargs)
        self.sign_name = kwargs.get("sign_name", "")
        self.name = 'Go to %s' % self.sign_name

    def from_child(self, status):
        self.status = status

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
        log.msg("Go To: sign details %s" % self.signpoint)
        self.add_subbehaviour(TravelToBehaviour, coords=self.signpoint.coords)


class FollowPlayerBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(FollowPlayerBehaviour, self).__init__(*args, **kwargs)
        self.last_block = None
        self.last_position = None
        self.name = "Following %s" % self.world.commander.name

    def from_child(self, status):
        self.status = Status.running
        self.last_position = self.bot.bot_object.position_grid

    def _tick(self):
        if not self.world.commander.in_game:
            return
        entity = self.world.entities.get_entity(self.world.commander.eid)
        block = self.world.grid.standing_on_block(AABB.from_player_coords(entity.position))
        if block is None:
            return
        if self.last_block != block or self.last_position != self.bot.bot_object.position_grid:
            self.last_position = self.bot.bot_object.position_grid
            self.last_block = block
            self.add_subbehaviour(TravelToBehaviour, coords=block.coords, shorten_path_by=2)


class TravelToBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(TravelToBehaviour, self).__init__(*args, **kwargs)
        self.travel_coords = kwargs["coords"]
        self.shorten_path_by = kwargs.get("shorten_path_by", 0)
        self.ready = False
        log.msg(self.name)

    @property
    def name(self):
        return 'Travel to %s from %s' % (self.world.grid.get_block_coords(self.travel_coords), self.bot.standing_on_block(self.bot.bot_object))

    @inlineCallbacks
    def _prepare(self):
        sb = self.bot.standing_on_block(self.bot.bot_object)
        if sb is None:
            self.ready = False
        else:
            d = cooperate(AStar(dimension=self.world.dimension,
                                start_coords=sb.coords,
                                end_coords=self.travel_coords)).whenDone()
            d.addErrback(logbot.exit_on_error)
            astar = yield d
            if astar.path is None:
                self.status = Status.failure
            else:
                current_start = self.bot.standing_on_block(self.bot.bot_object)
                if sb == current_start:
                    self.path = astar.path
                    self.path.remove_last(self.shorten_path_by)
                    self.ready = True
                    if len(astar.path) < 2:
                        self.status = Status.success

    def from_child(self, status):
        if status != Status.success:
            self.ready = False
        self.status = Status.running

    @inlineCallbacks
    def _tick(self):
        if not self.ready:
            yield self._prepare()
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
            current_start = self.bot.standing_on_block(self.bot.bot_object)
            if current_start is not None:
                current_bot_coords = current_start.coords
                self.add_subbehaviour(MoveToBehaviour, start=current_bot_coords, target=step.coords)
            else:
                self.status = Status.failure
                return


class MoveToBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(MoveToBehaviour, self).__init__(*args, **kwargs)
        self.target_coords = kwargs["target"]
        self.start_coords = kwargs["start"]
        self.was_at_target = False
        self.hold_position_flag = False
        self.name = 'Move to %s' % str(self.target_coords)
        #log.msg(self.name)

    def check_status(self, b_obj):
        gs = GridSpace(self.world.grid)
        self.start_state = gs.get_state_coords(self.start_coords)
        self.target_state = gs.get_state_coords(self.target_coords)
        go = gs.can_go(self.start_state, self.target_state)
        if not go:
            log.msg('Cannot go between %s %s' % (self.start_state, self.target_state))
            return Status.failure
        if not self.was_at_target:
            self.was_at_target = self.target_state.vertical_center_in(b_obj.position)
        if self.target_state.base_in(b_obj.aabb) and self.target_state.touch_platform(b_obj.position):
            return Status.success
        return Status.running

    def _tick(self):
        b_obj = self.bot.bot_object
        self.status = self.check_status(b_obj)
        if self.status != Status.running:
            return
        on_ladder = self.bot.is_on_ladder(b_obj)
        in_water = self.bot.is_in_water(b_obj)
        if on_ladder or in_water:
            elev = self.target_state.platform_y - b_obj.y
            if fops.gt(elev, 0):
                self.jump(b_obj)
                self.move(b_obj)
            elif fops.lt(elev, 0):
                self.move(b_obj)
            else:
                if on_ladder:
                    self.sneak(b_obj)
                self.move(b_obj)
        elif self.bot.is_standing(b_obj):
            elev = self.target_state.platform_y - b_obj.y
            if fops.lte(elev, 0):
                self.move(b_obj)
            elif fops.gt(elev, 0):
                if self.start_state.base_in(b_obj.aabb):
                    self.jump(b_obj)
                self.move(b_obj)
        else:
            self.move(b_obj)

    def move(self, b_obj):
        direction = utils.Vector2D(self.target_state.center_x - b_obj.x, self.target_state.center_z - b_obj.z)
        direction.normalize()
        if not self.was_at_target:
            self.bot.turn_to_direction(b_obj, direction.x, direction.z)
        b_obj.direction = direction

    def jump(self, b_obj):
        b_obj.is_jumping = True

    def sneak(self, b_obj):
        self.bot.start_sneaking(b_obj)
