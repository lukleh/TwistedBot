
import inspect
import sys

import logbot
import tools
import materials
from axisbox import AABB
from vector import Vector


log = logbot.getlogger("BLOCKS")


class BlockMetaClass(type):
    def __new__(meta, name, bases, dct):
        cls = super(BlockMetaClass, meta).__new__(meta, name, bases, dct)

        def name_or_class(cls, name):
            try:
                subcls = globals()[name]
                return issubclass(cls, subcls)
            except KeyError:
                return cls.__name__ == name

        cls.is_sign = name_or_class(cls, 'BlockSign')
        cls.is_water = name_or_class(cls, 'BlockWater')
        cls.is_lava = name_or_class(cls, 'BlockLava')
        cls.is_stairs = name_or_class(cls, 'BlockStairs')
        cls.is_ladder = name_or_class(cls, 'Ladders')
        cls.is_vine = name_or_class(cls, 'Vines')
        cls.is_simple_cube = name_or_class(cls, 'BlockCube')
        cls.is_ladder_or_vine = cls.is_ladder or cls.is_vine
        #atts = [(k, v) for k, v in cls.__dict__.items() if k.startswith("is_") and (v == False or v == True)]
        #if any([v == True for k, v in atts]):
        #    print ', '.join(["%s, %s" % (k, v) for k, v in atts]), cls.__name__
        return cls


class Block(object):
    __metaclass__ = BlockMetaClass

    slipperiness = 0.6
    render_as_normal_block = True
    is_opaque_cube = True

    def __init__(self, grid, x, y, z, meta):
        self.grid = grid
        self.x = x
        self.y = y
        self.z = z
        self.meta = meta
        self.coords = Vector(self.x, self.y, self.z)

    def __str__(self):
        return "|%s %s %s|" % (self.coords, self.name, tools.meta2str(self.meta))

    @property
    def is_collidable(self):
        return True

    @property
    def is_free(self):
        return not self.is_collidable and not isinstance(self, BlockFluid) and not self.number == Cobweb.number and not self.number == Fire.number

    @property
    def is_avoid(self):
        return self.is_lava or self.number == Cobweb.number or self.number == Fire.number

    @property
    def is_fence(self):
        return isinstance(self, BlockFence) or (self.number == FenceGate.number and not FenceGate.is_open)

    @property
    def grid_bounding_box(self):
        return self.bounding_box.offset(self.x, self.y, self.z)

    def add_grid_bounding_boxes_to(self, out):
        out.append(self.grid_bounding_box)

    @property
    def grid_bounding_boxes(self):
        out = []
        self.add_grid_bounding_boxes_to(out)
        return out

    @property
    def effective_flow_decay(self):
        return -1

    @property
    def is_solid_block(self, block, ignore):
        return block.material.is_solid

    def on_entity_collided(self, ignore):
        pass


class BlockCube(Block):
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)


class BlockNonSolid(Block):
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def bounding_box(self):
        raise Exception('no bounding box on non solid block')

    @property
    def is_collidable(self):
        return False

    def add_grid_bounding_boxes_to(self, out):
        pass


class BlockFluid(BlockNonSolid):
    @classmethod
    def fluid_aabb(cls, x, y, z):
        return AABB(x, y + 0.4, z, x + 1, y + 0.6, z + 1)


class BlockWater(BlockFluid):
    material = materials.water

    def is_solid_block(self, block, v):
        if block is None:
            return False
        if self.material == block.material:
            return False
        else:
            if v == 1:
                return True
            else:
                if block.material == materials.ice:
                    return False
                else:
                    return super(BlockWater, self).is_solid_block(block, v)

    @property
    def effective_flow_decay(self):
        if self.meta >= 8:
            return 0
        else:
            return self.meta

    @property
    def flow_vector(self):
        v = Vector(0, 0, 0)
        this_efd = self.effective_flow_decay
        for i, j in tools.cross:
            blk = self.grid.get_block(self.x + i, self.y, self.z + j)
            efd = blk.effective_flow_decay
            if efd < 0:
                if not blk.material.blocks_movement:
                    blk = self.grid.get_block(self.x + i, self.y - 1, self.z + j)
                    efd = blk.effective_flow_decay
                    if efd >= 0:
                        va = efd - (this_efd - 8)
                        v = Vector(i * va, 0, j * va)
            elif efd >= 0:
                va = efd - this_efd
                v = Vector(i * va, 0, j * va)
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
            if t or self.is_solid_block(self.grid.get_block(self.x - 1, self.y + 1, self.z), 4):
                t = True
            if t or self.is_solid_block(self.grid.get_block(self.x + 1, self.y + 1, self.z), 5):
                t = True
            if t:
                v.normalize()
                v.y = v.y - 6.0
        v.normalize()
        return v

    def add_velocity_to(self, v):
        fv = self.flow_vector
        return v + fv

    @property
    def height_percent(self):
        if self.meta >= 8:
            return 1 / 9.0
        else:
            return (self.meta + 1) / 9.0


