
from twisted.internet.task import cooperate
from twisted.internet.defer import inlineCallbacks

import items
import recipes
import config
import logbot
import utils
import fops
import dig
import packets
import blocks
from pathfinding import AStarBBCol, AStarCoords, AStarMultiCoords
from gridspace import GridSpace
from inventory import InventoryManipulation


log = logbot.getlogger("BEHAVIOUR_TREE")


class Status(object):
    success = 20
    failure = 30
    running = 40
    suspended = 50


class Priorities(object):
    idle = 0
    user_command = 10


class BlackBoard(object):
    def __init__(self, manager):
        self._manager = manager
        self._world = manager.world
        self._bot = manager.bot

    def setup(self):
        self._inventory_transaction_counter = 1
        self.last_look_at_block = None
        self.recipes_for_item = recipes.recipes_db.recipes_for_item
        self.get_entity = self._world.entities.get_entity
        self.grid_raycast_to_block = self._world.grid.raycast_to_block
        self.grid_standing_on_block = self._world.grid.standing_on_block
        self.send_chat_message = self._world.chat.send_chat_message
        self.entities_in_distance = self._world.entities.entities_in_distance
        self.entities_has_entity_eid = self._world.entities.has_entity_eid
        self.sign_waypoints_has_group = self._world.sign_waypoints.has_group
        self.sign_waypoints_get_groupnext_circulate = self._world.sign_waypoints.get_groupnext_circulate
        self.sign_waypoints_get_groupnext_rotate = self._world.sign_waypoints.get_groupnext_rotate
        self.sign_waypoints_check_sign = self._world.sign_waypoints.check_sign
        self.sign_waypoints_get_namepoint = self._world.sign_waypoints.get_namepoint
        self.sign_waypoints_get_name_from_group = self._world.sign_waypoints.get_name_from_group
        self.get_block_coords = self._world.grid.get_block_coords
        self.bot_standing_on_block = self._bot.standing_on_block
        self.bot_is_standing = self._bot.is_standing
        self.bot_is_on_ladder = self._bot.is_on_ladder
        self.bot_is_in_water = self._bot.is_in_water
        self.bot_turn_to_point = self._bot.turn_to_point
        self.bot_turn_to_vector = self._bot.turn_to_vector
        self.bot_turn_to_direction = self._bot.turn_to_direction
        self.bot_start_sneaking = self._bot.start_sneaking
        self.itemstack_as_slotdata = packets.itemstack_as_slotdata
        self.send_packet = self._world.send_packet
        self.inventory_player = self._world.inventories.player_inventory
        self.inventory_get_confirmation = self._world.inventories.get_confirmation
        self.inventory_item_collected_count = self._world.inventories.get_item_collected_count
        self.inventory_tool_for_block = self._world.inventories.tool_for_block
        self.receive_inventory = self._world.inventories.get_open_window
        self.blocks_around = self._world.grid.blocks_in_distance

    def positions_to_dig(self, coords):
        gs = GridSpace(self.grid)
        return list(gs.positions_to_dig(coords))

    def add_subbehavior(self, behavior):
        self._manager.bqueue.append(behavior)

    @property
    def inventory_transaction_counter_inc(self):
        self._inventory_transaction_counter += 1
        return self._inventory_transaction_counter

    @property
    def inventory_transaction_counter(self):
        return self._inventory_transaction_counter

    @property
    def world_current_tick(self):
        return self._world.game_ticks

    @property
    def commander_in_game(self):
        return self._world.commander.in_game

    @property
    def commander_eid(self):
        return self._world.commander.eid

    @property
    def commander_name(self):
        return self._world.commander.name

    @property
    def bot_object(self):
        return self._bot.bot_object

    @property
    def grid(self):
        return self._world.grid

    @property
    def dimension(self):
        return self._world.dimension


