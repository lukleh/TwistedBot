
import StringIO
import array


import utils
import blocks
import config
import logbot
import fops
from axisbox import AABB


log = logbot.getlogger("GRID")


class Chunk(object):
    levels = config.WORLD_HEIGHT / 16

    def __init__(self, coords):
        self.coords = coords
        self.x = coords[0]
        self.z = coords[1]
        self.grid_x = self.x << 4
        self.grid_z = self.z << 4
        self.blocks = [None for _ in xrange(self.levels)]
        self.meta = [None for _ in xrange(self.levels)]
        self.block_light = []  # ignore block light
        self.sky_light = []  # ifnore sky light
        self.biome = [None for _ in xrange(config.CHUNK_SIDE_LEN * config.CHUNK_SIDE_LEN)]
        self.complete = False

    def set_meta(self, level, pos, meta):
        val = self.meta[level][pos / 2]
        if pos % 2 == 0:
            val = (val & 240) | meta
        else:
            val = (val & 15) | (meta << 4)
        self.meta[level][pos / 2] = val

    def get_meta(self, level, pos):
        if pos % 2 == 0:
            return self.meta[level][pos / 2] & 15
        else:
            return self.meta[level][pos / 2] >> 4

    def __str__(self):
        return "%s %s %s" % (str(self.coords), self.complete, [i if i is None else 1 for i in self.blocks])


