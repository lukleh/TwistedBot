
from collections import defaultdict

import items
import blocks
import logbot


log = logbot.getlogger("RECIPES")


recipe_map = {}
recipes_count = defaultdict(int)


class RecipeMetaClass(type):
    def __new__(meta, name, bases, dct):
        cls = super(RecipeMetaClass, meta).__new__(meta, name, bases, dct)
        if hasattr(cls, 'name'):
            cls.resources = []
            cls.itemstack = items.item_db.item_by_name(cls.name, count=cls.count)
            #if cls.itemstack.common:
            #    print 'recipes check', cls
            if issubclass(cls, MineBluePrint):
                cls.type = 'mine'
                cls.block = blocks.block_map[cls.block]
            elif issubclass(cls, SmeltBluePrint):
                cls.type = 'smelt'
                cls.smelt_item = items.item_db.item_by_name(cls.smelt_item)
                cls.resources = [cls.smelt_item]
            elif issubclass(cls, CraftBluePrint):
                cls.type = 'craft'
                if cls.plan is not None:
                    cls.need_bench = len(cls.plan[0]) == 3
                    if not all(map(lambda s: len(s) == len(cls.plan[0]), cls.plan)):
                        raise Exception("Bad blueprint plan %s %s" % (cls.name, cls))
                    if len(cls.plan[0]) == 1:
                        raise Exception("Bad blueprint plan %s %s" % (cls.name, cls))
                    cls.plan = map(lambda mark: items.item_db.item_by_name(cls.parts[mark]) if mark != " " else None, "".join(cls.plan))
                elif cls.parts is not None:
                    cls.need_bench = len(cls.parts) > 4
                    cls.plan = [items.item_db.item_by_name(name) for name in cls.parts]
                else:
                    raise Exception("Bad blueprint no plan or parts %s %s" % (cls.name, cls))
                for istack in cls.plan:
                    if istack is None:
                        continue
                    for rstack in cls.resources:
                        if rstack.is_same(istack):
                            rstack.inc_count(1)
                            break
                    else:
                        cls.resources.append(istack)
            elif issubclass(cls, MobkillBluePrint):
                cls.type = 'mob kill'
            elif issubclass(cls, BrewBluePrint):
                cls.type = 'brew'
            elif issubclass(cls, CustomBluePrint):
                cls.type = 'custom'
            else:
                raise Exception('Unknow recipe type %s' % str(cls))
            recipes_count[cls.type] += 1
            cls.is_obtainable = cls.mine_recipe or cls.craft_recipe or cls.smelt_recipe or cls.brew_recipe or cls.mobkill_recipe
            if cls.name not in recipe_map:
                recipe_map[cls.name] = [cls]
            else:
                recipe_map[cls.name].append(cls)
        return cls

    def __repr__(cls):
        return "%s %s" % (cls.type, cls.name)


class BluePrint(object):
    __metaclass__ = RecipeMetaClass
    mine_recipe = False
    smelt_recipe = False
    craft_recipe = False
    brew_recipe = False
    mobkill_recipe = False
    count = 1


class MineBluePrint(BluePrint):
    mine_recipe = True
    block = None
    block_filter = None
    drop_everytime = True


class SmeltBluePrint(BluePrint):
    smelt_recipe = True
    smelt_item = None


class CraftBluePrint(BluePrint):
    craft_recipe = True
    need_bench = False
    plan = None
    parts = None

    @classmethod
    def crafted_item(cls, recources):
        return cls.itemstack


class MobkillBluePrint(BluePrint):
    mobkill_recipe = True
    mob = None


class BrewBluePrint(BluePrint):
    brew_recipe = True
    ingredient = None
    base_potion = None


class CustomBluePrint(BluePrint):
    pass


class Stone(SmeltBluePrint):
    name = "stone"
    smelt_item = "cobblestone"


class Dirt_grassblock(MineBluePrint):
    name = "dirt"
    block = "grass block"


class Dirt_dirt(MineBluePrint):
    name = "dirt"
    block = "dirt"


class Cobblestone_cobblestone(MineBluePrint):
    name = "cobblestone"
    block = "cobblestone"


class Cobblestone_stone(MineBluePrint):
    name = "cobblestone"
    block = "stone"


class WoodenPlanks(CraftBluePrint):
    name = "wooden planks"
    parts = ["wood"]
    count = 4

    @classmethod
    def crafted_item(cls, recources):
        """ wooden planks depend on the wood type """
        wood = recources[0]
        return cls.itemstack.copy(meta=wood.meta, common=False)


class OakWoodenPlanks(CraftBluePrint):
    name = "oak wooden planks"
    parts = ["oak wood"]
    count = 4


class SpruceWoodenPlanks(CraftBluePrint):
    name = "spruce wooden planks"
    parts = ["spruce wood"]
    count = 4


class BirchWoodenPlanks(CraftBluePrint):
    name = "birch wooden planks"
    parts = ["birch wood"]
    count = 4


class JungleWoodenPlanks(CraftBluePrint):
    name = "jungle wooden planks"
    parts = ["jungle wood"]
    count = 4


class Saplings(MineBluePrint):
    name = "saplings"
    block = "leaves"
    drop_everytime = False


class Sand(MineBluePrint):
    name = "sand"
    block = "sand"


class Gravel(MineBluePrint):
    name = "gravel"
    block = "gravel"


class GoldOre(MineBluePrint):
    name = "gold ore"
    block = "gold ore"


class IronOre(MineBluePrint):
    name = "iron ore"
    block = "iron ore"


class Wood(MineBluePrint):
    name = "wood"
    block = "wood"


class OakWood(MineBluePrint):
    name = "oak wood"
    block = "wood"

    @classmethod
    def block_filter(cls, meta):
        return (meta & 0x2) == 0


class SpruceWood(MineBluePrint):
    name = "spruce wood"
    block = "wood"

    @classmethod
    def block_filter(cls, meta):
        return (meta & 0x2) == 1


