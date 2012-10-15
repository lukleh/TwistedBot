
import inspect
import sys

import config
import logbot
import tools
import materials
import fops
from aabb import AABB


log = logbot.getlogger("BLOCKS")

    
class Block(object):
    slipperiness = 0.6
    render_as_normal_block = True
    is_opaque_cube = True
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    
    def __init__(self, grid=None, x=None, y=None, z=None, meta=0):
        if grid.__class__.__name__ != "Grid":
            raise Exception("bad parameter to Block. Expecting World, received %s" % grid.__class__.__name__)
        self.grid = grid
        self.x = x
        self.y = y
        self.z = z
        self.meta = meta
        
    def __str__(self):
        return "%d %d %d %s %s" % (self.x, self.y, self.z, self.name, tools.meta2str(self.meta))

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
    def stand_type(self):
        return (-1,)

    @property
    def stand_number(self):
        return (self.number,)

    @property
    def collidable(self):
        return True

    @property
    def is_sign(self):
        return isinstance(self, SignPost) or isinstance(self, WallSign)

    @property
    def is_fence(self):
        return isinstance(self, BlockFence) or (isinstance(self, FenceGate) and not self.is_open)

    @property
    def is_ladder_vine(self):
        return isinstance(self, Ladders) or isinstance(self, Vines)
        #return False

    @property
    def coords(self):
        return (self.x, self.y, self.z)

    def adjacent_block(self, dx=None, dy=None, dz=None):
        x = dx if dx is not None else 0
        y = dy if dy is not None else 0
        z = dz if dz is not None else 0
        return self.grid.get_block(x, y, z)

    @property
    def grid_bounding_box(self):
        return self.bounding_box + self.coords

    def add_grid_bounding_boxes_to(self, out):
        out.append(self.grid_bounding_box)

    def sweep_collision(self, bb, vect, debug=False, max_height=False):
        col, d = bb.sweep_collision(self.grid_bounding_box, vect, debug=debug)
        return col, d, self.grid_bounding_box

    def maxedge_platform(self, x = 0, y = 0, z = 0):
        return self.grid_bounding_box.face(x, y, z)

    def collides_with(self, bb):
        return bb.collides(self.grid_bounding_box)

    def collides_on_axes(self, bb, x=False, y=False, z=False):
        return bb.collides_on_axes(self.grid_bounding_box, x, y, z)

    def intersection_on_axes(self, bb, x=False, y=False, z=False, debug=False):
        return bb.intersection_on_axes(self.grid_bounding_box, x, y, z, debug=debug)

    @property
    def effective_flow_decay(self):
        return -1

    def is_solid_block(self, blk, v):
        return blk.material.is_solid


class BlockNonSolid(Block):
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def stand_type(self):
        return (0,)

    @property
    def collidable(self):
        return False

    @property
    def grid_collision_boxes(self):
        pass

    def add_grid_bounding_boxes_to(self, out):
        pass

    def sweep_collision(self, bb, vect, debug=False, max_height=False):
        return False, None, None

    def maxedge_platform(self, x = 0, y = 0, z = 0):
        raise Exception("maxedge_platform cannot be called for non solid block")

    def collides_with(self, bb):
        return False

    def collides_on_axes(self, bb, x=False, y=False, z=False):
        return False

    def intersection_on_axes(self, bb, x=False, y=False, z=False, debug=False):
        return None


class BlockFluid(BlockNonSolid):
    pass
    

class BlockWater(BlockFluid):
    material = materials.water

    @property
    def stand_type(self):
        return (-2,)

    def is_solid_block(self, blk, v):
        if self.material == blk.material:
            return False
        else:
            if v == 1:
                return True
            else:
                if blk.material == materials.ice:
                    return False
                else:
                    return super(BlockWater, self).is_solid_block(blk, v)

    @property
    def effective_flow_decay(self):
        if self.meta >= 8:
            return 0
        else:
            return self.meta

    @property
    def flow_vector(self):
        v = [0, 0, 0]
        for i, j in tools.cross:
            blk = self.grid.get_block(self.x + i, self.y, self.z + j)
            fd = blk.effective_flow_decay
            if fd < -1:
                if not blk.material.blocks_movement:
                    blk_below = self.grid.get_block(self.x + i, self.y - 1, self.z + j)
                    if blk_below.effective_flow_decay >= 0:
                        va = fd - (self.effective_flow_decay - 8)
                        v = [v[0] + i * va, v[1], v[2] + j * va]
            elif fd >= 0:
                va = fd - self.effective_flow_decay
                v = [v[0] + i * va, v[1], v[2] + j * va]
        if self.meta >= 8:
            t = False
            if t or self.is_solid_block(self.grid.get_block(self.x, self.y, self.z - 1), 2):
                t = True
            if t or self.is_solid_block(self.grid.get_block(self.x, self.y, self.z + 1), 3):
                t = True
            if t or self.is_solid_block(self.grid.get_block(self.x - 1, self.y, self.z), 4):
                t = True
            if t or self.is_solid_block(self.grid.get_block(self.x + 1, self.y, self.z), 5):
                t = True
            if t or self.is_solid_block(self.grid.get_block(self.x, self.y + 1, self.z - 1), 2):
                t = True
            if t or self.is_solid_block(self.grid.get_block(self.x, self.y + 1, self.z + 1), 3):
                t = True
            if t or selfis_solid_block(self.grid.get_block(self.x - 1, self.y + 1, self.z), 4):
                t = True
            if t or self.is_solid_block(self.grid.get_block(self.x + 1, self.y + 1, self.z), 5):
                t = True
            if t:
                v = tools.normalize(v)
                v = [v[0], v[1] - 6.0, v[2]]
        return tools.normalize(v)

    def velocity_to_add_to(self, v):
        fv = self.flow_vector
        return (v[0] + fv[0], v[1] + fv[1], v[2] + fv[2])

    
    def height_percent(self):
        if self.meta >= 8:
            return 1 / 9.0
        else:
            return (self.meta + 1) / 9.0
    
    
