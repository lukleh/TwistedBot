
import re

import logbot
import utils
import materials
import fops
import config
import block_details
from axisbox import AABB


log = logbot.getlogger("BLOCKS")

block_list = [None for _ in xrange(256)]
block_map = {}

wood_names = ["Oak", "Spruce", "Birch", "Jungle"]
stone_lab_names = ["Stone", "Sandstone", None, "Cobblestone", "Brick", "Stone Brick", "Nether Brick", "Quartz"]


class BlockMetaClass(type):
    def __new__(meta, name, bases, dct):
        cls = super(BlockMetaClass, meta).__new__(meta, name, bases, dct)

        def name_or_class(cls, name):
            try:
                subcls = globals()[name]
                return issubclass(cls, subcls)
            except KeyError:
                return cls.__name__ == name

        cls.is_cube = name_or_class(cls, 'BlockCube')
        cls.is_sign = name_or_class(cls, 'BlockSign')
        cls.is_water = name_or_class(cls, 'BlockWater')
        cls.is_lava = name_or_class(cls, 'BlockLava')
        cls.is_fluid = cls.is_water or cls.is_lava
        cls.is_stairs = name_or_class(cls, 'BlockStairs')
        cls.is_ladder = name_or_class(cls, 'Ladders')
        cls.is_vine = name_or_class(cls, 'Vines')
        cls.is_single_slab = name_or_class(cls, 'BlockSingleSlab')
        cls.is_burning = cls.is_lava or name_or_class(cls, 'Fire')
        if hasattr(cls, 'number'):
            if not hasattr(cls, 'name'):
                cls.name = " ".join(re.findall('[A-Z][^A-Z]*', cls.__name__))
            cls.name = cls.name.lower()
            cls.hardness = block_details.block_hardness.get(cls.number, 0.0)
            block_list[cls.number] = cls
            block_map[cls.name] = cls
        return cls


class Block(object):
    __metaclass__ = BlockMetaClass

    slipperiness = 0.6
    render_as_normal_block = True
    is_opaque_cube = True

    inventory_avoid = False
    has_common_type = True
    sub_name_override = False

    def __init__(self, grid, x, y, z, meta):
        self.grid = grid
        self.x = x
        self.y = y
        self.z = z
        self.meta = meta
        self.coords = utils.Vector(self.x, self.y, self.z)

    def __repr__(self):
        return "|%s %s %s|" % (self.coords, self.name, utils.meta2str(self.meta))

    def __eq__(self, other):
        return other is not None and self.coords == other.coords and self.meta == other.meta

    def __ne__(self, other):
        return not (self == other)

    @property
    def is_free(self):
        return not self.is_collidable and not isinstance(self, BlockFluid) and not self.number == Cobweb.number and not self.number == Fire.number

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

    def is_solid_block(self, block, ignore):
        return block.material.is_solid

    def on_entity_collided(self, ignore):
        pass

    @property
    def is_climbable(self):
        return False


class BlockSolid(Block):

    @property
    def is_collidable(self):
        return True

    @property
    def can_fall_through(self):
        return False

    @property
    def can_stand_in(self):
        return False

    @property
    def can_stand_on(self):
        return False


class BlockCube(BlockSolid):
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)

    @property
    def can_stand_on(self):
        return True


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

    @property
    def can_stand_on(self):
        return False

    @property
    def can_fall_through(self):
        return True


class BlockFluid(BlockNonSolid):
    inventory_avoid = True

    @classmethod
    def fluid_aabb(cls, x, y, z):
        return AABB(x, y + 0.4, z, x + 1, y + 0.6, z + 1)

    @property
    def is_climbable(self):
        return True

    @property
    def can_fall_through(self):
        return True


class BlockWater(BlockFluid):
    material = materials.water

    @property
    def can_stand_in(self):
        return True

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
        v = utils.Vector(0, 0, 0)
        this_efd = self.effective_flow_decay
        for i, j in utils.cross:
            blk = self.grid.get_block(self.x + i, self.y, self.z + j)
            efd = blk.effective_flow_decay
            if efd < 0:
                if not blk.material.blocks_movement:
                    blk = self.grid.get_block(self.x + i, self.y - 1, self.z + j)
                    efd = blk.effective_flow_decay
                    if efd >= 0:
                        va = efd - (this_efd - 8)
                        v = utils.Vector(i * va, 0, j * va)
            elif efd >= 0:
                va = efd - this_efd
                v = utils.Vector(i * va, 0, j * va)
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