class BirchWood(MineBluePrint):
    name = "birch wood"
    block = "wood"

    @classmethod
    def block_filter(cls, meta):
        return (meta & 0x2) == 2


class JungleWood(MineBluePrint):
    name = "jungle wood"
    block = "wood"

    @classmethod
    def block_filter(cls, meta):
        return (meta & 0x2) == 3


class Glass(SmeltBluePrint):
    name = "glass"
    smelt_item = "sand"


class LapisLazuliBlock(CraftBluePrint):
    name = "lapis lazuli block"
    plan = ["XXX", "XXX", "XXX"]
    parts = {"X": "lapis lazuli"}


class Dispenser(CraftBluePrint):
    name = "dispenser"
    plan = ["XXX", "X#X", "XRX"]
    parts = {"X": "lapis lazuli", "#": "bow", "R": "redstone"}


class Sandstone(CraftBluePrint):
    name = "sandstone"
    plan = ["XX", "XX"]
    parts = {"X": "sand"}


class NoteBlock(CraftBluePrint):
    name = "note block"
    plan = ["XXX", "XRX", "XXX"]
    parts = {"X": "wooden planks", "R": "redstone"}


class Poweredrail(CraftBluePrint):
    name = "powered rail"
    plan = ["G G", "GSG", "GRG"]
    parts = {"G": "gold ingot", "S": "sticks", "R": "redstone"}


class Detectorrail(CraftBluePrint):
    name = "detector rail"
    plan = ["I I", "ISI", "IRI"]
    parts = {"I": "iron ingot", "S": "stone pressure plate", "R": "redstone"}


class Stickypiston(CraftBluePrint):
    name = "sticky piston"
    plan = ["S ", "P "]
    parts = {"S": "slimeball", "P": "piston"}


class Piston(CraftBluePrint):
    name = "piston"
    plan = ["WWW", "CIC", "CRC"]
    parts = {"I": "iron ingot", "C": "cobblestone", "R": "redstone", "W": "wooden planks"}


class Wool_white(CraftBluePrint):
    name = "white wool"
    plan = ["SS", "SS"]
    parts = {"S": "string"}


class Wool_light_gray(CraftBluePrint):
    name = "light gray wool"
    parts = ["white wool", "light gray dye"]


class Wool_gray(CraftBluePrint):
    name = "gray wool"
    parts = ["white wool", "gray dye"]


class Wool_black(CraftBluePrint):
    name = "black wool"
    parts = ["white wool", "ink sac"]


class Wool_red(CraftBluePrint):
    name = "red wool"
    parts = ["white wool", "rose red"]


class Wool_orange(CraftBluePrint):
    name = "orange wool"
    parts = ["white wool", "orange dye"]


class Wool_yellow(CraftBluePrint):
    name = "yellow wool"
    parts = ["white wool", "dandelion yellow"]


class Wool_lime(CraftBluePrint):
    name = "lime wool"
    parts = ["white wool", "lime dye"]


class Wool_green(CraftBluePrint):
    name = "green wool"
    parts = ["white wool", "cactus green"]


class Wool_cyan(CraftBluePrint):
    name = "cyan wool"
    parts = ["white wool", "cyan dye"]


class Wool_light_blue(CraftBluePrint):
    name = "light blue wool"
    parts = ["white wool", "light blue dye"]


class Wool_blue(CraftBluePrint):
    name = "blue wool"
    parts = ["white wool", "lapis lazuli"]


class Wool_purple(CraftBluePrint):
    name = "purple wool"
    parts = ["white wool", "purple dye"]


class Wool_magenta(CraftBluePrint):
    name = "magenta wool"
    parts = ["white wool", "magenta dye"]


class Wool_pink(CraftBluePrint):
    name = "pink wool"
    parts = ["white wool", "pink dye"]


class Wool_brown(CraftBluePrint):
    name = "brown wool"
    parts = ["white wool", "cocoa beans"]


class Dandelion(MineBluePrint):
    name = "dandelion"
    block = "dandelion"


class Rose(MineBluePrint):
    name = "rose"
    block = "rose"


class Brownmushroom(MineBluePrint):
    name = "brown mushroom"
    block = "brown mushroom"


class Redmushroom(MineBluePrint):
    name = "red mushroom"
    block = "red mushroom"


class Blockofgold(CraftBluePrint):
    name = "block of gold"
    plan = ["GGG", "GGG", "GGG"]
    parts = {"G": "gold ingot"}    


class BlockOfIron(CraftBluePrint):
    name = "block of iron"
    plan = ["XXX", "XXX", "XXX"]
    parts = {"X": "iron ingot"}


class SlabBluePrint(CraftBluePrint):
    plan = ["   ", "   ", "XXX"]
    count = 6


class Stoneslab(SlabBluePrint):
    name = "stone slab"
    parts = {"X": "stone"}


class Sandstoneslab(SlabBluePrint):
    name = "sandstone slab"
    parts = {"X": "sandstone"}


class Cobblestoneslab(SlabBluePrint):
    name = "cobblestone slab"
    parts = {"X": "cobblestone"}


class Brickslab(SlabBluePrint):
    name = "brick slab"
    parts = {"X": "bricks"}


class Stonebrickslab(SlabBluePrint):
    name = "stone brick slab"
    parts = {"X": "stone bricks"}


class Netherbrickslab(SlabBluePrint):
    name = "nether brick slab"
    parts = {"X": "nether brick"}


class Quartzslab(SlabBluePrint):
    name = "quartz slab"
    parts = {"X": "block of quartz"}


class Bricks(CraftBluePrint):
    name = "bricks"
    plan = ["XX", "XX"]
    parts = {"X": "brick"}


class TNT(CraftBluePrint):
    name = "tnt"
    plan = ["GSG", "SGS", "GSG"]
    parts = {"G": "gunpowder", "S": "sand"}


class Bookshelf(CraftBluePrint):
    name = "bookshelf"
    plan = ["WWW", "BBB", "WWW"]
    parts = {"W": "wooden planks", "B": "book"}