class BlockLava(BlockFluid):
    material = materials.lava

    @property
    def stand_type(self):
        return (-3,)


class BlockFlower(BlockNonSolid):
    material = materials.plants


class BlockTorch(BlockNonSolid):
    pass


class BlockOre(Block):
    material = materials.rock


class RedstoneRepeater(Block):
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.125, 1.0)
    material = materials.circuits
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def stand_type(self):
        return (-4,)


class BlockMultiBox(Block):
    def add_grid_bounding_boxes_to(self, out):
        out.extend(self.grid_bounding_box)

    def sweep_collision(self, bb, vect, debug=False, max_height=False):
        boxes = self.grid_bounding_box
        if len(boxes) == 0:
            raise Exception("0 bounding boxes from block %s, cannot handle that" % self)
        elif len(boxes) == 1:
            col, rel_d = bb.sweep_collision(boxes[0], vect, debug=debug)
            return col, rel_d, boxes[0]
        else:
            col_rel_d = 1.1
            col_bb = None
            for box in boxes:
                col, rel_d = bb.sweep_collision(box, vect, debug=debug)
                if col and fops.eq(col_rel_d, rel_d):
                    if max_height:
                        if fops.lt(col_bb.max_y, bb.max_y):
                            col_bb = bb
                if col and fops.lt(rel_d, col_rel_d):
                    col_rel_d = rel_d
                    col_bb = bb
            return col_bb is not None, col_rel_d, col_bb

    def maxedge_platform(self, x = 0, y = 0, z = 0):
        faces = []
        for bb in self.grid_bounding_box:
            faces.append(bb.face(x, y, z))
        maxes = []
        for face in faces:
            if x:
                maxes.append(face.min_x)
            elif y:
                maxes.append(face.min_y)
            elif z:
                maxes.append(face.min_z)
        if min([x, y, z]) < 0:
            level = min(maxes)
        elif max([x, y, z]) > 0:
            level = max(maxes)
        max_faces = [faces[i] for i, v in enumerate(maxes) if v == level]
        if len(max_faces) == 1:
            return max_faces[0]
        else:
            max_face = None
            for i in xrange(0, len(max_faces) - 1):
                if max_face is None:
                    max_face = max_faces[i].union(max_faces[i+1])
                else:
                    max_face = max_face.union(max_faces[i+1])
            return max_face

    def collides_with(self, bb):
        for box in self.grid_bounding_box:
            if bb.collides(box):
                return True
        return False

    def collides_on_axes(self, bb, x=False, y=False, z=False):
        for box in self.grid_bounding_box:
            if bb.collides_on_axes(box, x, y, z):
                return True
        return False

    def intersection_on_axes(self, bb, x=False, y=False, z=False, debug=False):
        ubb = self.grid_bounding_box[0]
        for box in self.grid_bounding_box[1:]:
            ubb = ubb.union(box)
        return bb.intersection_on_axes(ubb, x, y, z, debug=debug)

    
