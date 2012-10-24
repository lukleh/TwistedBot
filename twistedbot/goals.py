
import math

from twisted.internet.task import cooperate

import config
import tools

import logbot
import fops
from gridspace import GridSpace
from pathfinding import AStar

log = logbot.getlogger("GOALS")


class Status(object):
    not_finished = 10
    finished = 20
    broken = 30
    impossible = 40


class Manager(object):
    def __init__(self, bot):
        self.bot = bot
        self.grid = self.bot.world.grid
        self.goalq = []
        self.default_goal = LookAtPlayerGoal(self, self.bot)
        self.running = False

    @property
    def current_goal(self):
        if self.goalq:
            return self.goalq[-1]
        else:
            return self.default_goal

    def cancel_goal(self):
        for g in self.goalq:
            g.cancel()
        self.goalq = []

    def run_goal(self):
        if self.running:
            return
        self.running = True
        cg = self.current_goal
        cg.perform()

    def goal_return(self, goal, status):
        self.current_goal.cancel()
        g = self.goalq.pop()
        if self.goalq:
            self.current_goal.from_child(status)
        else:
            self.bot.chat_message("Finished: %s" % g.name)
            self.not_running()

    def not_running(self):
        self.running = False

    def add_subgoal(self, goal, *args, **kwargs):
        self.goalq.append(goal(self, self.bot, *args, **kwargs))
        cg = self.current_goal
        tools.do_later(0, cg.perform)

    def command_goal(self, goal, *args, **kwargs):
        self.cancel_goal()
        self.goalq.append(goal(self, self.bot, *args, **kwargs))
        self.running = False
        log.msg("Added command goal %s" % self.current_goal.name)


class GoalBase(object):
    def __init__(self, manager=None, bot=None):
        self.manager = manager
        self.bot = bot
        self.world = bot.world
        self.grid = self.world.grid
        self.ready = False
        self.mark_manager_stop = False
        self.cancelled = False

    def activate(self):
        self.ready = True

    def perform(self):
        self.activate()
        if self.ready is False:
            return
        state = self.check_state()
        if state is None:
            raise Exception("goal state cannot be None")
        if state != Status.not_finished:
            self.manager_goal_return(state)
        else:
            self.do()
            self.mark_manager()

    def cancel(self):
        self.cancelled = True

    def mark_manager(self):
        if self.mark_manager_stop:
            self.manager.not_running()

    def check_state(self):
        return Status.not_finished

    def do(self):
        pass

    def from_child(self, status):
        self.do()

    def manager_goal_return(self, status):
        self.manager.goal_return(self, status)


class LookAtPlayerGoal(GoalBase):
    def __init__(self, *args, **kwargs):
        super(LookAtPlayerGoal, self).__init__(*args)
        self.mark_manager_stop = True
        self.name = 'Look at player %s' % config.COMMANDER
        log.msg(self.name)

    def do(self):
        eid = self.bot.commander.eid
        if eid is None:
            return
        player = self.world.entities.get_entity(eid)
        if player is None:
            return
        p = player.position
        self.bot.set_turn_to(
            (p[0], p[1] + config.PLAYER_EYELEVEL, p[2]), elevation=True)


class WalkSignsGoal(GoalBase):
    def __init__(self, *args, **kwargs):
        super(WalkSignsGoal, self).__init__(*args)
        self.signpoint = None
        self.group = kwargs.get("group")
        self.walk_type = kwargs.get("type")
        if self.walk_type == "circulate":
            self.next_sign = \
                self.bot.world.navgrid.sign_waypoints.get_groupnext_circulate
        elif self.walk_type == "rotate":
            self.next_sign = \
                self.bot.world.navgrid.sign_waypoints.get_groupnext_rotate
        else:
            raise Exception("unknown walk type")
        self.name = '%s signs in group "%s"' % (
            self.walk_type.capitalize(), self.group)
        log.msg(self.name)
        self.bot.world.navgrid.sign_waypoints.reset_group(self.group)

    def from_child(self, status):
        is_ok = self.manager.grid.check_sign(self.signpoint.coords)
        if not is_ok:
            self.manager.not_running()
            return
        if status == Status.finished or status == Status.impossible:
            self.do()
        elif status == Status.broken:
            if self.signpoint is not None:
                self.manager.add_subgoal(
                    TravelToGoal, coords=self.signpoint.coords)
            else:
                self.manager_goal_return(Status.finished)

    def check_state(self):
        if not self.bot.world.navgrid.sign_waypoints.has_group(self.group):
            self.bot.chat_message("cannnot %s group named %s" % (self.walk_type, self.group))
            return Status.impossible
        else:
            return Status.not_finished

    def do(self):
        self.signpoint = self.next_sign(self.group)
        if self.signpoint is not None:
            self.manager.add_subgoal(
                TravelToGoal, coords=self.signpoint.nav_coords)
        else:
            self.manager_goal_return(Status.finished)


