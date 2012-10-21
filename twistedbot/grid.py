
import StringIO
import array


import tools
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
        self.biome = [None for _ in xrange(
            config.CHUNK_SIDE_LEN * config.CHUNK_SIDE_LEN)]
        self.complete = False

    def fill_level(self, level):
        self.blocks[level] = array.array('b', [0 for _ in xrange(4096)])
        self.meta[level] = array.array('b', [0 for _ in xrange(4096)])

    def __str__(self):
        return "%s %s %s" % (str(self.coords), self.complete, [i if i is None else 1 for i in self.blocks])


class Grid(object):
    def __init__(self, world):
        self.world = world
        self.chunks = {}
        self.chunks_loaded = 0
        self.spawn_position = None
        self.can_stand_memory = tools.TreeMemory()
        self.can_stand_memory2 = tools.TreeMemory()

    def in_spawn_area(self, coords):
        return abs(coords[0] - self.spawn_position[0]) <= 16 or abs(coords[2] - self.spawn_position[2]) <= 16

    def get_chunk(self, coords, auto_create=False):
        if coords in self.chunks:
            return self.chunks[coords]
        elif auto_create:
            chunk = Chunk(coords)
            self.chunks[coords] = chunk
            return chunk
        else:
            #log.err("chunk %s not initialized" % str(coords))
            return None

    def get_block(self, x, y, z):
        if y > 255 or y < 0:
            #return None
            return blocks.Air(self, x, y, z)
        chunk_x = x >> 4
        chunk_z = z >> 4
        chunk = self.get_chunk((chunk_x, chunk_z))
        if chunk is None:
            return blocks.Air(self, x, y, z)
        y_level = y >> 4
        block_types = chunk.blocks[y_level]
        if block_types is None:
            #log.err("level %s not in chunk %s" % (y_level, str(chunk.coords)))
            return blocks.Air(self, x, y, z)
        cx = x & 15
        cy = y & 15
        cz = z & 15
        pos = self.chunk_array_position(cx, cy, cz)
        try:
            return blocks.block_map[block_types[pos]](self, x, y, z, chunk.meta[y_level][pos])
        except:
            log.err("get block pos %s y_level %s block_types array length %d meta array length %d " % (pos, y_level, len(block_types), len(chunk.meta[y_level])))
            raise

    def chunk_updated(self, chunk_x, chunk_z):
        for i, j in tools.adjacency:
            c = (chunk_x + i, chunk_z + j)
            if c in self.chunks:
                self.navgrid.incomplete_on_chunk_border(c, (chunk_x, chunk_z))

    def half_bytes_from_string(self, bstr):
        for s in bstr:
            bv = ord(s)
            yield bv & 15
            yield bv >> 4

    def load_chunk(self, x, z, continuous, primary_bit, add_bit, data_array, update_after=True):
        if primary_bit == 0:
            #log.msg("Received erase packet for %s, %s" % (x, z))
            return  # TODO actually remove this chunk....
        self.chunks_loaded += 1
        if (x, z) not in self.chunks:
            chunk = Chunk((x, z))
            self.chunks[(x, z)] = chunk
        else:
            chunk = self.get_chunk((x, z))
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
                    ndata = array.array(
                        'B', self.half_bytes_from_string(data_str))
                    if h == 0:
                        chunk.meta[i] = ndata
                    # for now ignore block light and sky light
                    #elif h == 1:
                    #    chunk.block_light[i] = ndata
                    #else:
                    #    chumk.sky_light[i] = ndata
        # higher block id value will be used after Mojang adds them
        for i in xrange(chunk.levels):
            if add_bit >> i & 1:
                data_str = data.read(2048)
                data_count += 2048
                ndata = array.array('B', self.half_bytes_from_string(data_str))
                log.msg("Add data %s" % ndata)
        if continuous:
            data_str = data.read(256)
            data_count += 256
        chunk.biome = array.array('b', data_str)
        if update_after:
            self.chunk_updated(x, z)

    def load_bulk_chunk(self, metas, data_array):
        data_start = 0
        data_end = 0
        for meta in metas:
            for i in xrange(Chunk.levels):
                if meta.primary_bitmap & 1 << i:
                    data_end += 4096 + 4096 + 2048
            data_end += 256
            self.load_chunk(meta.x, meta.z, True, meta.primary_bitmap, meta.add_bitmap, data_array[data_start:data_end], update_after=False)
            data_start = data_end
        for meta in metas:
            self.chunk_updated(meta.x, meta.z)

    def chunk_array_position(self, x, y, z):
        """ compute index from 3D to 1D """
        return y * 256 + z * 16 + x

    def change_block_to(self, x, y, z, block_type, meta):
        current_block = self.get_block(x, y, z)
        if current_block is None:
            log.err("change_block block %s type %s meta %s is None" %
                    ((x, y, z), block_type, meta))
            return None, None
        if current_block.is_sign and not current_block.number == block_type:
            self.navgrid.sign_waypoints.remove(current_block.coords)
        cx = x & 15
        y_level = current_block.y >> 4
        cy = y & 15
        cz = z & 15
        pos = self.chunk_array_position(cx, cy, cz)
        chunk_x = x >> 4
        chunk_z = z >> 4
        if (chunk_x, chunk_z) not in self.chunks:
            chunk = Chunk((chunk_x, chunk_z))
            self.chunks[(chunk_x, chunk_z)] = chunk
        else:
            chunk = self.get_chunk((chunk_x, chunk_z))
        if chunk.blocks[y_level] is None:
            chunk.fill_level(y_level)
        chunk.blocks[y_level][pos] = block_type
        chunk.meta[y_level][pos] = meta
        new_block = self.get_block(x, y, z)
        return current_block, new_block

    def block_change(self, x, y, z, btype, bmeta):
        ob, nb = self.change_block_to(x, y, z, btype, bmeta)
        self.navgrid.block_change(ob, nb)

    def multi_block_change(self, chunk_x, chunk_z, blocks):
        shift_x = chunk_x << 4
        shift_z = chunk_z << 4
        changed = []
        for block in blocks:
            ob, nb = self.change_block_to(block.x + shift_x, block.y, block.z + shift_z, block.block_id, block.meta)
            changed.append((ob, nb))
        for ob, nb in changed:
            self.navgrid.block_change(ob, nb)

    def sign(self, x, y, z, line1, line2, line3, line4):
        sign = tools.Sign((x, y, z), line1, line2, line3, line4)
        if sign.is_waypoint:
            self.navgrid.sign_waypoints.new(sign)

    def explosion(self, x, y, z, records):
        for rec in records:
            rx = x + rec.x
            ry = y + rec.y
            rz = z + rec.z
            gx = int(rx)
            gy = int(ry)
            gz = int(rz)
            self.block_change(gx, gy, gz, 0, 0)

    def chunk_complete_at(self, crd):
        chunk = self.get_chunk(crd)
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

    def is_any_liquid(self, bb):  # mcp has --val is val < 0
        minus_one_x, minus_one_y, minus_one_z = (-1 if bb.min_x < 0 else 0, -1 if bb.min_y < 0 else 0, -1 if bb.min_z < 0 else 0)
        for blk in self.blocks_in_aabb(AABB(bb.min_x + minus_one_x,
                                            bb.min_y + minus_one_y,
                                            bb.min_z + minus_one_z,
                                            bb.max_x,
                                            bb.max_y,
                                            bb.max_z)):
            if blk.material.is_liquid:
                return True
        return False

    def aabb_collides(self, bb):
        ebb = bb.extend_to(dy=-1)
        for block in self.blocks_in_aabb(ebb):
            if block.collides_with(bb):
                return True
        return False

    def passing_blocks_between(self, bb1, bb2):
        out = []
        ubb = bb1.union(bb2)
        blcks = self.blocks_in_aabb(ubb)
        dvect = bb1.vector_to(bb2)
        for blk in blcks:
            bb = AABB.from_block_cube(blk.coords)
            col, _ = bb1.sweep_collision(bb, dvect)
            if col:
                out.append(blk)
        return out

    def min_collision_between(self, bb1, bb2, horizontal=False, max_height=False):
        ubb = bb1.extend_to(dy=-1).union(bb2.extend_to(dy=-1))
        blcks = self.blocks_in_aabb(ubb)
        dvect = bb1.vector_to(bb2)
        if horizontal:
            dvect = (dvect[0], 0, dvect[2])
        col_rel_d = 1.1
        col_bb = None
        for blk in blcks:
            col, rel_d, bb = blk.sweep_collision(
                bb1, dvect, max_height=max_height)
            if col and fops.eq(col_rel_d, rel_d):
                if max_height:
                    if fops.lt(col_bb.max_y, bb.max_y):
                        col_bb = bb
            if col and fops.lt(rel_d, col_rel_d):
                col_rel_d = rel_d
                col_bb = bb
        if col_bb is not None:
            return col_rel_d * tools.vector_size(dvect), col_bb
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

    def aabbs_in(self, bb1):
        out = []
        blcks = self.blocks_in_aabb(bb1.extend_to(0, -1, 0))
        for blk in blcks:
            blk.add_grid_bounding_boxes_to(out)
        return out

    def aabb_on_ladder(self, bb):
        blk = self.get_block(bb.grid_x, bb.grid_y, bb.grid_z)
        return blk.number == blocks.Ladders.number or blk.number == blocks.Vines.number

    def aabb_in_water(self, bb):
        for blk in self.blocks_in_aabb(bb):
            if blk.is_water:
                return True
        return False

    def standing_on_solidblock(self, bb):
        standing_on = None
        blocks = self.blocks_in_aabb(bb.extend_to(dy=-1))
        dvect = (0, -1, 0)
        for blk in blocks:
            col, rel_d, _ = blk.sweep_collision(bb, dvect)
            if col and fops.eq(rel_d, 0):
                standing_on = blk
                if standing_on.x == bb.grid_x and standing_on.z == bb.grid_z:
                    break
        if standing_on is None:
            if self.aabb_on_ladder(bb):
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

    def check_sign(self, crd):
        sblk = self.get_block(crd[0], crd[1], crd[2])
        if not sblk.is_sign:
            self.navgrid.sign_waypoints.remove(crd)
            return False
        return True

    def aabb_eyelevel_inside_water(self, bb, eye_height=config.PLAYER_EYELEVEL):
        eye_y = bb.min_y + eye_height
        ey = tools.grid_shift(eye_y)
        blk = self.get_block(bb.grid_x, ey, bb.grid_z)
        if blk.is_water:
            wh = blk.height_percent - 0.11111111
            surface = ey + 1 - wh
            return eye_y < surface
        else:
            return False