class BlockStairs(BlockMultiBox):
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box_half = AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
    bounding_box_quarter = [AABB(0.5, 0.5, 0.0, 1.0, 1.0, 1.0),
                            AABB(0.0, 0.5, 0.0, 0.5, 1.0, 1.0),
                            AABB(0.0, 0.5, 0.5, 1.0, 1.0, 1.0),
                            AABB(0.0, 0.5, 0.0, 1.0, 1.0, 0.5)]
    bounding_box_upper_half = AABB(0.0, 0.5, 0.0, 1.0, 1.0, 1.0)
    bounding_box_upper_quarter =     [AABB(0.5, 0.0, 0.0, 1.0, 0.5, 1.0),
                                    AABB(0.0, 0.0, 0.0, 0.5, 0.5, 1.0),
                                    AABB(0.0, 0.0, 0.5, 1.0, 0.5, 1.0),
                                    AABB(0.0, 0.0, 0.0, 1.0, 0.5, 0.5)]

    @property
    def stand_type(self):
        return (-5, )

    @property
    def grid_bounding_box(self):
        if self.meta >= 4:
            return [self.bounding_box_upper_half + self.coords, self.bounding_box_upper_quarter[self.meta - 4] + self.coords]
        else:
            return [self.bounding_box_half + self.coords, self.bounding_box_quarter[self.meta] + self.coords]


class BlockDoor(Block):
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_boxes = [AABB(0.0, 0.0, 0.0, 0.1875, 1.0, 1.0),
                      AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.1875),
                      AABB(0.8125, 0.0, 0.0, 1.0, 1.0, 1.0),
                      AABB(0.0, 0.0, 0.8125, 1.0, 1.0, 1.0)] 
    top_part = None
    bottom_part = None

    @property
    def stand_type(self):
        return (-6, self.boxes_index)

    @property
    def stand_number(self):
        return (self.number, self.boxes_index)

    def assign_parts(self):
        if self.top_part is not None:
            return
        if self.is_top_half:
            self.top_part = self
            self.bottom_part = self.grid.get_block(self.x, self.y - 1, self.z)
        else:
            self.bottom_part = self
            self.top_part = self.grid.get_block(self.x, self.y + 1, self.z)
    
    @property
    def is_open(self):
        self.assign_parts()
        return (self.bottom_part.meta & 4) != 0
    
    @property
    def hinge_right(self):
        return (self.top_part.meta & 1) != 0

    @property
    def facing_index(self):
        return self.bottom_part.meta & 3

    @property
    def is_top_half(self):
        return (self.meta & 8) != 0

    @property
    def boxes_index(self):
        self.assign_parts()
        if self.is_open:
            if self.hinge_right:
                return self.facing_index - 1 if self.facing_index - 1 >= 0 else 3
            else:
                return self.facing_index + 1 if self.facing_index + 1 <  4 else 0
        else:
            return self.facing_index
        
    @property
    def grid_bounding_box(self):
        return self.bounding_boxes[self.boxes_index] + self.coords
    

class BlockPane(BlockMultiBox):
    render_as_normal_block = False
    is_opaque_cube = False

    def can_connect_to(self, x, y, z):
        blk = self.grid.get_block(x, y, z)
        return blk.is_opaque_cube or blk.number == self.number or blk.number == Glass.number

    def cross_connected(self):
        return (self.can_connect_to(self.x, self.y, self.z - 1), self.can_connect_to(self.x, self.y, self.z + 1), \
                self.can_connect_to(self.x - 1, self.y, self.z), self.can_connect_to(self.x + 1, self.y, self.z))

    @property
    def grid_bounding_box(self):
        out = []
        zl , zr, xl, xr = self.cross_connected()
        if (not xl or not xr) and (xl or xr or zl or zr):
            if xl and not xr:
                out.append(AABB(0.0, 0.0, 0.4375, 0.5, 1.0, 0.5625) + self.coords)
            elif not xl and xr:
                out.append(AABB(0.5, 0.0, 0.4375, 1.0, 1.0, 0.5625) + self.coords)
        else:
            out.append(AABB(0.0, 0.0, 0.4375, 1.0, 1.0, 0.5625) + self.coords)
        if (not zl or not zr) and (xl or xr or zl or zr):
            if zl and not zr:
                out.append(AABB(0.4375, 0.0, 0.0, 0.5625, 1.0, 0.5) + self.coords)
            elif not zl and zr:
                out.append(AABB(0.4375, 0.0, 0.5, 0.5625, 1.0, 1.0) + self.coords)
        else:
            out.append(AABB(0.4375, 0.0, 0.0, 0.5625, 1.0, 1.0) + self.coords)
         return out

    
class BlockFence(Block):
    is_opaque_cube = False
    render_as_normal_block = False

    @property
    def stand_type(self):
        return (-7, )

    @property
    def grid_bounding_box(self):
        if self.can_connect_to(self.x, self.y, self.z - 1):
            minz = 0.0
        else:
            minz = 0.375
        if self.can_connect_to(self.x, self.y, self.z + 1):
            maxz = 1.0
        else:
            maxz = 0.625
        if self.can_connect_to(self.x - 1, self.y, self.z):
            minx = 0.0
        else:
            minx = 0.375
        if self.can_connect_to(self.x + 1, self.y, self.z):
            maxx = 1.0
        else:
            maxx = 0.625
        return AABB(minx, 0, minz, maxx, 1.5, maxz) + self.coords

    def can_connect_to(self, x, y, z):
        blk = self.grid.get_block(x, y, z)
        if blk.number != self.number and blk.number != FenceGate.number:
            if blk.material.is_opaque and blk.render_as_normal_block:
                return blk.material != materials.pumpkin
            else:
                return False
        else:
            return True


