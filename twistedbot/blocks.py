
import inspect
import sys

import config
from aabb import AABB


	
class Block(object):
	speed_on = config.SPEED_WALK
	speed_in = config.SPEED_WALK
	avoid = False
	
	def __init__(self, x=None, y=None, z=None, meta=0):
		self.x = x
		self.y = y
		self.z = z
		self.meta = meta
		
	def __str__(self):
		return "%d %d %d %s" % (self.x, self.y, self.z, self.name)

	def __hash__(self):
		return hash(self.x, self.y, self.z)
		
	def __getitem__(self, i):
		if i == 0:
			return self.x
		elif i == 1:
			return self.y
		elif i == 2:
			return self.z
		
	@property
	def is_solid(self):
		return isinstance(self, BlockSolid)
		
	@property
	def is_fluid(self):
		return isinstance(self, BlockFluid)
	
	@property
	def is_free(self):
		return not self.is_solid and not self.is_fluid
		
	@property
	def is_sign(self):
		return isinstance(self, SignPost) or isinstance(self, WallSign)
		
	@property
	def is_wood(self):
		return isinstance(self, Wood)

	@property
	def bounding_boxes(self):
		return self.get_shapes(self.meta)

	@property
	def grid_bounding_boxes(self):
		out = []
		shift = (self.x, self.y, self.z)
		for b in self.bounding_boxes:
			out.append(b + shift)
		return out
		
	@property	
	def grid_height(self):
		return self.y + self.height
		
	@property
	def coords(self):
		return (self.x, self.y, self.z)

	def same_type(self, t):
		return t == self.number
	
	
class BlockFluid(Block):
	@classmethod
	def get_shapes(cls, meta):
		return []
	
	
class BlockWater(BlockFluid):
	avoid = True
	speed_in = Block.speed_in * 0.5
	
	
class BlockLava(BlockFluid):
	avoid = True
	speed_in = BlockWater.speed_in * 0.3067915690866511
	
	
class BlockSolid(Block):
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
	
	@classmethod
	def get_shapes(cls, meta):
		return [cls.shapes]
	
	@property
	def height(self):
		return 1.0
		
		
class BlockStairs(BlockSolid):
	shape_lower = AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
	shape_higher = [AABB(0.5, 0.5, 0.0, 1.0, 1.0, 1.0),
					AABB(0.0, 0.5, 0.0, 0.5, 1.0, 1.0),
					AABB(0.0, 0.5, 0.5, 1.0, 1.0, 1.0),
					AABB(0.0, 0.5, 0.0, 1.0, 1.0, 0.5)]
	
	@classmethod
	def get_shapes(cls, meta):
		return [cls.shape_lower, cls.shape_higher[meta]]
		
		
class BlockDoor(BlockSolid):
	shapes = [AABB(0.0, 0.0, 0.0, 0.1875, 1.0, 1.0),
					 AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.1875),
					 AABB(0.8125, 0.0, 0.0, 1.0, 1.0, 1.0),
					 AABB(0.0, 0.0, 0.8125,	1.0, 1.0, 1.0)]
	
	@classmethod
	def top_part(cls, meta):
		return meta >> 3 == 1
		
	@classmethod
	def get_shapes(cls, meta_top, meta_bottom):
		hinge_right = (meta_top & 1) == 0
		closed = (meta_bottom & 4) == 0
		facing = meta_bottom & 3
		if closed:
			return [cls.shapes[facing]]
		else:
			if hinge_right:
				return [cls.shapes[facing-1 if facing-1 > 0 else 3]]
			else:
				return [cls.shapes[facing+1 if facing+1 < 4 else 0]]
	
	
class BlockNonSolid(Block):
	@classmethod
	def get_shapes(cls, meta):
		return []
	

class Air(BlockNonSolid):
	number = 0
	name = "Air"
	
	
class Stone(BlockSolid):
	number = 1
	name = "Stone"
	
	
class Grass(BlockSolid):
	number = 2
	name = "Grass Block"

	
class Dirt(BlockSolid):
	number = 3
	name = "Dirt"

	
class Cobblestone(BlockSolid):
	number = 4
	name = "Cobblestone"
	

