
import re

import blocks
import logbot
import materials


log = logbot.getlogger("ITEMS")

item_list = [None for _ in xrange(2300)]


class ToolMaterial(object):
    def __init__(self, harvest_level, max_uses, efficiency_on_proper_material, damage_vs_entity, enchantability):
        self.harvest_level = harvest_level
        self.max_uses = max_uses
        self.efficiency_on_proper_material = efficiency_on_proper_material
        self.damage_vs_entity = damage_vs_entity
        self.enchantability = enchantability


class EnumToolMaterial(object):
    WOOD = ToolMaterial(0, 59, 2.0, 0, 15)
    STONE = ToolMaterial(1, 131, 4.0, 1, 5)
    IRON = ToolMaterial(2, 250, 6.0, 2, 14)
    DIAMOND = ToolMaterial(3, 1561, 8.0, 3, 10)
    GOLD = ToolMaterial(0, 32, 12.0, 0, 22)


class ArmorMaterial(object):
    def __init__(self, damage_factor, damage_reduction_amount_array, enchantability):
        self.damage_factor = damage_factor
        self.damage_reduction_amount_array = damage_reduction_amount_array
        self.enchantability = enchantability

    def damage_reduction_amount(self, armor_type):
        return self.damage_reduction_amount_array[armor_type]

    def durability(self, armor_type):
        return ItemArmor.max_damage_array[armor_type] * self.damage_factor


class EnumArmorMaterial(object):
    LEATHER = ArmorMaterial(5, [1, 3, 2, 1], 15)
    CHAIN = ArmorMaterial(15, [2, 5, 4, 1], 12)
    IRON = ArmorMaterial(15, [2, 6, 5, 2], 9)
    GOLD = ArmorMaterial(7, [2, 5, 3, 1], 25)
    DIAMOND = ArmorMaterial(33, [3, 8, 6, 3], 10)


class EnumArmorPart(object):
    HELMET = 0
    CHESTPLATE = 1
    LEGGINGS = 2
    BOOTS = 3


class ItemMetaClass(type):
    def __new__(meta, name, bases, dct):
        cls = super(ItemMetaClass, meta).__new__(meta, name, bases, dct)
        if hasattr(cls, 'number'):
            if not hasattr(cls, 'name'):
                cls.name = " ".join(re.findall('[A-Z][^A-Z]*', cls.__name__))
            cls.name = cls.name.lower()
        return cls


class Item(object):
    __metaclass__ = ItemMetaClass
    max_damage = 0
    stacksize = 64

    def __init__(self, number=None):
        self.has_subtypes = False
        self.has_common_type = False
        if hasattr(self, 'number'):
            number = self.number
        self.number = number + 256

    def get_name(self, meta):
        return self.name

    def get_types(self):
        yield ItemStack(self.number)

    def can_harvest_block(self, block):
        return False

    def strength_vs_block(self, block):
        return 1.0

    @property
    def is_damageable(self):
        return self.max_damage > 0 and not self.has_subtypes

    @property
    def is_tool(self):
        return self.stacksize == 1 and self.is_damageable


class ItemBlock(Item):
    def __init__(self, block=None, **kwargs):
        super(ItemBlock, self).__init__(number=block.number - 256, **kwargs)
        self.name = block.name
        self.block = block
        if block.inventory_avoid:
            raise Exception("trying to make an invalid item? block %s" % self.block)


class ItemHandles(Item):
    def __init__(self, **kwargs):
        super(ItemHandles, self).__init__(**kwargs)
        self.stacksize = 1
        self.max_damage = self.material.max_uses


class ItemTool(ItemHandles):
    blocks_effective_against = []

    def strength_vs_block(self, block):
        for block_eff_against in self.blocks_effective_against:
            if block_eff_against.number == block.number:
                return self.material.efficiency_on_proper_material
        return 1.0