class BlockPiston(Block):
    material = materials.piston
    render_as_normal_block = False
    is_opaque_cube = False


class BlockSingleSlab(Block):
    bounding_box_lower = AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
    bounding_box_higher = AABB(0.0, 0.5, 0.0, 1.0, 1.0, 1.0)
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def stand_type(self):
        return (-8, self.lower_part)

    @property
    def stand_number(self):
        return (self.number, self.lower_part)

    @property
    def lower_part(self):
        return self.meta & 8 == 0

    @property
    def grid_bounding_box(self):
        if self.lower_part:
            return self.bounding_box_lower + self.coords
        else:
            return self.bounding_box_higher + self.coords


class Air(BlockNonSolid):
    number = 0
    name = "Air"
    material = materials.air

    
class Stone(Block):
    number = 1
    name = "Stone"
    material = materials.rock
    

class Grass(Block):
    number = 2
    name = "Grass Block"
    material = materials.grass

    
class Dirt(Block):
    number = 3
    name = "Dirt"
    material = materials.ground

    
class Cobblestone(Block):
    number = 4
    name = "Cobblestone"
    material = materials.rock


class WoodenPlanks(Block):
    number = 5
    name = "Wooden Planks"
    material = materials.wood


class Saplings(BlockFlower):
    number = 6
    name = "Saplings"

    
class Bedrock(Block):
    number = 7
    name = "Bedrock"
    material = materials.rock

    
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
    
    
class Sand(Block):
    number = 12
    name = "Sand"
    material = materials.sand

    
class Gravel(Block):
    number = 13
    name = "Gravel"
    material = materials.sand


class GoldOre(BlockOre):
    number = 14
    name = "Gold Ore"
    

class IronOre(BlockOre):
    number = 15
    name = "Iron Ore"


class CoalOre(BlockOre):
    number = 16
    name = "Coal Ore"

    
class Wood(Block):
    number = 17
    name = "Wood"
    material = materials.wood


class Leaves(Block):
    number = 18
    name = "Leaves"
    material = materials.leaves
    is_opaque_cube = False


class Sponge(Block):
    number = 19
    name = "Sponge"
    material = materials.sponge

    
class Glass(Block):
    number = 20
    name = "Glass"
    material = materials.glass
    render_as_normal_block = False
    is_opaque_cube = False

    
class LapisLazuliOre(BlockOre):
    number = 21
    name = "Lapis Lazuli Ore"
    

class LapisLazuliBlock(Block):
    number = 22
    name = "Lapis Lazuli Block"
    material = materials.rock
    
    
class Dispenser(Block):
    number = 23
    name = "Dispenser"
    material = materials.rock
    
    
class Sandstone(Block):
    number = 24
    name = "Sandstone"    
    material = materials.rock


class NoteBlock(Block):
    number = 25
    name = "Note Block"
    material = materials.wood

    
class Bed(Block):
    number = 26
    name = "Bed"
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.5625, 1.0)
    material = materials.cloth
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def stand_type(self):
        return (self.number, )


class PoweredRail(BlockNonSolid):
    number = 27
    name = "Powered Rail"    
    material = materials.circuits


class DetectorRail(BlockNonSolid):
    number = 28
    name = "Detector Rail"
    material = materials.circuits
    

class StickyPiston(BlockPiston): #TODO bounding box from blockpistonbase
    number = 29
    name = "Sticky Piston"


class Cobweb(BlockNonSolid):
    number = 30
    name = "Cobweb"    
    material = materials.web

    @property
    def stand_type(self):
        return (self.number, )


class TallGrass(BlockFlower):
    number = 31
    name = "Tall Grass"    
    material = materials.vine

    
class DeadBush(BlockFlower):
    number = 32
    name = "Dead Bush"        
    material = materials.vine


class Piston(BlockPiston):
    number = 33
    name = "Piston"

    
class PistonExtension(Block): #TODO bounding box from blockpistonextension
    number = 34
    name = "Piston Extension"
    material = materials.piston
    render_as_normal_block = False
    is_opaque_cube = False

    
class Wool(Block):
    number = 35
    name = "Wool"    
    material = materials.cloth


class PistonMoving(Block): #TODO bounding box from blockpistonmoving
    number = 36
    name = "Piston Moving"
    material = materials.piston
    render_as_normal_block = False
    is_opaque_cube = False
    
    
class Dandelion(BlockFlower):
    number = 37
    name = "Dandelion"    

    
class Rose(BlockFlower):
    number = 38
    name = "Rose"    
    
    