class WoodenPlanks(BlockSolid):
	number = 5
	name = "Wooden Planks"
	

class Saplings(BlockNonSolid):
	number = 6
	name = "Saplings"
	
	
class Bedrock(BlockSolid):
	number = 7
	name = "Bedrock"
	
	
class FlowingWater(BlockWater):
	number = 8
	name = "Flowing Water"
	

class StillWater(BlockWater):
	number = 9
	name = "Still Water"
	

class FlowingLava(BlockLava):
	number = 10
	name = "Flowing Lava"
	
	
class StillLava(BlockLava):
	number = 11
	name = "Still Lava"
	
	
class Sand(BlockSolid):
	number = 12
	name = "Sand"

	
class Gravel(BlockSolid):
	number = 13
	name = "Gravel"
	

class GoldOre(BlockSolid):
	number = 14
	name = "Gold Ore"

	
class IronOre(BlockSolid):
	number = 15
	name = "Iron Ore"
	

class CoalOre(BlockSolid):
	number = 16
	name = "Coal Ore"
	
	
class Wood(BlockSolid):
	number = 17
	name = "Wood"


class Leaves(BlockSolid):
	number = 18
	name = "Leaves"
	

class Sponge(BlockSolid):
	number = 19
	name = "Sponge"

	
class Glass(BlockSolid):
	number = 20
	name = "Glass"
	
	
class LapisLazuliOre(BlockSolid):
	number = 21
	name = "Lapis Lazuli Ore"


class LapisLazuliBlock(BlockSolid):
	number = 22
	name = "Lapis Lazuli Block"
	
	
class Dispenser(BlockSolid):
	number = 23
	name = "Dispenser"	
	
	
class Sandstone(BlockSolid):
	number = 24
	name = "Sandstone"	


class NoteBlock(BlockSolid):
	number = 25
	name = "Note Block"

	
class Bed(BlockSolid):
	number = 26
	name = "Bed"
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 0.5625, 1.0)
	
	@property
	def height(self):
		return 0.5625


class PoweredRail(BlockNonSolid):
	number = 27
	name = "Powered Rail"		


class DetectorRail(BlockNonSolid):
	number = 28
	name = "Detector Rail"	
	

class StickyPiston(BlockSolid):
	number = 29
	name = "Sticky Piston"


class Cobweb(BlockNonSolid):
	number = 30
	name = "Cobweb"	
	speed_in = config.SPEED_COBWEB


class TallGrass(BlockNonSolid):
	number = 31
	name = "Tall Grass"	
	
	
class DeadBush(BlockNonSolid):
	number = 32
	name = "Dead Bush"		
	

class Piston(BlockSolid):
	number = 33
	name = "Piston"
	
	
class PistonExtension(BlockSolid):
	number = 34
	name = "Piston Extension"
	
	
class Wool(BlockSolid):
	number = 35
	name = "Wool"	
	

class PistonMoving(BlockSolid):
	number = 36
	name = "Piston Moving"
	
	
class Dandelion(BlockNonSolid):
	number = 37
	name = "Dandelion"	

	
class Rose(BlockNonSolid):
	number = 38
	name = "Rose"	
	
	
class BrownMushroom(BlockNonSolid):
	number = 39
	name = "Brown Mushroom"

	
class RedMushroom(BlockNonSolid):
	number = 40
	name = "Red Mushroom"
	

class BlockOfGold(BlockSolid):
	number = 41
	name = "Block of Gold"	
	

class BlockOfIron(BlockSolid):
	number = 42
	name = "Block of Iron"	

	
class DoubleSlab(BlockSolid):
	number = 43
	name = "Double Slab"		

	
class SingleSlab(BlockSolid):
	number = 44
	name = "Single Slab"
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
	
	@property
	def height(self):
		return 0.5

	
class Bricks(BlockSolid):
	number = 45
	name = "Bricks"

	
class TNT(BlockSolid):
	number = 46
	name = "TNT"	
	

class Bookshelf(BlockSolid):
	number = 47
	name = "Bookshelf"	
	
	
class MossStone(BlockSolid):
	number = 48
	name = "Moss Stone"
	

class Obsidian(BlockSolid):
	number = 49
	name = "Obsidian"
	