class BlockRedstoneRepeater(BlockSolid):
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.125, 1.0)
    material = materials.circuits
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def can_stand_in(self):
        return True


class BlockMultiBox(BlockSolid):

    @property
    def grid_bounding_box(self):
        raise Exception('grid_bounding_box called from BlockMultiBox')


class BlockStairs(BlockMultiBox):
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box_half = AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
    bounding_box_up_half = AABB(0.0, 0.5, 0.0, 1.0, 1.0, 1.0)

    @property
    def can_stand_on(self):
        return True

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

    def check_aabbs(self):
        out = []
        self.add_grid_bounding_boxes_to(out)
        check = [0, 0, 0, 0]
        if len(out) == 3:
            bb = out[2]
            if fops.gt(bb.min_x, self.x):
                check[2] = -1
            elif fops.lt(bb.max_x, self.x + 1):
                check[2] = 1
            if fops.gt(bb.min_z, self.z):
                check[3] = -1
            elif fops.lt(bb.max_z, self.z + 1):
                check[3] = 1
        bb = out[1]
        if fops.gt(bb.min_x, self.x):
            check[0] = -1
        elif fops.lt(bb.max_x, self.x + 1):
            check[0] = 1
        if fops.gt(bb.min_z, self.z):
            check[1] = -1
        elif fops.lt(bb.max_z, self.z + 1):
            check[1] = 1
        if check[2] != 0 or check[3] != 0:
            if check[0] != 0:
                check[2] = check[0]
            if check[1] != 0:
                check[3] = check[1]
            yield AABB.from_block_coords(self.x + check[2] * config.PLAYER_RADIUS, self.y + 0.5, self.z + check[3] * config.PLAYER_RADIUS)
        else:
            if check[0] != 0:
                yield AABB.from_block_coords(self.x + check[0] * config.PLAYER_RADIUS, self.y + 0.5, self.z)
            if check[1] != 0:
                yield AABB.from_block_coords(self.x, self.y + 0.5, self.z + check[1] * config.PLAYER_RADIUS)


class BlockDoor(BlockSolid):
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_boxes = [AABB(0.0, 0.0, 0.0, 0.1875, 1.0, 1.0),
                      AABB(0.0, 0.0, 0.0, 1.0, 1.0, 0.1875),
                      AABB(0.8125, 0.0, 0.0, 1.0, 1.0, 1.0),
                      AABB(0.0, 0.0, 0.8125, 1.0, 1.0, 1.0)]
    top_part = None
    bottom_part = None

    @property
    def can_fall_through(self):
        return True

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


class BlockFence(BlockSolid):
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


class BlockSingleSlab(BlockSolid):
    bounding_box_lower = AABB(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
    bounding_box_higher = AABB(0.0, 0.5, 0.0, 1.0, 1.0, 1.0)
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def can_stand_in(self):
        return self.lower_part

    @property
    def can_stand_on(self):
        return not self.can_stand_in

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

    @property
    def can_stand_in(self):
        raise NotImplemented('can_stand_in')

    @property
    def can_fall_through(self):
        raise NotImplemented('can_fall_through')

    @property
    def can_stand_on(self):
        raise NotImplemented('can_stand_on')


class BlockSign(BlockNonSolid):
    material = materials.wood


class BlockChest(BlockSolid):
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box = AABB(0.0625, 0.0, 0.0625, 0.9375, 0.875, 0.9375)


class Air(BlockNonSolid):
    inventory_avoid = True
    number = 0
    material = materials.air


class Stone(BlockCube):
    number = 1
    material = materials.rock


class GrassBlock(BlockCube):
    number = 2
    material = materials.grass
    inventory_avoid = True


class Dirt(BlockCube):
    number = 3
    material = materials.ground


class Cobblestone(BlockCube):
    number = 4
    material = materials.rock


class WoodenPlanks(BlockCube):
    number = 5
    material = materials.wood
    sub_names = wood_names


class Saplings(BlockFlower):
    number = 6
    sub_names = wood_names


class Bedrock(BlockCube):
    number = 7
    material = materials.rock
    inventory_avoid = True


class FlowingWater(BlockWater):
    number = 8


class StillWater(BlockWater):
    number = 9


class FlowingLava(BlockLava):
    number = 10


class StillLava(BlockLava):
    number = 11


class Sand(BlockCube):
    number = 12
    material = materials.sand


class Gravel(BlockCube):
    number = 13
    material = materials.sand


class GoldOre(BlockOre):
    number = 14


class IronOre(BlockOre):
    number = 15


class CoalOre(BlockOre):
    number = 16
    inventory_avoid = True


class Wood(BlockCube):
    number = 17
    material = materials.wood
    sub_names = wood_names


class Leaves(BlockCube):
    number = 18
    material = materials.leaves
    is_opaque_cube = False
    sub_names = wood_names


class Sponge(BlockCube):
    number = 19
    material = materials.sponge
    inventory_avoid = True


class Glass(BlockCube):
    number = 20
    material = materials.glass
    render_as_normal_block = False
    is_opaque_cube = False


class LapisLazuliOre(BlockOre):
    number = 21
    inventory_avoid = True


class LapisLazuliBlock(BlockCube):
    number = 22
    material = materials.rock


class Dispenser(BlockCube):
    number = 23
    material = materials.rock


class Sandstone(BlockCube):
    number = 24
    material = materials.rock
    sub_names = ["", "Chiseled", "Smooth"]
    has_common_type = False


class NoteBlock(BlockCube):
    number = 25
    material = materials.wood


class Bed(BlockSolid):
    inventory_avoid = True
    number = 26
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.5625, 1.0)
    material = materials.cloth
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def can_stand_in(self):
        return True


