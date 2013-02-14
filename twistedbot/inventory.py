
import items
import logbot


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


class PlayerInventory(InvetoryBase):
    extra_slots = 9

    def __init__(self):
        super(PlayerInventory, self).__init__()
        self.active_slot = None

    def slot_items(self):
        for i, itemstack in enumerate(self.slots):
            if itemstack is not None:
                yield i, itemstack


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
        for i, slotdata in enumerate(slotdata_list):
            itemstack = items.ItemStack.from_slotdata(slotdata)
            inv.set_slot(i, itemstack)

    def active_slot_change(self, sid):
        log.msg("active slot changed to %d" % sid)
        self.player_inventory.active_slot = sid