class Torch(BlockNonSolid):
	number = 50
	name = "Torch"
	
	
class Fire(BlockNonSolid):
	avoid = True
	number = 51
	name = "Fire"
	
	
class MonsterSpawner(BlockSolid):
	number = 52
	name = "Monster Spawner"


class WoodenStairs(BlockStairs):
	number = 53
	name = "Wooden Stairs"	

	
class Chest(BlockSolid):
	number = 54
	name = "Chest"

	
class RedstoneWire(BlockNonSolid):
	number = 55
	name = "Redstone Wire"	


class DiamondOre(BlockSolid):
	number = 56
	name = "Diamond Ore"
	
	
class BlockOfDiamond(BlockSolid):
	number = 57
	name = "Block of Diamond"

	
class CraftingTable(BlockSolid):
	number = 58
	name = "Crafting Table"
	

class WheatCrops(BlockNonSolid):
	number = 59
	name = "Wheat Crops"

	
class Farmland(BlockSolid):
	number = 60
	name = "Farmland"
	

class Furnace(BlockSolid):
	number = 61
	name = "Furnace"
	

class BurningFurnace(BlockSolid):
	number = 62
	name = "Burning Furnace"
	

class SignPost(BlockNonSolid):
	number = 63
	name = "Sign Post"

	
class WoodenDoor(BlockDoor):
	number = 64
	name = "Wooden Door"	
	

class Ladders(BlockSolid):
	number = 65
	name = "Ladders"
	speed_in = config.SPEED_CLIMB
	shapes = [AABB(0.0, 0.0, 0.875, 1.0, 1.0, 1.0),
			  AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.125),
			  AABB(0.875, 0.0, 0.0, 1.0, 1.0, 1.0),
			  AABB(0.0, 0.0, 0.0, 0.125, 1.0, 1.0)]
	
	@classmethod
	def get_shapes(cls, meta):
		if meta == 2: i = 0
		elif meta == 3: i = 1
		elif meta == 4: i = 2
		elif meta == 5: i = 3
		return [cls.shapes[i]]
		
	
class Rail(BlockNonSolid):
	number = 66
	name = "Rail"

	
class CobblestoneStairs(BlockStairs):
	number = 67
	name = "Cobblestone Stairs"

	
class WallSign(BlockNonSolid):
	number = 68
	name = "Wall Sign"

	
class Lever(BlockNonSolid):
	number = 69
	name = "Lever"

	
class StonePressurePlate(BlockNonSolid):
	number = 70
	name = "Stone Pressure Plate"

	
class IronDoor(BlockDoor):
	number = 71
	name = "Iron Door"

	
class WoodenPressurePlate(BlockNonSolid):
	number = 72
	name = "Wooden Pressure Plate"

	
class RedstoneOre(BlockSolid):
	number = 73
	name = "Redstone Ore"

	
class GlowingRedstoneOre(BlockSolid):
	number = 74
	name = "Glowing Redstone Ore"

	
class RedstoneTorchOffState(BlockNonSolid):
	number = 75
	name = "Redstone Torch off state"
	

class RedstoneTorchOnState(BlockNonSolid):
	number = 76
	name = "Redstone Torch on state"

	
class StoneButton(BlockNonSolid):
	number = 77
	name = "Stone Button"

	
class Snow(BlockNonSolid):
	number = 78
	name = "Snow"
	
	
class Ice(BlockSolid):
	number = 79
	name = "Ice"
	
	
class SnowBlock(BlockSolid):
	number = 80
	name = "Snow Block"
	
	
class Cactus(BlockSolid):
	avoid = True
	number = 81
	name = "Cactus"
	
	
class ClayBlock(BlockSolid):
	number = 82
	name = "Clay Block"
	
	
class SugarCane(BlockNonSolid):
	number = 83
	name = "Sugar Cane"
	
	
class Jukebox(BlockSolid):
	number = 84
	name = "Jukebox"
	

class BlockFence(BlockSolid):
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 1.5, 1.0)
	
	@property
	def height(self):
		return 1.5
		
		
class Fence(BlockFence):
	number = 85
	name = "Fence"

	
class Pumpkin(BlockSolid):
	number = 86
	name = "Pumpkin"
	
	