class PoweredRail(BlockNonSolid):
    number = 27
    material = materials.circuits


class DetectorRail(BlockNonSolid):
    number = 28
    material = materials.circuits


class StickyPiston(BlockPiston):
    number = 29


class Cobweb(BlockNonSolid):
    number = 30
    material = materials.web
    inventory_avoid = True

    @property
    def can_fall_through(self):
        return False


class Grass(BlockFlower):
    number = 31
    material = materials.vine
    sub_names = ["Dead Shrub", "Tall Grass", "Fern"]
    sub_name_override = True
    has_common_type = False


class DeadBush(BlockFlower):
    number = 32
    material = materials.vine


class Piston(BlockPiston):
    number = 33


class PistonExtension(BlockMultiBox):
    number = 34
    material = materials.piston
    render_as_normal_block = False
    is_opaque_cube = False
    inventory_avoid = True

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
    material = materials.cloth
    sub_names = ['White', 'Orange', 'Magenta', 'Light Blue', 'Yellow', 'Lime', 'Pink', 'Gray', 'Light Gray', 'Cyan', 'Purple', 'Blue', 'Brown', 'Green', 'Red', 'Black']


class PistonMoving(BlockSolid):
    number = 36
    material = materials.piston
    render_as_normal_block = False
    is_opaque_cube = False
    inventory_avoid = True

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


class Rose(BlockFlower):
    number = 38


class BrownMushroom(BlockFlower):
    number = 39


class RedMushroom(BlockFlower):
    number = 40


class BlockOfGold(BlockOfStorage):
    number = 41
    material = materials.iron


class BlockOfIron(BlockOfStorage):
    number = 42
    material = materials.iron


class StoneDoubleSlab(BlockCube):
    number = 43
    material = materials.rock
    sub_names = stone_lab_names
    inventory_avoid = True


class StoneSlab(BlockSingleSlab):
    number = 44
    material = materials.rock
    name = "Slab"
    sub_names = stone_lab_names


class Bricks(BlockCube):
    number = 45
    material = materials.rock


class TNT(BlockCube):
    number = 46
    name = "TNT"
    material = materials.tnt
    inventory_avoid = True


class Bookshelf(BlockCube):
    number = 47
    material = materials.wood


class MossStone(BlockCube):
    number = 48
    material = materials.rock


class Obsidian(BlockCube):
    number = 49
    material = materials.rock


class Torch(BlockTorch):
    number = 50
    material = materials.circuits


class Fire(BlockNonSolid):
    number = 51
    material = materials.fire
    inventory_avoid = True


class MonsterSpawner(BlockCube):
    number = 52
    material = materials.rock
    is_opaque_cube = False
    inventory_avoid = True


class WoodenStairs(BlockStairs):
    number = 53
    material = WoodenPlanks.material


class Chest(BlockChest):
    number = 54
    material = materials.wood

    @property
    def can_stand_in(self):
        return True


class RedstoneWire(BlockNonSolid):
    inventory_avoid = True
    number = 55
    material = materials.circuits


class DiamondOre(BlockOre):
    number = 56
    inventory_avoid = True


class BlockOfDiamond(BlockOfStorage):
    number = 57
    material = materials.iron


class CraftingTable(BlockCube):
    number = 58
    material = materials.wood


class WheatCrops(BlockFlower):
    number = 59
    inventory_avoid = True