class BrownMushroom(BlockFlower):
    number = 39
    name = "Brown Mushroom"

    
class RedMushroom(BlockFlower):
    number = 40
    name = "Red Mushroom"
    

class BlockOfGold(Block):
    number = 41
    name = "Block of Gold"    
    material = materials.iron


class BlockOfIron(Block):
    number = 42
    name = "Block of Iron"    
    material = materials.iron

    
class DoubleSlab(Block):
    number = 43
    name = "Double Slab"
    material = materials.rock

    
class SingleSlab(BlockSingleSlab):
    number = 44
    name = "Single Slab"
    material = materials.rock

    
class Bricks(Block):
    number = 45
    name = "Bricks"
    material = materials.rock

    
class TNT(Block):
    number = 46
    name = "TNT"    
    material = materials.tnt


class Bookshelf(Block):
    number = 47
    name = "Bookshelf"
    material = materials.wood
    
    
class MossStone(Block):
    number = 48
    name = "Moss Stone"
    material = materials.rock
    

class Obsidian(Block):
    number = 49
    name = "Obsidian"
    material = materials.rock
    

class Torch(BlockTorch):
    number = 50
    name = "Torch"
    material = materials.circuits
    
    
class Fire(BlockNonSolid):
    number = 51
    name = "Fire"
    material = materials.fire

    @property
    def stand_type(self):
        return (self.number, )
    
    
class MonsterSpawner(Block):
    number = 52
    name = "Monster Spawner"
    material = materials.rock
    is_opaque_cube = False


class WoodenStairs(BlockStairs):
    number = 53
    name = "Wooden Stairs"    
    material = WoodenPlanks.material

    
class Chest(Block):
    number = 54
    name = "Chest"
    material = materials.wood
    render_as_normal_block = False
    is_opaque_cube = False

    
class RedstoneWire(BlockNonSolid):
    number = 55
    name = "Redstone Wire"    
    material = materials.circuits


class DiamondOre(BlockOre):
    number = 56
    name = "Diamond Ore"
    
    
class BlockOfDiamond(Block):
    number = 57
    name = "Block of Diamond"
    material = materials.iron
    
    
class CraftingTable(Block):
    number = 58
    name = "Crafting Table"
    material = materials.wood
    

class WheatCrops(BlockFlower):
    number = 59
    name = "Wheat Crops"

    
class Farmland(Block):
    number = 60
    name = "Farmland"
    material = materials.ground
    render_as_normal_block = False
    is_opaque_cube = False
    

class Furnace(Block):
    number = 61
    name = "Furnace"
    material = materials.rock


class BurningFurnace(Block):
    number = 62
    name = "Burning Furnace"
    material = materials.rock


class SignPost(BlockNonSolid):
    number = 63
    name = "Sign Post"
    material = materials.wood

    
class WoodenDoor(BlockDoor):
    number = 64
    name = "Wooden Door"
    material = materials.wood    
    

class Ladders(Block):
    number = 65
    name = "Ladders"
    material = materials.circuits
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box = [AABB(0.0, 0.0, 0.875, 1.0, 1.0, 1.0),
              AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.125),
              AABB(0.875, 0.0, 0.0, 1.0, 1.0, 1.0),
              AABB(0.0, 0.0, 0.0, 0.125, 1.0, 1.0)]

    @property
    def stand_type(self):
        return (self.number, self.meta)

    @property
    def stand_number(self):
        return self.stand_type
    
    @property
    def grid_bounding_box(self):
        if self.meta == 2: i = 0
        elif self.meta == 3: i = 1
        elif self.meta == 4: i = 2
        elif self.meta == 5: i = 3
        return self.bounding_box[i] + self.coords
        
    
class Rail(BlockNonSolid):
    number = 66
    name = "Rail"
    material = materials.circuits

    
class CobblestoneStairs(BlockStairs):
    number = 67
    name = "Cobblestone Stairs"
    material = Cobblestone.material

    
class WallSign(BlockNonSolid):
    number = 68
    name = "Wall Sign"
    material = materials.wood

    
class Lever(BlockNonSolid):
    number = 69
    name = "Lever"
    material = materials.circuits

    
class StonePressurePlate(BlockNonSolid):
    number = 70
    name = "Stone Pressure Plate"
    material = materials.rock

    
class IronDoor(BlockDoor):
    number = 71
    name = "Iron Door"
    material = materials.iron

    
class WoodenPressurePlate(BlockNonSolid):
    number = 72
    name = "Wooden Pressure Plate"
    material = materials.wood

    
class RedstoneOre(Block):
    number = 73
    name = "Redstone Ore"
    material = materials.rock

    
class GlowingRedstoneOre(Block):
    number = 74
    name = "Glowing Redstone Ore"
    material = materials.rock

    
class RedstoneTorchOffState(BlockTorch):
    number = 75
    name = "Redstone Torch off state"
    material = materials.circuits
    

