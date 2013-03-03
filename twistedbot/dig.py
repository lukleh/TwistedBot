
import math


def relative_block_hardness(holding_item, block):
    block_hardness = block.hardness
    if block_hardness < 0.0:
        return 0.0
    elif block_hardness == 0.0:
        return -1.0
    else:
        if not can_harvest_block(holding_item, block):
            return 1.0 / block_hardness / 100.0
        else:
            return strength_vs_block(holding_item, block) / block_hardness / 30.0


def can_harvest_block(holding_item, block):
    if block.material.is_tool_not_required:
        return True
    else:
        if holding_item is None:  # empty slot
            return False
        else:
            can = holding_item.can_harvest_block(block)
            assert can is not None
            assert can is True or can is False
            return can


def strength_vs_block(holding_item, block):
    strength = 1.0
    if holding_item is not None:
        strength *= holding_item.strength_vs_block(block)
    # enchant_efficiency = EnchantmentHelper.getEfficiencyModifier(player)
    # if enchant_efficiency > 0 and current_held_item is not None:
    #     enchant_efficiency_modf = enchant_efficiency * enchant_efficiency + 1
    #     if not current_held_item.canHarvestBlock(block) and strength <= 1.0:
    #         strength += enchant_efficiency_modf * 0.08
    #     else:
    #         strength += enchant_efficiency_modf
    # if player.is_potion_active(potions.digSpeed):
    #     strength *= 1.0 + (potions.digSpeed.amplifier + 1) * 0.2
    # if player.is_potion_active(potions.digSlowdown):
    #     strength *= 1.0 - (potions.digSlowdown.amplifier + 1) * 0.2
    # if player_in_water and not EnchantmentHelper.getAquaAffinityModifier(player):
    #     strength /= 5.0
    # if not player.onGround:
    #     strength /= 5.0
    return strength


def dig_ticks(itemstack, block):
    rbh = relative_block_hardness(itemstack, block)
    ticks = int(math.ceil(1.0 / rbh))
    return ticks


def is_diggable(block_cls):
    return not block_cls.is_fluid and not block_cls.hardness < 0


def is_instant(block_cls):
    return block_cls.hardness == 0


def needs_tool(block_cls):
    return not block_cls.material.is_tool_not_required


def debug_printout(itemstack, block):
    rbh = relative_block_hardness(itemstack, block)
    ticks = int(math.ceil(1.0 / rbh))
    print 'TICKS %s RBH %.3f' % (ticks, rbh),
    if itemstack is not None:
        print itemstack.name, '-', block.name
    else:
        print itemstack, '-', block.name


def debug_dig_ticks():
    """
    goes through every combination of item X block and prints dig properties
    """
    import blocks
    import items
    for i in xrange(1, 256):
        block = blocks.block_list[i]
        if block is None:
            continue
        if block.is_fluid:  # no meaning of digging fluid, use bucket
            print block.name, "IS FLUID"
            continue
        if block.hardness < 0:
            print block.name, 'UNBREAKABLE'
            continue
        if block.hardness == 0:
            print block.name, 'INSTANT'
            continue
        if block.material.is_tool_not_required:
            print block.name, 'BARE HANDS'
            continue
        for itemstack in items.item_db.all_items():
            debug_printout(itemstack, block)
        else:
            debug_printout(None, block)


if __name__ == '__main__':
    debug_dig_ticks()
