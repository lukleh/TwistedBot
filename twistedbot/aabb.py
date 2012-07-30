
import config

from math import floor

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
		self._grid_coords = None
		
	def __add__(self, o):
		return AABB(self.min_x + o[0], self.min_y + o[1], self.min_z + o[2], \
					self.max_x + o[0], self.max_y + o[1], self.max_z + o[2])
	

	def __sub__(self, o):
		return AABB(self.min_x - o[0], self.min_y - o[1], self.min_z - o[2], \
					self.max_x - o[0], self.max_y - o[1], self.max_z - o[2])
					
	def __str__(self):
		return "AABB [%s, %s, %s : %s, %s, %s]" % (self.min_x, self.min_y, self.min_z, self.max_x, self.max_y, self.max_z)

	@classmethod
	def from_player_coords(cls, xyz):
		x = xyz[0]
		y = xyz[1]
		z = xyz[2]
		return cls(x - config.PLAYER_BODY_EXTEND, y, z - config.PLAYER_BODY_EXTEND, \
				x + config.PLAYER_BODY_EXTEND, y + config.PLAYER_HEIGHT, z + config.PLAYER_BODY_EXTEND)

	def collision(self, bb):
		for i in xrange(3):
			if self.maxs[i] < bb.mins[i] or self.mins[i] > bb.maxs[i]:
				return False
		return True

	def collision_distance(self, collidee, dx=None, dy=None, dz=None):
		if dx is not None:
			axis = 0
			direction = dx
		elif dy is not None:
			axis = 1
			direction = dy
		elif dz is not None:
			axis = 2
			direction = dz
		else:
			raise Exception("direction for colllision distance is wrong: %s" % str((dx, dy, dz)))
		for i in xrange(3):
			if i == axis: continue
			if self.maxs[i] < collidee.mins[i] or self.mins[i] > collidee.maxs[i]:
				return None
		d = None
		if direction < 0:
			if self.mins[axis] > collidee.maxs[axis]:
				d = self.mins[axis] - collidee.maxs[axis]
		else:
			if collidee.mins[axis] > self.maxs[axis]:
				d = collidee.mins[axis] - self.maxs[axis]:
		return d
		
	def distance_from(self, B, on_axis=None):
		ds = [None, None, None]
		for i in xrange(3):
			if self.maxs[i] < B.mins[i]:
				ds[i] = B.mins[i] - self.maxs[i]
			elif self.mins[i] > B.maxs[i]:
				ds[i] = self.mins[i] - B.maxs[i]
		if on_axis is not None:
			return ds[on_axis]
		d  = None
		for s in ds:
			if s is not None and (d is None or s < d):
				d = s
		return d
		
	def shift(self, dx=0, dy=0, dz=0):
		self.min_x += dx
		self.max_x += dx
		self.min_y += dy
		self.max_y += dy
		self.min_z += dz
		self.max_z += dz
		self._grid_coords = None

	def extend_to(self, dx=0, dy=0, dz=0):
		return AABB(self.min_x if dx==0 or dx > 0 else self.min_x + dx,
					self.min_y if dy==0 or dy > 0 else self.min_y + dy,
					self.min_z if dz==0 or dz > 0 else self.min_z + dz,
					self.max_x if dx==0 or dx < 0 else self.max_x + dx,
					self.max_y if dy==0 or dy < 0 else self.max_y + dy,
					self.max_z if dz==0 or dz < 0 else self.max_z + dz)
		
	@property	
	def grid_box(self):
		if self._grid_coords is None:
			self._grid_coords = [
					int(floor(self.min_x)),
					int(self.min_y),
					int(floor(self.min_z)),
					int(floor(self.max_x)),
					int(self.max_y),
					int(floor(self.max_z))]
		return self._grid_coords

	@property
	def grid_corners(self):
		gbb = self.grid_box
		for x in xrange(gbb[0], gbb[3] + 1):
			for y in xrange(gbb[1], gbb[4] + 1):
				for z in xrange(gbb[2], gbb[5] + 1):
					yield (x, y, z)


def sweep_col(B, A, v):
	""" 
		Dead code now...
		B moving, A stationery 
		http://www.gamasutra.com/view/feature/3383/simple_intersection_tests_for_games.php?page=3	
	"""
	u_0 = [0, 0, 0]
	u_1 = [1, 1, 1]
	dists = [None, None, None]
	for i in xrange(3):
		if A[1][i] < B[0][i] and v[i] < 0:
			d = A[1][i] - B[0][i]
			dists[i] = d
			u_0[i] = d / v[i]
		elif B[1][i] < A[0][i] and v[i] > 0:
			d = A[0][i] - B[1][i]
			dists[i] = d
			u_0[i] = d / v[i]
			u_0[i] = (A[0][i] - B[1][i]) / v[i]
		
		if B[1][i] > A[0][i] and v[i] < 0:
			u_1[i] = (A[0][i] - B[1][i]) / v[i]
		elif A[1][i] > B[0][i] and v[i] > 0:
			u_1[i] = (A[1][i] - B[0][i]) / v[i]
	u0 = max(u_0)
	u1 = min(u_1)
	col = u0 <= u1
	if col:
		axis = u_0.index(u0)
		return col, axis, dists[axis], u0
	else:
		return col, None, None, None