class BehaviorTree(object):
    def __init__(self, world, bot):
        self.world = world
        self.bot = bot
        self.bqueue = []
        self.running = False
        self.user_command = None
        self.blackboard = BlackBoard(self)

    @property
    def current_behavior(self):
        return self.bqueue[-1]

    @property
    def recheck_goal(self):
        return self.world.game_ticks % 20 == 0

    def select_goal(self):
        """
        select survival goal if necessary, if same as current then pass
        right now only assign idle behavior
        """
        bh = LookAtPlayer(blackboard=self.blackboard)
        bh.setup()
        if not bh.is_valid():
            bh = Idle(blackboard=self.blackboard)
            bh.setup()
        if self.bqueue:
            if self.bqueue[0] == bh:
                return
        if not self.bqueue or bh.priority >= self.bqueue[0].priority:
            self.cancel_running()
            self.bqueue.append(bh)
            self.announce_behavior(bh)

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
            while True:
                yield utils.reactor_break()
                self.check_new_command()
                b = self.current_behavior
                self.bot.bot_object.hold_position_flag = b.hold_position_flag
                if b.sleep_until > self.blackboard.world_current_tick:
                    break
                if b.status == Status.running:
                    yield b.tick()
                if b.cancelled:
                    break
                elif b.status == Status.running:
                    break
                elif b.status == Status.suspended:
                    continue
                else:
                    self.child_to_parent()
        except:
            logbot.exit_on_error()
        self.running = False

    def child_to_parent(self):
        child = self.bqueue.pop()
        if self.bqueue:
            self.current_behavior.from_child(child)
        else:
            self.select_goal()

    def cancel_running(self):
        if not self.bqueue:
            return
        log.msg('cancelling %s' % self.bqueue[0])
        for b in reversed(self.bqueue):
            b.cancel()
        self.bqueue = []
        self.user_command = None

    def check_new_command(self):
        if self.user_command is not None and self.bqueue[0].priority <= Priorities.user_command:
            behavior, kwargs = self.user_command
            self.cancel_running()
            bh = behavior(blackboard=self.blackboard, **kwargs)
            bh.priority = Priorities.user_command
            bh.setup()
            if bh.is_valid():
                self.bqueue.append(bh)
                self.announce_behavior(bh)
            else:
                self.world.chat.send_chat_message("cannot start %s" % bh.name)
                self.select_goal()

    def new_command(self, behavior, **kwargs):
        self.user_command = (behavior, kwargs)

    def announce_behavior(self, bh):
        self.world.chat.send_chat_message("new goal behavior is %s" % bh.name)


class BTbase(object):
    def __init__(self, blackboard=None):
        self.blackboard = blackboard
        self.hold_position_flag = True
        self.priority = Priorities.idle
        self.cancelled = False
        self.status = Status.running
        self.sleep_until = 0

    def __eq__(self, b):
        return self.name == b.name

    def __repr__(self):
        return "%s %s" % (self.__class__.__name__, self.name)

    def setup(self):
        pass

    def is_valid(self):
        raise NotImplementedError()

    def tick(self):
        raise NotImplementedError()

    def from_child(self, child):
        raise NotImplementedError()

    def cleanup(self):
        pass

    def cancel(self):
        self.cancelled = True
        self.cleanup()

    def add_subbehavior(self, behavior):
        self.blackboard.add_subbehavior(behavior)
        self.status = Status.suspended

    def make_behavior(self, cls, **kwargs):
        return cls(blackboard=self.blackboard, **kwargs)


class BTGoal(BTbase):
    def __init__(self, **kwargs):
        super(BTGoal, self).__init__(**kwargs)
        self.choices_queue = self.choices()

    def choices(self):
        raise NotImplementedError()

    @property
    def goal_reached(self):
        raise NotImplementedError()

    def sleep_ticks(self, tplus):
        self.sleep_until = self.blackboard.world_current_tick + tplus

    @inlineCallbacks
    def tick(self):
        if self.sleep_until > self.blackboard.world_current_tick:
            return
        if self.goal_reached:
            self.blackboard.send_chat_message("%s finished" % self.name)
            self.status = Status.success
            return
        if not self.is_valid():
            self.status = Status.failure
            return
        try:
            b = self.choices_queue.next()
        except StopIteration:
            self.status = Status.success
            return
        if b is None:
            self.sleep_ticks(20)
            return
        yield b.setup()
        if b.is_valid():
            self.add_subbehavior(b)

    def from_child(self, child):
        if self.goal_reached:
            self.status = Status.success
        elif child.status == Status.failure:
            self.sleep_ticks(20)
            self.status = Status.running
        else:
            self.status = Status.running


class BTAction(BTbase):
    def __init__(self, **kwargs):
        super(BTAction, self).__init__(**kwargs)
        self.hold_position_flag = False
        self.duration_ticks = 0
        self.action_started = False

    def is_valid(self):
        return True

    def from_child(self, child):
        raise Exception("I am action, cannot receive children")

    def add_subbehavior(self, behavior):
        raise Exception("I am action, cannot have children")

    def action(self):
        raise NotImplementedError()

    def on_start(self):
        pass

    def on_end(self):
        pass

    @inlineCallbacks
    def tick(self):
        if not self.action_started:
            yield self.on_start()
            self.action_started = True
            if self.status != Status.running:
                return
        yield self.action()
        if self.status != Status.running:
            yield self.on_end()
        self.duration_ticks += 1


