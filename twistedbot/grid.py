
import StringIO
import array


import packets
import tools
import blocks
import config
import logbot
from navigationmesh import NavigationMesh
from chunk import Chunk
		

log = logbot.getlogger("GRID")

class Chunk(object):
	levels = config.WORLD_HEIGHT / 16
	def __init__(self, coords):
		self.coords = coords
		self.x 		= coords[0]
		self.z 		= coords[1]
		self.grid_x = self.x << 4
		self.grid_z = self.z << 4
		self.blocks 		= [None for _ in xrange(self.levels)]
		self.meta   		= [None for _ in xrange(self.levels)]
		self.block_light  	= [] #[None for _ in xrange(self.levels)]
		self.sky_light  	= [] #[None for _ in xrange(self.levels)]
		self.biome  		= [None for _ in xrange(config.CHUNK_SIDE_LEN * config.CHUNK_SIDE_LEN)]
		self.complete 		= False

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
			log.err("chunk %s not initialized" % str(coords))
			return None
			
	def get_block(self, x, y, z):
		if y > 255:
			return blocks.Air(x, y, z)
		elif y < 0:
			return blocks.Air(x, y, z)
		chunk_x = x >> 4
		chunk_z = z >> 4
		chunk = self.get_chunk((chunk_x, chunk_z))
		if chunk is None:
			return blocks.Air(x, y, z)
		y_level = y >> 4
		block_types = chunk.blocks[y_level]
		if block_types is None:
			log.err("level %s not in chunk %s" % (y_level, str(chunk.coords)))
			return blocks.Air(x, y, z)
		cx = x & 15
		cy = y & 15
		cz = z & 15
		pos = self.chunk_array_position(cx, cy, cz)
		try:
			return blocks.block_map[block_types[pos]](x, y, z, chunk.meta[y_level][pos])
		except:
			raise

	def chunk_updated(self, chunk_x, chunk_z):
		for i, j in tools.adjacency:
			c = (chunk_x + i, chunk_z + j)
			if c in self.chunks:
				self.navmesh.incomplete_on_chunk_border(c, (chunk_x, chunk_z))

	def half_bytes_from_string(self, bstr):
		for s in bstr:
			bv = ord(s)
			yield bv & 15
			yield bv >> 4

	def load_chunk(self, x, z, continuous, primary_bit, add_bit, data_array, update_after=True):
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
				ndata = array.array('b', data_str)  #y, z, x 
				chunk.blocks[i] = ndata
		for h in xrange(3):
			for i in xrange(chunk.levels):
				if primary_bit & 1 << i:
					data_str = data.read(2048)
					data_count += 2048
					if h == 0:
						ndata = array.array('b', self.half_bytes_from_string(data_str))
						chunk.meta[i] = ndata
					# for now ignore block light and sky light
					#elif h == 1:
					#	chunk.block_light[i] = ndata
					#else:
					#	chumk.sky_light[i] = ndata
		# higher block id value will be used after Mojang adds them
		for i in xrange(chunk.levels):
			if add_bit >> i & 1:
				data_str = data.read(2048)
				data_count += 2048
				#ndata = array.array('b', half_bytes_from_string(data_str))
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
			log.err("change_block chunk %s block %s type %s meta %s is None" % (chunk, (x, y, z), block_type, meta))
			return None, None
		if current_block.is_sign and not current_block.same_type(block_type):
			self.navmesh.sign_waypoints.remove(current_block.coords)
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
		new_block = blocks.block_map[block_type](x, y, z, meta)
		return current_block, new_block

	def block_change(self, x, y, z, btype, bmeta):
		ob, nb = self.change_block_to(x, y, z, btype, bmeta)
		self.navmesh.block_change(ob, nb)

	def multi_block_change(self, chunk_x, chunk_z, blocks):
		shift_x = chunk_x << 4
		shift_z = chunk_z << 4
		changed = []
		for block in blocks:
			ob, nb = self.change_block_to(block.x + shift_x, block.y, block.z + shift_z, block.block_id, block.meta)
			changed.append((ob, nb))
		for ob, nb in changed:
			self.navmesh.block_change(ob, nb)

	def sign(self, x, y, z, line1, line2, line3, line4):
		try:
			value = float(line2)
		except ValueError:
			value = None
		if line1.strip().lower() == "waypoint" and value is not None:
			self.navmesh.sign_waypoints.new((x, y, z), value, line3)