class BlockLava(BlockFluid):
    material = materials.lava


class BlockFlower(BlockNonSolid):
    material = materials.plants


class BlockTorch(BlockNonSolid):
    pass


class BlockOre(BlockCube):
    material = materials.rock


class BlockOfStorage(BlockCube):
    material = materials.iron


class BlockRedstoneRepeater(Block):
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.125, 1.0)
    material = materials.circuits
    render_as_normal_block = False
    is_opaque_cube = False


class BlockMultiBox(Block):

    @property
    def grid_bounding_box(self):
        raise Exception('grid_bounding_box called from BlockMultiBox')


class BlockStairs(BlockMultiBox):
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box_half = AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
    bounding_box_up_half = AABB(0.0, 0.5, 0.0, 1.0, 1.0, 1.0)

    @property
    def is_upsite_down(self):
        return (self.meta & 4) != 0

    def add_grid_bounding_boxes_to(self, out):
        if self.is_upsite_down:
            out.append(self.bounding_box_up_half.offset(self.x, self.y, self.z))
        else:
            out.append(self.bounding_box_half.offset(self.x, self.y, self.z))
        self.extra_bounding_boxes(out)

    def similar_stairs(self, blk):
        return blk.is_stairs and self.is_upsite_down == blk.is_upsite_down

    def same_orientation(self, x, y, z):
        blk = self.grid.get_block(x, y, z)
        return blk.is_stairs and blk.meta == self.meta

    def extra_bounding_boxes(self, out):
        minx = 0.0
        maxx = 1.0
        miny = 0.5
        maxy = 1
        minz = 0.0
        maxz = 0.5
        if self.is_upsite_down:
            miny = 0
            maxy = 0.5
        next_box = True
        dirc = self.meta & 3
        if dirc == 0:
            blk = self.grid.get_block(self.x + 1, self.y, self.z)
            minx = 0.5
            maxz = 1.0
            if self.similar_stairs(blk):
                m3 = blk.meta & 3
                if m3 == 3 and not self.same_orientation(self.x, self.y, self.z + 1):
                    maxz = 0.5
                    next_box = False
                elif m3 == 2 and not self.same_orientation(self.x, self.y, self.z - 1):
                    minz = 0.5
                    next_box = False
        elif dirc == 1:
            blk = self.grid.get_block(self.x - 1, self.y, self.z)
            maxx = 0.5
            maxz = 1.0
            if self.similar_stairs(blk):
                m3 = blk.meta & 3
                if m3 == 3 and not self.same_orientation(self.x, self.y, self.z + 1):
                    maxz = 0.5
                    next_box = False
                elif m3 == 2 and not self.same_orientation(self.x, self.y, self.z - 1):
                    minz = 0.5
                    next_box = False
        elif dirc == 2:
            blk = self.grid.get_block(self.x, self.y, self.z + 1)
            minz = 0.5
            maxz = 1.0
            if self.similar_stairs(blk):
                m3 = blk.meta & 3
                if m3 == 1 and not self.same_orientation(self.x + 1, self.y, self.z):
                    maxx = 0.5
                    next_box = False
                elif m3 == 0 and not self.same_orientation(self.x - 1, self.y, self.z):
                    minx = 0.5
                    next_box = False
        elif dirc == 3:
            blk = self.grid.get_block(self.x, self.y, self.z - 1)
            if self.similar_stairs(blk):
                m3 = blk.meta & 3
                if m3 == 1 and not self.same_orientation(self.x + 1, self.y, self.z):
                    maxx = 0.5
                    next_box = False
                elif m3 == 0 and not self.same_orientation(self.x - 1, self.y, self.z):
                    minx = 0.5
                    next_box = False
        out.append(AABB(minx, miny, minz, maxx, maxy, maxz).offset(self.x, self.y, self.z))
        if next_box:
            minx = 0.0
            maxx = 0.5
            miny = 0.5
            maxy = 1
            minz = 0.5
            maxz = 1.0
            if self.is_upsite_down:
                miny = 0
                maxy = 0.5
            next_box = False
            if dirc == 0:
                blk = self.grid.get_block(self.x - 1, self.y, self.z)
                if self.similar_stairs(blk):
                    m3 = blk.meta & 3
                    if m3 == 3 and not self.same_orientation(self.x, self.y, self.z - 1):
                        minz = 0.0
                        maxz = 0.5
                        next_box = True
                    elif m3 == 2 and not self.same_orientation(self.x, self.y, self.z + 1):
                        minz = 0.5
                        maxz = 1.0
                        next_box = True
            elif dirc == 1:
                blk = self.grid.get_block(self.x + 1, self.y, self.z)
                if self.similar_stairs(blk):
                    m3 = blk.meta & 3
                    minx = 0.5
                    maxx = 1.0
                    if m3 == 3 and not self.same_orientation(self.x, self.y, self.z - 1):
                        minz = 0.0
                        maxz = 0.5
                        next_box = True
                    elif m3 == 2 and not self.same_orientation(self.x, self.y, self.z + 1):
                        minz = 0.5
                        maxz = 1.0
                        next_box = True
            elif dirc == 2:
                blk = self.grid.get_block(self.x, self.y, self.z - 1)
                if self.similar_stairs(blk):
                    m3 = blk.meta & 3
                    minz = 0.0
                    maxz = 0.5
                    if m3 == 1 and not self.same_orientation(self.x - 1, self.y, self.z):
                        next_box = True
                    elif m3 == 0 and not self.same_orientation(self.x + 1, self.y, self.z):
                        minx = 0.5
                        maxx = 1.0
                        next_box = True
            elif dirc == 3:
                blk = self.grid.get_block(self.x, self.y, self.z + 1)
                if self.similar_stairs(blk):
                    m3 = blk.meta & 3
                    if m3 == 1 and not self.same_orientation(self.x - 1, self.y, self.z):
                        next_box = True
                    elif m3 == 0 and not self.same_orientation(self.x + 1, self.y, self.z):
                        minx = 0.5
                        maxx = 1.0
                        next_box = True
            if next_box:
                out.append(AABB(minx, miny, minz, maxx, maxy, maxz).offset(self.x, self.y, self.z))