class BTSelector(BTbase):

    def __init__(self, **kwargs):
        super(BTSelector, self).__init__(**kwargs)
        self.choices_queue = self.choices()

    def choices(self):
        raise NotImplementedError()

    @inlineCallbacks
    def tick(self):
        try:
            b = self.choices_queue.next()
        except StopIteration:
            self.status = Status.failure
            return
        yield b.setup()
        if b.is_valid():
            self.add_subbehavior(b)

    def from_child(self, child):
        if child.status == Status.success:
            self.status = Status.success
        elif child.status == Status.failure:
            self.status = Status.running
        else:
            raise Exception("bad child %s status code %s" % (child, child.status))


class BTSequencer(BTbase):

    def __init__(self, **kwargs):
        super(BTSequencer, self).__init__(**kwargs)
        self.choices_queue = self.choices()

    def choices(self):
        raise NotImplementedError()

    @inlineCallbacks
    def tick(self):
        try:
            b = self.choices_queue.next()
        except StopIteration:
            self.status = Status.success
            return
        yield b.setup()
        if b.is_valid():
            self.add_subbehavior(b)
        else:
            self.status = Status.failure

    def from_child(self, child):
        if child.status == Status.success:
            self.status = Status.running
        elif child.status == Status.failure:
            self.status = Status.failure
        else:
            raise Exception("bad child %s status code %s" % (child, child.status))