class ItemSpade(ItemTool):
    blocks_effective_against = [blocks.GrassBlock,
                                blocks.Dirt,
                                blocks.Sand,
                                blocks.Gravel,
                                blocks.Snow,
                                blocks.SnowBlock,
                                blocks.ClayBlock,
                                blocks.Farmland,
                                blocks.SoulSand,
                                blocks.Mycelium]

    def can_harvest_block(self, block):
        if block.number == blocks.Snow.number:
            return True
        else:
            return block.number == blocks.SnowBlock.number


class IronShovel(ItemSpade):
    number = 0
    material = EnumToolMaterial.IRON


class ItemPickaxe(ItemTool):
    blocks_effective_against = [blocks.Cobblestone,
                                blocks.StoneDoubleSlab,
                                blocks.StoneSlab,
                                blocks.Stone,
                                blocks.Sandstone,
                                blocks.MossStone,
                                blocks.IronOre,
                                blocks.BlockOfIron,
                                blocks.CoalOre,
                                blocks.BlockOfGold,
                                blocks.GoldOre,
                                blocks.DiamondOre,
                                blocks.BlockOfDiamond,
                                blocks.Ice,
                                blocks.Netherrack,
                                blocks.LapisLazuliOre,
                                blocks.LapisLazuliBlock,
                                blocks.RedstoneOre,
                                blocks.GlowingRedstoneOre,
                                blocks.Rail,
                                blocks.DetectorRail,
                                blocks.PoweredRail]

    def can_harvest_block(self, block):
        if block.number == blocks.Obsidian.number:
            return self.material.harvest_level == 3
        else:
            if block.number != blocks.BlockOfDiamond.number and block.number != blocks.DiamondOre.number:
                if block.number != blocks.BlockOfEmerald.number and block.number != blocks.EmeraldOre.number:
                    if block.number != blocks.BlockOfGold.number and block.number != blocks.GoldOre.number:
                        if block.number != blocks.BlockOfIron.number and block.number != blocks.IronOre.number:
                            if block.number != blocks.LapisLazuliBlock.number and block.number != blocks.LapisLazuliOre.number:
                                if block.number != blocks.RedstoneOre.number and block.number != blocks.GlowingRedstoneOre.number:
                                    if block.material == materials.rock:
                                        return True
                                    else:
                                        if block.material == materials.iron:
                                            return True
                                        else:
                                            return block.material == materials.anvil
                                else:
                                    return self.material.harvest_level >= 2
                            else:
                                return self.material.harvest_level >= 1
                        else:
                            return self.material.harvest_level >= 1
                    else:
                        return self.material.harvest_level >= 2
                else:
                    return self.material.harvest_level >= 2
            else:
                return self.material.harvest_level >= 2

    def strength_vs_block(self, block):
        if block.material == materials.iron or block.material == materials.anvil or block.material == materials.rock:
            return self.material.efficiency_on_proper_material
        else:
            return super(ItemPickaxe, self).strength_vs_block(block)


class IronPickaxe(ItemPickaxe):
    number = 1
    material = EnumToolMaterial.IRON


class ItemAxe(ItemTool):
    blocks_effective_against = [blocks.WoodenPlanks,
                                blocks.Bookshelf,
                                blocks.Wood,
                                blocks.Chest,
                                blocks.StoneDoubleSlab,
                                blocks.StoneSlab,
                                blocks.Pumpkin,
                                blocks.JackOLantern]

    def strength_vs_block(self, block):
        if block.material == materials.wood or block.material == materials.plants or block.material == materials.vine:
            return self.material.efficiency_on_proper_material
        else:
            return super(ItemAxe, self).strength_vs_block(block)


class IronAxe(ItemAxe):
    number = 2
    material = EnumToolMaterial.IRON


class FlintAndSteel(Item):
    number = 3
    stacksize = 1
    max_damage = 64


class ItemFood(Item):
    def __init__(self, **kwargs):
        super(ItemFood, self).__init__(**kwargs)
        if not hasattr(self, 'heal_amount'):
            raise Exception('ItemFood missing "heal_amount"')