class BlockDoor(Block):
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_boxes = [AABB(0.0, 0.0, 0.0, 0.1875, 1.0, 1.0),
                      AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.1875),
                      AABB(0.8125, 0.0, 0.0, 1.0, 1.0, 1.0),
                      AABB(0.0, 0.0, 0.8125, 1.0, 1.0, 1.0)]
    top_part = None
    bottom_part = None

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
    def is_hinge_right(self):
        return (self.top_part.meta & 1) != 0

    @property
    def facing_index(self):
        return self.bottom_part.meta & 3

    @property
    def is_top_half(self):
        return (self.meta & 8) != 0

    @property
    def bounding_boxes_index(self):
        self.assign_parts()
        if self.is_open:
            if self.is_hinge_right:
                fi = self.facing_index - 1
                if fi >= 0:
                    return fi
                else:
                    return 3
            else:
                fi = self.facing_index + 1
                if fi < 4:
                    return fi
                else:
                    return 0
        else:
            return self.facing_index

    @property
    def grid_bounding_box(self):
        return self.bounding_boxes[self.bounding_boxes_index].offset(self.x, self.y, self.z)


class BlockPane(BlockMultiBox):
    render_as_normal_block = False
    is_opaque_cube = False

    def can_connect_to(self, x, y, z):
        blk = self.grid.get_block(x, y, z)
        return blk.is_opaque_cube or \
            blk.number == self.number or \
            blk.number == Glass.number

    def cross_connected(self):
        return (self.can_connect_to(self.x, self.y, self.z - 1),
                self.can_connect_to(self.x, self.y, self.z + 1),
                self.can_connect_to(self.x - 1, self.y, self.z),
                self.can_connect_to(self.x + 1, self.y, self.z))

    def add_grid_bounding_boxes_to(self, out):
        zl, zr, xl, xr = self.cross_connected()
        if (not xl or not xr) and (xl or xr or zl or zr):
            if xl and not xr:
                out.append(AABB(0.0, 0.0, 0.4375, 0.5, 1.0, 0.5625).offset(self.x, self.y, self.z))
            elif not xl and xr:
                out.append(AABB(0.5, 0.0, 0.4375, 1.0, 1.0, 0.5625).offset(self.x, self.y, self.z))
        else:
            out.append(AABB(0.0, 0.0, 0.4375, 1.0, 1.0, 0.5625).offset(self.x, self.y, self.z))
        if (not zl or not zr) and (xl or xr or zl or zr):
            if zl and not zr:
                out.append(AABB(0.4375, 0.0, 0.0, 0.5625, 1.0, 0.5).offset(self.x, self.y, self.z))
            elif not zl and zr:
                out.append(AABB(0.4375, 0.0, 0.5, 0.5625, 1.0, 1.0).offset(self.x, self.y, self.z))
        else:
            out.append(AABB(0.4375, 0.0, 0.0, 0.5625, 1.0, 1.0).offset(self.x, self.y, self.z))