class GoToSignGoal(GoalBase):
    def __init__(self, *args, **kwargs):
        super(GoToSignGoal, self).__init__(*args)
        self.sign_name = kwargs.get("sign_name", "")
        self.name = 'Go to %s' % self.sign_name
        log.msg(self.name)

    def from_child(self, status):
        is_ok = self.manager.grid.check_sign(self.signpoint.coords)
        if not is_ok:
            self.self.manager.not_running()
            return
        if status == Status.broken:
            self.do()
        else:
            self.manager_goal_return(Status.finished)

    def check_state(self):
        self.signpoint = self.bot.world.navgrid.sign_waypoints.get_namepoint(
            self.sign_name)
        if self.signpoint is None:
            self.bot.chat_message(
                "don't have sign with name %s" % self.sign_name)
            return Status.impossible
        else:
            return Status.not_finished

    def do(self):
        self.manager.add_subgoal(
            TravelToGoal, coords=self.signpoint.nav_coords)


class TravelToGoal(GoalBase):
    def __init__(self, *args, **kwargs):
        super(TravelToGoal, self).__init__(*args)
        self.travel_coords = kwargs["coords"]
        self.calculating = False
        self.current_step = None
        self.last_step = None
        self.name = 'Travel to %s' % str(self.travel_coords)
        log.msg(self.name)

    def activate(self):
        if not self.ready:
            if not self.calculating:
                tools.do_later(0, self.calculate_path)
                self.calculating = True

    def calculate_path(self):
        if self.bot.standing_on_block is not None:
            cootask = cooperate(AStar(self.bot.world.navgrid,
                                      self.bot.standing_on_block.coords,
                                      self.travel_coords))
            d = cootask.whenDone()
            d.addCallback(self.pathfind_finished)
            d.addErrback(logbot.exit_on_error)
        else:
            self.calculating = False

    def pathfind_finished(self, astar):
        self.calculating = False
        if astar.path is None:
            self.manager.not_running()
            return
        else:
            if self.bot.world.navgrid.check_path(astar.path):
                self.ready = True
                self.path = astar.path
                tools.do_now(self.perform)
            else:
                self.manager.not_running()

    def from_child(self, status):
        if status == Status.finished:
            self.last_step = self.current_step
            self.do()
        elif status == Status.broken:
            self._do()
        elif status == Status.impossible:
            self.manager_goal_return(Status.broken)
        else:
            raise Exception('Wrong status')

    def _do(self):
        gs = GridSpace(self.manager.grid, coords=self.current_step)
        if not gs.can_stand_on:
            self.manager_goal_return(Status.broken)
            return
        elif self.last_step is not None:
            last_gs = GridSpace(self.manager.grid, coords=self.last_step)
            if not last_gs.can_go(gs):
                self.manager_goal_return(Status.broken)
                return
        self.manager.add_subgoal(MoveToGoal, target_space=gs)

    def do(self):
        if self.path.has_next():
            self.current_step = self.path.next_step().coords
            self._do()
        else:
            self.manager_goal_return(Status.finished)


class MoveToGoal(GoalBase):
    def __init__(self, *args, **kwargs):
        super(MoveToGoal, self).__init__(*args)
        self.mark_manager_stop = True
        self.target_space = kwargs["target_space"]
        self.was_at_target = False
        self.name = 'Move to %s' % str(self.target_space.coords)
        log.msg(self.name)

    def check_state(self):
        bb_stand = self.target_space.bb_stand
        elev = bb_stand.min_y - self.bot.aabb.min_y
        if fops.gt(elev, config.MAX_JUMP_HEIGHT):
            return Status.impossible
        if not self.target_space._can_stand_on():
            self.grid.navgrid.delete_node(self.target_space.coords)
            return Status.impossible
        if self.bot.aabb.horizontal_distance(bb_stand) > 2:
            # too far from the next step, better try again
            return Status.impossible
        if self.bot.position_grid == self.target_space.coords and \
                (self.bot.is_on_ladder or self.grid.aabb_in_water(self.bot.aabb)):
            return Status.finished
        if self.bot.aabb.horizontal_distance(bb_stand) < self.bot.current_motion:
            self.was_at_target = True
            if fops.eq(elev, 0):
                return Status.finished
        if self.bot.on_ground and self.bot.horizontally_blocked:
            gs = GridSpace(self.grid, bb=self.bot.aabb)
            if not gs.can_go(self.target_space):
                log.msg("I am stuck, let's try again? vels %s" %
                        str(self.bot.velocities))
                return Status.broken
        return Status.not_finished

    def do(self):
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
        #log.msg("JUMP")
        self.bot.is_jumping = True

    def jumpstep(self, h=config.MAX_STEP_HEIGHT):
        #log.msg("JUMPSTEP")
        self.bot.set_jumpstep(h)
