
import math

import config
import fops
import tools


class AABB(object):
	def __init__(self, min_x, min_y, min_z, max_x, max_y, max_z):
		self.min_x = min_x
		self.min_y = min_y
		self.min_z = min_z
		self.max_x = max_x
		self.max_y = max_y
		self.max_z = max_z
		self.mins = [min_x, min_y, min_z]
		self.maxs = [max_x, max_y, max_z]
		
	def __add__(self, o):
		return AABB(self.min_x + o[0], self.min_y + o[1], self.min_z + o[2], \
					self.max_x + o[0], self.max_y + o[1], self.max_z + o[2])
	

	def __sub__(self, o):
		return AABB(self.min_x - o[0], self.min_y - o[1], self.min_z - o[2], \
					self.max_x - o[0], self.max_y - o[1], self.max_z - o[2])
					
	def __str__(self):
		return "AABB [%s, %s, %s : %s, %s, %s]" % (self.min_x, self.min_y, self.min_z, self.max_x, self.max_y, self.max_z)

	def __repr__(self):
		return self.__str__()

	@classmethod
	def from_player_coords(cls, xyz):
		x = xyz[0]
		y = xyz[1]
		z = xyz[2]
		return cls(x - config.PLAYER_BODY_EXTEND, y, z - config.PLAYER_BODY_EXTEND, \
				x + config.PLAYER_BODY_EXTEND, y + config.PLAYER_HEIGHT, z + config.PLAYER_BODY_EXTEND)

	@classmethod
	def from_block_coords(cls, xyz):
		return cls.from_player_coords((xyz[0] + 0.5, xyz[1], xyz[2] + 0.5))

	@classmethod
	def from_block_cube(cls, xyz):
		return cls(xyz[0], xyz[1], xyz[2], xyz[0] + 1, xyz[1] + 1, xyz[2] + 1)

	@property
	def bottom_center(self):
		return (self.posx, self.posy, self.posz)

	@property
	def center(self):
		return self.bottom_center

	def face(self, dx=0, dy=0, dz=0):
		if dx < 0:
			return AABB(self.min_x, self.min_y, self.min_z, self.min_x, self.max_y, self.max_z)
		elif dx > 0:
			return AABB(self.max_x, self.min_y, self.min_z, self.max_x, self.max_y, self.max_z)
		elif dy < 0:
			return AABB(self.min_x, self.min_y, self.min_z, self.max_x, self.min_y, self.max_z)
		elif dy > 0:
			return AABB(self.min_x, self.max_y, self.min_z, self.max_x, self.max_y, self.max_z)
		elif dz < 0:
			return AABB(self.min_x, self.min_y, self.min_z, self.max_x, self.max_y, self.min_z)
		elif dz > 0:
			return AABB(self.min_x, self.min_y, self.max_z, self.max_x, self.max_y, self.max_z)
		raise Exception("no face choosen in AABB")
		
	def collides(self, bb):
		for i in xrange(3):
			if fops.lte(self.maxs[i], bb.mins[i]) or fops.gte(self.mins[i],bb.maxs[i]):
				return False
		return True
		
	def collides_on_axes(self, bb, x=False, y=False, z=False):
		if not (x or y or z):
			raise Exception("axes not set in collides_on_axes")
		if x:
			if fops.lte(self.max_x, bb.min_x) or fops.gte(self.min_x, bb.max_x):
				return False
		if y:
			if fops.lte(self.max_y, bb.min_y) or fops.gte(self.min_y, bb.max_y):
				return False
		if z:
			if fops.lte(self.max_z, bb.min_z) or fops.gte(self.min_z, bb.max_z):
				return False
		return True

	def collision_distance(self, collidee, axis=None, direction=None):
		for i in xrange(3):
			if i == axis: continue
			if fops.lte(self.maxs[i], collidee.mins[i]) or fops.gte(self.mins[i], collidee.maxs[i]):
				return None
		p = None
		if direction < 0:
			if fops.eq(self.mins[axis], collidee.maxs[axis]):
				p = 0
			elif fops.gt(self.mins[axis], collidee.maxs[axis]):
				p = self.mins[axis] - collidee.maxs[axis]
		else:
			if fops.eq(collidee.mins[axis], self.maxs[axis]):
				p = 0
			elif fops.gt(collidee.mins[axis], self.maxs[axis]):
				p = collidee.mins[axis] - self.maxs[axis]
		return p

	def set_to(self, max_y=None):
		if max_y is None:
			raise Exception("AABB set_to wrong parameters")
		return AABB(self.min_x, self.min_y, self.min_z, self.max_x, max_y, self.max_z)
		
	def offset(self, dx=0, dy=0, dz=0):
		return AABB(self.min_x + dx,
					self.min_y + dy,
					self.min_z + dz,
					self.max_x + dx,
					self.max_y + dy,
					self.max_z + dz)

	def shift(self, min_x=None, min_y=None, min_z=None):
		return AABB(min_x if min_x is not None else self.min_x,
					min_y if min_y is not None else self.min_y,
					min_z if min_z is not None else self.min_z,
					self.max_x - self.min_x + min_x if min_x is not None else self.max_x,
					self.max_y - self.min_y + min_y if min_y is not None else self.max_y,
					self.max_z - self.min_z + min_z if min_z is not None else self.max_z)

	def extend_to(self, dx=0, dy=0, dz=0):
		return AABB(self.min_x if dx==0 or dx > 0 else self.min_x + dx,
					self.min_y if dy==0 or dy > 0 else self.min_y + dy,
					self.min_z if dz==0 or dz > 0 else self.min_z + dz,
					self.max_x if dx==0 or dx < 0 else self.max_x + dx,
					self.max_y if dy==0 or dy < 0 else self.max_y + dy,
					self.max_z if dz==0 or dz < 0 else self.max_z + dz)
		
	def expand(self, dx=0, dy=0, dz=0):
		return AABB(self.min_x - dx,
					self.min_y - dy,
					self.min_z - dz,
					self.max_x + dx,
					self.max_y + dy,
					self.max_z + dz)

	def union(self, bb):
		return AABB(self.min_x if self.min_x < bb.min_x else bb.min_x,
					self.min_y if self.min_y < bb.min_y else bb.min_y,
					self.min_z if self.min_z < bb.min_z else bb.min_z,
					self.max_x if self.max_x > bb.max_x else bb.max_x,
					self.max_y if self.max_y > bb.max_y else bb.max_y,
					self.max_z if self.max_z > bb.max_z else bb.max_z,)

	@property	
	def snap_to_grid(self):
		return AABB(*self.grid_box)

	@property	
	def grid_box(self):
		return [int(math.floor(self.min_x)),
				int(math.floor(self.min_y)),
				int(math.floor(self.min_z)),
				int(math.floor(self.max_x)),
				int(math.floor(self.max_y)),
				int(math.floor(self.max_z))]

	@property
	def grid_area(self):
		gbb = self.grid_box
		for x in xrange(gbb[0], gbb[3] + 1):
			for y in xrange(gbb[1], gbb[4] + 1):
				for z in xrange(gbb[2], gbb[5] + 1):
					yield x, y, z

	@property
	def posx(self):
		return (self.min_x + self.max_x) / 2.0

	@property
	def posy(self):
		return self.min_y

	@property
	def posz(self):
		return (self.min_z + self.max_z) / 2.0

	@property
	def grid_x(self):
		return tools.grid_shift(self.posx)

	@property
	def grid_y(self):
		return tools.grid_shift(self.posy)

	@property
	def grid_z(self):
		return tools.grid_shift(self.posz)

	def vector_to(self, bb):
		return bb.posx - self.posx, bb.posy - self.posy, bb.posz - self.posz

	def horizontal_vector_to(self, bb):
		return bb.min_x - self.min_x, 0, bb.min_z - self.min_z

	def distance_to(self, bb):
		x, y, z = self.vector_to(bb)
		return math.sqrt(x*x + y*y + z*z)

	def horizontal_distance_to(self, bb):
		x, _, z = self.vector_to(bb)
		return math.hypot(x, z)

	def vertical_distance_to(self, bb):
		_, y, _ = self.vector_to(bb)
		return abs(y)

	def horizontal_direction_to(self, bb):
		x, _, z = self.vector_to(bb)
		size = math.hypot(x, z)
		if fops.eq(size, 0):
			return (0, 0)
		return (x/size, z/size)

	def sweep_collision(self, collidee, v, debug=False):
		""" 
			self moving by v, collidee stationery 
			based on http://www.gamasutra.com/view/feature/3383/simple_intersection_tests_for_games.php?page=3	
		"""
		u_0 = [2, 2, 2]
		u_1 = [1, 1, 1]
		dists = [None, None, None]
		for i in xrange(3):
			if fops.lte(self.maxs[i], collidee.mins[i]) and fops.gt(v[i], 0):
				d = collidee.mins[i] - self.maxs[i]
				dists[i] = d
				u_0[i] = d / v[i]
			elif fops.lte(collidee.maxs[i], self.mins[i]) and fops.lt(v[i], 0):
				d = collidee.maxs[i] - self.mins[i]
				dists[i] = d
				u_0[i] = d / v[i]
			elif fops.eq(v[i], 0) and not(fops.lte(self.maxs[i], collidee.mins[i]) or fops.gte(self.mins[i],collidee.maxs[i])):
				u_0[i] = 0
			elif not(fops.lte(self.maxs[i], collidee.mins[i]) or fops.gte(self.mins[i],collidee.maxs[i])):
				u_0[i] = 0
			if fops.gte(collidee.maxs[i], self.mins[i]) and fops.gt(v[i], 0):
				d = collidee.maxs[i] - self.mins[i]
				u_1[i] = d / v[i]
			elif fops.gte(self.maxs[i], collidee.mins[i]) and fops.lt(v[i], 0):
				d = collidee.mins[i] - self.maxs[i]
				u_1[i] = d / v[i]
		
		if max(u_0) == 2:
			u0 = None
			col = False
		else:
			u0 = max(u_0)
			u1 = min(u_1)
			if fops.gte(u0, 1.0):
				col = False
			else:
				col = fops.lte(u0, u1)
		return col, u0

	def calculate_axis_offset(self, collidee, d, axis):
		for i in xrange(3):
			if i == axis: continue
			if fops.lte(self.maxs[i], collidee.mins[i]) or fops.gte(self.mins[i], collidee.maxs[i]):
				return d
		if d < 0 and fops.lte(collidee.maxs[axis], self.mins[axis]):
			dout = collidee.maxs[axis] - self.mins[axis]
			if fops.gt(dout, d):
				d = dout
		elif d > 0 and fops.gte(collidee.mins[axis], self.maxs[axis]):
			dout = collidee.mins[axis] - self.maxs[axis]
			if fops.lt(dout, d):
				d = dout
		return d

	def intersection_on_axes(self, bb, x=False, y=False, z=False, debug=False):
		if not (x or y or z):
			raise Exception("axes not set in collides_on_axes")
		truth = 0
		if x: truth += 1
		if y: truth += 1
		if z: truth += 1
		if truth != 2:
			raise Exception("set exactly two axes to True in collides_on_axes")
		inter = []
		if x:
			if fops.lte(self.max_x, bb.min_x) or fops.gte(self.min_x, bb.max_x):
				return None
			else:
				min_x = self.min_x if self.min_x > bb.min_x else bb.min_x
				max_x = self.max_x if self.max_x < bb.max_x else bb.max_x
		else:
			min_x = self.min_x
			max_x = self.max_x
		if y:
			if fops.lte(self.max_y, bb.min_y) or fops.gte(self.min_y, bb.max_y):
				return None
			else:
				min_y = self.min_y if self.min_y > bb.min_y else bb.min_y
				max_y = self.max_y if self.max_y < bb.max_y else bb.max_y
		else:
			min_y = self.min_y
			max_y = self.max_y
		if z:
			if fops.lte(self.max_z, bb.min_z) or fops.gte(self.min_z, bb.max_z):
				return None
			else:
				min_z = self.min_z if self.min_z > bb.min_z else bb.min_z
				max_z = self.max_z if self.max_z < bb.max_z else bb.max_z
		else:
			min_z = self.min_z
			max_z = self.max_z
		return AABB(min_x, min_y, min_z, max_x, max_y, max_z)

	def get_side(self, which=None, x=False, y=False, z=False):
		if which is None:
			raise Exception('aabb get_side type not choosen')
		mx = self.max_x - self.min_x
		my = self.max_y - self.min_y
		mz = self.max_z - self.min_z
		if not x:
			if which == 'max':
				return my if my > mz else mz
			else:
				return my if my < mz else mz
		elif not y:
			if which == 'max':
				return mx if mx > mz else mz
			else:
				return mx if mx < mz else mz
		elif not z:
			if which == 'max':
				return mx if mx > my else my
			else:
				return mx if mx < my else my

	def inside_plane_to(self, bb, aabb_center, debug=False):
		center = (aabb_center[0], aabb_center[2])
		lines = []
		lines.append(Line(bb.min_x, bb.min_z, self.min_x, self.min_z, 'min min', debug=debug))
		lines.append(Line(bb.max_x, bb.min_z, self.max_x, self.min_z, 'max min', debug=debug))
		lines.append(Line(bb.max_x, bb.max_z, self.max_x, self.max_z, 'max max', debug=debug))
		lines.append(Line(bb.min_x, bb.max_z, self.min_x, self.max_z, 'min max', debug=debug))
		this_center = (self.posx, self.posz)
		ds = [(line.distance_to(this_center), line) for line in lines]
		lsorted = sorted(ds, key=lambda el: el[0])
		line1 = lsorted[-1][1]
		line2 = lsorted[-2][1]
		#line1.set_direction_towards(this_center, debug=debug)
		#line2.set_direction_towards(this_center, debug=debug)
		width = line1.distance_parallel(line2)  # / 3.0 * 2
		is_inside = fops.lte(line1.distance_to(center), width) and fops.lte(line2.distance_to(center), width)
		return is_inside

	def on_trajectory_to(self, bb, center, debug=False):
		line = Line(bb.posx, bb.posz, self.posx, self.posz)
		return line.has_point(center)


class Line(object):
	def __init__(self, a1, b1, a2, b2, name=None, debug=False):
		self.name = name
		self.a1 = a1
		self.b1 = b1
		self.a2 = a2
		self.b2 = b2
		self.a = a1 - a2
		self.b = b1 - b2
		self.length = math.hypot(self.a, self.b)

	def __str__(self):
		return "%s a %s b %s L %s" % (self.a, self.b, self.name, self.length)

	def __repr__(self):
		return self.__str__()

	def has_point(self, p):
		return fops.eq(abs(self.a), abs(self.a1 - p[0])) and fops.eq(abs(self.b), abs(self.b1 - p[1]))

	def set_direction_towards(self, point, debug=False):
		if fops.lt(self.distance_to(point), 0):
			self.a *= -1
			self.b *= -1

	def distance_to(self, point):
		return abs(self.a * (self.b1 - point[1]) - (self.a1 - point[0]) * self.b) / self.length

	def distance_parallel(self, line):
		return abs(self.a * (self.b1 - line.b1) - (self.a1 -line.a1) * self.b) / self.length