class RedApple(ItemFood):
    number = 4
    heal_amount = 4
    saturation_modifier = 0.3


class Bow(Item):
    number = 5
    stacksize = 1
    max_damage = 384


class Arrow(Item):
    number = 6


class MultiItem(Item):
    def __init__(self, **kwargs):
        super(MultiItem, self).__init__(**kwargs)
        self.has_subtypes = True

    def get_types(self):
        for i, _ in enumerate(self.sub_names):
            yield ItemStack(self.number, i)

    def get_name(self, meta):
        return self.sub_names[meta].lower()


class Coal(MultiItem):
    number = 7
    sub_names = ["Coal", "Charcoal"]


class Diamond(Item):
    number = 8


class IronIngot(Item):
    number = 9


class GoldIngot(Item):
    number = 10


class ItemSword(ItemTool):
    def can_harvest_block(self, block):
        return block.number == blocks.Cobweb.number

    def strength_vs_block(self, block):
        if block.number == blocks.Cobweb.number:
            return 15.0
        else:
            mat = block.material
            if mat != materials.plants and mat != materials.vine and mat != materials.coral and mat != materials.leaves and mat != materials.pumpkin:
                return 1.0
            else:
                return 1.5


class IronSword(ItemSword):
    number = 11
    material = EnumToolMaterial.IRON


class WoodenSword(ItemSword):
    number = 12
    material = EnumToolMaterial.WOOD


class WoodenShovel(ItemSpade):
    number = 13
    material = EnumToolMaterial.WOOD


class WoodenPickaxe(ItemPickaxe):
    number = 14
    material = EnumToolMaterial.WOOD


class WoodenAxe(ItemAxe):
    number = 15
    material = EnumToolMaterial.WOOD


class StoneSword(ItemSword):
    number = 16
    material = EnumToolMaterial.STONE


class StoneShovel(ItemSpade):
    number = 17
    material = EnumToolMaterial.STONE


class StonePickaxe(ItemPickaxe):
    number = 18
    material = EnumToolMaterial.STONE


class StoneAxe(ItemAxe):
    number = 19
    material = EnumToolMaterial.STONE


class DiamiondSword(ItemSword):
    number = 20
    material = EnumToolMaterial.DIAMOND


class DiamiondShovel(ItemSpade):
    number = 21
    material = EnumToolMaterial.DIAMOND


class DiamondPickaxe(ItemPickaxe):
    number = 22
    material = EnumToolMaterial.DIAMOND


class DiamondAxe(ItemAxe):
    number = 23
    material = EnumToolMaterial.DIAMOND


class Sticks(Item):
    number = 24


class EmptyBowl(Item):
    number = 25


class SoupBowl(ItemFood):
    number = 26
    stacksize = 1
    heal_amount = 6
    saturation_modifier = 0.6


class GoldenSword(ItemSword):
    number = 27
    material = EnumToolMaterial.GOLD


class GoldenShovel(ItemSpade):
    number = 28
    material = EnumToolMaterial.GOLD


class GoldenPickaxe(ItemPickaxe):
    number = 29
    material = EnumToolMaterial.GOLD


class GoldenAxe(ItemAxe):
    number = 30
    material = EnumToolMaterial.GOLD


class String(Item):
    number = 31


class Feather(Item):
    number = 32


class GunPowder(Item):
    number = 33


class ItemHoe(ItemHandles):
    pass


class WoodenHoe(ItemHoe):
    number = 34
    material = EnumToolMaterial.WOOD


class StoneHoe(ItemHoe):
    number = 35
    material = EnumToolMaterial.STONE


class SteelHoe(ItemHoe):
    number = 36
    material = EnumToolMaterial.IRON


class DiamondHoe(ItemHoe):
    number = 37
    material = EnumToolMaterial.DIAMOND