class Grid(object):
    def __init__(self, dimension):
        self.dimension = dimension
        self.chunks = {}
        self.chunks_loaded = 0
        self.spawn_position = None

    def in_spawn_area(self, coords):
        return abs(coords[0] - self.spawn_position[0]) <= 16 or abs(coords[2] - self.spawn_position[2]) <= 16

    def get_chunk(self, coords):
        return self.chunks.get(coords, None)

    def make_block(self, x, y, z, block_type, meta):
        return blocks.block_map[block_type](self, x, y, z, meta)

    def get_block(self, x, y, z):
        if y > 255 or y < 0:
            return self.make_block(x, y, z, 0, 0)
        chunk_x = x >> 4
        chunk_z = z >> 4
        chunk = self.get_chunk((chunk_x, chunk_z))
        if chunk is None:
            return self.make_block(x, y, z, 0, 0)
        y_level = y >> 4
        block_types = chunk.blocks[y_level]
        if block_types is None:
            return self.make_block(x, y, z, 0, 0)
        cx = x & 15
        cy = y & 15
        cz = z & 15
        pos = self.chunk_array_position(cx, cy, cz)
        return self.make_block(x, y, z, block_types[pos], chunk.get_meta(y_level, pos))

    def chunk_updated(self, chunk_x, chunk_z):
        pass

    def new_chunk(self, x, z):
        crd = (x, z)
        chunk = Chunk(crd)
        self.chunks[crd] = chunk
        return chunk

    def _load_chunk(self, x, z, continuous, primary_bit, add_bit, data, light_data=True):
        if primary_bit == 0:
            try:
                del self.chunks[(x, z)]
                return
            except KeyError:
                pass
        self.chunks_loaded += 1
        chunk = self.get_chunk((x, z))
        if chunk is None:
            chunk = self.new_chunk(x, z)
        if continuous:
            chunk.complete = True
        else:
            log.msg("WARNING: received noncontinuous chunk, current complete state is %s" % chunk.complete)
        for i in xrange(chunk.levels):
            if primary_bit & (1 << i):
                data_str = data.read(4096)
                ndata = array.array('B', data_str)  # y, z, x
                chunk.blocks[i] = ndata
        for i in xrange(chunk.levels):
            if primary_bit & (1 << i):
                data_str = data.read(2048)
                ndata = array.array('B', data_str)
                chunk.meta[i] = ndata
        if light_data:
            for i in xrange(chunk.levels):
                if primary_bit & (1 << i):
                    data_str = data.read(2048)
                    #ndata = array.array('B', data_str)
            for i in xrange(chunk.levels):
                if primary_bit & (1 << i):
                    data_str = data.read(2048)
                    #ndata = array.array('B', data_str)
        # higher block id value will be used after Mojang adds them
        for i in xrange(chunk.levels):
            if add_bit >> i & 1:
                data_str = data.read(2048)
                ndata = array.array('B', data_str)
        if continuous:
            data_str = data.read(256)
            chunk.biome = array.array('b', data_str)

    def on_load_chunk(self, x, z, continuous, primary_bit, add_bit, data_array):
        self._load_chunk(x, z, continuous, primary_bit, add_bit, StringIO.StringIO(data_array))
        self.chunk_updated(x, z)

    def on_load_bulk_chunk(self, metas, data_array, light_data):
        data = StringIO.StringIO(data_array)
        for meta in metas:
            self._load_chunk(meta.x, meta.z, True, meta.primary_bitmap, meta.add_bitmap, data, light_data=light_data)
        for meta in metas:
            self.chunk_updated(meta.x, meta.z)

    def chunk_array_position(self, x, y, z):
        """ compute index from 3D to 1D """
        return y * 256 + z * 16 + x

    def change_block_to(self, x, y, z, block_type, meta):
        chunk_x = x >> 4
        chunk_z = z >> 4
        if (chunk_x, chunk_z) not in self.chunks:
            return None, None
        else:
            chunk = self.get_chunk((chunk_x, chunk_z))
        y_level = y >> 4
        if chunk.blocks[y_level] is None:
            return None, None
        current_block = self.get_block(x, y, z)
        if current_block is None:
            log.err("change_block block %s type %s meta %s is None" % ((x, y, z), block_type, meta))
            return None, None
        cx = x & 15
        cy = y & 15
        cz = z & 15
        pos = self.chunk_array_position(cx, cy, cz)
        chunk.blocks[y_level][pos] = block_type
        chunk.set_meta(y_level, pos, meta)
        new_block = self.make_block(x, y, z, block_type, meta)
        return current_block, new_block

    def on_block_change(self, x, y, z, btype, bmeta):
        _, _ = self.change_block_to(x, y, z, btype, bmeta)

    def on_multi_block_change(self, chunk_x, chunk_z, blocks):
        shift_x = chunk_x << 4
        shift_z = chunk_z << 4
        for block in blocks:
            _, _ = self.change_block_to(block.x + shift_x, block.y, block.z + shift_z, block.block_id, block.meta)

    def on_explosion(self, x, y, z, records):
        for rec in records:
            rx = x + rec.x
            ry = y + rec.y
            rz = z + rec.z
            gx = int(rx)
            gy = int(ry)
            gz = int(rz)
            ob, nb = self.change_block_to(gx, gy, gz, 0, 0)

    def chunk_complete_at(self, x, z):
        cx = x >> 4
        cz = z >> 4
        chunk = self.get_chunk((cx, cz))
        if chunk is None:
            return False
        else:
            return chunk.complete

    def blocks_in_aabb(self, bb):
        for x, y, z in bb.grid_area:
            blk = self.get_block(x, y, z)
            if blk is not None:
                yield blk

    def is_any_liquid(self, bb):
        for blk in self.blocks_in_aabb(bb):
            if blk.material.is_liquid:
                return True
        return False

    def aabb_collides(self, bb):
        for col_bb in self.collision_aabbs_in(bb):
            if col_bb.collides(bb):
                return True
        return False

    def collision_aabbs_in(self, bb):
        out = []
        for blk in self.blocks_in_aabb(bb.extend_to(0, -1, 0)):
            blk.add_grid_bounding_boxes_to(out)
        return out

    def avoid_aabbs_in(self, bb):
        out = []
        for blk in self.blocks_in_aabb(bb):  # lava, fire, web
            if blk.is_lava or blk.number == blocks.Fire.number or blk.number == blocks.Cobweb.number:
                out.append(AABB.from_block_cube(blk.x, blk.y, blk.z))
        return out

    def aabb_on_ladder(self, bb):
        blk = self.get_block(bb.gridpos_x, bb.gridpos_y, bb.gridpos_z)
        return blk.number == blocks.Ladders.number or blk.number == blocks.Vines.number

    def aabb_in_water(self, bb):
        #TODO return the bast water block instead of boolean
        for blk in self.blocks_in_aabb(bb.expand(-0.001, -0.4010000059604645, -0.001)):
            if blk.is_water:
                return True
        return False

    def standing_on_solidblock(self, bb):
        standing_on = None
        for col_bb in self.collision_aabbs_in(bb):
            if fops.eq(col_bb.max_y, bb.min_y):
                standing_on = self.get_block(col_bb.grid_x, col_bb.grid_y, col_bb.grid_z)
                if standing_on.x == bb.gridpos_x and standing_on.z == bb.gridpos_z:
                    break
        if standing_on is not None:
            if not fops.eq(bb.grid_y, standing_on.y):
                standing_on = self.get_block(standing_on.x, standing_on.y + 1, standing_on.z)
        return standing_on

    def standing_on_block(self, bb):
        standing_on = self.standing_on_solidblock(bb)
        if standing_on is None:
            if self.aabb_on_ladder(bb):
                standing_on = self.get_block(bb.gridpos_x, bb.gridpos_y, bb.gridpos_z)
        if standing_on is None:
            if self.aabb_in_water(bb):
                standing_on = self.get_block(bb.grid_x, bb.grid_y, bb.grid_z)
        return standing_on

    def aabb_in_chunks(self, bb):
        chunk_coords = set()
        for x, _, z in bb.grid_area:
            chunk_coords.add((x >> 4, z >> 4))
        return [self.get_chunk(coord) for coord in chunk_coords]

    def aabb_in_complete_chunks(self, bb):
        for chunk in self.aabb_in_chunks(bb):
            if chunk is None:
                return False
            elif chunk.complete is False:
                return False
        return True

    def aabb_eyelevel_inside_water(self, bb, eye_height=config.PLAYER_EYELEVEL):
        eye_y = bb.min_y + eye_height
        ey = utils.grid_shift(eye_y)
        blk = self.get_block(bb.gridpos_x, ey, bb.gridpos_z)
        if blk.is_water:
            wh = blk.height_percent - 0.11111111
            return eye_y < (ey + 1 - wh)
        else:
            return False
