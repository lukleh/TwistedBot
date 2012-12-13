
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

    def _load_chunk(self, x, z, continuous, primary_bit, add_bit, data_array):
        if primary_bit == 0:
            log.msg("Received chunk erase packet for %s, %s" % (x, z))
            if (x, z) in self.chunks:
                del self.chunks[(x, z)]
            return
        self.chunks_loaded += 1
        chunk = self.get_chunk((x, z))
        if chunk is None:
            chunk = self.new_chunk(x, z)
        if continuous:
            chunk.complete = True
        else:
            log.msg("WARNING: received noncontinuous chunk, current complete state is %s" % chunk.complete)
        data = StringIO.StringIO(data_array)
        data_count = 0
        for i in xrange(chunk.levels):
            if primary_bit & 1 << i:
                data_str = data.read(4096)
                data_count += 4096
                ndata = array.array('B', data_str)  # y, z, x
                chunk.blocks[i] = ndata
        for h in xrange(3):
            for i in xrange(chunk.levels):
                if primary_bit & 1 << i:
                    data_str = data.read(2048)
                    data_count += 2048
                    ndata = array.array('B', data_str)
                    if h == 0:
                        chunk.meta[i] = ndata
                    # for now ignore block light and sky light
                    elif h == 1:
                        pass
                    else:
                        pass
        # higher block id value will be used after Mojang adds them
        for i in xrange(chunk.levels):
            if add_bit >> i & 1:
                data_str = data.read(2048)
                data_count += 2048
                ndata = array.array('B', data_str)
        if continuous:
            data_str = data.read(256)
            data_count += 256
        chunk.biome = array.array('b', data_str)

    def on_load_chunk(self, x, z, continuous, primary_bit, add_bit, data_array):
        self._load_chunk(x, z, continuous, primary_bit, add_bit, data_array)
        self.chunk_updated(x, z)

    def on_load_bulk_chunk(self, metas, data_array):
        data_start = 0
        data_end = 0
        for meta in metas:
            for i in xrange(Chunk.levels):
                if meta.primary_bitmap & 1 << i:
                    data_end += 4096 + 4096 + 2048
            data_end += 256
            self._load_chunk(meta.x, meta.z, True, meta.primary_bitmap, meta.add_bitmap, data_array[data_start:data_end])
            data_start = data_end
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
        out = []
        for x, y, z in bb.grid_area:
            blk = self.get_block(x, y, z)
            if blk is not None:
                out.append(blk)
        return out

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

    def passing_blocks_between(self, bb1, bb2):
        out = []
        ubb = bb1.union(bb2)
        blcks = self.blocks_in_aabb(ubb)
        dvect = bb1.vector_to(bb2)
        for blk in blcks:
            bb = AABB.from_block_cube(blk.coords.x, blk.coords.y, blk.coords.z)
            col, _ = bb1.sweep_collision(bb, dvect)
            if col:
                out.append(blk)
        return out

    def min_collision_between(self, bb1, bb2, horizontal=False, max_height=False):
        ubb = bb1.extend_to(dy=-1).union(bb2.extend_to(dy=-1))
        blcks = self.blocks_in_aabb(ubb)
        dvect = bb1.vector_to(bb2)
        if horizontal:
            dvect.y = 0
        col_rel_d = 1.1
        col_bb = None
        for blk in blcks:
            col, rel_d, bb = blk.sweep_collision(bb1, dvect, max_height=max_height)
            if col and fops.eq(col_rel_d, rel_d):
                if max_height:
                    if fops.lt(col_bb.max_y, bb.max_y):
                        col_bb = bb
            if col and fops.lt(rel_d, col_rel_d):
                col_rel_d = rel_d
                col_bb = bb
        if col_bb is not None:
            return col_rel_d * dvect.size, col_bb
        else:
            return None, None

    def collision_between(self, bb1, bb2, debug=False):
        ubb = bb1.extend_to(dy=-1).union(bb2.extend_to(dy=-1))
        blcks = self.blocks_in_aabb(ubb)
        dvect = bb1.vector_to(bb2)
        for blk in blcks:
            col, _, _ = blk.sweep_collision(bb1, dvect, debug=debug)
            if col:
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
        blk = self.get_block(bb.grid_x, bb.grid_y, bb.grid_z)
        return blk.number == blocks.Ladders.number or blk.number == blocks.Vines.number

    def aabb_in_water(self, bb):
        for blk in self.blocks_in_aabb(bb.expand(-0.001, -0.4010000059604645, -0.001)):
            if blk.is_water:
                return True
        return False

    def standing_on_solid(self, bb):
        for col_bb in self.collision_aabbs_in(bb):
            if fops.eq(col_bb.max_y, bb.min_y):
                return True
        return False

    def standing_on_solidblock(self, bb):
        standing_on = None
        for col_bb in self.collision_aabbs_in(bb):
            if fops.eq(col_bb.max_y, bb.min_y):
                standing_on = self.get_block(col_bb.grid_x, col_bb.grid_y, col_bb.grid_z)
                if standing_on.x == bb.grid_x and standing_on.z == bb.grid_z:
                    break
        return standing_on

    def standing_on_block(self, bb):
        standing_on = self.standing_on_solidblock(bb)
        if standing_on is None:
            if self.aabb_on_ladder(bb):
                standing_on = self.get_block(bb.grid_x, bb.grid_y, bb.grid_z)
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
        blk = self.get_block(bb.grid_x, ey, bb.grid_z)
        if blk.is_water:
            wh = blk.height_percent - 0.11111111
            return eye_y < (ey + 1 - wh)
        else:
            return False
