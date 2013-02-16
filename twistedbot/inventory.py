
import random

from twisted.internet.defer import Deferred

import items
import logbot
import utils


log = logbot.getlogger("INVENTORY")


class InvetoryBase(object):
    def __init__(self):
        self.slots = [None for _ in xrange(self.extra_slots + 36)]

    def set_slot(self, position, itemstack):
        self.slots[position] = itemstack

    def slot_items(self):
        for i in xrange(self.extra_slots):
            if self.slots[i] is not None:
                yield i, self.slots[i]

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


class PlayerInventory(InvetoryBase):
    extra_slots = 9

    def __init__(self):
        super(PlayerInventory, self).__init__()
        self.active_slot = None

    def holding_possition_as_slot(self, i):
        return 36 + i

    def slot_items(self):
        for i, itemstack in enumerate(self.slots):
            if itemstack is not None:
                yield i, itemstack

    def is_holding_item(self, item):
        slot_number = self.holding_possition_as_slot(self.active_slot)
        return item.is_same(self.slots[slot_number])

    def item_holding_position(self, item):
        for i in xrange(9):
            slot = self.holding_possition_as_slot(i)
            if item.is_same(self.slots[slot]):
                return i
        else:
            return None

    def holding_position(self, i):
        self.active_slot = i


class CraftingTable(InvetoryBase):
    extra_slots = 10


class Chest(InvetoryBase):
    extra_slots = 27


class LargeChest(InvetoryBase):
    extra_slots = 54


class Furnace(InvetoryBase):
    extra_slots = 3


class Dispenser(InvetoryBase):
    extra_slots = 9


class EnchantmentTable(InvetoryBase):
    extra_slots = 1


class InvetoryContainer(object):
    inventory_types = [LargeChest, CraftingTable, Furnace, Dispenser, EnchantmentTable]

    def __init__(self):
        self.player_inventory = PlayerInventory()
        self.container = {0: self.player_inventory}
        self.holding_item = None
        self.opened_window = None
        self.on_confirmation = None

    def open_window(self, window_id=None, window_type=None, extra_slots=None):
        if window_id not in self.container:
            self.container[window_id] = self.inventory_types[window_type]()
        self.opened_window = self.container[window_id]

    def close_window(self, window_id=None):
        self.opened_window = None

    def click_window(self, window_id=None, slot_id=None, mouse_button=None, token=None, hold_shift=None, slotdata=None):
        pass

    def set_slot(self, window_id=None, slot_id=None, slotdata=None):
        itemstack = items.ItemStack.from_slotdata(slotdata)
        if window_id == -1 and slot_id == -1:
            self.holding_item = itemstack
        else:
            self.container[window_id].set_slot(slot_id, itemstack)

    def set_slots(self, window_id=None, slotdata_list=None):
        inv = self.container[window_id]
        for slot_id, slotdata in enumerate(slotdata_list):
            itemstack = items.ItemStack.from_slotdata(slotdata)
            inv.set_slot(slot_id, itemstack)

    def active_slot_change(self, sid):
        log.msg("active slot changed to %d" % sid)
        self.player_inventory.active_slot = sid

    def confirm_transaction(self, window_id=None, action_number=None, acknowledged=None):
        if self.on_confirmation is not None:
            self.on_confirmation.confirm(window_id=window_id, action_number=action_number, acknowledged=acknowledged)
            utils.do_now(self.on_confirmation.d.callback, self.on_confirmation.confirmed)
            self.on_confirmation = None

    def get_confirmation(self, action_number=None, window_id=0):
        con = Confirmation(action_number=action_number, window_id=window_id)
        con.d = Deferred()
        self.on_confirmation = con
        return con.d

    def choose_holding_slot(self):
        return self.player_inventory.holding_possition_as_slot(random.randint(0, 8))


class Confirmation(object):
    def __init__(self, window_id=0, action_number=None):
        self.d = None
        self.window_id = window_id
        self.action_number = action_number
        self.confirmed = False

    def confirm(self, window_id=None, action_number=None, acknowledged=None):
        if self.window_id != window_id:
            return
        if self.action_number != action_number:
            return
        self.confirmed = acknowledged