class BlockFence(Block):
    is_opaque_cube = False
    render_as_normal_block = False

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
        return AABB(minx, 0, minz, maxx, 1.5, maxz).offset(self.x, self.y, self.z)

    def can_connect_to(self, x, y, z):
        blk = self.grid.get_block(x, y, z)
        if blk.number != self.number and blk.number != FenceGate.number:
            if blk.material.is_opaque and blk.render_as_normal_block:
                return blk.material != materials.pumpkin
            else:
                return False
        else:
            return True


class BlockPiston(BlockCube):
    material = materials.piston
    render_as_normal_block = False
    is_opaque_cube = False


class BlockSingleSlab(Block):
    bounding_box_lower = AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
    bounding_box_higher = AABB(0.0, 0.5, 0.0, 1.0, 1.0, 1.0)
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def lower_part(self):
        return self.meta & 8 == 0

    @property
    def grid_bounding_box(self):
        if self.lower_part:
            return self.bounding_box_lower.offset(self.x, self.y, self.z)
        else:
            return self.bounding_box_higher.offset(self.x, self.y, self.z)


class BlockBiCollidable(Block):

    def add_grid_bounding_boxes_to(self, out):
        if self.is_collidable:
            out.append(self.grid_bounding_box)


class BlockSign(BlockNonSolid):
    material = materials.wood


class Air(BlockNonSolid):
    number = 0
    name = "Air"
    material = materials.air


class Stone(BlockCube):
    number = 1
    name = "Stone"
    material = materials.rock


class Grass(BlockCube):
    number = 2
    name = "Grass Block"
    material = materials.grass


class Dirt(BlockCube):
    number = 3
    name = "Dirt"
    material = materials.ground


class Cobblestone(BlockCube):
    number = 4
    name = "Cobblestone"
    material = materials.rock


class WoodenPlanks(BlockCube):
    number = 5
    name = "Wooden Planks"
    material = materials.wood


class Saplings(BlockFlower):
    number = 6
    name = "Saplings"


class Bedrock(BlockCube):
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


class Sand(BlockCube):
    number = 12
    name = "Sand"
    material = materials.sand


class Gravel(BlockCube):
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


class Wood(BlockCube):
    number = 17
    name = "Wood"
    material = materials.wood


class Leaves(BlockCube):
    number = 18
    name = "Leaves"
    material = materials.leaves
    is_opaque_cube = False


class Sponge(BlockCube):
    number = 19
    name = "Sponge"
    material = materials.sponge


class Glass(BlockCube):
    number = 20
    name = "Glass"
    material = materials.glass
    render_as_normal_block = False
    is_opaque_cube = False


