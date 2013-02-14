
import items
import blocks
import logbot


log = logbot.getlogger("RECIPES")


recipe_map = {}
recipes_count = {"craft": 0, "smelt": 0, "mine": 0, "brew": 0, "mob kill": 0}


class RecipeMetaClass(type):
    def __new__(meta, name, bases, dct):
        cls = super(RecipeMetaClass, meta).__new__(meta, name, bases, dct)
        if hasattr(cls, 'name'):
            cls.resources = []
            cls.itemstack = items.item_db.item_by_name(cls.name)
            if issubclass(cls, MineBluePrint):
                cls.block = blocks.block_map[cls.block]
                recipes_count["mine"] += 1
            elif issubclass(cls, SmeltBluePrint):
                cls.smelt_item = items.item_db.item_by_name(cls.smelt_item)
                cls.resources = [cls.smelt_item]
                recipes_count["smelt"] += 1
            elif issubclass(cls, CraftBluePrint):
                recipes_count["craft"] += 1
                if cls.plan is not None:
                    cls.need_bench = len(cls.plan[0]) == 3
                    if not all(map(lambda s: len(s) == len(cls.plan[0]), cls.plan)):
                        raise Exception("Bad blueprint plan %s %s" % (cls.name, cls))
                    if len(cls.plan[0]) == 1:
                        raise Exception("Bad blueprint plan %s %s" % (cls.name, cls))
                    cls.plan = map(lambda mark: items.item_db.item_by_name(cls.parts[mark]) if mark in cls.parts else None, "".join(cls.plan))
                elif cls.parts is not None:
                    cls.need_bench = len(cls.parts) > 4
                    cls.plan = [items.item_db.item_by_name(name) for name in cls.parts]
                cls.resources = [istack for istack in cls.plan if istack is not None]
            cls.is_obtainable = cls.mine_recipe or cls.craft_recipe or cls.smelt_recipe or cls.brew_recipe or cls.mobkill_recipe
            if cls.name not in recipe_map:
                recipe_map[cls.name] = [cls]
            else:
                recipe_map[cls.name].append(cls)
        return cls

    def __repr__(cls):
        return cls.name


class BluePrint(object):
    __metaclass__ = RecipeMetaClass
    mine_recipe = False
    smelt_recipe = False
    craft_recipe = False
    brew_recipe = False
    mobkill_recipe = False


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
    count = 1


class Cobblestone_stone(MineBluePrint):
    name = "cobblestone"
    block = "stone"


class Cobblestone_cobblestone(MineBluePrint):
    name = "cobblestone"
    block = "cobblestone"


class Diamond(MineBluePrint):
    name = "diamond"
    block = "diamond ore"


class IronOre(MineBluePrint):
    name = "iron ore"
    block = "iron ore"


class GoldOre(MineBluePrint):
    name = "gold ore"
    block = "gold ore"


class Wood(MineBluePrint):
    name = "wood"
    block = "wood"


class SugarCanes(MineBluePrint):
    name = "sugar canes"
    block = "sugar cane"


class Cocoabeans(MineBluePrint):
    name = "cocoa beans"
    block = "cocoa pod"
    drop_everytime = False

    @classmethod
    def block_filter(cls, meta):
        return (meta & 0x8) != 0


class Netherwart(MineBluePrint):
    name = "nether wart"
    block = "nether wart"

    @classmethod
    def block_filter(cls, meta):
        return meta >= 3


class Stone(SmeltBluePrint):
    name = "stone"
    smelt_item = "cobblestone"


class GoldIngot(SmeltBluePrint):
    name = "gold ingot"
    smelt_item = "gold ore"


class IronIngot_s(SmeltBluePrint):
    name = "iron ingot"
    smelt_item = "iron ore"


class IronIngot_c(CraftBluePrint):
    name = "iron ingot"
    parts = ["block of iron"]
    count = 9


class Sticks(CraftBluePrint):
    name = "sticks"
    plan = ["X ", "X "]
    parts = {"X": "wooden planks"}
    count = 4


class BlockOfIron(CraftBluePrint):
    name = "block of iron"
    plan = ["XXX", "XXX", "XXX"]
    parts = {"X": "iron ingot"}


class Chest(CraftBluePrint):
    name = "chest"
    plan = ["###", "# #", "###"]
    parts = {"#": "wooden planks"}


class CraftingTable(CraftBluePrint):
    name = "crafting table"
    plan = ["XX", "XX"]
    parts = {"X": "wooden planks"}


class Furnace(CraftBluePrint):
    name = "furnace"
    plan = ["###", "# #", "###"]
    parts = {"#": "cobblestone"}


class WoodenPlanks(CraftBluePrint):
    name = "wooden planks"
    parts = ["wood"]
    count = 4


class Axe(CraftBluePrint):
    plan = ["XX ", "X# ", " # "]


class DiamondAxe(Axe):
    name = "diamond axe"
    parts = {"X": "diamond", "#": "sticks"}


class GoldenAxe(Axe):
    name = "golden axe"
    parts = {"X": "gold ingot", "#": "sticks"}


class IronAxe(Axe):
    name = "iron axe"
    parts = {"X": "iron ingot", "#": "sticks"}


class StoneAxe(Axe):
    name = "stone axe"
    parts = {"X": "cobblestone", "#": "sticks"}


class WoodenAxe(Axe):
    name = "wooden axe"
    parts = {"X": "wooden planks", "#": "sticks"}


class PickAxe(CraftBluePrint):
    plan = ["XXX", " # ", " # "]


class DiamondPickaxe(PickAxe):
    name = "diamond pickaxe"
    parts = {"X": "diamond", "#": "sticks"}


class GoldenPickaxe(PickAxe):
    name = "golden pickaxe"
    parts = {"X": "gold ingot", "#": "sticks"}


class IronPickaxe(PickAxe):
    name = "iron pickaxe"
    parts = {"X": "iron ingot", "#": "sticks"}


class StonePickaxe(PickAxe):
    name = "stone pickaxe"
    parts = {"X": "cobblestone", "#": "sticks"}


class WoodenPickaxe(PickAxe):
    name = "wooden pickaxe"
    parts = {"X": "wooden planks", "#": "sticks"}


class RecipesDB(object):
    def __init__(self):
        self.item_recipes_map = recipe_map
        self.recipes_count = recipes_count
        self.check_dependency()
        self.log_count()

    def log_count(self):
        log.msg("registered %d recipes" % len(self.item_recipes_map))
        for key, value in self.recipes_count.items():
            log.msg("know how to %s %d items" % (key, value))

    def check_dependency(self):
        for recipe in self.all_recipes:
            for istack in recipe.resources:
                if self.has_recipe(istack.name):
                    self.get_recipes_by_name(istack.name)
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