class Mossstone(MineBluePrint):
    name = "moss stone"
    block = "moss stone"


class Obsidian(MineBluePrint):
    name = "obsidian"
    block = "obsidian"


class Torch(CraftBluePrint):
    name = "torch"
    plan = ["C ", "S "]
    parts = {"C": "coal", "S": "sticks"}


class Torch_char(CraftBluePrint):
    name = "torch"
    plan = ["C ", "S "]
    parts = {"C": "charcoal", "S": "sticks"}


class StairsBluePrint(CraftBluePrint):
    plan = ["  S", " SS", "SSS"]
    count = 4


class Oakwoodstairs(StairsBluePrint):
    name = "oak wood stairs"
    parts = {"S": "oak wooden planks"}


class Chest(CraftBluePrint):
    name = "chest"
    plan = ["###", "# #", "###"]
    parts = {"#": "wooden planks"}


class Blockofdiamond(CraftBluePrint):
    name = "diamond"
    plan = ["###", "###", "###"]
    parts = {"#": "diamond"}


class CraftingTable(CraftBluePrint):
    name = "crafting table"
    plan = ["XX", "XX"]
    parts = {"X": "wooden planks"}


class Furnace(CraftBluePrint):
    name = "furnace"
    plan = ["###", "# #", "###"]
    parts = {"#": "cobblestone"}


class Ladders(CraftBluePrint):
    name = "ladders"
    plan = ["# #", "###", "# #"]
    parts = {"#": "sticks"}
    count = 3


class Rails(CraftBluePrint):
    name = "rails"
    plan = ["# #", "#X#", "# #"]
    parts = {"#": "iron ingot", "X": "sticks"}
    count = 16


class Cobblestonestairs(StairsBluePrint):
    name = "cobblestone stairs"
    parts = {"S": "cobblestone"}


class Lever(CraftBluePrint):
    name = "lever"
    plan = [" S", " C"]
    parts = {"S": "sticks", "C": "cobblestone"}


class Stonepressureplate(CraftBluePrint):
    name = "stone pressure plate"
    plan = ["  ", "SS"]
    parts = {"S": "stone"}


class Woodenpressureplate(CraftBluePrint):
    name = "wooden pressure plate"
    plan = ["  ", "WW"]
    parts = {"W": "wooden planks"}


class Redstonetorch(CraftBluePrint):
    name = "redstone torch"
    plan = ["R ", "S "]
    parts = {"R": "redstone", "S": "sticks"}


class Stonebutton(CraftBluePrint):
    name = "stone button"
    parts = ["stone"]


class Snowblock(CraftBluePrint):
    name = "snow block"
    plan = ["BB", "BB"]
    parts = {"B": "snowball"}


class Cactus(MineBluePrint):
    name = "cactus"
    block = "cactus"


class Clayblock(CraftBluePrint):
    name = "clay block"
    plan = ["BB", "BB"]
    parts = {"B": "clay"}


class Jukebox(CraftBluePrint):
    name = "jukebox"
    plan = ["WWW", "WDW", "WWW"]
    parts = {"W": "cobblestone", "D": "diamond"}


class Fence(CraftBluePrint):
    name = "fence"
    plan = ["   ", "WWW", "WWW"]
    parts = {"W": "sticks"}
    count = 2


class Pumpkin(MineBluePrint):
    name = "pumpkin"
    block = "pumpkin"


class Netherrack(MineBluePrint):
    name = "netherrack"
    block = "netherrack"


class Soulsand(MineBluePrint):
    name = "soul sand"
    block = "soul sand"


class GlowstoneBlock(CraftBluePrint):
    name = "glowstone block"
    plan = ["BB", "BB"]
    parts = {"B": "glowstone dust"}


class JackOLantern(CraftBluePrint):
    name = "jack 'o' lantern"
    plan = ["B ", "T "]
    parts = {"B": "pumpkin", "T": "torch"}


class Stonebricks(CraftBluePrint):
    name = "stone bricks"
    plan = ["SS", "SS"]
    parts = {"S": "stone"}
    count = 4


#TODO mushrooms from huge mushrooms


class Ironbars(CraftBluePrint):
    name = "iron bars"
    plan = ["   ", "III", "III"]
    parts = {"I": "iron ingot"}


class Glasspane(CraftBluePrint):
    name = "glass pane"
    plan = ["   ", "GGG", "GGG"]
    parts = {"G": "glass"}


class Melonblock(CraftBluePrint):
    name = "melon block"
    plan = ["MMM", "MMM", "MMM"]
    parts = {"M": "melon slice"}


class Fencegate(CraftBluePrint):
    name = "fence gate"
    plan = ["   ", "SWS", "SWS"]
    parts = {"S": "sticks", "W": "wooden planks"}


class Brickstairs(StairsBluePrint):
    name = "brick stairs"
    parts = {"S": "bricks"}


class Stonebrickstairs(StairsBluePrint):
    name = "stone brick stairs"
    parts = {"S": "stone bricks"}


class Dirt_mycelium(MineBluePrint):
    name = "dirt"
    block = "mycelium"


class Lilypad(MineBluePrint):
    name = "lily pad"
    block = "lily pad"


class Netherbricks(CraftBluePrint):
    name = "nether bricks"
    plan = ["BB", "BB"]
    parts = {"B": "nether brick"}


class Netherbrickfence(CraftBluePrint):
    name = "nether brick fence"
    plan = ["   ", "BBB", "BBB"]
    parts = {"B": "nether bricks"}


class Netherbrickstairs(StairsBluePrint):
    name = "nether brick stairs"
    parts = {"S": "nether bricks"}


class Enchantmenttable(CraftBluePrint):
    name = "enchantment table"
    plan = [" B ", "DOD", "OOO"]
    parts = {"B": "book", "D": "diamond", "O": "obsidian"}


class Endstone(MineBluePrint):
    name = "end stone"
    block = "end stone"