class LapisLazuliOre(BlockOre):
    number = 21
    name = "Lapis Lazuli Ore"


class LapisLazuliBlock(BlockCube):
    number = 22
    name = "Lapis Lazuli Block"
    material = materials.rock


class Dispenser(BlockCube):
    number = 23
    name = "Dispenser"
    material = materials.rock


class Sandstone(BlockCube):
    number = 24
    name = "Sandstone"
    material = materials.rock


class NoteBlock(BlockCube):
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


class PoweredRail(BlockNonSolid):
    number = 27
    name = "Powered Rail"
    material = materials.circuits


class DetectorRail(BlockNonSolid):
    number = 28
    name = "Detector Rail"
    material = materials.circuits


class StickyPiston(BlockPiston):
    number = 29
    name = "Sticky Piston"


class Cobweb(BlockNonSolid):
    number = 30
    name = "Cobweb"
    material = materials.web


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


class PistonExtension(BlockMultiBox):
    number = 34
    name = "Piston Extension"
    material = materials.piston
    render_as_normal_block = False
    is_opaque_cube = False

    def add_grid_bounding_boxes_to(self, out):
        direction = self.meta & 7
        if direction == 0:
            out.append(AABB(0.0, 0.0, 0.0, 1.0, 0.25, 1.0).offset(self.x, self.y, self.z))
            out.append(AABB(0.375, 0.25, 0.375, 0.625, 1.0, 0.625).offset(self.x, self.y, self.z))
        elif direction == 1:
            out.append(AABB(0.0, 0.75, 0.0, 1.0, 1.0, 1.0).offset(self.x, self.y, self.z))
            out.append(AABB(0.375, 0.0, 0.375, 0.625, 0.75, 0.625).offset(self.x, self.y, self.z))
        elif direction == 2:
            out.append(AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.25).offset(self.x, self.y, self.z))
            out.append(AABB(0.25, 0.375, 0.25, 0.75, 0.625, 1.0).offset(self.x, self.y, self.z))
        elif direction == 3:
            out.append(AABB(0.0, 0.0, 0.75, 1.0, 1.0, 1.0).offset(self.x, self.y, self.z))
            out.append(AABB(0.25, 0.375, 0.0, 0.75, 0.625, 0.75).offset(self.x, self.y, self.z))
        elif direction == 4:
            out.append(AABB(0.0, 0.0, 0.0, 0.25, 1.0, 1.0).offset(self.x, self.y, self.z))
            out.append(AABB(0.375, 0.25, 0.25, 0.625, 0.75, 1.0).offset(self.x, self.y, self.z))
        elif direction == 5:
            out.append(AABB(0.75, 0.0, 0.0, 1.0, 1.0, 1.0).offset(self.x, self.y, self.z))
            out.append(AABB(0.0, 0.375, 0.25, 0.75, 0.625, 0.75).offset(self.x, self.y, self.z))


class Wool(BlockCube):
    number = 35
    name = "Wool"
    material = materials.cloth


class PistonMoving(Block):
    #TODO
    number = 36
    name = "Piston Moving"
    material = materials.piston
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def is_collidable(self):
        return False

    def get_tile_entity(self, x, y, z):
        # just a crud
        te = self.grid.get_tile_entity(x, y, z)
        TileEntityPiston = object
        return te if isinstance(te, TileEntityPiston) else None

    @property
    def grid_bounding_box(self):
        # short circuit for now
        return self.bounding_box.offset(self.x, self.y, self.z)
        te = self.get_tile_entity(self.x, self.y, self.z)
        if te is None:
            return
        p = te.progress(0.0)
        if te.is_extending:
            p = 1.0 - p
        return self.get_aabb(te.stored_blockID, p, te.piston_orientation)


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


class BlockOfGold(BlockOfStorage):
    number = 41
    name = "Block of Gold"
    material = materials.iron


class BlockOfIron(BlockOfStorage):
    number = 42
    name = "Block of Iron"
    material = materials.iron


class DoubleSlab(BlockCube):
    number = 43
    name = "Double Slab"
    material = materials.rock


class SingleSlab(BlockSingleSlab):
    number = 44
    name = "Single Slab"
    material = materials.rock