class Netherrack(BlockSolid):
	number = 87
	name = "Netherrack"
	
	
class SoulSand(BlockSolid):
	number = 88
	name = "Soul Sand"
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 7/8.0, 1.0)
	speed_in = Block.speed_in * 0.5
	
	@property
	def height(self):
		return 7/8.0
	
	
class GlowstoneBlock(BlockSolid):
	number = 89
	name = "Glowstone Block"
	
	
class NetherPortal(BlockNonSolid):
	number = 90
	name = "Nether Portal"
	
	
class JackOLantern(BlockSolid):
	number = 91
	name = "Jack 'o' Lantern"
	
	
class Cake(BlockSolid):
	number = 92
	name = "Cake"
	f = 0.0625
	shapes = None
	
	@property
	def height(self):
		return 0.5 - self.f
	
	@classmethod
	def get_shapes(cls, meta):
		f1 = (1 + meta * 2) / 16.0;
		return [AABB(f1, 0.0, cls.f, 1.0 - cls.f, 0.5 - cls.f, 1.0 - cls.f)]
	
class RedstoneRepeater(BlockSolid):
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 0.125, 1.0)
	
	@property
	def height(self):
		return 0.125
		
		
class RedstoneRepeaterOff(RedstoneRepeater):
	number = 93
	name = "Redstone Repeater ('off' state)"
	
	
class RedstoneRepeaterOn(RedstoneRepeater):
	number = 94
	name = "Redstone Repeater ('on' state)"
	
	
class LockedChest(BlockSolid):
	number = 95
	name = "Locked Chest"
	
	
class Trapdoor(BlockSolid):
	number = 96
	name = "Trapdoor"
	shape_closed = AABB(0.0, 0.0, 0.0, 1.0, 0.1875, 1.0)
	shapes = [AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.1875),
			  AABB(0.0, 0.0, 0.8125, 1.0, 1.0, 1.0),
			  AABB(0.0, 0.0, 0.0, 0.1875, 1.0, 1.0),
			  AABB(0.8125, 0.0,	0.0, 1.0, 1.0, 1.0)]
			
	@property
	def height(self):
		if (self.meta & 4) == 0:
			return 0.1875
		else:
			return 1.0
	
	@classmethod
	def get_shapes(cls, meta):
		if (meta & 4) == 0:
			return [cls.shape_closed]
		else:
			return [cls.shapes[meta & 3]]
	
	
class HiddenSilverfish(BlockSolid):
	number = 97
	name = "Hidden Silverfish"
	
	
class StoneBrick(BlockSolid):
	number = 98
	name = "Stone Brick"
	
	
class HugeBrownMushroom(BlockSolid):
	number = 99
	name = "Huge Brown Mushroom"
	
	
class HugeRedMushroom(BlockSolid):
	number = 100
	name = "Huge Red Mushroom"
	
	
class IronBars(BlockSolid):
	number = 101
	name = "Iron Bars"
	
	
class GlassPane(BlockSolid):
	number = 102
	name = "Glass Pane"
	
	
class MelonBlock(BlockSolid):
	number = 103
	name = "Melon Block"
	
	
class PumpkinStem(BlockNonSolid):
	number = 104
	name = "Pumpkin Stem"
	
	
class MelonStem(BlockNonSolid):
	number = 105
	name = "Melon Stem"

	
class Vines(BlockNonSolid):
	number = 106
	name = "Vines"
	speed_in = config.SPEED_CLIMB
	shapes = [AABB(0.0, 0.0, 0.9375, 1.0, 1.0, 1.0),
			  AABB(0.0, 0.0, 0.0, 0.0625, 1.0, 1.0),
			  AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.0625),
			  AABB(0.9375, 0.0, 0.0, 1.0, 1.0, 1.0)]
			
	@classmethod
	def get_shapes(cls, meta):
		shs = []
		if meta & 1:
			shs.append(cls.shapes[0])
		elif meta & 2:
			shs.append(cls.shapes[1])
		elif meta & 4:
			shs.append(cls.shapes[2])
		elif meta & 8:
			shs.append(cls.shapes[3])
	
	