class GoldenHoe(ItemHoe):
    number = 38
    material = EnumToolMaterial.GOLD


class ItemSeeds(Item):
    pass


class Seeds(ItemSeeds):
    number = 39


class Wheat(Item):
    number = 40


class Bread(ItemFood):
    number = 41
    heal_amount = 5
    saturation_modifier = 0.6


class ItemArmor(Item):
    max_damage_array = [11, 16, 15, 13]

    def __init__(self, **kwargs):
        super(ItemArmor, self).__init__(**kwargs)
        self.stacksize = 1
        self.damage_reduction_amount = self.material.damage_reduction_amount(self.armor_type)
        self.max_damage = self.material.durability(self.armor_type)


class ItemHelmet(ItemArmor):
    armor_type = EnumArmorPart.HELMET


class ItemChestPlate(ItemArmor):
    armor_type = EnumArmorPart.CHESTPLATE


class ItemLeggings(ItemArmor):
    armor_type = EnumArmorPart.LEGGINGS


class ItemBoots(ItemArmor):
    armor_type = EnumArmorPart.BOOTS


class LeatherHelmet(ItemHelmet):
    number = 42
    material = EnumArmorMaterial.LEATHER


class LeatherChestPlate(ItemChestPlate):
    number = 43
    material = EnumArmorMaterial.LEATHER


class LeatherLeggings(ItemLeggings):
    number = 44
    material = EnumArmorMaterial.LEATHER


class LeatherBoots(ItemBoots):
    number = 45
    material = EnumArmorMaterial.LEATHER


class ChainHelmet(ItemHelmet):
    number = 46
    material = EnumArmorMaterial.CHAIN


class ChainChestPlate(ItemChestPlate):
    number = 47
    material = EnumArmorMaterial.CHAIN


class ChainLeggings(ItemLeggings):
    number = 48
    material = EnumArmorMaterial.CHAIN


class ChainBoots(ItemBoots):
    number = 49
    material = EnumArmorMaterial.CHAIN


class IronHelmet(ItemHelmet):
    number = 50
    material = EnumArmorMaterial.IRON


class IronChestPlate(ItemChestPlate):
    number = 51
    material = EnumArmorMaterial.IRON


class IronLeggings(ItemLeggings):
    number = 52
    material = EnumArmorMaterial.IRON


class IronBoots(ItemBoots):
    number = 53
    material = EnumArmorMaterial.IRON


class DiamondHelmet(ItemHelmet):
    number = 54
    material = EnumArmorMaterial.DIAMOND


class DiamondChestPlate(ItemChestPlate):
    number = 55
    material = EnumArmorMaterial.DIAMOND


class DiamondLeggings(ItemLeggings):
    number = 56
    material = EnumArmorMaterial.DIAMOND


class DiamondBoots(ItemBoots):
    number = 57
    material = EnumArmorMaterial.DIAMOND


class GoldenHelmet(ItemHelmet):
    number = 58
    material = EnumArmorMaterial.GOLD


class GoldenChestPlate(ItemChestPlate):
    number = 59
    material = EnumArmorMaterial.GOLD


class GoldenLeggings(ItemLeggings):
    number = 60
    material = EnumArmorMaterial.GOLD


class GoldenBoots(ItemBoots):
    number = 61
    material = EnumArmorMaterial.GOLD


class Flint(Item):
    number = 62


class RawPork(ItemFood):
    number = 63
    heal_amount = 3
    saturation_modifier = 0.3


class CookedPork(ItemFood):
    number = 64
    heal_amount = 8
    saturation_modifier = 0.8


class Painting(Item):
    number = 65


class GoldenApple(ItemFood):
    number = 66
    heal_amount = 4
    saturation_modifier = 1.2

    def __init__(self, **kwargs):
        super(GoldenApple, self).__init__(**kwargs)
        self.has_subtypes = True


class Sign(Item):
    number = 67
    stacksize = 16


