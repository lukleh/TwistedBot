

import blocks


class Item(object):
    pass


class NonStackable(Item):
    stackable = 1


class Stackable(Item):
    stackable = 64


class IronShovel(NonStackable):
    number = 256
    name = "Iron Shovel"


class IronPickAxe(NonStackable):
    number = 257
    name = "Iron Pickaxe"


class IronAxe(NonStackable):
    number = 258
    name = "Iron Axe"


class FlintAndSteel(NonStackable):
    number = 259
    name = "Flint and Steel"


class RedApple(Stackable):
    number = 260
    name = "Red Apple"


class Bow(NonStackable):
    number = 261
    name = "Bow"


class Arrow(Stackable):
    number = 262
    name = "Arrow"


class Coal(Stackable):
    number = 263
    name = "Coal"


class Diamond(Stackable):
    number = 264
    name = "Diamond"


class IronIngot(Stackable):
    number = 265
    name = "Iron Ingot"


class GoldIngot(Stackable):
    number = 266
    name = "Gold Ingot"


class GoldIngot(Stackable):
    number = 266
    name = "Gold Ingot"


class IronSword(NonStackable):
    number = 267
    name = "Iron Sword"


class WoodenSword(NonStackable):
    number = 268
    name = "Wooden Sword"


class WoodenShovel(NonStackable):
    number = 269
    name = "Wooden Showel"


class WoodenPickaxe(NonStackable):
    number = 270
    name = "Wooden Pickaxe"


class WoodenAxe(NonStackable):
    number = 271
    name = "Wooden Axe"


class StoneSword(NonStackable):
    number = 272
    name = "Stone Sword"


class StoneShovel(NonStackable):
    number = 273
    name = "Stone Shovel"


class StonePickaxe(NonStackable):
    number = 274
    name = "Stone Pickaxe"


class StoneAxe(NonStackable):
    number = 275
    name = "Stone Axe"


class DiamiondSword(NonStackable):
    number = 276
    name = "Diamond Sword"


class String(Stackable):
    number = 287
    name = "String"


class Sign(NonStackable):
    number = 323
    name = "Sign"


class WoodenDoor(NonStackable):
    number = 324
    name = "Wooden Door"


class IronDoor(NonStackable):
    number = 330
    name = "Iron Door"


class RedstoneDust(Stackable):
    number = 331
    name = "Redstone Dust"


class SugarCane(Stackable):
    number = 338
    name = "Sugar Cane"


class Cake(NonStackable):
    number = 354
    name = "Cake"


class Bed(NonStackable):
    number = 355
    name = "Bed"


class RedstoneRepeater(Stackable):
    number = 356
    name = "Redstone Repeater"


class NetherWart(Stackable):
    number = 372
    name = "Nether Wart"


class BrewingStand(Stackable):
    number = 379
    name = "Brewing Stand"


item_map = blocks.block_map[:]


def prepare():
    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    for _, cl in clsmembers:
        try:
            item_map[cl.number] = cl
        except:
            pass

prepare()