class RedstoneTorchOnState(BlockTorch):
    number = 76
    name = "Redstone Torch on state"
    material = materials.circuits

    
class StoneButton(BlockNonSolid):
    number = 77
    name = "Stone Button"
    material = materials.circuits

    
class Snow(Block):
    number = 78
    name = "Snow"
    material = materials.snow
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box = None

    @property
    def stand_type(self):
        return (self.number, self.meta)

    @property
    def stand_number(self):
        return self.stand_type

    @property
    def collidable(self):
        return (self.meta & 7) >= 3

    @property
    def grid_bounding_box(self):
        m = self.meta & 7
        if m >= 3:
            return AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0) + self.coords
        else:
            return None
    
    
class Ice(Block):
    number = 79
    name = "Ice"
    slipperiness = 0.98
    material = materials.ice
    is_opaque_cube = False
    
    
class SnowBlock(Block):
    number = 80
    name = "Snow Block"
    material = materials.crafted_snow
    
    
class Cactus(Block):
    number = 81
    name = "Cactus"
    material = materials.cactus
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box = AABB(0.0625, 0.0, 0.0625, 1.0 - 0.0625, 1.0 - 0.0625, 1.0 - 0.0625)

    @property
    def stand_type(self):
        return (self.number, )
    
    
class ClayBlock(Block):
    number = 82
    name = "Clay Block"
    material = materials.clay
    
    
class SugarCane(BlockNonSolid):
    number = 83
    name = "Sugar Cane"
    material = materials.plants
    
    
class Jukebox(Block):
    number = 84
    name = "Jukebox"
    material = materials.wood

        
class Fence(BlockFence):
    number = 85
    name = "Fence"
    material = materials.wood

    
class Pumpkin(Block):
    number = 86
    name = "Pumpkin"
    material = materials.pumpkin

    
class Netherrack(Block):
    number = 87
    name = "Netherrack"
    material = materials.rock
    
    
class SoulSand(Block):
    number = 88
    name = "Soul Sand"
    material = materials.sand
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 1.0 - 0.125, 1.0)

    @property
    def stand_type(self):
        return (self.number, )
    
    
class GlowstoneBlock(Block):
    number = 89
    name = "Glowstone Block"
    material = materials.glass
    
    
class NetherPortal(BlockNonSolid):
    number = 90
    name = "Nether Portal"
    material = materials.portal
    
    
class JackOLantern(Block):
    number = 91
    name = "Jack 'o' Lantern"
    material = materials.pumpkin

    
class Cake(Block):
    number = 92
    name = "Cake"
    material = materials.cake
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def stand_type(self):
        return (self.number, self.meta)

    @property
    def stand_number(self):
        return self.stand_type
    
    @property
    def grid_bounding_box(self):
        f = 0.0625
        f1 = (1 + self.meta * 2) / 16.0
        return AABB(f1, 0.0, f, 1.0 - f, 0.5 - f, 1.0 - f) + self.coords

        
class RedstoneRepeaterOff(RedstoneRepeater):
    number = 93
    name = "Redstone Repeater ('off' state)"
    
    
class RedstoneRepeaterOn(RedstoneRepeater):
    number = 94
    name = "Redstone Repeater ('on' state)"
    
    
class LockedChest(Block):
    number = 95
    name = "Locked Chest"
    material = materials.wood
    
    
class Trapdoor(Block):
    number = 96
    name = "Trapdoor"
    material = materials.wood
    bounding_box_closed = AABB(0.0, 0.0, 0.0, 1.0, 0.1875, 1.0)
    bounding_boxes = [AABB(0.0, 0.0, 0.8125, 1.0, 1.0, 1.0),
                    AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.1875),
                    AABB(0.8125, 0.0,    0.0, 1.0, 1.0, 1.0),
                    AABB(0.0, 0.0, 0.0, 0.1875, 1.0, 1.0)]
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def stand_type(self):
        return (self.number, self.is_closed)

    @property
    def stand_number(self):
        return self.stand_type

    @property
    def is_closed(self):
        return (self.meta & 4) == 0
    
    @property
    def grid_bounding_box(self):
        if self.is_closed:
            return self.bounding_box_closed + self.coords
        else:
            return self.bounding_boxes[self.meta & 3] + self.coords
    
    
class HiddenSilverfish(Block):
    number = 97
    name = "Hidden Silverfish"
    material = materials.clay
    
    
class StoneBrick(Block):
    number = 98
    name = "Stone Brick"
    material = materials.rock
    
    
class HugeBrownMushroom(Block):
    number = 99
    name = "Huge Brown Mushroom"
    material = materials.wood
    
    
class HugeRedMushroom(Block):
    number = 100
    name = "Huge Red Mushroom"
    material = materials.wood
    
    