class WoodenDoor(Item):
    number = 68


class ItemBucket(Item):
    stacksize = 1


class EmptyBucket(ItemBucket):
    number = 69
    stacksize = 16


class WaterBucket(ItemBucket):
    number = 70


class LavaBucket(ItemBucket):
    number = 71


class ItemMinecart(Item):
    pass


class EmptyMinecart(ItemMinecart):
    number = 72


class Saddle(Item):
    number = 73


class IronDoor(Item):
    number = 74


class Redstone(Item):
    number = 75


class SnowBall(Item):
    number = 76


class Boat(Item):
    number = 77


class Leather(Item):
    number = 78


class MilkBucket(ItemBucket):
    number = 79
    stacksize = 1


class Brick(Item):
    number = 80


class Clay(Item):
    number = 81


class SugarCanes(Item):
    number = 82


class Paper(Item):
    number = 83


class Book(Item):
    number = 84


class SlimeBall(Item):
    number = 85


class MinecartWithChest(ItemMinecart):
    number = 86


class MinecartWithFurnace(ItemMinecart):
    number = 87


class Egg(Item):
    number = 88
    stacksize = 16


class Compass(Item):
    number = 89


class FishingRod(Item):
    number = 90
    stacksize = 1
    max_damage = 64


class Clock(Item):
    number = 91


class GlowstoneDust(Item):
    number = 92


class RawFish(ItemFood):
    number = 93
    heal_amount = 2
    saturation_modifier = 0.3


class CookedFish(ItemFood):
    number = 94
    heal_amount = 5
    saturation_modifier = 0.6


class Dye(MultiItem):
    number = 95
    sub_names = ["Ink Sac", "Rose Red", "Cactus Green", "Cocoa Beans", "Lapis Lazuli", "Purple Dye", "Cyan Dye", "Light Gray Dye", "Gray Dye", "Pink Dye", "Lime Dye", "Dandelion Yellow", "Light Blue Dye", "Magenta Dye", "Orange Dye", "Bone Meal"]


class Bone(Item):
    number = 96


class Sugar(Item):
    number = 97


class Cake(Item):
    number = 98
    stacksize = 1


class Bed(Item):
    number = 99
    stacksize = 1


class RedstoneRepeater(Item):
    number = 100


class Coookie(ItemFood):
    number = 101
    heal_amount = 2
    saturation_modifier = 0.1


class Map(Item):
    number = 102


class Shears(Item):
    number = 103
    stacksize = 1
    max_damage = 238

    def can_harvest_block(self, block):
        return block.number == blocks.Cobweb.number or block.number == blocks.RedstoneWire.number or block.number == blocks.Tripwire.number

    def strength_vs_block(self, block):
        if block.number != blocks.Cobweb.number and block.number != blocks.Leaves.number:
            if block.number == blocks.Wool.number:
                return 5.0
            else:
                return super(Shears, self).strength_vs_block(block)
        else:
            return 15.0


class Melon(ItemFood):
    number = 104
    heal_amount = 2
    saturation_modifier = 0.3


class ItemSeeds(Item):
    pass


class PumpkinSeeds(ItemSeeds):
    number = 105


class MelonSeeds(ItemSeeds):
    number = 106


class RawBeef(ItemFood):
    number = 107
    heal_amount = 3
    saturation_modifier = 0.3


class Steak(ItemFood):
    number = 108
    heal_amount = 8
    saturation_modifier = 0.8


class RawChicken(ItemFood):
    number = 109
    heal_amount = 2
    saturation_modifier = 0.3


class CookedChicken(ItemFood):
    number = 110
    heal_amount = 6
    saturation_modifier = 0.6


class RottenFlesh(ItemFood):
    number = 111
    heal_amount = 4
    saturation_modifier = 0.1


class EnderPearl(Item):
    number = 112


class BlazeRod(Item):
    number = 113


class GhastTear(Item):
    number = 114


class GoldenNugget(Item):
    number = 115


