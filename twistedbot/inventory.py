
import random
from collections import defaultdict

from twisted.internet.defer import Deferred

import items
import logbot
import utils


log = logbot.getlogger("INVENTORY")


class InvetoryBase(object):
    base_slots = 36

    def __init__(self, extra_slots, window_id, inventory_container):
        self.extra_slots = extra_slots + 1
        self.window_id = window_id
        self.inventory_container = inventory_container
        self.slots = [None for _ in xrange(self.extra_slots + self.base_slots)]

    def __repr__(self):
        return self.__class__.__name__

    def close_window(self):
        self.inventory_container.close_window()

    def set_slot(self, position, itemstack):
        self.slots[position] = itemstack

    def store_slots(self):
        for i in xrange(self.extra_slots, len(self.slots)):
            slot = i + self.extra_slots
            yield slot, self.slots[slot]

    def slot_for(self, itemstack):
        for position, slot_itemstack in self.store_slots():
            if slot_itemstack is None:
                return position
            if itemstack.is_same(slot_itemstack, ignore_common=True):
                if slot_itemstack.stacksize > slot_itemstack.count:
                    return position
        else:
            return None

    def slot_items(self):
        for i, itemstack in enumerate(self.slots):
            if itemstack is not None:
                yield i, itemstack

    def has_item(self, itemstack):
        for slot in self.slots:
            if itemstack.is_same(slot):
                return True
        else:
            return False

    def slot_at_item(self, item):
        for i, itemstack in enumerate(self.slots):
            if item.is_same(itemstack):
                return i
        else:
            return None

    def item_at_slot(self, slot):
        return self.slots[slot]

    def has_item_count(self, itemstack):
        count = itemstack.count
        for _, slot_itemstack in self.slot_items():
            #print 'has_item_count', itemstack, slot_itemstack, itemstack.is_same(slot_itemstack)
            if itemstack.is_same(slot_itemstack):
                count -= slot_itemstack.count
                if count <= 0:
                    return True
        else:
            return False

    def has_space_for(self, itemstack):
        count = itemstack.count
        for i, slot_itemstack in self.store_slots():
            if slot_itemstack is None:
                return True
            if itemstack.common:
                continue
            if itemstack.is_same(slot_itemstack):
                count = count - (itemstack.stacksize - slot_itemstack.count)
                if count <= 0:
                    return True
        else:
            return False


class PlayerInventory(InvetoryBase):
    extra_slots = 8
    crafted_slot = 0

    def __init__(self, **kwargs):
        super(PlayerInventory, self).__init__(extra_slots=self.extra_slots, window_id=0, **kwargs)
        self.active_slot = None

    def active_possition_as_slot(self, i):
        return self.base_slots + i

    def is_item_active(self, item):
        slot_number = self.active_possition_as_slot(self.active_slot)
        return item.is_same(self.slots[slot_number])

    def active_item(self):
        return self.slots[self.active_possition_as_slot(self.active_slot)]

    def item_at_active_slot(self, item):
        for i in xrange(9):
            slot = self.active_possition_as_slot(i)
            if item.is_same(self.slots[slot]):
                return i
        else:
            return None

    def active_position(self, i):
        self.active_slot = i

    def choose_active_slot(self):
        return random.randint(0, 8)

    def crafting_offset_as_slot(self, offset):
        return 1 + offset

    def crafting_slots(self):
        for i in xrange(4):
            yield self.crafting_offset_as_slot(i)


class CraftingTable(InvetoryBase):
    crafted_slot = 0

    def crafting_offset_as_slot(self, offset):
        return 1 + offset

    def crafting_slots(self):
        for i in xrange(9):
            yield self.crafting_offset_as_slot(i)


class Chest(InvetoryBase):
    """
    small chest 27 extra slots
    large chest 54 extra slots
    """
    def __init__(self, **kwargs):
        super(Chest, self).__init__(**kwargs)


class Furnace(InvetoryBase):
    pass


class Dispenser(InvetoryBase):
    pass


class EnchantmentTable(InvetoryBase):
    pass