class Farmland(BlockCube):
    number = 60
    material = materials.ground
    render_as_normal_block = False
    is_opaque_cube = False
    inventory_avoid = True


class Furnace(BlockCube):
    number = 61
    material = materials.rock


class BurningFurnace(BlockCube):
    number = 62
    material = materials.rock
    inventory_avoid = True


class SignPost(BlockSign):
    inventory_avoid = True
    number = 63


class WoodenDoor(BlockDoor):
    inventory_avoid = True
    number = 64
    material = materials.wood


class Ladders(BlockSolid):
    number = 65
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

    @property
    def can_fall_through(self):
        return True

    @property
    def can_stand_in(self):
        return True

    @property
    def is_climbable(self):
        return True


class Rail(BlockNonSolid):
    number = 66
    material = materials.circuits


class CobblestoneStairs(BlockStairs):
    number = 67
    material = Cobblestone.material


class WallSign(BlockSign):
    number = 68
    inventory_avoid = True


class Lever(BlockNonSolid):
    number = 69
    material = materials.circuits


class StonePressurePlate(BlockNonSolid):
    number = 70
    material = materials.rock


class IronDoor(BlockDoor):
    inventory_avoid = True
    number = 71
    material = materials.iron


class WoodenPressurePlate(BlockNonSolid):
    number = 72
    material = materials.wood


class RedstoneOre(BlockOre):
    number = 73
    inventory_avoid = True


class GlowingRedstoneOre(BlockOre):
    number = 74
    inventory_avoid = True


class RedstoneTorchOffState(BlockTorch):
    number = 75
    material = materials.circuits
    inventory_avoid = True


class RedstoneTorchOnState(BlockTorch):
    number = 76
    material = materials.circuits
    name = "Redstone Torch"


class StoneButton(BlockNonSolid):
    number = 77
    material = materials.circuits


class Snow(BlockBiCollidable):
    number = 78
    material = materials.snow
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box = None
    inventory_avoid = True

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

    @property
    def can_stand_in(self):
        return self.is_collidable

    @property
    def can_fall_through(self):
        return not self.is_collidable

    @property
    def can_stand_on(self):
        return False


class Ice(BlockCube):
    number = 79
    slipperiness = 0.98
    material = materials.ice
    is_opaque_cube = False
    inventory_avoid = True


class SnowBlock(BlockCube):
    number = 80
    material = materials.crafted_snow


class Cactus(BlockSolid):
    number = 81
    material = materials.cactus
    render_as_normal_block = False
    is_opaque_cube = False
    bounding_box = AABB(0.0625, 0.0, 0.0625, 1.0 - 0.0625, 1.0 - 0.0625, 1.0 - 0.0625)


class ClayBlock(BlockCube):
    number = 82
    material = materials.clay


class SugarCane(BlockNonSolid):
    inventory_avoid = True
    number = 83
    material = materials.plants


class Jukebox(BlockCube):
    number = 84
    material = materials.wood


class Fence(BlockFence):
    number = 85
    material = materials.wood


class Pumpkin(BlockCube):
    number = 86
    material = materials.pumpkin


class Netherrack(BlockCube):
    number = 87
    material = materials.rock


class SoulSand(BlockSolid):
    number = 88
    material = materials.sand
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 1.0 - 0.125, 1.0)

    def on_entity_collided(self, b_obj):
        b_obj.velocities.x *= 0.4
        b_obj.velocities.z *= 0.4

    @property
    def can_stand_in(self):
        return True


class GlowstoneBlock(BlockCube):
    number = 89
    material = materials.glass


class NetherPortal(BlockNonSolid):
    number = 90
    material = materials.portal
    inventory_avoid = True


class JackOLantern(BlockCube):
    number = 91
    name = "Jack 'o' Lantern"
    material = materials.pumpkin


class Cake(BlockSolid):
    inventory_avoid = True
    number = 92
    material = materials.cake
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def grid_bounding_box(self):
        f = 0.0625
        f1 = (1 + self.meta * 2) / 16.0
        return AABB(f1, 0.0, f, 1.0 - f, 0.5 - f, 1.0 - f).offset(self.x, self.y, self.z)


class RedstoneRepeaterOff(BlockRedstoneRepeater):
    inventory_avoid = True
    number = 93
    name = "Redstone Repeater (inactive)"


class RedstoneRepeaterOn(BlockRedstoneRepeater):
    inventory_avoid = True
    number = 94
    name = "Redstone Repeater (active)"