class FenceGate(BlockSolid):
	number = 107
	name = "Fence Gate"
	
	@classmethod
	def get_shapes(cls, meta):
		if (meta & 4) == 0:
			return []
		else:
			return [cls.shapes]
			
	@property
	def is_solid(self):
		return (self.meta & 4) != 0
			
	@property
	def height(self):
		if (self.meta & 4) != 0:
			return 1.5
	
	
class BrickStairs(BlockStairs):
	number = 108
	name = "Brick Stairs"
	
	
class StoneBrickStairs(BlockStairs):
	number = 109
	name = "Stone Brick Stairs"
	
	
class Mycelium(BlockSolid):
	number = 110
	name = "Mycelium"

	
class LilyPad(BlockSolid):
	number = 111
	name = "Lily Pad"
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 0.015, 1.0)
	
	@property
	def height(self):
		return 0.15
	
	
class NetherBrick(BlockSolid):
	number = 112
	name = "Nether Brick"
	
	
class NetherBrickFence(BlockFence):
	number = 113
	name = "Nether Brick Fence"
	
	
class NetherBrickStairs(BlockStairs):
	number = 114
	name = "Nether Brick Stairs"
	
	
class NetherWart(BlockNonSolid):
	number = 115
	name = "Nether Wart"

	
class EnchantmentTable(BlockSolid):
	number = 116
	name = "Enchantment Table"
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 0.75, 1.0)
	
	@property
	def height(self):
		return 0.75
	
	
class BrewingStand(BlockSolid):
	number = 117
	name = "Brewing Stand"
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 0.875, 1.0)
	
	@property
	def height(self):
		return 0.875
	
	
class Cauldron(BlockSolid):
	number = 118
	name = "Cauldron"
	
	
class EndPortal(BlockNonSolid):
	number = 119
	name = "End Portal"
	

class EndPortalFrame(BlockSolid):
	number = 120
	name = "End Portal Frame"
	shapes = AABB(0.0, 0.0, 0.0, 1.0, 0.8125, 1.0)
	
	@property
	def height(self):
		return 0.8125
	
	
class EndStone(BlockSolid):
	number = 121
	name = "End Stone"

	
class DragonEgg(BlockSolid):
	number = 122
	name = "Dragon Egg"

	
class RedstoneLampInactive(BlockSolid):
	number = 123
	name = "Redstone Lamp (inactive)"
	
class RedstoneLampActive(BlockSolid):
	number = 124
	name = "Redstone Lamp (active)"
	
class WoodenDoubleSlab(BlockSolid):
	number = 125
	name = "Wooden Double Slab"

class WoodenSlab(BlockSolid):
	number = 126
	name = "Wooden Slab"
	shape_lower = AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
	shape_higher = AABB(0.0, 0.5, 0.0, 1.0, 1.0, 1.0)

	@property
	def height(self):
		if self.meta & 8 == 0:
			return 0.5
		else:
			return 1.0
		
	@classmethod
	def get_shapes(cls, meta):
		if meta & 8 == 0:
			return [cls.shape_lower]
		else:
			return [cls.shape_higher]

class CocoaPlant(BlockSolid):
    number = 127
    name = "Cocoa Plant"

class SandstoneStairs(BlockStairs):
	number = 128
	name = "Sandstone Stairs"
	
class EmeraldOre(BlockSolid):
	number = 129
	name = "Emerald Ore"

class EnderChest(BlockSolid):
	number = 130
	name = "Ender Chest"

class TripwireHook(BlockNonSolid):
	number = 131
	name = "Tripwire Hook"

class Tripwire(BlockNonSolid):
	number = 132
	name = "Tripwire"

class BlockOfEmerald(BlockSolid):
	number = 133
	name = "Block of Emerald"

class SpruceWoodStairs(BlockStairs):
    number = 134
    name = "Spruce Wood Stairs"

class BirchWoodStairs(BlockStairs):
    number = 135
    name = "Birch Wood Stairs"

class JungleWoodStairs(BlockStairs):
    number = 136
    name = "Jungle Wood Stairs"


block_map = [None for i in xrange(config.NUMBER_OF_BLOCKS)]
		
def prepare():
	clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
	for _, cl in clsmembers:
		try:
			block_map[cl.number] = cl
		except:
			pass

prepare()