class Bricks(BlockCube):
    number = 45
    name = "Bricks"
    material = materials.rock


class TNT(BlockCube):
    number = 46
    name = "TNT"
    material = materials.tnt


class Bookshelf(BlockCube):
    number = 47
    name = "Bookshelf"
    material = materials.wood


class MossStone(BlockCube):
    number = 48
    name = "Moss Stone"
    material = materials.rock


class Obsidian(BlockCube):
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


class MonsterSpawner(BlockCube):
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
    bounding_box = AABB(0.0625, 0.0, 0.0625, 0.9375, 0.875, 0.9375)


class RedstoneWire(BlockNonSolid):
    number = 55
    name = "Redstone Wire"
    material = materials.circuits


class DiamondOre(BlockOre):
    number = 56
    name = "Diamond Ore"


class BlockOfDiamond(BlockOfStorage):
    number = 57
    name = "Block of Diamond"
    material = materials.iron


class CraftingTable(BlockCube):
    number = 58
    name = "Crafting Table"
    material = materials.wood


class WheatCrops(BlockFlower):
    number = 59
    name = "Wheat Crops"


class Farmland(BlockCube):
    number = 60
    name = "Farmland"
    material = materials.ground
    render_as_normal_block = False
    is_opaque_cube = False


class Furnace(BlockCube):
    number = 61
    name = "Furnace"
    material = materials.rock


class BurningFurnace(BlockCube):
    number = 62
    name = "Burning Furnace"
    material = materials.rock


class SignPost(BlockSign):
    number = 63
    name = "Sign Post"


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
    def grid_bounding_box(self):
        if self.meta == 2:
            i = 0
        elif self.meta == 3:
            i = 1
        elif self.meta == 4:
            i = 2
        elif self.meta == 5:
            i = 3
        return self.bounding_box[i].offset(self.x, self.y, self.z)


class Rail(BlockNonSolid):
    number = 66
    name = "Rail"
    material = materials.circuits


class CobblestoneStairs(BlockStairs):
    number = 67
    name = "Cobblestone Stairs"
    material = Cobblestone.material


class WallSign(BlockSign):
    number = 68
    name = "Wall Sign"


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


class RedstoneOre(BlockOre):
    number = 73
    name = "Redstone Ore"


class GlowingRedstoneOre(BlockOre):
    number = 74
    name = "Glowing Redstone Ore"


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


class Snow(BlockBiCollidable):
    number = 78
    name = "Snow"
    material = materials.snow
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box = None

    @property
    def is_collidable(self):
        return (self.meta & 7) >= 3

    @property
    def grid_bounding_box(self):
        m = self.meta & 7
        if m >= 3:
            return AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0).offset(self.x, self.y, self.z)
        else:
            return None


class Ice(BlockCube):
    number = 79
    name = "Ice"
    slipperiness = 0.98
    material = materials.ice
    is_opaque_cube = False


class SnowBlock(BlockCube):
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


class ClayBlock(BlockCube):
    number = 82
    name = "Clay Block"
    material = materials.clay


class SugarCane(BlockNonSolid):
    number = 83
    name = "Sugar Cane"
    material = materials.plants


class Jukebox(BlockCube):
    number = 84
    name = "Jukebox"
    material = materials.wood


class Fence(BlockFence):
    number = 85
    name = "Fence"
    material = materials.wood


class Pumpkin(BlockCube):
    number = 86
    name = "Pumpkin"
    material = materials.pumpkin


class Netherrack(BlockCube):
    number = 87
    name = "Netherrack"
    material = materials.rock


class SoulSand(Block):
    number = 88
    name = "Soul Sand"
    material = materials.sand
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 1.0 - 0.125, 1.0)

    def on_entity_collided(self, b_obj):
        b_obj.velocities[0] *= 0.4
        b_obj.velocities[2] *= 0.4


class GlowstoneBlock(BlockCube):
    number = 89
    name = "Glowstone Block"
    material = materials.glass


class NetherPortal(BlockNonSolid):
    number = 90
    name = "Nether Portal"
    material = materials.portal