class LockedChest(BlockCube):
    number = 95
    material = materials.wood
    inventory_avoid = True


class Trapdoor(BlockSolid):
    number = 96
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

    @property
    def can_stand_in(self):
        return self.is_closed

    @property
    def can_fall_through(self):
        return not self.can_stand_in


class HiddenSilverfish(BlockCube):
    number = 97
    material = materials.clay
    sub_names = ["Stone", "Cobblestone", "Stone Brick"]
    inventory_avoid = True


class StoneBrick(BlockCube):
    number = 98
    material = materials.rock
    sub_names = ["", "Mossy", "Cracked", "Chiseled"]
    has_common_type = False


class HugeBrownMushroom(BlockCube):
    number = 99
    material = materials.wood
    inventory_avoid = True


class HugeRedMushroom(BlockCube):
    number = 100
    material = materials.wood
    inventory_avoid = True


class IronBars(BlockPane):
    number = 101
    material = materials.iron


class GlassPane(BlockPane):
    number = 102
    material = materials.glass


class MelonBlock(BlockCube):
    number = 103
    material = materials.pumpkin


class PumpkinStem(BlockFlower):
    number = 104
    inventory_avoid = True


class MelonStem(BlockFlower):
    number = 105
    inventory_avoid = True


class Vines(BlockNonSolid):
    number = 106
    material = materials.vine

    @property
    def can_stand_in(self):
        return True

    @property
    def is_climbable(self):
        return self.grid.get_block(self.x - 1, self.y, self.z).is_cube or \
            self.grid.get_block(self.x, self.y, self.z - 1).is_cube or \
            self.grid.get_block(self.x + 1, self.y, self.z).is_cube or \
            self.grid.get_block(self.x, self.y, self.z + 1).is_cube


class FenceGate(BlockBiCollidable):
    number = 107
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
    def can_fall_through(self):
        return not self.is_collidable

    @property
    def can_stand_in(self):
        return False

    @property
    def can_stand_on(self):
        return False

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
    material = Bricks.material


class StoneBrickStairs(BlockStairs):
    number = 109
    material = StoneBrick.material


class Mycelium(BlockCube):
    number = 110
    material = materials.grass
    inventory_avoid = True


class LilyPad(BlockSolid):
    number = 111
    material = materials.plants
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.015625, 1.0)
    is_opaque_cube = False
    render_as_normal_block = False

    @property
    def can_stand_in(self):
        return True


class NetherBricks(BlockCube):
    number = 112
    material = materials.rock


class NetherBrickFence(BlockFence):
    number = 113
    material = NetherBricks.material


class NetherBrickStairs(BlockStairs):
    number = 114
    material = NetherBricks.material


class NetherWart(BlockFlower):
    inventory_avoid = True
    number = 115


class EnchantmentTable(BlockSolid):
    number = 116
    material = materials.rock
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.75, 1.0)
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def can_stand_in(self):
        return True


class BrewingStand(BlockMultiBox):
    inventory_avoid = True
    number = 117
    material = materials.iron
    bounding_box_stand = AABB(0.4375, 0.0, 0.4375, 0.5625, 0.875, 0.5625)
    bounding_box_base = AABB(0.0, 0.0, 0.0, 1.0, 0.125, 1.0)
    render_as_normal_block = False
    is_opaque_cube = False

    def add_grid_bounding_boxes_to(self, out):
        out.append(self.bounding_box_stand.offset(self.x, self.y, self.z))
        out.append(self.bounding_box_base.offset(self.x, self.y, self.z))


class Cauldron(BlockMultiBox):
    inventory_avoid = True
    number = 118
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
    material = materials.portal
    inventory_avoid = True


class EndPortalFrame(BlockMultiBox):
    number = 120
    material = materials.glass
    bounding_box = AABB(0.0, 0.0, 0.0, 1.0, 0.8125, 1.0)
    bounding_box_eye_inserted = AABB(0.3125, 0.8125, 0.3125, 0.6875, 1.0, 0.6875)
    is_opaque_cube = False
    inventory_avoid = True

    @property
    def eye_inserted(self):
        return (self.meta & 4) != 0

    def add_grid_bounding_boxes_to(self, out):
        out.append(self.bounding_box.offset(self.x, self.y, self.z))
        if self.eye_inserted:
            out.append(self.bounding_box_eye_inserted.offset(self.x, self.y, self.z))


class EndStone(BlockCube):
    number = 121
    material = materials.rock


class DragonEgg(BlockNonSolid):
    number = 122
    material = materials.dragon_egg