class Redstonelamp(CraftBluePrint):
    name = "redstone lamp"
    plan = [" R ", "RGR", " R "]
    parts = {"R": "redstone", "G": "glowstone dust"}


class OakWoodenslab(SlabBluePrint):
    name = "oak wooden slab"
    parts = {"X": "oak wooden planks"}


class SpruceWoodenslab(SlabBluePrint):
    name = "spruce wooden slab"
    parts = {"X": "spruce wooden planks"}


class BirchWoodenslab(SlabBluePrint):
    name = "birch wooden slab"
    parts = {"X": "birch wooden planks"}


class JungleWoodenslab(SlabBluePrint):
    name = "jungle wooden slab"
    parts = {"X": "jungle wooden planks"}


class Cocoabeans(MineBluePrint):
    name = "cocoa beans"
    block = "cocoa pod"
    drop_everytime = False

    @classmethod
    def block_filter(cls, meta):
        return (meta & 0x8) != 0


class Sandstonestairs(StairsBluePrint):
    name = "sandstone stairs"
    parts = {"S": "sandstone"}


class Enderchest(CraftBluePrint):
    name = "ender chest"
    plan = ["OOO", "OEO", "OOO"]
    parts = {"E": "eye of ender", "O": "obsidian"}


class Tripwirehook(CraftBluePrint):
    name = "tripwire hook"
    plan = [" I ", " S ", " W "]
    parts = {"I": "iron ingot", "S": "sticks", "W": "wooden planks"}
    count = 2


class Blockofemerald(CraftBluePrint):
    name = "block of emerald"
    plan = ["EEE", "EEE", "EEE"]
    parts = {"E": "emerald"}


class Sprucewoodstairs(StairsBluePrint):
    name = "spruce wood stairs"
    parts = {"S": "spruce wooden planks"}


class Birchwoodstairs(StairsBluePrint):
    name = "birch wood stairs"
    parts = {"S": "birch wooden planks"}


class Junglewoodstairs(StairsBluePrint):
    name = "jungle wood stairs"
    parts = {"S": "jungle wooden planks"}


class Beacon(CraftBluePrint):
    name = "beacon"
    plan = ["GGG", "GSG", "OOO"]
    parts = {"G": "glass", "S": "nether star", "O": "obsidian"}


class Cobblestonewall(CraftBluePrint):
    name = "cobblestone wall"
    plan = ["   ", "CCC", "CCC"]
    parts = {"C": "cobblestone"}
    count = 6


class MossyCobblestonewall(CraftBluePrint):
    name = "mossy cobblestone wall"
    plan = ["   ", "CCC", "CCC"]
    parts = {"C": "moss stone"}
    count = 6


class Woodenbutton(CraftBluePrint):
    name = "wooden button"
    parts = ["wooden planks"]


class Anvil(CraftBluePrint):
    name = "anvil"
    plan = ["BBB", " I ", "III"]
    parts = {"B": "block of iron", "I": "iron ingot"}


class TrapepdChest(CraftBluePrint):
    name = "trapped chest"
    plan = ["  ", "TC"]
    parts = {"T": "tripwire hook", "C": "chest"}


class WeightedPressurePlateLight(CraftBluePrint):
    name = "weighted pressure plate light"
    plan = ["  ", "II"]
    parts = {"I": "gold ingot"}


class WeightedPressurePlateHeavy(CraftBluePrint):
    name = "weighted pressure plate heavy"
    plan = ["  ", "II"]
    parts = {"I": "iron ingot"}


class DaylightSensor(CraftBluePrint):
    name = "daylight sensor"
    plan = ["GGG", "NNN", "WWW"]
    parts = {"G": "glass", "N": "nether quartz", "W": "wooden planks"}


class BlockofRedstone(CraftBluePrint):
    name = "block of redstone"
    plan = ["RRR", "RRR", "RRR"]
    parts = {"R": "redstone"}


class NetherQuartzOre(MineBluePrint):
    name = "nether quartz ore"
    block = "nether quartz ore"


class Hopper(CraftBluePrint):
    name = "hopper"
    plan = ["I I", "ICI", " I "]
    parts = {"I": "iron ingot", "C": "chest"}


class BlockofQuartz(CraftBluePrint):
    name = "block of quartz"
    plan = ["QQ", "QQ"]
    parts = {"Q": "nether quartz"}


class Quartzstairs(StairsBluePrint):
    name = "quartz stairs"
    parts = {"S": "block of quartz"}


class ActivatorRail(CraftBluePrint):
    name = "activator rail"
    plan = ["ISI", "IRI", "ISI"]
    parts = {"I": "iron ingot", "R": "redstone torch", "S": "sticks"}


class Dropper(CraftBluePrint):
    name = "dropper"
    plan = ["SSS", "S S", "SRS"]
    parts = {"R": "redstone", "S": "cobblestone"}


class Shovel(CraftBluePrint):
    plan = [" X ", " # ", " # "]


class PickAxe(CraftBluePrint):
    plan = ["XXX", " # ", " # "]


class Axe(CraftBluePrint):
    plan = ["XX ", "X# ", " # "]


class IronShovel(Shovel):
    name = "iron shovel"
    parts = {"X": "iron ingot", "#": "sticks"}


class IronPickaxe(PickAxe):
    name = "iron pickaxe"
    parts = {"X": "iron ingot", "#": "sticks"}


class IronAxe(Axe):
    name = "iron axe"
    parts = {"X": "iron ingot", "#": "sticks"}


class FlintAndSteel(CraftBluePrint):
    name = "flint and steel"
    plan = ["I ", " F"]
    parts = {"I": "iron ingot", "F": "flint"}


class Apple(MineBluePrint):
    name = "red apple"
    block = "leaves"
    drop_everytime = False

    @classmethod
    def block_filter(cls, meta):
        return (meta & 0x2) == 0


class Bow(CraftBluePrint):
    name = "bow"
    plan = [" ST", "S T", " ST"]
    parts = {"S": "sticks", "T": "string"}