class JackOLantern(BlockCube):
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
    def grid_bounding_box(self):
        f = 0.0625
        f1 = (1 + self.meta * 2) / 16.0
        return AABB(f1, 0.0, f, 1.0 - f, 0.5 - f, 1.0 - f).offset(self.x, self.y, self.z)


class RedstoneRepeaterOff(BlockRedstoneRepeater):
    number = 93
    name = "Redstone Repeater ('off' state)"


class RedstoneRepeaterOn(BlockRedstoneRepeater):
    number = 94
    name = "Redstone Repeater ('on' state)"


class LockedChest(BlockCube):
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
                      AABB(0.8125, 0.0, 0.0, 1.0, 1.0, 1.0),
                      AABB(0.0, 0.0, 0.0, 0.1875, 1.0, 1.0)]
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def is_closed(self):
        return (self.meta & 4) == 0

    @property
    def grid_bounding_box(self):
        if self.is_closed:
            return self.bounding_box_closed.offset(self.x, self.y, self.z)
        else:
            return self.bounding_boxes[self.meta & 3].offset(self.x, self.y, self.z)


class HiddenSilverfish(BlockCube):
    number = 97
    name = "Hidden Silverfish"
    material = materials.clay


class StoneBrick(BlockCube):
    number = 98
    name = "Stone Brick"
    material = materials.rock


class HugeBrownMushroom(BlockCube):
    number = 99
    name = "Huge Brown Mushroom"
    material = materials.wood


class HugeRedMushroom(BlockCube):
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


class MelonBlock(BlockCube):
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


class FenceGate(BlockBiCollidable):
    number = 107
    name = "Fence Gate"
    material = materials.wood
    bounding_box_north_south = AABB(0.375, 0, 0, 0.625, 1.5, 1.0)
    bounding_box_east_west = AABB(0, 0, 0.375, 1.0, 1.5, 0.625)
    is_opaque_cube = False
    render_as_normal_block = False

    @property
    def is_collidable(self):
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
            return self.bounding_box_north_south.offset(self.x, self.y, self.z)
        else:
            return self.bounding_box_east_west.offset(self.x, self.y, self.z)


class BrickStairs(BlockStairs):
    number = 108
    name = "Brick Stairs"
    material = Bricks.material


class StoneBrickStairs(BlockStairs):
    number = 109
    name = "Stone Brick Stairs"
    material = StoneBrick.material


class Mycelium(BlockCube):
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


class NetherBrick(BlockCube):
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


class BrewingStand(BlockMultiBox):
    number = 117
    name = "Brewing Stand"
    material = materials.iron
    bounding_box_stand = AABB(0.4375, 0.0, 0.4375, 0.5625, 0.875, 0.5625)
    bounding_box_base = AABB(0.0, 0.0, 0.0, 1.0, 0.125, 1.0)
    render_as_normal_block = False
    is_opaque_cube = False

    def add_grid_bounding_boxes_to(self, out):
        out.append(self.bounding_box_stand.offset(self.x, self.y, self.z))
        out.append(self.bounding_box_base.offset(self.x, self.y, self.z))


class Cauldron(BlockMultiBox):
    number = 118
    name = "Cauldron"
    material = materials.iron
    render_as_normal_block = False
    is_opaque_cube = False
    c = 0.125
    bounding_boxes = [AABB(0.0, 0.0, 0.0, 1.0, 0.3125, 1.0),
                      AABB(0.0, 0.0, 0.0, c, 1.0, 1.0),
                      AABB(0.0, 0.0, 0.0, 1.0, 1.0, c),
                      AABB(1.0 - c, 0.0, 0.0, 1.0, 1.0, 1.0),
                      AABB(0.0, 0.0, 1.0 - c, 1.0, 1.0, 1.0)]

    def add_grid_bounding_boxes_to(self, out):
        for box in self.bounding_boxes:
            out.append(box.offset(self.x, self.y, self.z))


class EndPortal(BlockNonSolid):
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
    def eye_inserted(self):
        return (self.meta & 4) != 0

    def add_grid_bounding_boxes_to(self, out):
        out.append(self.bounding_box.offset(self.x, self.y, self.z))
        if self.eye_inserted:
            out.append(self.bounding_box_eye_inserted.offset(self.x, self.y, self.z))