class InvetoryContainer(object):
    inventory_types = [Chest, CraftingTable, Furnace, Dispenser, EnchantmentTable]

    def __init__(self, world):
        self.world = world
        self.player_inventory = PlayerInventory(inventory_container=self)
        self.cursor_item = None
        self.opened_window = None
        self.on_confirmation = None
        self.on_openwindow = None
        self.item_collected_count = defaultdict(int)

    def open_window(self, window_id=None, window_type=None, extra_slots=None):
        log.msg("open window %d %d %d" % (window_id, window_type, extra_slots))
        self.opened_window = self.inventory_types[window_type](extra_slots=extra_slots, window_id=window_id, inventory_container=self)

    def close_window(self, window_id=None):
        if window_id is not None:
            log.msg('server closed window %d' % window_id)
        self.opened_window = None

    def set_slot(self, window_id=None, slot_id=None, slotdata=None):
        itemstack = items.ItemStack.from_slotdata(slotdata)
        log.msg('server set slot %d with %s' % (slot_id, itemstack))
        if window_id == -1 and slot_id == -1:
            self.cursor_item = itemstack
        elif window_id == 0:
            self.player_inventory.set_slot(slot_id, itemstack)
        else:
            self.opened_window.set_slot(slot_id, itemstack)

    def set_slots(self, window_id=None, slotdata_list=None):
        log.msg('received %d items for window_id %d %s' % (len(slotdata_list), window_id, str(["%d-%s" % (i, items.ItemStack.from_slotdata(slotdata)) for i, slotdata in enumerate(slotdata_list) if slotdata.id > 0])))
        inv = self.player_inventory if window_id == 0 else self.opened_window
        for slot_id, slotdata in enumerate(slotdata_list):
            itemstack = items.ItemStack.from_slotdata(slotdata)
            inv.set_slot(slot_id, itemstack)
        if self.on_openwindow is not None:
            utils.do_now(self.on_openwindow.d.callback, self.opened_window)
            self.on_openwindow = None

    def active_slot_change(self, sid):
        log.msg("active slot changed to %d" % sid)
        self.player_inventory.active_slot = sid

    def confirm_transaction(self, window_id=None, action_number=None, acknowledged=None):
        if self.on_confirmation is not None:
            self.on_confirmation.confirm(window_id=window_id, action_number=action_number, acknowledged=acknowledged)
            utils.do_now(self.on_confirmation.d.callback, self.on_confirmation.confirmed)
            self.on_confirmation = None

    def collect_action(self, collected_eid=None, collector_eid=None):
        if self.world.bot.eid == collector_eid:  # it's me picking up item
            ent = self.world.entities.get_entity(collected_eid)
            itemstack = ent.itemstack
            self.item_collected_count[itemstack.name] += itemstack.count
            log.msg("collected %s" % itemstack)

    def get_confirmation(self, action_number=None, window_id=0):
        con = Confirmation(action_number=action_number, window_id=window_id)
        self.on_confirmation = con
        return con.d

    def get_open_window(self):
        ow = OpenWindow()
        self.on_openwindow = ow
        return ow.d

    def get_item_collected_count(self, itemstack):
        return self.item_collected_count[itemstack.name]

    def tool_for_block(self, block_cls):
        if not dig.is_digable(block_cls):
            return False, False, None
        if dig.is_instant(block_cls):
            return True, True, None
        hand_ticks = dig.dig_ticks(None, block_cls)
        tool = None
        lowest_ticks = hand_ticks
        for _, istack in self.player_inventory.store_slots:
            tool_ticks = dig.dig_ticks(istack, block_cls)
            if tool_ticks < lowest_ticks:
                lowest_ticks = tool_ticks
                tool = istack
        if dig.needs_tool(block_cls) and tool is None:
            return True, False, None
        return True, True, tool


class OpenWindow(object):
    def __init__(self):
        self.d = Deferred()


class Confirmation(object):
    def __init__(self, window_id=0, action_number=None):
        self.d = Deferred()
        self.window_id = window_id
        self.action_number = action_number
        self.confirmed = False

    def confirm(self, window_id=None, action_number=None, acknowledged=None):
        if self.window_id != window_id:
            return
        if self.action_number != action_number:
            return
        self.confirmed = acknowledged