class Arrow(CraftBluePrint):
    name = "arrow"
    plan = [" F ", " S ", " E "]
    parts = {"S": "sticks", "F": "flint", "E": "feather"}


class Coal(MineBluePrint):
    name = "coal"
    block = "coal ore"


class Charcoal(SmeltBluePrint):
    name = "charcoal"
    smelt_item = "wood"


class Diamond(MineBluePrint):
    name = "diamond"
    block = "diamond ore"


class IronIngot_smelt(SmeltBluePrint):
    name = "iron ingot"
    smelt_item = "iron ore"


class IronIngot_craft(CraftBluePrint):
    name = "iron ingot"
    parts = ["block of iron"]
    count = 9


class GoldIngot_smelt(SmeltBluePrint):
    name = "gold ingot"
    smelt_item = "gold ore"


class GoldIngot_craft(CraftBluePrint):
    name = "gold ingot"
    parts = ["block of gold"]
    count = 9


class GoldIngot_craft2(CraftBluePrint):
    name = "gold ingot"
    plan = ["NNN", "NNN", "NNN"]
    parts = {"N": "gold nugget"}


class Sword(CraftBluePrint):
    plan = [" X ", " X ", " # "]


class IronSword(Sword):
    name = "iron sword"
    parts = {"X": "iron ingot", "#": "sticks"}


class WoodenSword(Sword):
    name = "wooden sword"
    parts = {"X": "wooden planks", "#": "sticks"}


class WoodenShovel(Shovel):
    name = "wooden shovel"
    parts = {"X": "wooden planks", "#": "sticks"}


class WoodenPickaxe(PickAxe):
    name = "wooden pickaxe"
    parts = {"X": "wooden planks", "#": "sticks"}


class WoodenAxe(Axe):
    name = "wooden axe"
    parts = {"X": "wooden planks", "#": "sticks"}


class StoneSword(Sword):
    name = "stone sword"
    parts = {"X": "cobblestone", "#": "sticks"}


class StoneShovel(Shovel):
    name = "stone shovel"
    parts = {"X": "cobblestone", "#": "sticks"}


class StonePickaxe(PickAxe):
    name = "stone pickaxe"
    parts = {"X": "cobblestone", "#": "sticks"}


class StoneAxe(Axe):
    name = "stone axe"
    parts = {"X": "cobblestone", "#": "sticks"}


class DiamondSword(Sword):
    name = "diamond sword"
    parts = {"X": "diamond", "#": "sticks"}


class DiamondShovel(Shovel):
    name = "diamond shovel"
    parts = {"X": "diamond", "#": "sticks"}


class DiamondPickaxe(PickAxe):
    name = "diamond pickaxe"
    parts = {"X": "diamond", "#": "sticks"}


class DiamondAxe(Axe):
    name = "diamond axe"
    parts = {"X": "diamond", "#": "sticks"}


class Sticks(CraftBluePrint):
    name = "sticks"
    plan = ["X ", "X "]
    parts = {"X": "wooden planks"}
    count = 4


class Bowl(CraftBluePrint):
    name = "bowl"
    plan = ["   ", "X X", " X "]
    parts = {"X": "wooden planks"}
    count = 4


class MushroomStew(CraftBluePrint):
    name = "mushroom stew"
    parts = ["red mushroom", "brown mushroom", "bowl"]


class GoldenSword(Sword):
    name = "golden sword"
    parts = {"X": "gold ingot", "#": "sticks"}


class GoldenShovel(Shovel):
    name = "golden shovel"
    parts = {"X": "gold ingot", "#": "sticks"}


class GoldenPickaxe(PickAxe):
    name = "golden pickaxe"
    parts = {"X": "gold ingot", "#": "sticks"}


class GoldenAxe(Axe):
    name = "golden axe"
    parts = {"X": "gold ingot", "#": "sticks"}


class String_mine(MineBluePrint):
    name = "string"
    block = "cobweb"


class String_mobkill(MobkillBluePrint):
    name = "string"
    mob = ["spider", "cave spider"]


class Feather(MobkillBluePrint):
    name = "feather"
    mob = "chicken"


class Gunpowder(MobkillBluePrint):
    name = "gunpowder"
    mob = ["creeper", "ghast", "witch"]


class Hoe(CraftBluePrint):
    plan = ["XX ", " # ", " # "]


class WoodenHoe(Hoe):
    name = "wooden hoe"
    parts = {"X": "wooden planks", "#": "sticks"}


class StoneHoe(Hoe):
    name = "stone hoe"
    parts = {"X": "cobblestone", "#": "sticks"}


class IronHoe(Hoe):
    name = "iron hoe"
    parts = {"X": "iron ingot", "#": "sticks"}


class DiamondHoe(Hoe):
    name = "diamond hoe"
    parts = {"X": "diamond", "#": "sticks"}


class GoldHoe(Hoe):
    name = "iron hoe"
    parts = {"X": "gold ingot", "#": "sticks"}


class Seeds(MineBluePrint):
    name = "seeds"
    block = "grass"

    @classmethod
    def block_filter(cls, meta):
        return meta == 0x1


class Crops(MineBluePrint):
    @classmethod
    def block_filter(cls, meta):
        return meta == 0x7


class Seeds_wheat(Crops):
    name = "seeds"
    block = "wheat crops"


class Wheat(Crops):
    name = "wheat"
    block = "wheat crops"


class Bread(CraftBluePrint):
    name = "bread"
    plan = ["   ", "   ", "XXX"]
    parts = {"X": "wheat"}


class Helmet(CraftBluePrint):
    plan = ["   ", "XXX", "X X"]


class Chestplate(CraftBluePrint):
    plan = ["X X", "XXX", "XXX"]


class Leggings(CraftBluePrint):
    plan = ["XXX", "X X", "X X"]


class Boots(CraftBluePrint):
    plan = ["   ", "X X", "X X"]