class NetherWart(ItemSeeds):
    number = 116


class Potion(MultiItem):
    number = 117
    stacksize = 1
    sub_names = []

    def get_name(self, meta):
        return "%s(%s)" % (self.name, meta)


class GlassBottle(Item):
    number = 118


class SpiderEye(ItemFood):
    number = 119
    heal_amount = 2
    saturation_modifier = 0.8


class FermentedSpiderEye(Item):
    number = 120


class BlazePowder(Item):
    number = 121


class MagmaCream(Item):
    number = 122


class BrewingStand(Item):
    number = 123


class Cauldron(Item):
    number = 124


class EyeOfEnder(Item):
    number = 125


class GlisteringMelon(Item):
    number = 126


class SpawnEgg(MultiItem):
    number = 127
    sub_names = []

    def get_name(self, meta):
        return "%s(%s)" % (self.name, meta)


class BottleOEnchanting(Item):
    number = 128
    name = "Bottle o' Enchanting"


class FireCharge(Item):
    number = 129


class BookAndQuill(Item):
    number = 130
    stacksize = 1


class WrittenBook(Item):
    number = 131
    stacksize = 1


class Emerald(Item):
    number = 132


class ItemFrame(Item):
    number = 133


class FlowerPot(Item):
    number = 134


class Carrot(ItemFood):
    number = 135
    heal_amount = 4
    saturation_modifier = 0.6


class Potato(ItemFood):
    number = 136
    heal_amount = 1
    saturation_modifier = 0.3


class BakedPotato(ItemFood):
    number = 137
    heal_amount = 6
    saturation_modifier = 0.6


class PoisonousPotato(ItemFood):
    number = 138
    heal_amount = 2
    saturation_modifier = 0.3


class EmptyMap(Item):
    number = 139


class GoldenCarrot(ItemFood):
    number = 140
    heal_amount = 6
    saturation_modifier = 1.2


class Skull(MultiItem):
    number = 141
    sub_names = ["Skeleton Skull", "Wither Skull", "Zombie Skull", "Human Skull", "Creeper Skull"]


class CarrotOnAStick(Item):
    number = 142
    stacksize = 1
    max_damage = 25


class NetherStar(Item):
    number = 143


class PumpkinPie(ItemFood):
    number = 144
    heal_amount = 8
    saturation_modifier = 0.3


class FireworkRocket(Item):
    number = 145


class FireworkStar(Item):
    number = 146


class EnchantedBook(Item):
    number = 147
    stacksize = 1


class RedstoneComparator(Item):
    number = 148


class NetherBrick(Item):
    number = 149


class NetherQuartz(Item):
    number = 150


class MinecartWithTNT(Item):
    number = 151
    stacksize = 1
    name = "Minecart with TNT"


class MinecartWithHopper(Item):
    number = 152
    stacksize = 1


class ItemDisc(Item):
    stacksize = 1


class Disc13(ItemDisc):
    number = 2000


class DiscCat(ItemDisc):
    number = 2001


class DiscBlocks(ItemDisc):
    number = 2002


class DiscChirp(ItemDisc):
    number = 2003


class DiscFar(ItemDisc):
    number = 2004


class DiscMall(ItemDisc):
    number = 2005


class DiscMellohi(ItemDisc):
    number = 2006


class DiscStal(ItemDisc):
    number = 2007


class DiscStrad(ItemDisc):
    number = 2008


class DiscWard(ItemDisc):
    number = 2009


class Disc11(ItemDisc):
    number = 2010


class DiscWait(ItemDisc):
    number = 2011