class CollectResources(BTGoal):
    def __init__(self, itemstack=None, **kwargs):
        super(CollectResources, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.count = itemstack.count
        self.collect_count = self.blackboard.inventory_item_collected_count(self.itemstack)
        self.collect_goal_count = self.collect_count + self.count
        self.name = 'gather %s' % self.itemstack

    def is_valid(self):
        return True

    @classmethod
    def parse_parameters(cls, params):
        if len(params) < 2:
            return None, None
        item_count = params[0]
        item_name = " ".join(params[1:])
        try:
            istack = items.item_db.item_by_name(item_name)
        except KeyError:
            istack = None
        try:
            count = int(item_count)
        except ValueError:
            count = None
        if istack is not None and count is not None:
            istack.inc_count(count - 1)
        return istack, count

    @property
    def goal_reached(self):
        return self.blackboard.inventory_item_collected_count(self.itemstack) >= self.collect_goal_count

    def choices(self):
        while True:
            yield self.make_behavior(Collect, itemstack=self.itemstack)


class Idle(BTGoal):
    def __init__(self, **kwargs):
        super(Idle, self).__init__(**kwargs)
        self.name = 'doing nothing'

    @property
    def goal_reached(self):
        return False

    def is_valid(self):
        return True

    def choices(self):
        while True:
            yield None


class LookAtPlayer(BTGoal):
    def __init__(self, **kwargs):
        super(LookAtPlayer, self).__init__(**kwargs)
        self.name = 'look at player %s' % self.blackboard.commander_name

    @property
    def goal_reached(self):
        return False

    def is_valid(self):
        return self.blackboard.commander_in_game

    def choices(self):
        while self.is_valid():
            player = self.blackboard.get_entity(self.blackboard.commander_eid)
            if player is None:
                yield None
            else:
                yield self.make_behavior(PeekAtPlayer, player=player)


class ShowPlayerCursor(BTGoal):
    def __init__(self, **kwargs):
        super(ShowPlayerCursor, self).__init__(**kwargs)
        self.name = 'show player %s cursor' % self.blackboard.commander_name

    def cleanup(self):
        self.blackboard.last_look_at_block = None

    @property
    def goal_reached(self):
        return False

    def is_valid(self):
        return self.blackboard.commander_in_game

    def choices(self):
        while self.is_valid():
            player = self.blackboard.get_entity(self.blackboard.commander_eid)
            if player is None:
                yield None
            else:
                yield self.make_behavior(ShowCursor, player=player)


class WalkSigns(BTGoal):
    def __init__(self, group=None, walk_type=None, **kwargs):
        super(WalkSigns, self).__init__(**kwargs)
        self.signpoint = None
        self.signpoint_forward_direction = True
        self.group = group
        self.walk_type = walk_type
        self.name = '%s signs in group "%s"' % (self.walk_type, self.group)

    @property
    def goal_reached(self):
        return False

    def setup(self):
        if self.walk_type == "circulate":
            self.next_sign = self.blackboard.sign_waypoints_get_groupnext_circulate
        elif self.walk_type == "rotate":
            self.next_sign = self.blackboard.sign_waypoints_get_groupnext_rotate

    def is_valid(self):
        if not self.blackboard.sign_waypoints_has_group(self.group):
            self.blackboard.send_chat_message("no group named '%s'" % self.group)
            return False
        return True

    def choices(self):
        while self.is_valid():
            new_signpoint, self.signpoint_forward_direction = self.next_sign(self.group, self.signpoint, self.signpoint_forward_direction)
            if new_signpoint == self.signpoint:
                break
            else:
                self.signpoint = new_signpoint
            if not self.blackboard.sign_waypoints_check_sign(self.signpoint):
                continue
            log.msg("go to sign %s" % self.signpoint)
            yield self.make_behavior(TravelTo, coords=self.signpoint.coords)


class FollowPlayer(BTGoal):
    def __init__(self, **kwargs):
        super(FollowPlayer, self).__init__(**kwargs)
        self.last_block = None
        self.name = "following %s" % self.blackboard.commander_name

    @property
    def goal_reached(self):
        return False

    def is_valid(self):
        return self.blackboard.commander_in_game

    def choices(self):
        while self.is_valid():
            entity = self.blackboard.get_entity(self.blackboard.commander_eid)
            block = self.blackboard.grid_standing_on_block(entity.aabb)
            if block is None:
                yield self.make_behavior(PeekAtPlayer, player=entity)
            elif self.last_block != block:
                self.last_block = block
                yield self.make_behavior(TravelTo, coords=block.coords, shorten_path_by=2)
                yield self.make_behavior(PeekAtPlayer, player=entity)
            else:
                yield self.make_behavior(PeekAtPlayer, player=entity)


class GoToSign(BTGoal):
    def __init__(self, sign_name=None, **kwargs):
        super(GoToSign, self).__init__(**kwargs)
        self.sign_name = sign_name
        self.name = 'go to %s' % self.sign_name

    @property
    def goal_reached(self):
        return self.signpoint.coords == self.blackboard.bot_object.position_grid

    def is_valid(self):
        self.signpoint = self.blackboard.sign_waypoints_get_namepoint(self.sign_name)
        if self.signpoint is None:
            self.signpoint = self.blackboard.sign_waypoints_get_name_from_group(self.sign_name)
        if self.signpoint is None:
            self.blackboard.send_chat_message("cannot idetify sign with name %s" % self.sign_name)
            return False
        if not self.blackboard.sign_waypoints_check_sign(self.signpoint):
            return False
        return True

    def choices(self):
        while self.is_valid():
            yield self.make_behavior(TravelTo, coords=self.signpoint.coords)


class Collect(BTSelector):
    def __init__(self, itemstack=None, **kwargs):
        super(Collect, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.count = itemstack.count
        self.name = 'collect %s' % self.itemstack
        log.msg(self.name)

    def is_valid(self):
        return True

    def setup(self):
        self.item_recipes = self.blackboard.recipes_for_item(self.itemstack)

    def choices(self):
        if not self.blackboard.inventory_player.has_space_for(self.itemstack):
            yield self.make_behavior(UnloadInvetoryToChest)
        yield self.make_behavior(CollectLayingAround, itemstack=self.itemstack)
        for recipe in self.item_recipes:
            log.msg('collect with recipe %s' % recipe)
            if not recipe.is_obtainable:
                continue
            if recipe.mine_recipe:
                yield self.make_behavior(CollectMine, itemstack=self.itemstack, recipe=recipe)
            if recipe.craft_recipe:
                yield self.make_behavior(CollectCraft, itemstack=self.itemstack, recipe=recipe)
            if recipe.smelt_recipe:
                yield self.make_behavior(CollectSmelt, itemstack=self.itemstack, recipe=recipe)
            if recipe.brew_recipe:
                yield self.make_behavior(CollectBrew, itemstack=self.itemstack, recipe=recipe)
            if recipe.mobkill_recipe:
                yield self.make_behavior(CollectMobKill, itemstack=self.itemstack, recipe=recipe)


class UnloadInvetoryToChest(BTSelector):
    def __init__(self, **kwargs):
        super(UnloadInvetoryToChest, self).__init__(**kwargs)
        self.name = 'unload inventory'

    def is_valid(self):
        return True

    def choices(self):
        """ for now just dump it """
        yield self.make_behavior(DropInventory)


class CollectLayingAround(BTSelector):
    def __init__(self, itemstack=None, **kwargs):
        super(CollectLayingAround, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.name = 'collect around %s' % self.itemstack

    def is_valid(self):
        if not self.is_entities_around:
            return False
        return True

    def setup(self):
        self.entities_around = [ent for ent in self.blackboard.entities_in_distance(self.blackboard.bot_object.position, distance=48) if ent.is_itemstack and self.itemstack.is_same(ent.itemstack)]

    @property
    def is_entities_around(self):
        return len(self.entities_around) > 0

    def get_closest_entity(self):
        self.entities_around = sorted(self.entities_around, key=lambda e: (e.position - self.blackboard.bot_object.position).size_pow)
        return self.entities_around.pop(0)

    def choices(self):
        while self.is_entities_around:
            ent = self.get_closest_entity()
            if not self.blackboard.entities_has_entity_eid(ent.eid):
                continue
            yield self.make_behavior(CollectEntity, entity=ent)


class CollectEntity(BTSequencer):
    """ future work, unconnected"""
    def __init__(self, entity=None, **kwargs):
        super(CollectEntity, self).__init__(**kwargs)
        self.entity = entity

    def is_valid(self):
        return self.blackboard.entities_has_entity_eid(self.entity.eid)

    def choices(self):
        yield self.make_behavior(GetTo, bb=self.entity.expand(1, 0.5, 1))
        yield self.make_behavior(PickUp)


class CollectMine(BTSequencer):
    def __init__(self, itemstack=None, recipe=None, **kwargs):
        super(CollectMine, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.recipe = recipe
        self.name = 'mine %s' % self.itemstack
        self.blocks_around = []

    def is_valid(self):
        return self.blocks_around

    def setup(self):
        _, self.have_tool, self.mine_tool = self.blackboard.inventory_tool_for_block(self.recipe.block)
        self.blocks_around = self.blackboard.blocks_around(self.blackboard.bot_object.position, block_number=self.recipe.block.number, block_filter=self.recipe.block_filter)

    def choices(self):
        if not self.have_tool:
            yield self.make_behavior(Collect, itemstack=self.blackboard.inventory_min_tool_for_block(self.recipe.block))
        for block in self.blocks_around:
            yield self.make_behavior(GetTo, digtarget=block.coords)
            if not self.have_tool:
                yield self.make_behavior(Collect, itemstack=self.blackboard.inventory_min_tool_for_block(self.recipe.block))
            yield self.make_behavior(InventorySelectActive, itemstack=self.mine_tool)
            yield self.make_behavior(DigBlock, block=block)
            yield self.make_behavior(WaitForDrop, block=block, itemstack=self.recipe.itemstack, drop_everytime=self.recipe.drop_everytime)
            break


class CollectCraft(BTSequencer):
    def __init__(self, itemstack=None, recipe=None, **kwargs):
        super(CollectCraft, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.recipe = recipe

    def is_valid(self):
        return True

    @property
    def missing_ingredient(self):
        for itemstack in self.recipe.resources:
            if not self.blackboard.inventory_player.has_item_count(itemstack):
                log.msg("missing ingredient %s for crafting" % itemstack)
                return itemstack

    def choices(self):
        while self.missing_ingredient is not None:
            yield self.make_behavior(Collect, itemstack=self.missing_ingredient)
        yield self.make_behavior(CraftItem, itemstack=self.itemstack, recipe=self.recipe)


class CollectSmelt(BTSelector):
    def __init__(self, itemstack=None, recipe=None, **kwargs):
        super(CollectSmelt, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.name = 'smelt %s' % self.itemstack

    def is_valid(self):
        """ smelting later today """
        return False


class CollectBrew(BTSelector):
    def __init__(self, itemstack=None, recipe=None, **kwargs):
        super(CollectBrew, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.name = 'brew %s' % self.itemstack

    def is_valid(self):
        """ brewing not today """
        return False


class CollectMobKill(BTSelector):
    def __init__(self, itemstack=None, recipe=None, **kwargs):
        super(CollectMobKill, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.name = 'kill for %s' % self.itemstack

    def is_valid(self):
        """ it will take time before the bot will kill mobs """
        return False


class CraftItem(BTSelector):
    def __init__(self, itemstack=None, recipe=None, **kwargs):
        super(CraftItem, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.recipe = recipe
        self.name = 'craft %s' % self.itemstack
        self.sorted_tables = None
        log.msg(self.name)

    def is_valid(self):
        for itemstack in self.recipe.resources:
            if not self.blackboard.inventory_player.has_item_count(itemstack):
                log.msg("don't have %s for crafting" % itemstack)
                return False
        return not self.recipe.need_bench or self.is_tables_around

    def setup(self):
        if self.recipe.need_bench:
            self.crafting_tables_around = list(self.blackboard.blocks_around(self.blackboard.bot_object.position, block_number=blocks.CraftingTable.number, distance=80))
            log.msg("There are %d crafting table around" % len(self.crafting_tables_around))

    @property
    def is_tables_around(self):
        return len(self.crafting_tables_around) > 0

    def get_closest_table(self):
        self.crafting_tables_around = sorted(self.crafting_tables_around, key=lambda b: (b.coords - self.blackboard.bot_object.position).size_pow)
        return self.crafting_tables_around.pop(0)

    def choices(self):
        if self.recipe.need_bench:
            while self.is_tables_around:
                table = self.get_closest_table()
                yield self.make_behavior(CraftItemAtTable, recipe=self.recipe, craftingtable=table)
        else:
            yield self.make_behavior(CraftItemInventory, recipe=self.recipe)


class CraftItemAtTable(BTSequencer):
    def __init__(self, recipe=None, craftingtable=None, **kwargs):
        super(CraftItemAtTable, self).__init__(**kwargs)
        self.recipe = recipe
        self.craftingtable = craftingtable
        self.name = "go to %s and craft %s" % (craftingtable, recipe)
        log.msg(self.name)

    def is_valid(self):
        return len(self.dig_positions) > 0

    def setup(self):
        self.dig_positions = self.blackboard.positions_to_dig(self.craftingtable.coords)

    def choices(self):
        yield self.make_behavior(TravelTo, coords=self.craftingtable.coords, multiple_goals=self.dig_positions)
        yield self.make_behavior(CraftItemTable, recipe=self.recipe, craftingtable=self.craftingtable)


class TravelTo(BTSequencer):
    def __init__(self, coords=None, bb=None, multiple_goals=None, shorten_path_by=0, **kwargs):
        super(TravelTo, self).__init__(**kwargs)
        self.travel_coords = coords
        self.travel_bb = bb
        self.travel_multiple_goals = multiple_goals
        self.shorten_path_by = shorten_path_by
        self.path = None
        log.msg(self.name)

    @property
    def name(self):
        if self.travel_coords is not None:
            return 'travel to %s from %s' % (self.blackboard.get_block_coords(self.travel_coords), self.blackboard.bot_standing_on_block(self.blackboard.bot_object))
        else:
            return 'travel to %s from %s' % (self.travel_bb.bottom_center, self.blackboard.bot_standing_on_block(self.blackboard.bot_object))

    def is_valid(self):
        return self.path is not None

    @inlineCallbacks
    def setup(self):
        sb = self.blackboard.bot_standing_on_block(self.blackboard.bot_object)
        while sb is None:
            yield utils.reactor_break()
            sb = self.blackboard.bot_standing_on_block(self.blackboard.bot_object)
        else:
            if self.travel_multiple_goals is not None:
                d = cooperate(AStarMultiCoords(dimension=self.blackboard.dimension,
                                               start_coords=sb.coords,
                                               goal_coords=self.travel_coords,
                                               multiple_goals=self.travel_multiple_goals)).whenDone()
            elif self.travel_coords is not None:
                d = cooperate(AStarCoords(dimension=self.blackboard.dimension,
                                          start_coords=sb.coords,
                                          goal_coords=self.travel_coords)).whenDone()
            else:
                d = cooperate(AStarBBCol(dimension=self.blackboard.dimension,
                                         start_coords=sb.coords,
                                         bb=self.travel_bb)).whenDone()
            d.addErrback(logbot.exit_on_error)
            astar = yield d
            if astar.path is not None:
                current_start = self.blackboard.bot_standing_on_block(self.blackboard.bot_object)
                if sb == current_start:
                    self.path = astar.path
                    if self.shorten_path_by > 0:
                        self.path = self.path[self.shorten_path_by:]
                    self.start_coords = current_start.coords

    def choices(self):
        for step in reversed(self.path):
            yield self.make_behavior(MoveTo, start=self.start_coords, target=step.coords)
            self.start_coords = step.coords


class MoveTo(BTAction):
    def __init__(self, target=None, start=None, **kwargs):
        super(MoveTo, self).__init__(**kwargs)
        self.target_coords = target
        self.start_coords = start
        self.was_at_target = False
        self.hold_position_flag = False
        self.name = 'move to %s' % str(self.target_coords)

    def _check_status(self, b_obj):
        gs = GridSpace(self.blackboard.grid)
        self.start_state = gs.get_state_coords(self.start_coords)
        self.target_state = gs.get_state_coords(self.target_coords)
        go = gs.can_go(self.start_state, self.target_state)
        if not go:
            log.msg('cannot go between %s %s' % (self.start_state, self.target_state))
            return Status.failure
        if not self.was_at_target:
            self.was_at_target = self.target_state.vertical_center_in(b_obj.position)
        if self.target_state.base_in(b_obj.aabb) and self.target_state.touch_platform(b_obj.position):
            return Status.success
        return Status.running

    def action(self):
        b_obj = self.blackboard.bot_object
        self.status = self._check_status(b_obj)
        if self.status != Status.running:
            return
        on_ladder = self.blackboard.bot_is_on_ladder(b_obj)
        in_water = self.blackboard.bot_is_in_water(b_obj)
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
        elif self.blackboard.bot_is_standing(b_obj):
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
            self.blackboard.bot_turn_to_direction(b_obj, direction.x, 0, direction.z)
        b_obj.direction = direction

    def jump(self, b_obj):
        b_obj.is_jumping = True

    def sneak(self, b_obj):
        self.blackboard.bot_start_sneaking(b_obj)


class PeekAtPlayer(BTAction):
    def __init__(self, player=None, **kwargs):
        super(PeekAtPlayer, self).__init__(**kwargs)
        self.player = player
        self.name = 'peek at player %s' % player.username

    def on_start(self):
        self.blackboard.bot_turn_to_point(self.blackboard.bot_object, self.player.position_eyelevel)

    def action(self):
        if self.duration_ticks > 0:
            self.status = Status.success


class ShowCursor(BTAction):
    def __init__(self, player=None, **kwargs):
        super(ShowCursor, self).__init__(**kwargs)
        self.player = player
        self.name = 'show player %s cursor' % config.COMMANDER

    def on_start(self):
        player_look_vector = utils.yaw_pitch_to_vector(self.player.yaw, self.player.pitch)
        looking_at_block = self.blackboard.grid_raycast_to_block(self.player.position_eyelevel, player_look_vector)
        if self.blackboard.last_look_at_block != looking_at_block:
            self.blackboard.last_look_at_block = looking_at_block
            if looking_at_block.number == 0:
                self.blackboard.send_chat_message("cursor too far")
                self.blackboard.bot_turn_to_vector(self.blackboard.bot_object, player_look_vector)
            else:
                self.blackboard.send_chat_message("cursor at %s %s" % (looking_at_block.name, looking_at_block.coords))
                self.blackboard.bot_turn_to_point(self.blackboard.bot_object, looking_at_block.coords.offset(0.5, 0.5, 0.5))

    def action(self):
        if self.duration_ticks > 0:
            self.status = Status.success


class CraftItemBase(BTAction):
    def __init__(self, recipe=None, **kwargs):
        super(CraftItemBase, self).__init__(**kwargs)
        self.recipe = recipe

    def on_end(self):
        if self.status == Status.success:
            self.inventory_man.close()

    @inlineCallbacks
    def action(self):
        for click in self.craftsteps():
            confirmed = yield click
            if confirmed not in [True, False]:
                raise Exception("confirmed transaction got to be boolean")
            if not confirmed:
                log.msg("bad news, inventory transaction not confirmed by the server")
                self.status = Status.failure
                return
        self.status = Status.success

    def craftsteps(self):
        for crafting_offset, itemstack in enumerate(self.recipe.plan):
            if itemstack is None:  # crafting spot in recipe is empty
                continue
            yield self.inventory_man.cursor_hold(itemstack)
            yield self.put_craftoffset_slot(crafting_offset)
        self.inventory_man.set_crafted_item(self.recipe)
        while not self.inventory_man.is_cursor_empty:
            yield self.inventory_man.empty_cursor()
        yield self.get_crafted_item()
        self.inventory_man.erase_craft_slots()
        while not self.inventory_man.is_cursor_empty:
            yield self.inventory_man.empty_cursor()
        self.inventory_man.increment_collected(self.recipe.itemstack)

    def put_craftoffset_slot(self, offset):
        slot = self.inventory.crafting_offset_as_slot(offset)
        return self.inventory_man.right_click_slot(slot)

    def get_crafted_item(self):
        return self.inventory_man.click_slot(self.inventory.crafted_slot)


class CraftItemInventory(CraftItemBase):
    def __init__(self, **kwargs):
        super(CraftItemInventory, self).__init__(**kwargs)
        self.name = "%s in inventory" % self.recipe
        log.msg(self.name)

    def on_start(self):
        self.inventory = self.blackboard.inventory_player
        self.inventory_man = InventoryManipulation(inventory=self.inventory, blackboard=self.blackboard)


class CraftItemTable(CraftItemBase):
    def __init__(self, craftingtable=None, **kwargs):
        super(CraftItemTable, self).__init__(**kwargs)
        self.craftingtable = craftingtable
        self.name = "%s on %s" % (self.recipe, self.craftingtable)
        log.msg(self.name)

    @inlineCallbacks
    def on_start(self):
        data = {"x": self.craftingtable.x,
                "y": self.craftingtable.y,
                "z": self.craftingtable.z,
                "face": 0,
                "slotdata": self.blackboard.itemstack_as_slotdata(itemstack=self.blackboard.inventory_player.active_item()),
                "cursor_x": 8,
                "cursor_y": 8,
                "cursor_z": 8}
        self.blackboard.send_packet("player block placement", data)
        self.inventory = yield self.blackboard.receive_inventory()
        self.inventory_man = InventoryManipulation(inventory=self.inventory, blackboard=self.blackboard)


class DropInventory(BTAction):
    def __init__(self, **kwargs):
        super(DropInventory, self).__init__(**kwargs)
        self.name = "drop inventory"

    def on_start(self):
        self.inventory_man = InventoryManipulation(inventory=self.blackboard.inventory_player, blackboard=self.blackboard)

    def dropsteps(self):
        for slot, itemstack in self.inventory_man.inventory.slot_items():
            yield self.inventory_man.click_slot(slot)
            yield self.inventory_man.click_drop()
            log.msg('dropped %s' % itemstack)

    @inlineCallbacks
    def action(self):
        for drop in self.dropsteps():
            confirmed = yield drop
            if not confirmed:
                log.err("bad news, inventory transaction not confirmed by the server, click slot")
                self.status = Status.failure
                return
        self.status = Status.success

    def on_end(self):
        if self.status == Status.success:
            self.inventory_man.close()


class InventorySelectActive(BTAction):
    def __init__(self, itemstack=None, **kwargs):
        super(InventorySelectActive, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.name = "hold item %s" % self.itemstack

    @classmethod
    def parse_parameters(cls, itemname):
        try:
            istack = items.item_db.item_by_name(itemname)
        except KeyError:
            istack = None
        return istack

    def on_start(self):
        self.inventory_man = InventoryManipulation(inventory=self.blackboard.inventory_player, blackboard=self.blackboard)

    @inlineCallbacks
    def action(self):
        if not self.inventory_man.has_item(self.itemstack):
            self.status = Status.failure
            self.blackboard.send_chat_message("don't have %s in my inventory" % self.itemstack.name)
            return
        if self.inventory_man.item_active(self.itemstack):
            self.status = Status.success
            return
        active_slot = self.inventory_man.item_at_active_slot(self.itemstack)
        if active_slot is not None:
            self.inventory_man.set_active_slot(active_slot)
            self.status = Status.success
            return
        slot_position = self.inventory_man.slot_at_item(self.itemstack)
        confirmed = yield self.inventory_man.click_slot(slot_position)
        if not confirmed:
            log.msg("bad news, inventory transaction not confirmed by the server")
            self.status = Status.failure
            return
        active_slot = self.inventory_man.choose_active_slot()
        confirmed = yield self.inventory_man.click_active_slot(active_slot)
        if not confirmed:
            log.msg("bad news, inventory transaction not confirmed by the server")
            self.status = Status.failure
            return
        if not self.inventory_man.is_cursor_empty:
            confirmed = yield self.inventory_man.click_slot(slot_position)
            if not confirmed:
                log.msg("bad news, inventory transaction not confirmed by the server")
                self.status = Status.failure
                return
        self.inventory_man.set_active_slot(active_slot)
        self.status = Status.success

    def on_end(self):
        """ make sure the item is on active slot and close the inventory """
        if self.status == Status.success:
            self.blackboard.send_chat_message("holding %s" % self.itemstack.name)
        self.inventory_man.close()


class WaitForDrop(BTAction):
    def __init__(self, block=None, itemstack=None, drop_everytime=None, **kwargs):
        super(DigBlock, self).__init__(**kwargs)
        self.itemstack = itemstack
        self.block = block
        self.drop_everytime = drop_everytime
        self.name = "wait for drop %s from %s" % (self.itemstack, self.block)

    def action(self):
        self.status = Status.success


class DigBlock(BTAction):
    def __init__(self, block=None, **kwargs):
        super(DigBlock, self).__init__(**kwargs)
        self.block = block
        self.name = 'dig %s' % block
        self.wait_ticks = dig.tick_duration(self.blackboard.held_item, self.block)
        self.block_packet_dict = {"x": self.block.x, "y": self.block.y, "z": self.block.z, "face": 0}

    def start_digging(self):
        pdict = {"state": 0}
        pdict.update(self.block_packet_dict)
        self.blackboard.send_packet("player digging", pdict)

    def stop_digging(self):
        pdict = {"state": 2}
        pdict.update(self.block_packet_dict)
        self.blackboard.send_packet("player digging", pdict)

    def cleanup(self):
        pdict = {"state": 1}
        pdict.update(self.block_packet_dict)
        self.blackboard.send_packet("player digging", pdict)

    def on_start(self):
        self.start_digging()

    def on_end(self):
        self.stop_digging()

    def action(self):
        if self.duration_ticks >= self.wait_ticks:
            self.status = Status.success