class LeatherHelmet(Helmet):
    name = "leather helmet"
    parts = {"X": "leather"}


class LeatherChestplate(Helmet):
    name = "leather chestplate"
    parts = {"X": "leather"}


class LeatherLeggings(Helmet):
    name = "leather leggings"
    parts = {"X": "leather"}


class LeatherBoots(Helmet):
    name = "leather boots"
    parts = {"X": "leather"}


class IronHelmet(Helmet):
    name = "iron helmet"
    parts = {"X": "iron ingot"}


class IronChestplate(Helmet):
    name = "iron chestplate"
    parts = {"X": "iron ingot"}


class IronLeggings(Helmet):
    name = "iron leggings"
    parts = {"X": "iron ingot"}


class IronBoots(Helmet):
    name = "iron boots"
    parts = {"X": "iron ingot"}


class DiamondHelmet(Helmet):
    name = "diamond helmet"
    parts = {"X": "diamond"}


class DiamondChestplate(Helmet):
    name = "diamond chestplate"
    parts = {"X": "diamond"}


class DiamondLeggings(Helmet):
    name = "diamond leggings"
    parts = {"X": "diamond"}


class DiamondBoots(Helmet):
    name = "diamond boots"
    parts = {"X": "diamond"}


class GoldenHelmet(Helmet):
    name = "golden helmet"
    parts = {"X": "gold ingot"}


class GoldenChestplate(Helmet):
    name = "golden chestplate"
    parts = {"X": "gold ingot"}


class GoldenLeggings(Helmet):
    name = "golden leggings"
    parts = {"X": "gold ingot"}


class GoldenBoots(Helmet):
    name = "golden boots"
    parts = {"X": "gold ingot"}


class Flint(MineBluePrint):
    name = "flint"
    block = "gravel"
    drop_everytime = False


class RawPorkchop(MobkillBluePrint):
    name = "raw porkchop"
    mob = "pig"


class CookedPorkchop(SmeltBluePrint):
    name = "cooked porkchop"
    smelt_item = "raw porkchop"


class Painting(CraftBluePrint):
    name = "painting"
    plan = ["XXX", "XWX", "XXX"]
    parts = {"X": "sticks", "W": "wool"}


class GoldenApple(CraftBluePrint):
    name = "golden apple"
    plan = ["XXX", "XAX", "XXX"]
    parts = {"X": "gold nugget", "A": "red apple"}


class EnchantedGoldenApple(CraftBluePrint):
    name = "enchanted golden apple"
    plan = ["XXX", "XAX", "XXX"]
    parts = {"X": "block of gold", "A": "red apple"}


class Sign(CraftBluePrint):
    name = "sign"
    plan = ["XXX", "XXX", " S "]
    parts = {"X": "wooden planks", "S": "sticks"}
    count = 3


class WoodenDoor(CraftBluePrint):
    name = "wooden door"
    plan = ["XX ", "XX ", "XX "]
    parts = {"X": "wooden planks"}


class Bucket(CraftBluePrint):
    name = "bucket"
    plan = ["   ", "X X", " X "]
    parts = {"X": "iron ingot"}


class WaterBucket(MineBluePrint):
    name = "water bucket"
    block = "still water"


class LavaBucket(MineBluePrint):
    name = "lava bucket"
    block = "still lava"


class Minecart(CraftBluePrint):
    name = "minecart"
    plan = ["   ", "X X", "XXX"]
    parts = {"X": "iron ingot"}


class IronDoor(CraftBluePrint):
    name = "iron door"
    plan = ["XX ", "XX ", "XX "]
    parts = {"X": "iron ingot"}


class Redstone(MineBluePrint):
    name = "redstone"
    block = "redstone ore"


class Redstone_g(MineBluePrint):
    name = "redstone"
    block = "glowing redstone ore"


class Snowball(MineBluePrint):
    name = "snowball"
    block = "snow"


class Snowball_block(MineBluePrint):
    name = "snowball"
    block = "snow block"


class Boat(CraftBluePrint):
    name = "boat"
    plan = ["   ", "X X", "XXX"]
    parts = {"X": "wooden planks"}


class Leather(MobkillBluePrint):
    name = "leather"
    mob = "cow"


class Milkbucket(CustomBluePrint):
    name = "milk bucket"
    mob = "cow"


class Brick(SmeltBluePrint):
    name = "brick"
    smelt_item = "clay"


class Clay(MineBluePrint):
    name = "clay"
    block = "clay block"


class SugarCanes(MineBluePrint):
    name = "sugar canes"
    block = "sugar cane"


class Paper(CraftBluePrint):
    name = "paper"
    plan = ["   ", "   ", "XXX"]
    parts = {"X": "sugar canes"}
    count = 3


class Book(CraftBluePrint):
    name = "book"
    parts = ["paper", "leather"]


class Slimeball(MobkillBluePrint):
    name = "slimeball"
    mob = "slime"


class MinecartwithChest(CraftBluePrint):
    name = "minecart with chest"
    plan = [" C", " M"]
    parts = {"C": "chest", "M": "minecart"}


class MinecartwithFurnace(CraftBluePrint):
    name = "minecart with furnace"
    plan = [" F", " M"]
    parts = {"F": "furnace", "M": "minecart"}


class Egg(CustomBluePrint):
    name = "egg"
    mob = "chicken"


class Compass(CraftBluePrint):
    name = "compass"
    plan = [" I ", "IRI", " I "]
    parts = {"I": "iron ingot", "R": "redstone"}


class FishingRod(CraftBluePrint):
    name = "fishing rod"
    plan = ["  S", " ST", "S T"]
    parts = {"S": "sticks", "T": "string"}


class Clock(CraftBluePrint):
    name = "clock"
    plan = [" G ", "GRG", " G "]
    parts = {"G": "gold ingot", "R": "redstone"}


class Glowstone(MineBluePrint):
    name = "glowstone dust"
    block = "glowstone block"