#
# Specific block items
#
class ItemBlockMulti(ItemBlock):

    def __init__(self, has_common_type=True, block=None, **kwargs):
        super(ItemBlockMulti, self).__init__(block=block, **kwargs)
        self.has_subtypes = True
        self.has_common_type = self.block.has_common_type

    def get_types(self):
        for i, sname in enumerate(self.block.sub_names):
            if sname is not None:
                yield ItemStack(self.number, i)
        if self.has_common_type is True:
            yield ItemStack(self.number, common=True)

    def get_name(self, meta):
        if self.block.sub_names[meta]:
            if self.block.sub_name_override:
                return self.block.sub_names[meta].lower()
            else:
                return "%s %s" % (self.block.sub_names[meta].lower(), self.block.name)
        else:
            return self.block.name


#
# Non item classes - ItemStack, ItemDB
#
class ItemStack(object):
    item_list = item_list

    def __init__(self, item_id, meta=0, count=1, common=False, nbt=None):
        self.item = self.item_list[item_id]
        self.number = item_id
        self.meta = meta
        self.count = count
        self.common = common
        self.nbt = nbt

    @classmethod
    def from_slotdata(cls, slotdata):
        #log.msg(slotdata)
        if slotdata.id >= 0:
            return cls(slotdata.id, slotdata.damage, count=slotdata.count, nbt=slotdata.data)
        else:
            return None

    @property
    def name(self):
        return self.item.name if self.common else self.item.get_name(self.meta)

    def __eq__(self, istack):
        return self.is_same(istack) and istack.is_same(self)

    def __repr__(self):
        return "%s:%d:%d:%d%s" % (self.name, self.number, self.meta, self.count, ":C" if self.common else "")

    def is_same(self, istack):
        if istack is None:
            return False
        if self.common:
            return self.number == istack.number
        if self.item.has_subtypes:
            return self.number == istack.number and self.meta == istack.meta
        return self.number == istack.number

    def strength_vs_block(self, block):
        return self.item.strength_vs_block(block)

    def can_harvest_block(self, block):
        return self.item.can_harvest_block(block)

    @property
    def is_tool(self):
        return self.item.is_tool

    @property
    def is_damageable(self):
        return self.item.is_damageable


class ItemDB(object):
    item_list = item_list

    def __init__(self):
        self.item_count = 0
        self.item_names_map = {}
        self.min_block_mine_tool = {}

    def bind(self, name, istack):
        if name in self.item_names_map:
            raise Exception("%s already binded" % name)
        self.item_names_map[name] = istack
        #log.msg("%s %s %s" % (istack.number, istack.meta, istack.name))

    def register(self, item):
        self.item_count += 1
        if not self.slot_empty(item.number):
            raise Exception("slot %d is already full" % item.number)
        self.item_list[item.number] = item
        for istack in item.get_types():
            self.bind(istack.name, istack)

    def slot_empty(self, number):
        return self.item_list[number] is None

    def item_by_name(self, name):
        return self.item_names_map[name]

    def needs_tool_for(self, block_cls):
        """ dummy for now """
        return True

    def tool_for(self, block_cls):
        """ dummy for now """
        return self.item_names_map['iron pickaxe']

    def all_items(self):
        for it in self.item_names_map.itervalues():
            yield it


item_db = ItemDB()


def init_list():
    for name, obj in globals().items():
        if isinstance(obj, ItemMetaClass) and hasattr(obj, 'number'):
            item = obj()
            item_db.register(item)

    for block_name in ["wool", "wood", "wooden planks", "stone brick", "sandstone", "slab", "wooden slab", "saplings", "leaves", "grass", "cobblestone wall"]:
        block = blocks.block_map[block_name]
        item_db.register(ItemBlockMulti(block=block))

    for i in xrange(1, 256):
        if blocks.block_list[i] is None or blocks.block_list[i].inventory_avoid or not item_db.slot_empty(i):
            continue
        item = ItemBlock(block=blocks.block_list[i])
        item_db.register(item)
    log.msg("registered %d items" % item_db.item_count)


init_list()


if __name__ == '__main__':
    for itemstack in item_db.all_items():
        print itemstack, 'is damageable', itemstack.is_damageable, 'is tool', itemstack.is_tool