class IronBars(BlockPane):
    number = 101
    name = "Iron Bars"
    material = materials.iron

    
class GlassPane(BlockPane):
    number = 102
    name = "Glass Pane"
    material = materials.glass
    
    
class MelonBlock(Block):
    number = 103
    name = "Melon Block"
    material = materials.pumpkin
    
    
class PumpkinStem(BlockFlower):
    number = 104
    name = "Pumpkin Stem"

    
class MelonStem(BlockFlower):
    number = 105
    name = "Melon Stem"

    
class Vines(BlockNonSolid):
    number = 106
    name = "Vines"
    material = materials.vine

    @property
    def stand_type(self):
        return (self.number, )

    
class FenceGate(Block):
    number = 107
    name = "Fence Gate"
    material = materials.wood
    bounding_box_north_south = AABB(0.375, 0, 0, 0.625, 1.5, 1.0) 
    bounding_box_east_west   = AABB(0, 0, 0.375, 1.0, 1.5, 0.625) 
    is_opaque_cube = False
    render_as_normal_block = False

    @property
    def stand_type(self):
        return (self.number, self.is_open)

    @property
    def stand_number(self):
        return self.stand_type

    @property
    def collidable(self):
        if self.is_open:
            return False
        else:
            return True

    @property
    def is_open(self):
        return (self.meta & 4) != 0
    
    @property
    def grid_bounding_box(self):
        if self.is_open:
            return None
        elif self.meta != 2 and self.meta != 0: 
            return self.bounding_box_north_south + self.coords
        else:
            return self.bounding_box_east_west + self.coords

    def add_grid_bounding_boxes_to(self, out):
        if not self.is_open:
            out.append(self.grid_bounding_box)

    def sweep_collision(self, bb, vect, debug=False, max_height=False):
        if not self.is_open:
            col, d = bb.sweep_collision(self.grid_bounding_box, vect, debug=debug)
            return col, d, self.grid_bounding_box
        else:
            return False, None, self.grid_bounding_box

    def collides_with(self, bb):
        if not self.collidable:
            return False
        return super(FenceGate, self).collides_with(bb)

    def collides_on_axes(self, bb, x=False, y=False, z=False):
        if not self.collidable:
            return False
        return super(FenceGate, self).collides_on_axes(bb, x, y, z)

    def intersection_on_axes(self, bb, x=False, y=False, z=False, debug=False):
        if not self.collidable:
            return None
        return bb.intersection_on_axes(self.grid_bounding_box, x, y, z, debug=debug)
    
    
class BrickStairs(BlockStairs):
    number = 108
    name = "Brick Stairs"
    material = Bricks.material

    
class StoneBrickStairs(BlockStairs):
    number = 109
    name = "Stone Brick Stairs"
    material = StoneBrick.material

    
class Mycelium(Block):
    number = 110
    name = "Mycelium"
    material = materials.grass

    
class LilyPad(Block):
    number = 111
    name = "Lily Pad"
    material = materials.plants
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.015625, 1.0)
    is_opaque_cube = False
    render_as_normal_block = False

    @property
    def stand_type(self):
        return (self.number, )
    
    
class NetherBrick(Block):
    number = 112
    name = "Nether Brick"
    material = materials.rock
    
    
class NetherBrickFence(BlockFence):
    number = 113
    name = "Nether Brick Fence"
    material = materials.rock
    
    
class NetherBrickStairs(BlockStairs):
    number = 114
    name = "Nether Brick Stairs"
    material = NetherBrick.material
    
    
class NetherWart(BlockFlower):
    number = 115
    name = "Nether Wart"

    
class EnchantmentTable(Block):
    number = 116
    name = "Enchantment Table"
    material = materials.rock
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.75, 1.0)
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def stand_type(self):
        return (self.number, )
    
    
class BrewingStand(BlockMultiBox):
    number = 117
    name = "Brewing Stand"
    material = materials.iron
    bounding_box_stand = AABB(0.4375, 0.0, 0.4375, 0.5625, 0.875, 0.5625)
    bounding_box_base = AABB(0.0, 0.0, 0.0, 1.0, 0.125, 1.0)
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def stand_type(self):
        return (self.number, )

    @property
    def grid_bounding_box(self):
        return [bounding_box_stand + self.coords, bounding_box_base + self.coords]
    
    
class Cauldron(Block):
    number = 118
    name = "Cauldron"
    material = materials.iron
    render_as_normal_block = False
    is_opaque_cube = False
    
    
class EndPortal(BlockNonSolid): #testing, anyone?
    number = 119
    name = "End Portal"
    material = materials.portal