class RawFish(CustomBluePrint):
    name = "raw fish"
    mob = "fish"


class CookedFish(SmeltBluePrint):
    name = "cooked fish"
    smelt_item = "raw fish"


class Inksac(MobkillBluePrint):
    name = "ink sac"
    mob = "squid"


class RoseRed_craft(CraftBluePrint):
    name = "rose red"
    parts = ["rose"]
    count = 2


class RoseRed_smelt(SmeltBluePrint):
    name = "rose red"
    smelt_item = "red mushroom"


class CactusGreen(SmeltBluePrint):
    name = "cactus green"
    smelt_item = "cactus"


class LapisLazuli_mine(MineBluePrint):
    name = "lapis lazuli"
    block = "lapis lazuli ore"


class LapisLazuli_craft(CraftBluePrint):
    name = "lapis lazuli"
    parts = ["lapis lazuli block"]
    count = 9


class PurpleDye(CraftBluePrint):
    name = "purple dye"
    parts = ["lapis lazuli", "rose red"]
    count = 2


class CyanDye(CraftBluePrint):
    name = "cyan dye"
    parts = ["lapis lazuli", "cactus green"]
    count = 2


class LightGrayDye(CraftBluePrint):
    name = "light gray dye"
    parts = ["ink sac", "bone meal", "bone meal"]
    count = 3


class LightGrayDye2(CraftBluePrint):
    name = "light gray dye"
    parts = ["gray dye", "bone meal"]
    count = 2


class GrayDye(CraftBluePrint):
    name = "gray dye"
    parts = ["ink sac", "bone meal"]
    count = 2


class PinkDye(CraftBluePrint):
    name = "pink dye"
    parts = ["rose red", "bone meal"]
    count = 2


class LimeDye(CraftBluePrint):
    name = "lime dye"
    parts = ["cactus green", "bone meal"]
    count = 2


class DandelionYellow(CraftBluePrint):
    name = "dandelion yellow"
    parts = ["dandelion"]
    count = 2


class LightBlueDye(CraftBluePrint):
    name = "light blue dye"
    parts = ["lapis lazuli", "bone meal"]
    count = 2


class MagentaDye2(CraftBluePrint):
    name = "magenta dye"
    parts = ["purple dye", "pink dye"]
    count = 2


class MagentaDye4(CraftBluePrint):
    name = "magenta dye"
    parts = ["rose red", "rose red", "bone meal", "lapis lazuli"]
    count = 4


class MagentaDye3(CraftBluePrint):
    name = "magenta dye"
    parts = ["rose red", "pink dye", "lapis lazuli"]
    count = 3


class OrangeDye(CraftBluePrint):
    name = "orange dye"
    parts = ["rose red", "dandelion yellow"]
    count = 2


class BoneMeal(CraftBluePrint):
    name = "bone meal"
    parts = ["bone"]
    count = 3


class Bone(MobkillBluePrint):
    name = "bone"
    mob = ["skeleton", "wither skeleton"]


class Sugar(CraftBluePrint):
    name = "sugar"
    parts = ["sugar canes"]


class Cake(CraftBluePrint):
    name = "cake"
    plan = ["MMM", "SES", "WWW"]
    parts = {"M": "milk bucket", "S": "sugar", "E": "egg", "W": "wheat"}


class Bed(CraftBluePrint):
    name = "bed"
    plan = ["   ", "WWW", "PPP"]
    parts = {"P": "wooden planks", "W": "wool"}


class RedstoneRepeater(CraftBluePrint):
    name = "redstone repeater"
    plan = ["   ", "TRT", "SSS"]
    parts = {"R": "redstone", "T": "redstone torch", "S": "stone"}


class Cookie(CraftBluePrint):
    name = "cookie"
    plan = ["   ", "WCW", "   "]
    parts = {"C": "cocoa beans", "W": "wheat"}
    count = 3


#class Map(CraftBluePrint):
#    name = "map"
#    plan = ["PPP", "PMP", "PPP"]
#    parts = {"M": "empty map", "P": "paper"}


class Shears(CraftBluePrint):
    name = "shears"
    plan = [" I", "I "]
    parts = {"I": "iron ingot"}


class Melonslice(MineBluePrint):
    name = "melon slice"
    block = "melon block"


class PumpkinSeeds(CraftBluePrint):
    name = "pumpkin seeds"
    parts = ["pumpkin"]


class MelonSeeds(CraftBluePrint):
    name = "melon seeds"
    parts = ["melon slice"]


class RawBeef(MobkillBluePrint):
    name = "raw beef"
    mob = "cow"


class Steak(SmeltBluePrint):
    name = "steak"
    smelt_item = "raw beef"


class RawChicken(MobkillBluePrint):
    name = "raw chicken"
    mob = "chicken"


class CookedChicken(SmeltBluePrint):
    name = "cooked chicken"
    smelt_item = "raw chicken"


class RottenFlesh(MobkillBluePrint):
    name = "rotten flesh"
    mob = ["zombie", "zombie pigman"]


class EnderPearl(MobkillBluePrint):
    name = "ender pearl"
    mob = "enderman"


class BlazeRod(MobkillBluePrint):
    name = "blaze rod"
    mob = "blaze"


class GhastTear(MobkillBluePrint):
    name = "ghast tear"
    mob = "ghast"


class GoldNugget(MobkillBluePrint):
    name = "gold nugget"
    mob = "zombie pigman"


class GoldNugget_craft(CraftBluePrint):
    name = "gold nugget"
    parts = ["gold ingot"]
    count = 9


class Netherwart(MineBluePrint):
    name = "nether wart"
    block = "nether wart"

    @classmethod
    def block_filter(cls, meta):
        return meta >= 3


#class Potion(BrewB)
# not now


class GlassBottle(CraftBluePrint):
    name = "glass bottle"
    plan = ["   ", "G G", " G "]
    parts = {"G": "glass"}
    count = 3


class SpiderEye(MobkillBluePrint):
    name = "spider eye"
    mob = ["spider", "cave spider"]