class InventoryManipulation(object):
    def __init__(self, inventory=None, blackboard=None):
        self.inventory = inventory
        self.blackboard = blackboard
        self.clicked_slot = None
        self.cursor_item = None

    @property
    def is_cursor_empty(self):
        return self.cursor_item is None

    def close(self):
        self.blackboard.send_packet("close window", {"window_id": self.inventory.window_id})
        self.inventory.close_window()

    def erase_craft_slots(self):
        for slot in self.inventory.crafting_slots():
            self.inventory.set_slot(slot, None)

    def set_crafted_item(self, recipe):
        resources = []
        for slot in self.inventory.crafting_slots():
            res = self.inventory.item_at_slot(slot)
            if res is not None:
                resources.append(res)
        itemstack = recipe.crafted_item(resources)
        #log.msg('crafted item is %s from %s' % (itemstack, resources))
        self.inventory.set_slot(self.inventory.crafted_slot, itemstack)

    def cursor_hold(self, itemstack):
        if itemstack.is_same(self.cursor_item):
            return True
        else:
            slot = self.slot_at_item(itemstack)
            return self.click_slot(slot)

    def empty_cursor(self):
        if self.is_cursor_empty:
            return True
        else:
            slot = self.inventory.slot_for(self.cursor_item)
            if slot is None:
                raise Exception("could not choose inventory slot")
            return self.click_slot(slot)

    def click_active_slot(self, active_position):
        return self.click_slot(self.inventory.active_possition_as_slot(active_position))

    def right_click_slot(self, slot):
        return self.click_slot(slot, right_mouse_button=True)

    def click_drop(self):
        data = {"window_id": self.inventory.window_id,
                "slot": -999,
                "mouse_button": 0,
                "action_number": self.blackboard.inventory_transaction_counter_inc,
                "hold_shift": False,
                "slotdata": self.blackboard.itemstack_as_slotdata(itemstack=None)}
        self.blackboard.send_packet("click window", data)
        d = self.blackboard.inventory_get_confirmation(action_number=self.blackboard.inventory_transaction_counter, window_id=self.inventory.window_id)
        d.addCallback(self.transaction_confirmed_drop)
        return d

    def transaction_confirmed_drop(self, confirmed):
        if confirmed:
            self.cursor_item = None
            self.inventory.set_slot(self.clicked_slot, None)
        return confirmed

    def click_slot(self, slot, right_mouse_button=False):
        if slot is None:
            raise Exception("click slot is None, inventory full?")
        itemstack = self.inventory.item_at_slot(slot)
        self.clicked_slot = slot
        self.clicked_right_mouse_button = right_mouse_button
        data = {"window_id": self.inventory.window_id,
                "slot": slot,
                "mouse_button": 1 if right_mouse_button else 0,
                "action_number": self.blackboard.inventory_transaction_counter_inc,
                "hold_shift": False,
                "slotdata": self.blackboard.itemstack_as_slotdata(itemstack=itemstack)}
        #log.msg('click inventory %s' % str(data))
        self.blackboard.send_packet("click window", data)
        d = self.blackboard.inventory_get_confirmation(action_number=self.blackboard.inventory_transaction_counter, window_id=self.inventory.window_id)
        d.addCallback(self.transaction_confirmed)
        return d

    def transaction_confirmed(self, confirmed):
        if not confirmed:
            return confirmed
        if self.clicked_right_mouse_button:
            if self.cursor_item is not None:
                next_cursor_item = self.cursor_item.copy(count=self.cursor_item.count - 1)
                under_cursor = self.inventory.item_at_slot(self.clicked_slot)
                if under_cursor is None:
                    self.inventory.set_slot(self.clicked_slot, self.cursor_item.copy(count=1))
                else:
                    if not self.cursor_item.is_same(under_cursor):
                        raise Exception("This could not be planned, cursor item %s diff from slot item %s during right click" % (self.cursor_item, under_cursor))
                    if under_cursor.count == under_cursor.stacksize:
                        raise Exception("right click on full itemstack, no no...")
                    self.inventory.set_slot(self.clicked_slot, under_cursor.copy(count=under_cursor.count + 1))
                self.cursor_item = next_cursor_item
            else:
                raise Exception('right click with empty cursor? maybe later')
        else:
            under_cursor = self.inventory.item_at_slot(self.clicked_slot)
            if under_cursor is not None and self.cursor_item is not None and under_cursor.is_same(self.cursor_item):
                slotspace = under_cursor.stacksize - under_cursor.count
                if slotspace > 0:
                    if slotspace >= self.cursor_item.count:
                        self.inventory.set_slot(self.clicked_slot, under_cursor.copy(count=under_cursor.count + self.cursor_item.count))
                        self.cursor_item = None
                    else:
                        self.inventory.set_slot(self.clicked_slot, under_cursor.copy(count=under_cursor.stacksize))
                        self.cursor_item = self.cursor_item.copy(count=self.cursor_item.count - slotspace)
                else:
                    raise Exception("left click on full itemstack, no no...")
            else:
                self.inventory.set_slot(self.clicked_slot, self.cursor_item)
                self.cursor_item = under_cursor
        return confirmed

    def set_active_slot(self, active_slot):
        if active_slot != self.blackboard.inventory_player.active_slot:
            self.blackboard.send_packet("held item change", {"active_slot": active_slot})
            self.blackboard.inventory_player.active_slot = active_slot

    def has_item(self, itemstack):
        return self.inventory.has_item(itemstack)

    def item_active(self, itemstack):
        return self.inventory.is_item_active(itemstack)

    def item_at_active_slot(self, itemstack):
        return self.inventory.item_at_active_slot(itemstack)

    def slot_at_item(self, itemstack):
        return self.inventory.slot_at_item(itemstack)

    def choose_active_slot(self):
        return self.blackboard.inventory_player.choose_active_slot()

    def increment_collected(self, itemstack):
        self.inventory.inventory_container.item_collected_count[itemstack.name] += itemstack.count