class EndStone(BlockCube):
    number = 121
    name = "End Stone"
    material = materials.rock


class DragonEgg(BlockNonSolid):
    number = 122
    name = "Dragon Egg"
    material = materials.dragon_egg


class RedstoneLampInactive(BlockCube):
    number = 123
    name = "Redstone Lamp (inactive)"
    material = materials.redstone_light


class RedstoneLampActive(BlockCube):
    number = 124
    name = "Redstone Lamp (active)"
    material = materials.redstone_light


class WoodenDoubleSlab(BlockCube):
    number = 125
    name = "Wooden Double Slab"
    material = materials.wood


class WoodenSlab(BlockSingleSlab):
    number = 126
    name = "Wooden Slab"
    material = materials.wood


class CocoaPlant(Block):
    number = 127
    name = "Cocoa Plant"
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def get_direction(self):
        return self.meta & 3

    @property
    def grid_bounding_box(self):
        direction = self.get_direction
        v7 = (self.meta & 12) >> 2
        v8 = 4 + v7 * 2
        v9 = 5 + v7 * 2
        v10 = v8 / 2.0
        if direction == 0:
            gbb = AABB((8.0 - v10) / 16.0, (12.0 - v9) / 16.0, (15.0 - v8) / 16.0, (8.0 + v10) / 16.0, 0.75, 0.9375)
        elif direction == 1:
            gbb = AABB(0.0625, (12.0 - v9) / 16.0, (8.0 - v10) / 16.0, (1.0 + v8) / 16.0, 0.75, (8.0 + v10) / 16.0)
        elif direction == 2:
            gbb = AABB((8.0 - v10) / 16.0, (12.0 - v9) / 16.0, 0.0625, (8.0 + v10) / 16.0, 0.75, (1.0 + v8) / 16.0)
        elif direction == 3:
            gbb = AABB((15.0 - v8) / 16.0, (12.0 - v9) / 16.0, (8.0 - v10) / 16.0, 0.9375, 0.75, (8.0 + v10) / 16.0)
        else:
            raise Exception("undefined cocoa bounding box for %s" % direction)
        return gbb.offset(self.x, self.y, self.z)


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
    bounding_box = AABB(0.0625, 0.0, 0.0625, 0.9375, 0.875, 0.9375)


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


class BlockOfEmerald(BlockOfStorage):
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


class CommandBlock(BlockCube):
    number = 137
    name = "Command Block"
    material = materials.iron


class Beacon(BlockCube):
    number = 138
    name = "Beacon"
    material = materials.glass
    render_as_normal_block = False
    is_opaque_cube = False


class CobblestoneWall(BlockFence):
    number = 139
    name = "Cobblestone Wall"
    material = Cobblestone.material


class FlowerPot(Block):
    number = 140
    name = "Flower Pot"
    material = materials.circuits
    render_as_normal_block = False
    is_opaque_cube = False
    b1 = 0.375
    b2 = b1 / 2.0
    bounding_box = AABB(0.5 - b2, 0.0, 0.5 - b2, 0.5 + b2, b1, 0.5 + b2)


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


class Skull(Block):
    number = 144
    name = "Skull"
    material = materials.circuits
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def grid_bounding_box(self):
        att = self.meta & 7
        if att == 1:
            gbb = AABB(0.25, 0.0, 0.25, 0.75, 0.5, 0.75)
        elif att == 2:
            gbb = AABB(0.25, 0.25, 0.5, 0.75, 0.75, 1.0)
        elif att == 3:
            gbb = AABB(0.25, 0.25, 0.0, 0.75, 0.75, 0.5)
        elif att == 4:
            gbb = AABB(0.5, 0.25, 0.25, 1.0, 0.75, 0.75)
        elif att == 5:
            gbb = AABB(0.0, 0.25, 0.25, 0.5, 0.75, 0.75)
        return gbb.offset(self.x, self.y, self.z)


class Anvil(Block):
    number = 145
    name = "Anvil"
    material = materials.iron
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.75, 1.0)


block_map = [None for _ in xrange(256)]
selfmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
for _, cl in selfmembers:
    if issubclass(cl, Block) and hasattr(cl, 'number'):
        block_map[cl.number] = cl