class FermentedSpiderEye(CraftBluePrint):
    name = "fermented spider eye"
    parts = ["brown mushroom", "sugar", "spider eye"]


class BlazePowder(CraftBluePrint):
    name = "blaze powder"
    parts = ["blaze rod"]
    count = 2


class MagmaCream(CraftBluePrint):
    name = "magma cream"
    parts = ["blaze powder", "slimeball"]


class Brewingstand(CraftBluePrint):
    name = "brewing stand"
    plan = ["   ", " B ", "CCC"]
    parts = {"B": "blaze rod", "C": "cobblestone"}


class Cauldron(CraftBluePrint):
    name = "cauldron"
    plan = ["I I", "I I", "III"]
    parts = {"I": "iron ingot"}


class EyeofEnder(CraftBluePrint):
    name = "eye of ender"
    parts = ["blaze powder", "ender pearl"]


class GlisteringMelon(CraftBluePrint):
    name = "glistering melon"
    parts = ["melon slice", "gold nugget"]


class BottleOEnchanting(CustomBluePrint):
    name = "bottle o' enchanting"
    trade = "priest"


class FireCharge(CraftBluePrint):
    name = "fire charge"
    parts = ["blaze powder", "coal", "gunpowder"]


class FireCharge_charcoal(CraftBluePrint):
    name = "fire charge"
    plan = ["BC", " G"]
    parts = {"B": "blaze powder", "C": "charcoal", "G": "gunpowder"}
    count = 3


class BookandQuill(CraftBluePrint):
    name = "book and quill"
    parts = ["book", "ink sac", "feather"]


class Emerald_mine(MineBluePrint):
    name = "emerald"
    block = "emerald ore"


class Emerald_craft(CraftBluePrint):
    name = "emerald"
    parts = ["block of emerald"]
    count = 9


class ItemFrame(CraftBluePrint):
    name = "item frame"
    plan = ["SSS", "SLS", "SSS"]
    parts = {"S": "sticks", "L": "leather"}


class Flowerpot(CraftBluePrint):
    name = "flower pot"
    plan = ["   ", "C C", " C "]
    parts = {"C": "brick"}


class Carrot(Crops):
    name = "carrot"
    block = "carrots"


class Potato(Crops):
    name = "potato"
    block = "potatoes"


class BakedPotato(SmeltBluePrint):
    name = "baked potato"
    smelt_item = "potato"


class EmptyMap(CraftBluePrint):
    name = "empty map"
    plan = ["PPP", "PCP", "PPP"]
    parts = {"C": "compass", "P": "paper"}


class GoldenCarrot(CraftBluePrint):
    name = "golden carrot"
    plan = ["GGG", "GCG", "GGG"]
    parts = {"C": "carrot", "G": "gold nugget"}


class CarrotonaStick(CraftBluePrint):
    name = "carrot on a stick"
    plan = ["F ", " C"]
    parts = {"C": "carrot", "F": "fishing rod"}


class NetherStar(MobkillBluePrint):
    name = "nether star"
    mob = "wither"


class PumpkinPie(CraftBluePrint):
    name = "pumpkin pie"
    parts = ["pumpkin", "sugar", "egg"]


class EnchantedBook(CustomBluePrint):
    name = "enchanted book"
    trade = "enchant"


class RedstoneComparator(CraftBluePrint):
    name = "redstone comparator"
    plan = [" R ", "RNR", "SSS"]
    parts = {"R": "redstone torch", "N": "nether quartz", "S": "stone"}


class NetherBrick(SmeltBluePrint):
    name = "nether brick"
    smelt_item = "netherrack"


class NetherQuartz(MineBluePrint):
    name = "nether quartz"
    block = "nether quartz ore"


class MinecartwithTNT(CraftBluePrint):
    name = "minecart with tnt"
    plan = [" T", " M"]
    parts = {"T": "tnt", "M": "minecart"}


class MinecartwithHopper(CraftBluePrint):
    name = "minecart with hopper"
    plan = [" H", " M"]
    parts = {"H": "hopper", "M": "minecart"}


class Discs(CustomBluePrint):
    pass



class RecipesDB(object):
    def __init__(self):
        self.item_recipes_map = recipe_map
        self.recipes_count = recipes_count
        self.check_dependency()
        self.log_count()

    def log_count(self):
        log.msg("registered %d recipes" % len(self.item_recipes_map))
        for key, value in self.recipes_count.items():
            log.msg("%d %s recipes" % (value, key))

    def check_dependency(self):
        for recipe in self.all_recipes:
            for istack in recipe.resources:
                if self.has_recipe(istack.name):
                    self.get_recipes_by_name(istack.name)
                elif istack.common:
                    for ist in istack.item.get_types():
                        if ist.common:
                            continue
                        if self.has_recipe(ist.name):
                            break
                    else:
                        raise Exception("Incomplete recipe dependency for '%s' common item '%s'" % (recipe.name, istack.name))
                else:
                    raise Exception("Incomplete recipe dependency for '%s' missing '%s'" % (recipe.name, istack.name))
            if recipe.mine_recipe and items.item_db.needs_tool_for(recipe.block):
                tool = items.item_db.tool_for(recipe.block)
                if not self.has_recipe(tool.name):
                    raise Exception("Incomplete recipe mining tool '%s' for block '%s'" % (tool.name, recipe.block.name))

    @property
    def all_recipes(self):
        for recipes in self.item_recipes_map.itervalues():
            for recipe in recipes:
                yield recipe

    def has_recipe(self, name):
        return name in self.item_recipes_map

    def get_recipes_by_name(self, name):
        try:
            return self.item_recipes_map[name]
        except KeyError:
            return []

    def recipes_for_item(self, istack):
        return self.get_recipes_by_name(istack.name)


recipes_db = RecipesDB()

if __name__ == "__main__":
    for recipe in recipes_db.all_recipes:
        #pass
        log.msg("recipe %s" % recipe)