class EndPortalFrame(BlockMultiBox):
    number = 120
    name = "End Portal Frame"
    material = materials.glass
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.8125, 1.0)
    bounding_box_eye_inserted = AABB(0.3125, 0.8125, 0.3125, 0.6875, 1.0, 0.6875)
    is_opaque_cube = False

    @property
    def stand_type(self):
        return (self.number, self.eye_inserted)

    @property
    def stand_number(self):
        return self.stand_type

    @property
    def eye_inserted(self):
        return (self.meta & 4) != 0

    @property
    def grid_bounding_box(self):
        out = [bounding_box + self.coords]
        if self.eye_inserted:
            out.append(bounding_box_eye_inserted + self.coords)
        return out
    
    
class EndStone(Block):
    number = 121
    name = "End Stone"
    material = materials.rock

    
class DragonEgg(BlockNonSolid):
    number = 122
    name = "Dragon Egg"
    material = materials.dragon_egg

    
class RedstoneLampInactive(Block):
    number = 123
    name = "Redstone Lamp (inactive)"
    material = materials.redstone_light

    
class RedstoneLampActive(Block):
    number = 124
    name = "Redstone Lamp (active)"
    material = materials.redstone_light

    
class WoodenDoubleSlab(Block):
    number = 125
    name = "Wooden Double Slab"
    material = materials.wood


class WoodenSlab(BlockSingleSlab):
    number = 126
    name = "Wooden Slab"
    material = materials.wood


class CocoaPlant(BlockFlower):
    number = 127
    name = "Cocoa Plant"
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def get_direction(self):
        return self.meta & 3
    
    @property
    def grid_bounding_box(self):
        v6 = self.get_direction
        v7 = (self.meta & 12) >> 2
        v8 = 4 + v7 * 2
        v9 = 5 + v7 * 2
        v10 = v8 / 2.0
        if v6 == 0:
            gbb = AABB((8.0 - v10) / 16.0, (12.0 - v9) / 16.0, (15.0 - v8) / 16.0, (8.0 + v10) / 16.0, 0.75, 0.9375)
        elif v6 == 1:
            gbb = AABB(0.0625, (12.0 - v9) / 16.0, (8.0 - v10) / 16.0, (1.0 + v8) / 16.0, 0.75, (8.0 + v10) / 16.0)
        elif v6 == 2:
            gbb = AABB((8.0 - v10) / 16.0, (12.0 - v9) / 16.0, 0.0625, (8.0 + v10) / 16.0, 0.75, (1.0 + v8) / 16.0)
        elif v6 == 3:
            gbb = AABB((15.0 - var8) / 16.0, (12.0 - v9) / 16.0, (8.0 - v10) / 16.0, 0.9375, 0.75, (8.0 + v10) / 16.0)
        else:
            raise Extension("undefined cocoa bounding box for %s" % v6)
        return gbb + self.coords


class SandstoneStairs(BlockStairs):
    number = 128
    name = "Sandstone Stairs"
    material = Sandstone.material

    
class EmeraldOre(BlockOre):
    number = 129
    name = "Emerald Ore"


class EnderChest(Block):
    number = 130
    name = "Ender Chest"
    material = materials.rock
    render_as_normal_block = False
    is_opaque_cube = False


class TripwireHook(BlockNonSolid):
    number = 131
    name = "Tripwire Hook"
    material = materials.circuits
    render_as_normal_block = False


class Tripwire(BlockNonSolid):
    number = 132
    name = "Tripwire"
    material = materials.circuits
    render_as_normal_block = False


class BlockOfEmerald(Block):
    number = 133
    name = "Block of Emerald"
    material = materials.iron


class SpruceWoodStairs(BlockStairs):
    number = 134
    name = "Spruce Wood Stairs"
    material = WoodenPlanks.material


class BirchWoodStairs(BlockStairs):
    number = 135
    name = "Birch Wood Stairs"
    material = WoodenPlanks.material


class JungleWoodStairs(BlockStairs):
    number = 136
    name = "Jungle Wood Stairs"
    material = WoodenPlanks.material

#TODO just guessing the materials and bounding boxes, need to wait for MCP
class CommandBlock(Block):
    number = 137
    name = "Command Block"
    material = materials.iron


class Beacon(Block):
    number = 138
    name = "Beacon"
    material = materials.iron


class CobblestoneWall(BlockFence):
    number = 139
    name = "Cobblestone Wall"
    material = materials.rock


class FlowerPot(Block):
    number = 140
    name = "Flower Pot"
    material = materials.wood


class Carrots(BlockFlower):
    number = 141
    name = "Carrots"


class Potatoes(BlockFlower):
    number = 142
    name = "Potatoes"


class WoodenButton(BlockNonSolid):
    number = 143
    name = "Wooden Button"
    material = materials.circuits


class Head(Block):
    number = 144
    name = "Head"
    material = materials.rock



block_map = [None for _ in xrange(256)]
clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
for _, cl in clsmembers:
    if issubclass(cl, Block) and hasattr(cl, 'number'):
        block_map[cl.number] = cl