class RedstoneLampInactive(BlockCube):
    number = 123
    name = "Redstone Lamp"
    material = materials.redstone_light


class RedstoneLampActive(BlockCube):
    number = 124
    name = "Redstone Lamp (active)"
    material = materials.redstone_light
    inventory_avoid = True


class WoodenDoubleSlab(BlockCube):
    number = 125
    material = materials.wood
    sub_names = wood_names
    inventory_avoid = True


class WoodenSlab(BlockSingleSlab):
    number = 126
    material = materials.wood
    sub_names = wood_names


class CocoaPod(BlockSolid):
    inventory_avoid = True
    number = 127
    material = materials.plants
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
    material = Sandstone.material


class EmeraldOre(BlockOre):
    number = 129
    inventory_avoid = True


class EnderChest(BlockChest):
    number = 130
    material = materials.rock

    @property
    def can_stand_in(self):
        return True


class TripwireHook(BlockNonSolid):
    number = 131
    material = materials.circuits
    render_as_normal_block = False


class Tripwire(BlockNonSolid):
    inventory_avoid = True
    number = 132
    material = materials.circuits
    render_as_normal_block = False


class BlockOfEmerald(BlockOfStorage):
    number = 133
    material = materials.iron


class SpruceWoodStairs(BlockStairs):
    number = 134
    material = WoodenPlanks.material


class BirchWoodStairs(BlockStairs):
    number = 135
    material = WoodenPlanks.material


class JungleWoodStairs(BlockStairs):
    number = 136
    material = WoodenPlanks.material


class CommandBlock(BlockCube):
    number = 137
    material = materials.iron
    inventory_avoid = True


class Beacon(BlockCube):
    number = 138
    material = materials.glass
    render_as_normal_block = False
    is_opaque_cube = False


class CobblestoneWall(BlockFence):
    number = 139
    material = Cobblestone.material
    sub_names = ["", "Mossy"]
    has_common_type = False


class FlowerPot(BlockSolid):
    inventory_avoid = True
    number = 140
    material = materials.circuits
    render_as_normal_block = False
    is_opaque_cube = False
    b1 = 0.375
    b2 = b1 / 2.0
    bounding_box = AABB(0.5 - b2, 0.0, 0.5 - b2, 0.5 + b2, b1, 0.5 + b2)


class Carrots(BlockFlower):
    number = 141
    inventory_avoid = True


class Potatoes(BlockFlower):
    number = 142
    inventory_avoid = True


class WoodenButton(BlockNonSolid):
    number = 143
    material = materials.circuits


class Skull(BlockSolid):
    inventory_avoid = True
    number = 144
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


class Anvil(BlockSolid):
    number = 145
    material = materials.anvil
    render_as_normal_block = False
    is_opaque_cube = False

    @property
    def grid_bounding_box(self):
        orient = self.meta & 3
        if orient != 3 or orient != 1:
            gbb = AABB(0.125, 0.0, 0.0, 0.875, 1.0, 1.0)
        else:
            gbb = AABB(0.0, 0.0, 0.125, 1.0, 1.0, 0.875)
        return gbb.offset(self.x, self.y, self.z)


class TrappedChest(BlockChest):
    number = 146
    material = materials.wood


class WeightedPressurePlateLight(BlockSolid):
    number = 147
    material = materials.wood
    name = "Weighted Pressure Plate (Light)"


class WeightedPressurePlateHeavy(BlockSolid):
    number = 148
    material = materials.wood
    name = "Weighted Pressure Plate (Heavy)"


class RedstoneComparatorOffState(BlockSolid):
    number = 149
    material = materials.wood
    name = "Redstone Comparator (inactive)"
    inventory_avoid = True


class RedstoneComparatorOnState(BlockSolid):
    number = 150
    material = materials.wood
    name = "Redstone Comparator (active)"
    inventory_avoid = True


class DaylightSensor(BlockSolid):
    number = 151
    material = materials.wood


class BlockOfRedstone(BlockCube):
    number = 152
    material = materials.wood


class NetherQuartzOre(BlockOre):
    number = 153
    material = materials.wood


class Hopper(BlockCube):
    number = 154
    material = materials.wood


class BlockOfQuartz(BlockCube):
    number = 155
    material = materials.wood


class QuartzStairs(BlockStairs):
    number = 156
    material = materials.wood


class ActivatorRails(BlockNonSolid):
    number = 157
    material = materials.wood


class Dropper(BlockCube):
    number = 158
    material = materials.wood


log.msg("registered %d blocks" % len(block_map))
